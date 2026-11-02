#!/usr/bin/env python3
"""
ShanghaiTech Student Activity & Lecture Check-in Tracker (xshdapp).
Adapted from TechPie-flutter's EgateAppService.

Features:
- Track student activity sign-in records (academic lectures, humanities workshops, sports).
- Calculate lecture attendance progress towards graduation general education requirement.
- Online query via TechPie / eGate API with session cookie or offline cache.
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.error
from datetime import datetime
from typing import List, Dict, Optional, Any

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPTS_DIR, "..", "data")
ACTIVITIES_CACHE_FILE = os.path.join(DATA_DIR, "my_activities.json")

def sync_activities_from_techpie(tgc: Optional[str] = None, student_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetch real activity history from TechPie backend using CASTGC session derivation."""
    if not tgc:
        cookie_path = os.path.join(DATA_DIR, "eams_cookie.txt")
        if os.path.exists(cookie_path):
            try:
                with open(cookie_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if "CASTGC=" in content:
                        tgc = content.split("CASTGC=", 1)[1].split(";", 1)[0].strip()
                    else:
                        tgc = content
            except Exception:
                pass
    if not tgc:
        return None

    if not student_id:
        plan_path = os.path.join(DATA_DIR, "my_plan_completion.json")
        if os.path.exists(plan_path):
            try:
                with open(plan_path, "r", encoding="utf-8") as f:
                    p = json.load(f)
                    student_id = p.get("student_id")
            except Exception:
                pass
    if not student_id:
        try:
            import eams_session
            prof = eams_session.get_student_profile(tgc)
            if prof:
                student_id = prof.get("student_id")
        except Exception:
            pass
    if not student_id:
        return None

    # 1. Exchange TGC for egate-app derived cookies
    auth_url = "https://techpie.geekpie.club/api/auth/third-party/egate-app"
    try:
        req = urllib.request.Request(
            auth_url,
            data=json.dumps({"tgc": tgc}).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "TechPie-SeniorSkill/2.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            auth_res = json.loads(resp.read().decode("utf-8"))
            if not auth_res.get("success") or "data" not in auth_res:
                return None
            cookies = auth_res["data"]["token"]
    except Exception:
        return None

    # 2. Query egate-app/history
    hist_url = "https://techpie.geekpie.club/api/egate-app/history"
    try:
        req2 = urllib.request.Request(
            hist_url,
            data=json.dumps({"studentId": student_id, "cookies": cookies}).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "TechPie-SeniorSkill/2.0"}
        )
        with urllib.request.urlopen(req2, timeout=10) as resp2:
            hdata = json.loads(resp2.read().decode("utf-8"))
            if not hdata.get("success"):
                return None
            rows = hdata.get("data", {}).get("rows", [])
    except Exception:
        return None

    # 3. Format into standardized activity objects
    mapped_activities = []
    for r in rows:
        name = r.get("HDMC", "--")
        atype = r.get("HDLX_DISPLAY", "形势与政策课程讲座")
        rcqd = r.get("RCQD")
        lcqd = r.get("LCQD")
        sqrq = r.get("SQRQ")
        date_val = sqrq or (rcqd.split(" ")[0] if rcqd else None) or "--"
        is_signed = bool(rcqd or lcqd)
        status = "已核销打卡" if is_signed else r.get("HDZT_DISPLAY", "未签到")
        mapped_activities.append({
            "wid": r.get("WID", ""),
            "activityName": name,
            "typeDisplay": atype,
            "statusDisplay": status,
            "date": date_val,
            "creditCounted": is_signed,
            "rcqd": rcqd,
            "lcqd": lcqd,
            "academicYear": r.get("XN_DISPLAY", ""),
        })

    # Sort descending by check-in time / date
    mapped_activities.sort(key=lambda x: x.get("rcqd") or x.get("date") or "", reverse=True)

    result_data = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "studentId": student_id,
        "studentName": rows[0].get("XM", "") if rows else "",
        "requiredLectures": 24,
        "requiredXingce": 24,
        "activities": mapped_activities
    }

    try:
        with open(ACTIVITIES_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return result_data

def load_cached_activities() -> Dict[str, Any]:
    if os.path.exists(ACTIVITIES_CACHE_FILE):
        try:
            with open(ACTIVITIES_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"activities": []}

def format_activities_report(data: Dict[str, Any], filter_type: Optional[str] = None) -> str:
    activities = data.get("activities", [])
    student_id = data.get("studentId", "未绑定学号")
    required = data.get("requiredXingce") or data.get("requiredLectures") or 24
    updated_at = data.get("updated_at", "")

    if not activities:
        return (
            "## ⚠️ 上科大学生活动（xshdapp）打卡记录查询未果\n"
            f"- **学号**：`{student_id}`\n"
            "- **状态**：当前未能拉取到有效的学生活动与形策讲座签到流水记录。\n"
            "- **技术原因排查**：\n"
            "  1. 本地统一身份认证凭据 (`CASTGC`) 可能已过期，可运行 `python3 scripts/senior.py login` 重新获取凭据；\n"
            "  2. 离线环境下暂无本地缓存，或网络通信受限；\n"
            "- **事实诚信铁律**：严禁在未查询到权威数据时编造任何虚构讲座名称、日期或考核状态！\n"
            "👉 **权威核对渠道**：请直接在手机端打开 **TechPie App（首页功能网格 ->【学生活动】/【校园签到】）** 查看实时核销历史。"
        )

    completed_count = len([a for a in activities if a.get("creditCounted", True) and "已" in a.get("statusDisplay", "")])
    gap = max(0, required - completed_count)
    progress_pct = min(100, int((completed_count / required) * 100)) if required > 0 else 100

    bar_len = 20
    filled_len = int(bar_len * progress_pct // 100)
    bar = "█" * filled_len + "░" * (bar_len - filled_len)

    # Alias normalization for common ShanghaiTech student terms
    norm_filter = filter_type.strip() if filter_type else None
    if norm_filter:
        if norm_filter in ("形策", "形势政策", "形势与政策讲座", "形策讲座"):
            match_keywords = ["形势与政策", "形策"]
            filter_label = "形势与政策 (形策讲座)"
        else:
            match_keywords = [norm_filter]
            filter_label = norm_filter

        filtered_activities = [
            a for a in activities
            if any(kw.lower() in a.get("typeDisplay", "").lower() or kw.lower() in a.get("activityName", "").lower() for kw in match_keywords)
        ]
    else:
        filtered_activities = activities
        filter_label = None

    # Calculate current semester (2026 Fall: starting 2026-09-01)
    current_term_start = "2026-09-01"
    current_term_count = len([a for a in filtered_activities if a.get("date", "") >= current_term_start and "已" in a.get("statusDisplay", "")])

    lines = []
    if filter_label:
        lines.append(f"## 🎟️ 上科大学生活动（xshdapp）「{filter_label}」签到打卡看板")
        lines.append(f"- **学号**：`{student_id}`" + (f" | **数据同步时间**：`{updated_at}`" if updated_at else ""))
        matched_done = len([a for a in filtered_activities if "已" in a.get("statusDisplay", "")])
        lines.append(f"- **本科毕业形策打卡要求**：`{required}` 次")
        lines.append(f"- **累计已核销打卡**：**{matched_done}** / `{required}` 次 (`{progress_pct}%`)")
        lines.append(f"  `[{bar}]`")
        lines.append(f"- **本学期（2026秋季学期）已打卡**：**{current_term_count}** 次")
    else:
        lines.append("## 🎟️ 上科大学生活动与通识讲座打卡看板 (xshdapp 校园签到)")
        lines.append(f"- **学号**：`{student_id}`" + (f" | **数据同步时间**：`{updated_at}`" if updated_at else ""))
        lines.append(f"- **本科毕业讲座达标进度**：`{completed_count} / {required}` 次 (`{progress_pct}%`)")
        lines.append(f"  `[{bar}]`")
        lines.append(f"- **本学期（2026秋季学期）已打卡**：**{current_term_count}** 次")

    if gap == 0:
        lines.append("  🎉 **恭喜！您已修满本科阶段要求的形势与政策/通识学术讲座打卡次数！**")
    else:
        lines.append(f"  ⚠️ **毕业预审预警**：距离本科毕业硬性要求（{required} 次）尚缺 **{gap}** 次打卡，请重点关注本学期与后续学期的形策排期！")

    lines.append("")
    # Sort by date descending (newest first)
    sorted_activities = sorted(filtered_activities, key=lambda x: x.get("date", ""), reverse=True)

    if filter_label:
        lines.append(f"### 📋 学生活动「{filter_label}」历史打卡清单（共 {len(sorted_activities)} 场，倒序排列）：")
    else:
        lines.append(f"### 📋 个人历史活动打卡清单（共 {len(sorted_activities)} 场，倒序排列）：")
    lines.append("| 序号 | 活动名称 | 活动类别 | 申请/打卡日期 | 审核状态 | 计入通识/形策 |")
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")

    if not sorted_activities:
        lines.append(f"| -- | *(暂无匹配「{filter_label}」的打卡记录)* | -- | -- | -- | -- |")
    else:
        for idx, act in enumerate(sorted_activities, 1):
            name = act.get("activityName", "--")
            atype = act.get("typeDisplay", "学术讲座")
            adate = act.get("date", "--")
            status = act.get("statusDisplay", "已打卡")
            counted = "✅ 是" if act.get("creditCounted", True) else "➖ 否"
            lines.append(f"| {idx} | **{name}** | `{atype}` | `{adate}` | {status} | {counted} |")

    lines.append("")
    lines.append("💡 **老学长讲座通关备忘**：")
    lines.append("- 进入会场或讲座结束后，请务必使用学校官方移动应用扫描现场公布的签到二维码完成签到（WID 绑定）；")
    lines.append("- 部分由学院主办的高规格研讨会支持多次签到或半程签到，打卡后请于 3 个工作日内于此核对记录。")

    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="上海科技大学活动打卡与讲座签到查询工具")
    parser.add_argument("category", nargs="?", default=None, help="活动类别筛选 (如 '形策', '形势与政策')")
    parser.add_argument("--type", "-t", dest="filter_type", help="活动类别筛选")
    parser.add_argument("--sync", action="store_true", help="强制从 TechPie 联网同步最新记录")
    parser.add_argument("--json", action="store_true", help="输出原始 JSON 数据")

    args = parser.parse_args()

    cookie_path = os.path.join(DATA_DIR, "eams_cookie.txt")
    has_tgc = os.environ.get("CASTGC") or os.environ.get("SHANGHAITECH_CASTGC") or os.path.exists(cookie_path)
    if not has_tgc:
        print("⚠️ 未检测到有效统一身份认证凭据 (CASTGC)。")
        print("学长 SKILL 第一要义：本地严禁存放或展示任何虚假个人讲座打卡与活动 Demo 数据。")
        print("所有个人的形势与政策及学术讲座打卡流水必须连接 xshdapp / eGate 网络端口实时查询。")
        print("👉 请先运行 `python3 scripts/senior.py login` 登录获取授权。")
        sys.exit(1)

    data = sync_activities_from_techpie()
    if not data:
        data = load_cached_activities()

    if not data or not data.get("activities"):
        print("❌ 无法从 xshdapp 网络端口获取讲座签到流水（凭据可能已过期或未能解析学号）。")
        print("👉 请运行 `python3 scripts/senior.py login` 重新登录获取有效授权。")
        sys.exit(1)

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    filter_val = args.filter_type or args.category
    print(format_activities_report(data, filter_type=filter_val))

if __name__ == "__main__":
    main()
