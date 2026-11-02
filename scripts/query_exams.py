#!/usr/bin/env python3
"""Fresh official EAMS exam queries; no local records or calendar files."""
import argparse
import json
import sys
from typing import Any, Dict
from campus_locations import find_location
from live_session import LiveQueryError, post_json, queried_at
from sync_my_plan import schedule_context


def fetch_live_exams(cookie=None, semester_id=""):
    cookies, student_id, semester, _, _ = schedule_context(cookie, semester_id)
    data = post_json("/schedule/exam_table", {"cookies": cookies, "studentId": student_id, "semester_id": semester})
    if not isinstance(data, dict) or not isinstance(data.get("exams"), list) or not all(isinstance(e, dict) for e in data["exams"]):
        raise LiveQueryError("EAMS 考务响应缺少有效 exams 列表，不能当作暂无排考")
    return {**data, "semester_id": semester, "updated_at": queried_at(),
            "source": "EAMS via TechPie /schedule/exam_table"}


def format_exams_report(data: Dict[str, Any]) -> str:
    exams = data.get("exams", [])
    batch_name = data.get("examBatchName") or "目标学期考试安排"
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
        extype = ex.get("examType", "未提供")
        edate = ex.get("examDate", "--")
        etime = ex.get("examTimeRange", "--")
        eplace = ex.get("examPlace", "--")
        seat = ex.get("seat", "--")
        status = ex.get("examStatus", "未提供")

        loc = find_location(eplace)
        place_str = f"📍 {eplace}" if loc else eplace

        status_str = f"✅ {status}" if status == "正常" else f"⚠️ {status}"
        lines.append(f"| `{code}` | **{name}** | {extype} | `{edate}` | `{etime}` | {place_str} | **{seat}** | {status_str} |")

    lines.append("")
    lines.append("💡 **老学长考前贴士**：")
    lines.append("- 请按官方排考中的时间与地点前往考场；")
    lines.append("- 进入考场请务必携带**学生证（或校园卡）**以及必备文具（答题卡填涂需 2B 铅笔）。")
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="EAMS 实时考试安排与座位号（不落盘）")
    parser.add_argument("--semester", "-s", default="", help="默认使用实时当前学期")
    parser.add_argument("--ics", action="store_true", help="将本次实时考试日历输出到标准输出")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        data = fetch_live_exams(semester_id=args.semester)
        if args.ics:
            from export_schedule_ics import build_ics_calendar
            from datetime import date
            print(build_ics_calendar([], date.today(), calendar_name="上海科技大学考试日程", exams=data["exams"]), end="")
        elif args.json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print(f"来源：{data['source']} | 实时查询：{data['updated_at']}")
            print(format_exams_report(data))
    except LiveQueryError as error:
        print(f"查询失败：{error}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
