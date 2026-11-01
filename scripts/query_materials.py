#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Query Course Materials for ShanghaiTech Courses
Quickly retrieves exam papers, solutions, homework, slides, and project code across:
- iTechX (file-base)
- XiongWenye shanghaitech-course-database
- zsc2003 courses-summary
"""

import os
import sys
import json
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_FILE = BASE_DIR / "data" / "materials_index.json"


def load_index():
    if not INDEX_FILE.exists():
        print(f"Error: Index file not found at {INDEX_FILE}", file=sys.stderr)
        print("Please run `python3 scripts/build_index.py` first.", file=sys.stderr)
        sys.exit(1)
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_course_code(index, query):
    query = query.strip()
    q_lower = query.lower()
    
    # 1. Exact match code
    for code in index["courses"]:
        if code.lower() == q_lower:
            return code
            
    # 2. Inverted index match
    inverted = index.get("inverted_index", {})
    if q_lower in inverted and inverted[q_lower]:
        return inverted[q_lower][0]
        
    # 3. Substring match in inverted index or names
    candidates = []
    for alias, codes in inverted.items():
        if q_lower in alias or alias in q_lower:
            for c in codes:
                if c not in candidates:
                    candidates.append(c)
                    
    # 4. Check Chinese names
    for code, info in index["courses"].items():
        name_zh = info.get("name_zh", "").lower()
        if q_lower in name_zh or name_zh in q_lower:
            if code not in candidates:
                candidates.append(code)
                
    if len(candidates) == 1:
        return candidates[0]
    elif len(candidates) > 1:
        return candidates
        
    return None


def format_markdown_report(course):
    code = course["code"]
    name_zh = course.get("name_zh") or "未知课程"
    name_en = course.get("name_en") or ""
    inst = course.get("institute") or "上海科技大学"
    credit = course.get("credit", 0.0)
    scores = course.get("cb_scores", {})
    res = course.get("resources", {})

    lines = []
    lines.append(f"## 📚 【{code}】{name_zh} 完整备考与修课资料包")
    if name_en:
        lines.append(f"*{name_en}* | **开课单位**：{inst} | **学分**：{credit}学分\n")
    else:
        lines.append(f"**开课单位**：{inst} | **学分**：{credit}学分\n")

    # CourseBench Score Summary
    if scores and scores.get("quality"):
        sq = scores.get("quality", 0)
        sw = scores.get("workload", 0)
        sd = scores.get("difficulty", 0)
        sg = scores.get("grade", 0)
        lines.append(f"> 🌟 **CourseBench 口碑指数**：教学质量 `{sq:.1f}/5.0` | 课业负担 `{sw:.1f}/5.0` | 考核难度 `{sd:.1f}/5.0` | 给分情况 `{sg:.1f}/5.0`")
        lines.append("")

    # Source badges
    badges = []
    if res.get("itechx", {}).get("available"):
        badges.append("🟢 **iTechX 课程库** (课件/作业/标准答案/历年卷)")
    if res.get("xiongwenye", {}).get("available"):
        badges.append("🟠 **XiongWenye 资料库** (独家期中期末真题/回忆卷/解析)")
    if res.get("zsc2003", {}).get("available"):
        badges.append("🟣 **zsc2003 学长通关仓库** (高分代码/Recitation教程/复习提纲)")
    lines.append("### 📦 收录资料库状态")
    for b in badges:
        lines.append(f"- {b}")
    lines.append("")

    # Section 1: Past Exams & Quizzes
    lines.append("### 📝 1. 历年真题与考试资料 (Past Exams & Quizzes)")
    has_exam = False
    
    # XiongWenye exams
    xw = res.get("xiongwenye")
    if xw and xw.get("exams"):
        for ex in xw["exams"]:
            lines.append(f"- 📄 **真题卷**：[{ex['name']}]({ex['url']})")
            has_exam = True
    if xw and xw.get("solutions"):
        for sol in xw["solutions"]:
            lines.append(f"- 🔑 **考卷解析与答案**：[{sol['name']}]({sol['url']})")
            has_exam = True

    # iTechX exams
    itx = res.get("itechx")
    if itx and itx.get("categories", {}).get("exams"):
        for ex in itx["categories"]["exams"]:
            lines.append(f"- 📑 **iTechX 考卷目录**：[{ex['semester']} - {ex['folder']}]({ex['url']})")
            has_exam = True

    if not has_exam:
        lines.append("- *暂无独立切分的试卷文件，建议直接浏览下方共享库根目录。*")
    lines.append("")

    # Section 2: Homework & Official Solutions
    lines.append("### 📚 2. 平时作业与参考解答 (Homework & Solutions)")
    has_hw = False
    if itx:
        hw_sols = itx.get("categories", {}).get("homework_solutions", [])
        hws = itx.get("categories", {}).get("homework", [])
        for sol in hw_sols:
            lines.append(f"- 💡 **作业标准解答**：[{sol['semester']} - {sol['folder']}]({sol['url']})")
            has_hw = True
        for hw in hws:
            lines.append(f"- 📝 **平时作业题目**：[{hw['semester']} - {hw['folder']}]({hw['url']})")
            has_hw = True
    if not has_hw:
        lines.append("- *暂无单独分类的作业答案，可查看下方学长仓库或总库。*")
    lines.append("")

    # Section 3: Slides, Notes & Recitation Tutorials
    lines.append("### 🖥️ 3. 讲义课件与复习提纲 (Lecture Slides & Tutorials)")
    has_slides = False
    if itx and itx.get("categories", {}).get("slides_notes"):
        for sl in itx["categories"]["slides_notes"]:
            lines.append(f"- 📊 **教学课件 PPT**：[{sl['semester']} - {sl['folder']}]({sl['url']})")
            has_slides = True
    if itx and itx.get("categories", {}).get("recitations"):
        for rc in itx["categories"]["recitations"]:
            lines.append(f"- 👨‍🏫 **习题课与复习讲义**：[{rc['semester']} - {rc['folder']}]({rc['url']})")
            has_slides = True
    if xw and xw.get("slides_notes"):
        for sn in xw["slides_notes"]:
            lines.append(f"- 📖 **学长提纲/讲义**：[{sn['name']}]({sn['url']})")
            has_slides = True
    if not has_slides:
        lines.append("- *可直接在下方资料库主页中查阅课件。*")
    lines.append("")

    # Section 4: Projects, Labs & Templates
    lines.append("### 💡 4. 实验报告与大作业设计 (Projects & Labs)")
    has_proj = False
    if itx and itx.get("categories", {}).get("projects"):
        for pj in itx["categories"]["projects"]:
            lines.append(f"- 🛠️ **课程大作业/设计**：[{pj['semester']} - {pj['folder']}]({pj['url']})")
            has_proj = True
    if xw and xw.get("labs"):
        for lb in xw["labs"][:8]:
            lines.append(f"- 🧪 **实验讲义/报告**：[{lb['name']}]({lb['url']})")
            has_proj = True
    if not has_proj:
        lines.append("- *该课程无大作业或实验材料，或已归并在作业目录中。*")
    lines.append("")

    # Section 5: Direct Repository Deep-links
    lines.append("### 🔗 5. 共享资料库一键直达 (Direct Repositories)")
    if itx and itx.get("repo_url"):
        lines.append(f"- 🌐 **[iTechX 课程资源主页]({itx['repo_url']})**（收录 {itx.get('semesters_count', 0)} 个学期教学完整档案）")
    if xw and xw.get("repo_url"):
        lines.append(f"- 🌐 **[XiongWenye 上科大课程资料库 - {xw.get('folder_name')}]({xw['repo_url']})**（收录 {xw.get('total_files', 0)} 份资料）")
    zsc = res.get("zsc2003")
    if zsc and zsc.get("repo_url"):
        lines.append(f"- 🌐 **[zsc2003 专属修课与通关仓库]({zsc['repo_url']})**（包含 {', '.join(zsc.get('semesters', []))} 个人高分通关经验与代码）")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="ShanghaiTech Course Materials Query Engine")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # get command
    get_p = subparsers.add_parser("get", help="Get complete materials for a course")
    get_p.add_argument("course", help="Course code (e.g. CS100) or Chinese name/alias (e.g. 计算机编程, 大物, 数分)")
    get_p.add_argument("--json", action="store_true", help="Output raw JSON instead of markdown")

    # search command
    search_p = subparsers.add_parser("search", help="Fuzzy search courses in the database")
    search_p.add_argument("keyword", help="Search keyword")
    search_p.add_argument("--limit", type=int, default=10, help="Max results to display")

    # list command
    list_p = subparsers.add_parser("list", help="List all courses with available materials")
    list_p.add_argument("--dept", help="Filter by department/institute keyword")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    index = load_index()

    if args.command == "get":
        target = resolve_course_code(index, args.course)
        if not target:
            print(f"❌ 未在资料库中找到与 '{args.course}' 匹配的课程。", file=sys.stderr)
            print("💡 建议：可使用 `python3 scripts/query_materials.py search <关键词>` 模糊检索课程代码。", file=sys.stderr)
            sys.exit(1)
        
        if isinstance(target, list):
            print(f"🔍 找到多个可能的匹配项，请输入具体课号或更精确的名称：")
            for c in target[:8]:
                info = index["courses"][c]
                print(f"  - [{c}] {info.get('name_zh')} ({info.get('institute')})")
            sys.exit(0)
            
        course = index["courses"][target]
        if args.json:
            print(json.dumps(course, ensure_ascii=False, indent=2))
        else:
            print(format_markdown_report(course))

    elif args.command == "search":
        kw = args.keyword.strip().lower()
        matches = []
        for code, info in index["courses"].items():
            name_zh = info.get("name_zh", "").lower()
            name_en = info.get("name_en", "").lower()
            aliases = [a.lower() for a in info.get("aliases", [])]
            inst = info.get("institute", "").lower()
            
            score = 0
            if kw == code.lower() or kw == name_zh:
                score = 100
            elif kw in code.lower() or kw in name_zh:
                score = 80
            elif any(kw in a for a in aliases):
                score = 60
            elif kw in name_en or kw in inst:
                score = 40
                
            if score > 0:
                matches.append((score, code, info))
                
        matches.sort(key=lambda x: x[0], reverse=True)
        results = matches[:args.limit]
        
        if not results:
            print(f"❌ 未找到包含关键词 '{args.keyword}' 的课程资料。")
            sys.exit(0)
            
        print(f"🔍 找到 {len(matches)} 门相关课程（展示前 {len(results)} 个）：\n")
        print(f"| 课号 | 课程名称 | 开课学院 | 包含资料库 | 常用别名 |")
        print(f"| :--- | :--- | :--- | :--- | :--- |")
        for _, code, info in results:
            res = info.get("resources", {})
            sources = []
            if res.get("itechx", {}).get("available"):
                sources.append("iTechX")
            if res.get("xiongwenye", {}).get("available"):
                sources.append("XiongWenye")
            if res.get("zsc2003", {}).get("available"):
                sources.append("zsc2003")
            s_str = ", ".join(sources)
            
            # colloquial aliases subset
            als = [a for a in info.get("aliases", []) if a.lower() != code.lower() and a != info.get("name_zh")][:3]
            als_str = "/".join(als) if als else "-"
            
            print(f"| **{code}** | {info.get('name_zh')} | {info.get('institute', '上海科技大学')} | {s_str} | {als_str} |")

    elif args.command == "list":
        dept_filter = args.dept.strip().lower() if args.dept else None
        count = 0
        print(f"📋 上海科技大学全课程复习与资料库清单：\n")
        print(f"| 课号 | 课程名称 | 学分 | 开课学院 | 资料来源 |")
        print(f"| :--- | :--- | :--- | :--- | :--- |")
        for code, info in sorted(index["courses"].items()):
            inst = info.get("institute", "上海科技大学")
            if dept_filter and dept_filter not in inst.lower() and dept_filter not in info.get("name_zh", "").lower():
                continue
            count += 1
            res = info.get("resources", {})
            sources = []
            if res.get("itechx", {}).get("available"):
                sources.append("iTechX")
            if res.get("xiongwenye", {}).get("available"):
                sources.append("XiongWenye")
            if res.get("zsc2003", {}).get("available"):
                sources.append("zsc2003")
            print(f"| **{code}** | {info.get('name_zh')} | {info.get('credit', 0)} | {inst} | {', '.join(sources)} |")
        print(f"\n共计 {count} 门课程具备完整资料。")


if __name__ == "__main__":
    main()
