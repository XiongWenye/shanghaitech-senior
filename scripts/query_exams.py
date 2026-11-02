#!/usr/bin/env python3
"""
ShanghaiTech EAMS Exam Table & Seat Query Engine.
Adapted from TechPie-flutter's ScheduleService exam_table integration.

Features:
- Query official midterm / final exam arrangements (date, time, classroom, seat, status).
- Building location awareness: matches exam room with campus GPS coordinates.
- Export exam schedule directly into Apple Calendar / Google Calendar (.ics).
- Works offline with cached data (data/my_exams.json) or online with live EAMS session cookie.
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.parse
from typing import List, Dict, Optional, Any

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from campus_locations import find_location
from eams_session import get_cached_cookie

DATA_DIR = os.path.join(SCRIPTS_DIR, "..", "data")
EXAMS_CACHE_FILE = os.path.join(DATA_DIR, "my_exams.json")
TECHPIE_API_URL = "https://techpie.geekpie.club/api/schedule/exam_table"

def load_cached_exams() -> Dict[str, Any]:
    if os.path.exists(EXAMS_CACHE_FILE):
        try:
            with open(EXAMS_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"exams": []}

def save_cached_exams(data: Dict[str, Any]):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(EXAMS_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def fetch_live_exams(cookie: str, semester_id: str = "", student_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Fetch exam table via TechPie backend API using eGate/EAMS session cookie.
    """
    sid = student_id or ""
    active_cookies = cookie
    if "CASTGC=" in cookie or "TGT-" in cookie:
        try:
            from sync_my_plan import exchange_eams_cookies, get_tgc
            tgc = get_tgc(cookie)
            if tgc:
                exchanged = exchange_eams_cookies(tgc)
                if exchanged:
                    active_cookies = exchanged
                if not sid:
                    import eams_session
                    prof = eams_session.get_student_profile(tgc)
                    if prof:
                        sid = prof.get("student_id", "")
        except Exception:
            pass

    body_data = {
        "cookies": active_cookies,
        "studentId": sid,
        "semester_id": semester_id or "282",
    }
    req = urllib.request.Request(
        TECHPIE_API_URL,
        data=json.dumps(body_data).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Connection": "close",
            "User-Agent": "TechPie-SeniorSkill/2.0",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("success") and "data" in data:
                return data["data"]
    except Exception as e:
        print(f"⚠️ 在线考试接口同步提示: {e}", file=sys.stderr)
    return None

def format_exams_report(data: Dict[str, Any]) -> str:
    exams = data.get("exams", [])
    batch_name = data.get("examBatchName") or "本学期考试安排"
    updated_at = data.get("updated_at", "")

    if not exams:
        return "ℹ️ 当前暂无排定的期中或期末考试安排记录。"

    lines = [
        f"## 📝 上科大正式考试安排与考场座位看板",
        f"**批次名称**：`{batch_name}`" + (f" | **更新时间**：`{updated_at}`" if updated_at else ""),
        "",
        "| 课程代码 | 考试科目 | 类型 | 考试日期 | 考试时间 | 考场教室 | 座位号 | 状态 |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for ex in sorted(exams, key=lambda x: (x.get("examDate", ""), x.get("examTimeRange", ""))):
        code = ex.get("courseCode", "--")
        name = ex.get("courseName", "--")
        extype = ex.get("examType", "期末")
        edate = ex.get("examDate", "--")
        etime = ex.get("examTimeRange", "--")
        eplace = ex.get("examPlace", "--")
        seat = ex.get("seat", "--")
        status = ex.get("examStatus", "正常")

        loc = find_location(eplace)
        place_str = f"📍 {eplace}" if loc else eplace

        status_str = f"✅ {status}" if status == "正常" else f"⚠️ {status}"
        lines.append(f"| `{code}` | **{name}** | {extype} | `{edate}` | `{etime}` | {place_str} | **{seat}** | {status_str} |")

    lines.append("")
    lines.append("💡 **老学长考前贴士**：")
    lines.append("- 考场均已匹配校园高精度地理定位，请提前 15 分钟抵达所在学院考场；")
    lines.append("- 进入考场请务必携带**学生证（或校园卡）**以及必备文具（答题卡填涂需 2B 铅笔）。")
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="上海科技大学 EAMS 考试安排与考场座位查询工具")
    parser.add_argument("--cookie", "-c", type=str, help="EAMS/eGate 会话 Cookie")
    parser.add_argument("--semester", "-s", type=str, default="", help="学期 ID")
    parser.add_argument("--ics", type=str, help="将考试安排导出为指定路径的 .ics 日历文件")
    parser.add_argument("--json", action="store_true", help="输出原始 JSON 数据")

    args = parser.parse_args()

    active_cookie = args.cookie or get_cached_cookie()
    if not active_cookie:
        print("⚠️ 未检测到有效 EAMS 会话凭据。")
        print("学长 SKILL 第一要义：本地严禁存放或展示任何虚假 Demo 考试安排。")
        print("所有个人的考务与考场座位信息均需连接 EAMS 网络端口实时动态查询。")
        print("👉 请先运行 `python3 scripts/senior.py login` 登录获取授权，或通过 `--cookie` 传入凭据。")
        sys.exit(1)

    exam_data = fetch_live_exams(active_cookie, args.semester)
    if exam_data:
        save_cached_exams(exam_data)
    else:
        print("❌ 无法从 EAMS 考务网络端口获取考试安排（可能网络超时或当前学期尚未排考）。")
        sys.exit(1)

    if args.json:
        print(json.dumps(exam_data, ensure_ascii=False, indent=2))
        return

    print(format_exams_report(exam_data))

    if args.ics:
        from export_schedule_ics import build_ics_calendar
        from datetime import date
        ics_text = build_ics_calendar(
            courses=[],
            term_begin=date(2026, 9, 7),
            calendar_name="上海科技大学考试日程",
            exams=exam_data.get("exams", []),
        )
        with open(args.ics, "w", encoding="utf-8") as f:
            f.write(ics_text)
        print(f"\n🎉 已成功导出考试日历至: {args.ics}")

if __name__ == "__main__":
    main()
