#!/usr/bin/env python3
"""
ShanghaiTech ELRC (Course Video Recordings) Client & Query Engine.
Adapted from TechPie-flutter's ElrcClient.

Provides:
- Search course lecture recordings by course code or course name.
- View lesson schedules (week, weekday, section, title).
- Direct deep-links to ELRC playback portal.
- Support syncing latest recordings from elrc.shanghaitech.edu.cn with live session cookie.
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.parse
from typing import List, Dict, Optional, Any

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPTS_DIR, "..", "data")
ELRC_CATALOG_FILE = os.path.join(DATA_DIR, "elrc_catalog.json")

ELRC_ORIGIN = "https://elrc.shanghaitech.edu.cn"
COURSE_LIST_PATH = "/learn/v1/course/video/review/1"
COURSE_INFO_PATH = "/learn/v1/course/recording/video/info"

def load_elrc_catalog() -> Dict[str, Any]:
    if os.path.exists(ELRC_CATALOG_FILE):
        try:
            with open(ELRC_CATALOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"courses": []}

def get_elrc_course_url(course: Dict[str, Any]) -> str:
    course_id = course.get("courseId", "")
    review_id = course.get("reviewId")
    school_year = course.get("schoolYear")
    semester = course.get("semester")
    
    query_parts = []
    if review_id:
        query_parts.append(f"id={urllib.parse.quote(str(review_id))}")
    if school_year:
        query_parts.append(f"schoolYear={urllib.parse.quote(str(school_year))}")
    if semester:
        query_parts.append(f"semester={urllib.parse.quote(str(semester))}")
        
    query_str = f"?{'&'.join(query_parts)}" if query_parts else ""
    return f"{ELRC_ORIGIN}/learn/videoreview/{course_id}{query_str}"

def search_elrc_courses(query: str) -> List[Dict[str, Any]]:
    catalog = load_elrc_catalog()
    courses = catalog.get("courses", [])
    if not query:
        return courses

    q = query.strip().upper()
    matches = []
    
    # Normalization mappings
    synonyms = {
        "高数": "GEMA1001",
        "高数I": "GEMA1001",
        "高等数学": "GEMA1001",
        "数分": "GEMA1001",
        "数学分析": "GEMA1001",
        "大物": "SP101",
        "大学物理": "SP101",
        "普通物理": "SP101",
        "概统": "SI140A",
        "概率论": "SI140A",
        "体系结构": "CS130",
        "计系": "CS110",
        "计算机系统": "CS110",
        "操作系统": "CS130",
        "电路": "EE111",
    }
    
    target_code = None
    for k, v in synonyms.items():
        if k in q:
            target_code = v
            break

    for c in courses:
        name = c.get("name", "").upper()
        code = c.get("courseNo", "").upper()
        desc = c.get("description", "").upper()
        
        if (target_code and target_code in code) or (q in code) or (q in name) or (q in desc):
            matches.append(c)

    return matches

def format_elrc_report(course: Dict[str, Any], filter_week: Optional[str] = None) -> str:
    name = course.get("name", "未知课程")
    code = course.get("courseNo", "")
    teachers = course.get("teachers", "教师")
    year = course.get("schoolYear", "2025-2026")
    sem = course.get("semester", "1")
    sem_name = "秋季学期" if sem == "1" else ("春季学期" if sem == "2" else "暑期")
    total_count = course.get("lessonsCount", 0)
    url = get_elrc_course_url(course)

    lines = []
    lines.append(f"### 🎥 ELRC 官方课堂录播：{name}")
    lines.append(f"- **开课学期**：`{year} {sem_name}` | **任课教师**：`{teachers}`")
    lines.append(f"- **录播课次**：共 `{total_count}` 讲录播视频在架")
    lines.append(f"- **🔗 录播主页直达**：[{name} 随堂录播]({url})")
    lines.append("")

    lessons = course.get("lessons", [])
    if filter_week:
        lessons = [l for l in lessons if str(l.get("week")) == str(filter_week)]

    if lessons:
        lines.append("#### 📋 重点课次录播索引：")
        lines.append("| 周次 | 星期/节次 | 课次重点主题 / 录播内容 | 直达播放 |")
        lines.append("| :--- | :--- | :--- | :--- |")
        for l in lessons:
            w = f"第 {l.get('week')} 周"
            t = f"{l.get('weekDay', '')} {l.get('section', '')}"
            title = l.get('title', '随堂讲授')
            lines.append(f"| {w} | {t} | {title} | [点击观看]({url}) |")
    else:
        if filter_week:
            lines.append(f"*注：未检索到第 {filter_week} 周的独立录播切片，请直接访问录播主页查看完整列表。*")

    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="上海科技大学 ELRC 课程录播查询工具")
    parser.add_argument("query", nargs="?", default="", help="课程名称或课程代码 (如 CS100, 高数I, CS110)")
    parser.add_argument("--week", "-w", type=str, help="指定查询的周次 (如 5)")
    parser.add_argument("--json", action="store_true", help="输出原始 JSON 格式")

    args = parser.parse_args()

    if not args.query:
        print("💡 请提供查询的课程名称或课号。示例：")
        print("   python3 scripts/query_elrc.py CS100")
        print("   python3 scripts/query_elrc.py CS110 --week 6")
        sys.exit(0)

    matches = search_elrc_courses(args.query)
    if not matches:
        print(f"❌ 未在 ELRC 录播索引库中找到与「{args.query}」相关的录播课程。")
        print(f"👉 建议登录学校 ELRC 平台查看最新排播: {ELRC_ORIGIN}")
        sys.exit(0)

    if args.json:
        print(json.dumps(matches, ensure_ascii=False, indent=2))
        return

    for c in matches:
        print(format_elrc_report(c, filter_week=args.week))
        print("\n" + "-" * 60 + "\n")

if __name__ == "__main__":
    main()
