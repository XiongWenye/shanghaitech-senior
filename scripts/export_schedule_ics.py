#!/usr/bin/env python3
"""
ShanghaiTech Course Table to iCalendar (.ics) Exporter.
Faithfully adapted from TechPie-flutter's IcsExportService.

Supports:
- RFC 5545 iCalendar specification.
- Standard ShanghaiTech 13 periods (08:15 to 21:30).
- Building geo-coordinates and Apple Calendar structured locations.
- Single/alternate/multi-week range expansion.
- Exam events expansion with seat and room details.
"""

import os
import sys
import json
import argparse
from datetime import datetime, date, timedelta, time, timezone
from typing import List, Dict, Optional, Tuple, Any

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from campus_locations import (
    find_location,
    format_apple_structured_location,
    format_geo_attribute,
    CAMPUS_NAME,
    CAMPUS_ADDRESS,
)

# Standard ShanghaiTech 13 periods
DEFAULT_PERIODS = {
    1: ("08:15", "09:00"),
    2: ("09:10", "09:55"),
    3: ("10:15", "11:00"),
    4: ("11:10", "11:55"),
    5: ("13:00", "13:45"),
    6: ("13:55", "14:40"),
    7: ("15:00", "15:45"),
    8: ("15:55", "16:40"),
    9: ("16:50", "17:35"),
    10: ("18:00", "18:45"),
    11: ("18:55", "19:40"),
    12: ("19:50", "20:35"),
    13: ("20:45", "21:30"),
}

def escape_ics_text(text: str) -> str:
    if not text:
        return ""
    return (
        text.replace('\\', '\\\\')
        .replace(';', r'\;')
        .replace(',', r'\,')
        .replace('\n', r'\n')
    )

def format_datetime_ics(dt: datetime) -> str:
    """Format local datetime for ICS: YYYYMMDDTHHMMSS."""
    return dt.strftime("%Y%m%dT%H%M%S")

def format_utc_timestamp(dt: Optional[datetime] = None) -> str:
    """Format UTC timestamp for DTSTAMP: YYYYMMDDTHHMMSSZ."""
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%SZ")

def parse_time_str(time_str: str) -> time:
    parts = time_str.strip().split(':')
    return time(hour=int(parts[0]), minute=int(parts[1]))

def combine_date_time(d: date, t: time) -> datetime:
    return datetime.combine(d, t)

def build_ics_calendar(
    courses: List[Dict[str, Any]],
    term_begin: date,
    calendar_name: str = "上科大课表",
    exams: Optional[List[Dict[str, Any]]] = None,
    periods_map: Optional[Dict[int, Tuple[str, str]]] = None,
    enable_alarms: bool = True,
    alarm_minutes_before: int = 15,
) -> str:
    """
    Build RFC 5545 VCALENDAR text from courses and term begin date.
    
    courses format:
    [
        {
            "name": "计算机体系结构",
            "classroom": "信息学院1A-200",
            "teachers": "主讲教师",
            "weeks": "01111111111111111000",  # week 1 is index 1
            "times": {"1": [1, 2], "3": [3, 4]}  # weekday 1-7: [period indices]
        }
    ]
    """
    if periods_map is None:
        periods_map = DEFAULT_PERIODS

    # Monday of Week 1
    # Python weekday(): Monday is 0, Sunday is 6.
    monday_week_one = term_begin - timedelta(days=term_begin.weekday())
    dtstamp = format_utc_timestamp()

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//ShanghaiTech Senior Skill//Schedule Export//CN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_ics_text(calendar_name)}",
        "X-WR-TIMEZONE:Asia/Shanghai",
    ]

    event_count = 0

    # Expand courses
    for c in courses:
        name = c.get("name", "课程")
        classroom = c.get("classroom", "").strip()
        teachers = c.get("teachers", "").strip()
        weeks_str = c.get("weeks", "")
        times_dict = c.get("times", {})
        loc = find_location(classroom)

        location_str = f"{classroom} {CAMPUS_NAME}" if classroom else CAMPUS_NAME

        # Iterate active weeks (1-based index)
        active_weeks = []
        for w_idx in range(1, len(weeks_str)):
            if weeks_str[w_idx] == "1":
                active_weeks.append(w_idx)

        for week in active_weeks:
            monday_of_week = monday_week_one + timedelta(days=(week - 1) * 7)

            for day_key, period_list in times_dict.items():
                try:
                    weekday = int(day_key)  # 1=Mon, 7=Sun
                except ValueError:
                    continue

                if isinstance(period_list, str):
                    period_list = [int(p.strip()) for p in period_list.split(",") if p.strip().isdigit()]
                
                periods = sorted([int(p) for p in period_list if int(p) in periods_map])
                if not periods:
                    continue

                start_p = periods[0]
                end_p = periods[-1]
                start_time_str = periods_map[start_p][0]
                end_time_str = periods_map[end_p][1]

                class_date = monday_of_week + timedelta(days=weekday - 1)
                start_dt = combine_date_time(class_date, parse_time_str(start_time_str))
                end_dt = combine_date_time(class_date, parse_time_str(end_time_str))

                uid = f"{name}-{classroom}-W{week}-D{weekday}-P{start_p}-{end_p}@shanghaitech-senior"

                lines.append("BEGIN:VEVENT")
                lines.append(f"UID:{uid}")
                lines.append(f"DTSTAMP:{dtstamp}")
                lines.append(f"DTSTART;TZID=Asia/Shanghai:{format_datetime_ics(start_dt)}")
                lines.append(f"DTEND;TZID=Asia/Shanghai:{format_datetime_ics(end_dt)}")
                lines.append(f"SUMMARY:{escape_ics_text(name)}")
                lines.append("LOCATION-TYPE:SCHOOL")
                lines.append(f"LOCATION:{escape_ics_text(location_str)}")

                if loc:
                    lines.append(format_geo_attribute(loc))
                    lines.append(format_apple_structured_location(loc))

                desc_parts = []
                if teachers:
                    desc_parts.append(f"任课教师: {teachers}")
                desc_parts.append(f"学期周次: 第 {week} 周")
                desc_parts.append(f"节次: 第 {start_p}-{end_p} 节 ({start_time_str}~{end_time_str})")
                if classroom:
                    desc_parts.append(f"教室: {classroom}")
                lines.append(f"DESCRIPTION:{escape_ics_text(chr(10).join(desc_parts))}")

                if enable_alarms:
                    lines.append("BEGIN:VALARM")
                    lines.append("ACTION:DISPLAY")
                    lines.append(f"DESCRIPTION:即将开始上课: {escape_ics_text(name)}")
                    lines.append(f"TRIGGER:-PT{alarm_minutes_before}M")
                    lines.append("END:VALARM")

                lines.append("SEQUENCE:0")
                lines.append("END:VEVENT")
                event_count += 1

    # Expand exams if present
    if exams:
        for exam in exams:
            title = exam.get("title") or exam.get("courseName") or "考试"
            course_name = exam.get("course") or exam.get("courseCode") or ""
            exam_type = exam.get("examType", "考试")
            date_str = exam.get("examDate") or exam.get("date")
            time_range = exam.get("examTimeRange") or exam.get("time") or "09:00~11:00"
            place = exam.get("examPlace") or exam.get("location") or ""
            seat = exam.get("seat") or exam.get("seatUrl") or ""

            if not date_str:
                continue

            try:
                exam_date = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
            except ValueError:
                continue

            time_parts = time_range.replace('-', '~').split('~')
            start_t = parse_time_str(time_parts[0])
            end_t = parse_time_str(time_parts[1]) if len(time_parts) > 1 else time(start_t.hour + 2, start_t.minute)

            start_dt = combine_date_time(exam_date, start_t)
            end_dt = combine_date_time(exam_date, end_t)

            loc = find_location(place)
            loc_str = f"{place} {CAMPUS_NAME}" if place else CAMPUS_NAME
            summary = f"[{exam_type}] {title}"
            uid = f"exam-{course_name}-{date_str}-{time_parts[0]}@shanghaitech-senior"

            lines.append("BEGIN:VEVENT")
            lines.append(f"UID:{uid}")
            lines.append(f"DTSTAMP:{dtstamp}")
            lines.append(f"DTSTART;TZID=Asia/Shanghai:{format_datetime_ics(start_dt)}")
            lines.append(f"DTEND;TZID=Asia/Shanghai:{format_datetime_ics(end_dt)}")
            lines.append(f"SUMMARY:{escape_ics_text(summary)}")
            lines.append("LOCATION-TYPE:SCHOOL")
            lines.append(f"LOCATION:{escape_ics_text(loc_str)}")

            if loc:
                lines.append(format_geo_attribute(loc))
                lines.append(format_apple_structured_location(loc))

            desc_parts = [f"科目: {title} ({course_name})", f"类型: {exam_type}", f"考场: {place}"]
            if seat:
                desc_parts.append(f"座位信息: {seat}")
            lines.append(f"DESCRIPTION:{escape_ics_text(chr(10).join(desc_parts))}")

            if enable_alarms:
                lines.append("BEGIN:VALARM")
                lines.append("ACTION:DISPLAY")
                lines.append(f"DESCRIPTION:考试提醒: {escape_ics_text(summary)}")
                lines.append("TRIGGER:-PT60M")
                lines.append("END:VALARM")

            lines.append("SEQUENCE:0")
            lines.append("END:VEVENT")
            event_count += 1

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"

def main():
    from live_session import LiveQueryError
    from sync_my_plan import fetch_live_schedule
    parser = argparse.ArgumentParser(description="实时 EAMS 课表转 ICS，仅标准输出，不读取或保存个人文件")
    parser.add_argument("--semester", "-s", default="")
    parser.add_argument("--name", "-n", default="上海科技大学课表")
    args = parser.parse_args()
    try:
        data = fetch_live_schedule(semester_id=args.semester, with_calendar=True)
        periods = {}
        for entry in data.get("periods", []):
            for index, time_range in entry.items():
                parts = time_range.split("-")
                if len(parts) != 2:
                    raise LiveQueryError("EAMS 作息时间格式无效")
                periods[int(index)] = tuple(part.strip() for part in parts)
        if data["courses"] and not periods:
            raise LiveQueryError("EAMS 课表缺少作息时间，不能用静态时间代替本次实时查询")
        content = build_ics_calendar(data["courses"], datetime.fromisoformat(data["termBegin"]).date(),
                                     calendar_name=args.name, periods_map=periods)
    except (LiveQueryError, ValueError, TypeError, AttributeError) as error:
        print(f"日历生成失败：{error}", file=sys.stderr)
        raise SystemExit(1)
    print(content, end="")


if __name__ == "__main__":
    main()
