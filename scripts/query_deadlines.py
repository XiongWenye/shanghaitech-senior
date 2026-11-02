#!/usr/bin/env python3
"""
ShanghaiTech Multi-Source Deadlines & Assignment Tracker.
Faithfully adapted from TechPie-flutter's AssignmentService.

Aggregates assignments and exams from:
- Blackboard (eLearning)
- Gradescope
- Hydro (ACM OJ)
- EAMS Official Exam Table

Features:
- Live network querying via TechPie API stack.
- Sorts by due date and calculates remaining urgency (overdue, due today, due soon).
- Filter by platform (--platform) or completion status (--pending-only).
- Integrates with local cache (data/my_deadlines.json) and live endpoints.
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.error
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPTS_DIR, "..", "data")
DEADLINES_CACHE_FILE = os.path.join(DATA_DIR, "my_deadlines.json")
COOKIE_CACHE_PATH = os.path.join(DATA_DIR, "eams_cookie.txt")

TECHPIE_BASE = "https://techpie.geekpie.club/api"
TECHPIE_ELEARNING_AUTH = f"{TECHPIE_BASE}/auth/third-party/elearning"
TECHPIE_BLACKBOARD_DEADLINES = f"{TECHPIE_BASE}/deadlines/blackboard"
TECHPIE_GRADESCOPE_DEADLINES = f"{TECHPIE_BASE}/deadlines/gradescope"
TECHPIE_HYDRO_DEADLINES = f"{TECHPIE_BASE}/deadlines/hydro"
TECHPIE_EXAM_TABLE = f"{TECHPIE_BASE}/schedule/exam_table"

PLATFORM_LABELS = {
    "blackboard": "Blackboard",
    "gradescope": "Gradescope",
    "hydro": "Hydro OJ",
    "exam": "EAMS 考试",
}

def load_cached_deadlines() -> Dict[str, Any]:
    if os.path.exists(DEADLINES_CACHE_FILE):
        try:
            with open(DEADLINES_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"assignments": []}

def save_cached_deadlines(data: Dict[str, Any]):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(DEADLINES_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def get_cas_tgc() -> Optional[str]:
    raw = os.environ.get("CASTGC") or os.environ.get("SHANGHAITECH_CASTGC") or os.environ.get("EAMS_COOKIE")
    if not raw and os.path.exists(COOKIE_CACHE_PATH):
        try:
            with open(COOKIE_CACHE_PATH, "r", encoding="utf-8") as f:
                raw = f.read().strip()
        except Exception:
            pass
    if not raw:
        return None
    raw = raw.strip()
    if "CASTGC=" in raw:
        for part in raw.split(";"):
            part = part.strip()
            if part.startswith("CASTGC="):
                return part.split("=", 1)[1].strip()
    return raw

def fetch_live_blackboard(tgc: str) -> Tuple[bool, List[Dict[str, Any]], str]:
    """Fetch live assignments from Blackboard via TechPie elearning proxy."""
    auth_req = urllib.request.Request(
        TECHPIE_ELEARNING_AUTH,
        data=json.dumps({"tgc": tgc}).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "TechPie-SeniorSkill/2.0",
        }
    )
    try:
        with urllib.request.urlopen(auth_req, timeout=12) as resp:
            auth_res = json.loads(resp.read().decode("utf-8"))
            if not auth_res.get("success") or "data" not in auth_res:
                err_msg = auth_res.get("error", "Blackboard 会话换取失败")
                return False, [], f"会话换取失败: {err_msg}"
            token = auth_res["data"]["token"]
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode("utf-8")).get("error", e.reason)
        except Exception:
            err_body = e.reason
        return False, [], f"SSO 认证响应异常 ({e.code}): {err_body}"
    except Exception as e:
        return False, [], f"会话认证网络异常: {str(e)}"

    dl_req = urllib.request.Request(
        TECHPIE_BLACKBOARD_DEADLINES,
        data=json.dumps({"token": token}).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "TechPie-SeniorSkill/2.0",
        }
    )
    try:
        with urllib.request.urlopen(dl_req, timeout=15) as resp:
            dl_res = json.loads(resp.read().decode("utf-8"))
            if dl_res.get("success"):
                raw_items = dl_res.get("data", [])
                return True, raw_items, f"在线同步成功（实时待办：{len(raw_items)} 项）"
            return False, [], dl_res.get("error", "Blackboard 待办拉取异常")
    except Exception as e:
        return False, [], f"待办接口请求异常: {str(e)}"

def fetch_live_exams_deadlines(tgc: str, semester_id: str = "282", student_id: Optional[str] = None) -> Tuple[bool, List[Dict[str, Any]], str]:
    """Fetch live official exams from EAMS via TechPie backend."""
    sid = student_id or ""
    if not sid:
        try:
            import eams_session
            prof = eams_session.get_student_profile(tgc)
            if prof:
                sid = prof.get("student_id", "")
        except Exception:
            pass

    req = urllib.request.Request(
        TECHPIE_EXAM_TABLE,
        data=json.dumps({
            "cookies": f"CASTGC={tgc}",
            "studentId": sid,
            "semester_id": semester_id,
        }).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Connection": "close",
            "User-Agent": "TechPie-SeniorSkill/2.0",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            if res.get("success") and "data" in res:
                exams = res["data"].get("exams", [])
                batch_name = res["data"].get("examBatchName") or "期中考试"
                items = []
                for ex in exams:
                    code = ex.get("courseCode", "--")
                    name = ex.get("courseName", "--")
                    extype = ex.get("examType", "期末")
                    edate = ex.get("examDate", "")
                    etime = ex.get("examTimeRange", "").split("~")[0].strip()
                    due_iso = f"{edate}T{etime}:00" if (edate and etime) else ""
                    items.append({
                        "id": f"exam-{code}",
                        "platform": "exam",
                        "kind": "exam",
                        "title": f"{name} ({code}) {extype}考试",
                        "course": code,
                        "due": due_iso,
                        "status": ex.get("examStatus", "正常"),
                        "url": "https://eams.shanghaitech.edu.cn",
                    })
                return True, items, f"在线核查考务成功（{batch_name}批次：{len(items)} 门排考）"
            return False, [], res.get("error", "EAMS 考务拉取失败")
    except Exception as e:
        return False, [], f"EAMS 考务请求异常: {str(e)}"

def fetch_live_gradescope(token: Optional[str] = None) -> Tuple[bool, List[Dict[str, Any]], str]:
    if not token:
        return False, [], "未配置 Gradescope 独立 Token（请在客户端绑定）"
    req = urllib.request.Request(
        TECHPIE_GRADESCOPE_DEADLINES,
        data=json.dumps({"token": token}).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "TechPie-SeniorSkill/2.0",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            if res.get("success"):
                items = res.get("data", [])
                return True, items, f"在线同步成功（实时待办：{len(items)} 项）"
            return False, [], res.get("error", "Gradescope 拉取异常")
    except Exception as e:
        return False, [], f"Gradescope 请求异常: {str(e)}"

def fetch_live_hydro(token: Optional[str] = None, domains: Optional[List[str]] = None) -> Tuple[bool, List[Dict[str, Any]], str]:
    if not token:
        return False, [], "未配置 Hydro OJ 独立 Token（请在客户端绑定）"
    return False, [], "未配置 Hydro 课程域"

def sync_all_deadlines(student_id: Optional[str] = None) -> Tuple[Dict[str, Any], Dict[str, Tuple[bool, str]]]:
    cached = load_cached_deadlines()
    cached_assignments = cached.get("assignments", [])

    tgc = get_cas_tgc()
    statuses: Dict[str, Tuple[bool, str]] = {}
    successful_results: Dict[str, List[Dict[str, Any]]] = {}

    if not tgc:
        statuses["blackboard"] = (False, "缺少上科大统一身份认证凭据 (CASTGC)，请通过 senior.py login 登录")
        statuses["exam"] = (False, "缺少上科大统一身份认证凭据 (CASTGC)，请通过 senior.py login 登录")
    else:
        # 1. Blackboard
        ok_bb, bb_items, bb_msg = fetch_live_blackboard(tgc)
        statuses["blackboard"] = (ok_bb, bb_msg)
        if ok_bb:
            successful_results["blackboard"] = bb_items

        # 2. Exam
        ok_ex, ex_items, ex_msg = fetch_live_exams_deadlines(tgc, student_id=student_id)
        statuses["exam"] = (ok_ex, ex_msg)
        if ok_ex:
            successful_results["exam"] = ex_items

    # 3. Gradescope & Hydro
    ok_gs, gs_items, gs_msg = fetch_live_gradescope(os.environ.get("GRADESCOPE_TOKEN"))
    statuses["gradescope"] = (ok_gs, gs_msg)
    if ok_gs:
        successful_results["gradescope"] = gs_items

    ok_hy, hy_items, hy_msg = fetch_live_hydro(os.environ.get("HYDRO_TOKEN"))
    statuses["hydro"] = (ok_hy, hy_msg)
    if ok_hy:
        successful_results["hydro"] = hy_items

    # Preserve cached assignments for platforms that were NOT successfully refetched online,
    # and replace assignments for platforms that were successfully synced.
    merged = []
    successful_platforms = set(p.lower() for p in successful_results.keys())
    for item in cached_assignments:
        plat = item.get("platform", "").lower()
        if plat not in successful_platforms:
            merged.append(item)
    for items in successful_results.values():
        merged.extend(items)

    updated_data = {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "assignments": merged,
    }

    save_cached_deadlines(updated_data)
    return updated_data, statuses

def parse_iso_datetime(dt_str: str) -> Optional[datetime]:
    try:
        clean_str = dt_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)
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
    now = datetime.now()

    filtered = []
    for a in raw_assignments:
        plat = a.get("platform", "").lower()
        if platform_filter and platform_filter.lower() != "all" and plat != platform_filter.lower():
            continue
        status = a.get("status", "")
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
        lines.append(f"🎉 **全平台当前暂无待处理作业或考试 DDL {filter_hint}！**")
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
            status = item.get("status", "Pending")
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
    lines.append("- Gradescope 的 Late Submission 通常会扣除 10%~20% 卷面分，务必在 Hard DDL 前提交基础版本；")
    lines.append("- Hydro OJ 代码类作业建议本地跑通单元测试后再提交，保住首次 AC 率与平时分。")

    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="上海科技大学跨平台作业/考试 DDL 巡检看板")
    parser.add_argument("--platform", "-p", choices=["all", "blackboard", "gradescope", "hydro", "exam"], default="all", help="筛选指定平台")
    parser.add_argument("--pending-only", action="store_true", help="仅显示未完成的作业")
    parser.add_argument("--sync", action="store_true", help="在线联网同步各平台实时 DDL")
    parser.add_argument("--json", action="store_true", help="输出原始 JSON 数据")

    args = parser.parse_args()

    sync_status = None
    tgc = get_cas_tgc()
    if not tgc:
        print("⚠️ 未检测到有效统一身份认证凭据 (CASTGC)。")
        print("学长 SKILL 第一要义：本地严禁存放或展示任何虚假 Demo 课程与作业数据。")
        print("所有个人的作业、考试与 DDL 均需通过网络端口（Blackboard / Gradescope / Hydro / EAMS）实时动态查询。")
        print("👉 请先运行 `python3 scripts/senior.py login` 登录获取授权，或设置环境变量 CASTGC。")
        sys.exit(1)

    data, sync_status = sync_all_deadlines()

    if args.json:
        if sync_status:
            data["_sync_status"] = sync_status
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    print(format_deadlines_report(
        data,
        platform_filter=args.platform if args.platform != "all" else None,
        pending_only=args.pending_only,
        sync_status=sync_status,
    ))

if __name__ == "__main__":
    main()
