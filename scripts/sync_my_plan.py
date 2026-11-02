#!/usr/bin/env python3
"""Live EAMS schedule and degree audit. Personal responses stay in memory.

A course table establishes enrollment, never a passing grade or earned credit.
"""
import argparse
import json
import re
import sys
from datetime import datetime
from live_session import (LiveQueryError, derive_cookies, get_tgc, post_json,
                          queried_at, require_cookie)


def extract_course_code(raw_name, raw_code=""):
    code = raw_code.split(".")[0].strip().upper()
    if re.fullmatch(r"[A-Z]{2,6}[0-9]{3,4}[A-Z0-9]*", code):
        return code
    matches = re.findall(r"\b([A-Z]{2,6}[0-9]{3,4}[A-Z0-9]*)(?:\.[0-9]{2})?\b", raw_name.upper())
    return matches[-1] if matches else raw_name.strip()


def exchange_eams_cookies(tgc):
    return derive_cookies("eams", tgc)


def schedule_context(cookie=None, semester_id=""):
    from eams_session import get_student_profile
    cookies = derive_cookies("eams", require_cookie(cookie))
    profile = get_student_profile(cookies)
    if not profile or not profile.get("student_id"):
        raise LiveQueryError("未能从本次 EAMS 在线响应确认学号，不能查询个人课表或考务")
    student_id = profile["student_id"]
    metadata = post_json("/schedule/semesters", {"cookies": cookies, "studentId": student_id})
    if not isinstance(metadata, dict) or not isinstance(metadata.get("semesters"), dict):
        raise LiveQueryError("EAMS 学期目录响应无效")
    semester = str(semester_id or metadata.get("defaultSemester") or "")
    terms = [(year, term, str(sid)) for year, term_map in metadata["semesters"].items()
             if isinstance(term_map, dict) for term, sid in term_map.items()]
    selected = next(((year, term) for year, term, sid in terms if sid == semester), None)
    if not semester or not selected:
        raise LiveQueryError("EAMS 未返回可确认的目标学期；未采用写死的默认学期")
    return cookies, student_id, semester, metadata, selected


def fetch_live_schedule(cookie=None, semester_id="", with_calendar=False):
    cookies, student_id, semester, metadata, selected = schedule_context(cookie, semester_id)
    body = {"cookies": cookies, "studentId": student_id, "semester_id": semester}
    if metadata.get("tableId"):
        body["table_id"] = metadata["tableId"]
    data = post_json("/schedule/course_table", body)
    if not isinstance(data, dict) or not isinstance(data.get("courses"), list) or not all(isinstance(c, dict) for c in data["courses"]):
        raise LiveQueryError("EAMS 课表响应缺少有效 courses 列表")
    result = {**data, "semester_id": semester, "queried_at": queried_at(),
              "source": "EAMS via TechPie /schedule/course_table"}
    if with_calendar:
        year, term = selected
        term_numbers = {"秋": "1", "春": "2", "暑": "3"}
        term_no = term if term in ("1", "2", "3") else next((n for name, n in term_numbers.items() if name in term), None)
        if not term_no:
            raise LiveQueryError("无法从实时学期目录确认校历学期")
        calendar = post_json("/schedule/term_begin", {"cookies": cookies, "studentId": student_id,
                                                     "year": year.split("-")[0], "semester": term_no})
        if not isinstance(calendar, dict) or not calendar.get("termBegin"):
            raise LiveQueryError("实时校历缺少 termBegin")
        try:
            datetime.fromisoformat(calendar["termBegin"])
        except (TypeError, ValueError):
            raise LiveQueryError("实时校历开学日期格式无效") from None
        result["termBegin"] = calendar["termBegin"]
    return result


def fetch_live_plan(cookie=None):
    from eams_session import fetch_plan_lightweight, MY_PLAN_URL
    from analyze_plan import parse_html_plan
    html = fetch_plan_lightweight(require_cookie(cookie))
    completed, in_progress, header = parse_html_plan(html)
    if not header.get("student_id") or header.get("grade") is None or not header.get("major"):
        raise LiveQueryError("EAMS 页面学籍字段不完整，不能确认年级与专业")
    if header.get("compl_credits") is None:
        raise LiveQueryError("EAMS 页面未解析到官方学分统计")
    return {"completed": completed, "in_progress": in_progress, "header": header,
            "source": MY_PLAN_URL, "queried_at": queried_at()}


def sync_and_audit(cookie=None, major=None, grade=None, as_json=False):
    """Audit a fresh official completion page; no historical-enrollment inference."""
    from analyze_plan import resolve_curriculum_path, analyze_plan_gap, generate_personalized_recommendation_report
    record = fetch_live_plan(cookie)
    header = record["header"]
    try:
        path = resolve_curriculum_path(major or header["major"], grade or header["grade"])
    except LiveQueryError as error:
        # Public-curriculum coverage does not invalidate a successful live EAMS query.
        analysis = {"header_info": header, "curriculum": {}, "modules_analysis": [],
                    "total_earned_credits": sum(c["credit"] for c in record["completed"].values()),
                    "total_in_progress_credits": sum(c["credit"] for c in record["in_progress"].values()),
                    "comparison_available": False, "comparison_error": str(error)}
    else:
        analysis = analyze_plan_gap(record["completed"], record["in_progress"], path, header)
        analysis["comparison_available"] = True
    analysis.update(source=record["source"], queried_at=record["queried_at"])
    if as_json:
        print(json.dumps({**record, "analysis": analysis}, ensure_ascii=False, indent=2))
    else:
        print(f"来源：{record['source']} | 实时查询：{record['queried_at']}")
        print(generate_personalized_recommendation_report(analysis))
    return True


def main():
    parser = argparse.ArgumentParser(description="实时查询 EAMS 本学期选课与课表，不保存个人数据")
    parser.add_argument("--semester", default="", help="目标学期 ID，默认实时 EAMS 当前学期")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        data = fetch_live_schedule(semester_id=args.semester)
    except LiveQueryError as error:
        print(f"查询失败：{error}", file=sys.stderr)
        raise SystemExit(1)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"EAMS 学期 {data['semester_id']} | 实时查询：{data['queried_at']}")
        for course in data["courses"]:
            print(f"{course.get('name', '--')} | {course.get('classroom', '--')} | {course.get('teachers', '--')} | 周次 {course.get('weeks', '--')} | 节次 {course.get('times', {})}")
        if not data["courses"]:
            print("EAMS 本次查询成功，目标学期课表为空。")


if __name__ == "__main__":
    main()
