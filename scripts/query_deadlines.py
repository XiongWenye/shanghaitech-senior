#!/usr/bin/env python3
"""Query fresh Blackboard, Gradescope, Hydro and official EAMS deadlines in memory."""
import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote, urlparse
from live_session import (LiveQueryError, SHANGHAI, derive_cookies, get_tgc,
                          post_json, queried_at, request_login)

PLATFORM_LABELS = {"blackboard": "Blackboard", "gradescope": "Gradescope", "hydro": "Hydro OJ", "exam": "EAMS 考试"}


def get_cas_tgc():
    return get_tgc()


def _fetch_assignments(path, payload, platform):
    try:
        items = post_json(path, payload)
        if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
            raise LiveQueryError(f"{platform}: 返回的待办列表格式无效")
        return True, [{**item, "platform": platform} for item in items], f"实时查询成功（{len(items)} 项）"
    except LiveQueryError as error:
        return False, [], str(error)


def fetch_live_blackboard(tgc):
    try:
        token = derive_cookies("elearning", tgc)
    except LiveQueryError as error:
        return False, [], str(error)
    return _fetch_assignments("/deadlines/blackboard", {"token": token}, "blackboard")


def fetch_live_gradescope(token=None):
    if not token:
        return False, [], "未配置当前进程的 GRADESCOPE_TOKEN，待办状态未知"
    return _fetch_assignments("/deadlines/gradescope", {"token": token}, "gradescope")


def fetch_live_hydro(token=None, domains=None):
    if not token:
        return False, [], "未配置当前进程的 HYDRO_TOKEN，待办状态未知"
    domains = domains or [d.strip() for d in os.environ.get("HYDRO_DOMAINS", "").split(",") if d.strip()]
    if not domains:
        return False, [], "未配置 HYDRO_DOMAINS 课程域，待办状态未知"
    origin = os.environ.get("HYDRO_ORIGIN", "https://acm.shanghaitech.edu.cn").rstrip("/")
    parsed = urlparse(origin)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        return False, [], "HYDRO_ORIGIN 必须是有效 HTTPS 站点地址"
    items = []
    for domain in domains:
        ok, rows, message = _fetch_assignments("/deadlines/hydro", {
            "token": token, "args": {"url": origin + "/d/" + quote(domain, safe="")}}, "hydro")
        if not ok:
            return False, [], f"Hydro 部分课程域查询失败：{message}"
        items.extend(rows)
    return True, items, f"实时查询成功（{len(domains)} 个课程域，{len(items)} 项）"


def fetch_live_exams_deadlines(cookie=None, semester_id=""):
    from query_exams import fetch_live_exams
    try:
        data = fetch_live_exams(cookie, semester_id)
    except LiveQueryError as error:
        return False, [], str(error)
    items = []
    for index, exam in enumerate(data["exams"]):
        edate = exam.get("examDate", "")
        etime = exam.get("examTimeRange", "").replace("～", "~").split("~")[0].strip()
        due = f"{edate}T{etime}" if edate and etime else ""
        items.append({"id": f"exam-{index}", "platform": "exam", "kind": "exam",
                      "title": exam.get("courseName", "未提供名称"), "course": exam.get("courseCode", ""),
                      "due": due, "status": exam.get("examStatus", ""), "url": "https://eams.shanghaitech.edu.cn"})
    return True, items, f"实时查询成功（{len(items)} 项官方排考）"


def sync_all_deadlines(platform="all"):
    selected = list(PLATFORM_LABELS) if platform == "all" else [platform]
    assignments, statuses = [], {}
    for name in selected:
        if name == "blackboard":
            tgc = get_cas_tgc()
            if not tgc:
                request_login("Blackboard 缺少 CASTGC 凭据")
            result = fetch_live_blackboard(tgc) if tgc else (False, [], "缺少当前进程的 CASTGC 凭据，待办状态未知")
        elif name == "exam":
            result = fetch_live_exams_deadlines()
        elif name == "gradescope":
            result = fetch_live_gradescope(os.environ.get("GRADESCOPE_TOKEN"))
        else:
            result = fetch_live_hydro(os.environ.get("HYDRO_TOKEN"))
        ok, rows, message = result
        statuses[name] = (ok, message)
        if ok:
            assignments.extend(rows)
    return {"updated_at": queried_at(), "source": "实时网络查询", "assignments": assignments,
            "complete": all(ok for ok, _ in statuses.values())}, statuses


def parse_iso_datetime(dt_str: str) -> Optional[datetime]:
    try:
        if isinstance(dt_str, (int, float)) or isinstance(dt_str, str) and dt_str.isdigit():
            return datetime.fromtimestamp(float(dt_str), SHANGHAI).replace(tzinfo=None)
        clean_str = dt_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is not None:
            dt = dt.astimezone(SHANGHAI).replace(tzinfo=None)
        return dt
    except Exception:
        return None

def get_urgency_badge(due_dt: Optional[datetime], now: datetime, submitted: bool) -> str:
    if submitted:
        return "✅ 已提交"
    if not due_dt:
        return "📅 未定"
    diff = due_dt - now
    total_seconds = diff.total_seconds()
    
    if total_seconds < 0:
        return "🚨 已逾期"
    elif total_seconds <= 86400:
        hours = max(1, int(total_seconds // 3600))
        return f"🔥 仅剩 {hours}h"
    elif total_seconds <= 86400 * 3:
        days = int(total_seconds // 86400)
        return f"⏳ 还剩 {days} 天"
    else:
        days = int(total_seconds // 86400)
        return f"📘 {days} 天后"

def format_deadlines_report(
    data: Dict[str, Any],
    platform_filter: Optional[str] = None,
    pending_only: bool = False,
    sync_status: Optional[Dict[str, Tuple[bool, str]]] = None,
) -> str:
    raw_assignments = data.get("assignments", [])
    updated_at = data.get("updated_at", "")
    now = datetime.now(SHANGHAI).replace(tzinfo=None)

    filtered = []
    for a in raw_assignments:
        plat = a.get("platform", "").lower()
        if platform_filter and platform_filter.lower() != "all" and plat != platform_filter.lower():
            continue
        status = a.get("status") or ""
        is_submitted = status.lower() in ["submitted", "graded", "已提交"]
        if pending_only and is_submitted:
            continue
        filtered.append(a)

    def sort_key(item):
        d = parse_iso_datetime(item.get("due", ""))
        return d if d else datetime.max

    filtered.sort(key=sort_key)

    lines = [
        "## ⏱️ 上科大跨平台 Deadline 巡检看板 (Blackboard / Gradescope / Hydro / EAMS)",
        f"**巡检更新时间**：`{updated_at}` | **待办总数**：`{len(filtered)}` 项",
        "",
    ]

    if sync_status:
        lines.append("### 🌐 跨平台真实联网查询状态")
        for plat_key in ["blackboard", "exam", "gradescope", "hydro"]:
            label = PLATFORM_LABELS.get(plat_key, plat_key)
            if plat_key in sync_status:
                ok, msg = sync_status[plat_key]
                icon = "🟢" if ok else ("⚪" if "未配置" in msg else "🔴")
                lines.append(f"- **{label}**：{icon} {msg}")
        lines.append("")

    if not filtered:
        filter_hint = f"（筛选平台：{platform_filter}）" if platform_filter else ""
        if sync_status and any(not ok for ok, _ in sync_status.values()):
            lines.append("本次已成功查询的来源中暂无匹配 DDL；部分来源查询失败或缺少凭据，完整待办状态未知。")
        else:
            lines.append(f"本次成功查询的来源中暂无匹配 DDL {filter_hint}。")
    else:
        lines.extend([
            "| 紧急度 | 平台 | 课程 | 作业 / 考试任务 | 截止时间 (DDL) | 状态 | 平台链接 |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ])
        for item in filtered:
            plat = item.get("platform", "other").lower()
            plat_label = PLATFORM_LABELS.get(plat, plat.capitalize())
            course = item.get("course", "--")
            title = item.get("title", "--")
            due_str = item.get("due", "--")
            status = item.get("status") or "未提供"
            url = item.get("url", "")
            
            due_dt = parse_iso_datetime(due_str)
            is_submitted = status.lower() in ["submitted", "graded", "已提交"]
            badge = get_urgency_badge(due_dt, now, is_submitted)

            due_display = due_dt.strftime("%m-%d %H:%M") if due_dt else due_str
            late_due_str = item.get("lateDue")
            if late_due_str and plat == "gradescope":
                late_dt = parse_iso_datetime(late_due_str)
                if late_dt:
                    due_display += f" *(Late: {late_dt.strftime('%m-%d %H:%M')})*"

            link_str = f"[打开]({url})" if url else "--"
            lines.append(f"| **{badge}** | `{plat_label}` | {course} | **{title}** | `{due_display}` | {status} | {link_str} |")

    lines.append("")
    lines.append("💡 **老学长护肝提分建议**：")
    lines.append("- Gradescope 的迟交时限与扣分规则以课程实际公告为准；")
    lines.append("- Hydro OJ 代码类作业建议本地跑通单元测试后再提交，保住首次 AC 率与平时分。")

    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="实时多源 DDL 查询；失败来源状态未知，不读取旧记录")
    parser.add_argument("--platform", "-p", choices=["all", *PLATFORM_LABELS], default="all")
    parser.add_argument("--pending-only", action="store_true")
    parser.add_argument("--sync", action="store_true", help="兼容参数；每次查询均实时联网")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    data, statuses = sync_all_deadlines(args.platform)
    if args.pending_only:
        data["assignments"] = [item for item in data["assignments"]
                               if str(item.get("status") or "").lower() not in ("submitted", "graded", "已提交")]
    if args.json:
        print(json.dumps({**data, "_sync_status": statuses}, ensure_ascii=False, indent=2))
    else:
        print(format_deadlines_report(data, platform_filter=args.platform, pending_only=args.pending_only, sync_status=statuses))
    if not data["complete"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
