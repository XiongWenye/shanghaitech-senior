#!/usr/bin/env python3
"""
ShanghaiTech Major Curriculum & Personalized Course Recommendation Engine
Supports all 2026 Grade Majors (and 2023 Grade):
- CS (计算机科学与技术)
- CS-AI (人工智能荣誉班)
- EE (电子信息工程)
- MATH (数学与应用数学)
- ICS (信息与计算科学)
- PHYS (物理学)
- CHEM (化学)
- MSE (材料科学与工程)
- BIOSCI (生物科学)
- BIOTECH (生物技术)
- BME (生物医学工程)
- ID (工业设计)

Provides:
1. 'roadmap': Semester course progression plan with CourseBench ratings & workload warnings
2. 'diagnose': EAMS plan completion gap analysis + gap-targeted CourseBench recommendations
3. 'list': Available curriculums and graduation requirements
"""

import os
import sys
import json
import re
import argparse
import sqlite3

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPTS_DIR, "..", "data")
CURRICULUM_DIR = os.path.join(DATA_DIR, "curriculums")
DB_PATH = os.path.join(DATA_DIR, "coursebench.db")

# Import query_course engine
sys.path.append(SCRIPTS_DIR)
try:
    from query_course import recommend_courses, get_course_detail, search_courses
except ImportError:
    pass

MAJOR_ALIASES = {
    # CS
    "cs": "2026_CS_SIST.json",
    "计算机": "2026_CS_SIST.json",
    "计算机科学与技术": "2026_CS_SIST.json",
    "计科": "2026_CS_SIST.json",
    # CS-AI
    "ai": "2026_CS_AI_SIST.json",
    "ai班": "2026_CS_AI_SIST.json",
    "人工智能": "2026_CS_AI_SIST.json",
    "人工智能荣誉班": "2026_CS_AI_SIST.json",
    "ai荣誉班": "2026_CS_AI_SIST.json",
    # EE
    "ee": "2026_EE_SIST.json",
    "电子": "2026_EE_SIST.json",
    "电子信息": "2026_EE_SIST.json",
    "电子信息工程": "2026_EE_SIST.json",
    "电通": "2026_EE_SIST.json",
    # MATH
    "math": "2026_MATH_IMS.json",
    "数学": "2026_MATH_IMS.json",
    "数学与应用数学": "2026_MATH_IMS.json",
    "应数": "2026_MATH_IMS.json",
    # ICS
    "ics": "2026_ICS_IMS.json",
    "信计": "2026_ICS_IMS.json",
    "信息与计算科学": "2026_ICS_IMS.json",
    # PHYS
    "phys": "2026_PHYS_SPST.json",
    "物理": "2026_PHYS_SPST.json",
    "物理学": "2026_PHYS_SPST.json",
    # CHEM
    "chem": "2026_CHEM_SPST.json",
    "化学": "2026_CHEM_SPST.json",
    # MSE
    "mse": "2026_MSE_SPST.json",
    "材料": "2026_MSE_SPST.json",
    "材料科学与工程": "2026_MSE_SPST.json",
    # BIOSCI
    "biosci": "2026_BIOSCI_SLST.json",
    "生科": "2026_BIOSCI_SLST.json",
    "生物科学": "2026_BIOSCI_SLST.json",
    # BIOTECH
    "biotech": "2026_BIOTECH_SLST.json",
    "生技": "2026_BIOTECH_SLST.json",
    "生物技术": "2026_BIOTECH_SLST.json",
    # BME
    "bme": "2026_BME_BME.json",
    "生医工": "2026_BME_BME.json",
    "生物医学工程": "2026_BME_BME.json",
    # ID
    "id": "2026_ID_SCA.json",
    "工设": "2026_ID_SCA.json",
    "工业设计": "2026_ID_SCA.json",
    "创艺": "2026_ID_SCA.json"
}

def resolve_curriculum(major_str, grade=2026):
    """Resolves curriculum path from user input (e.g. '物理', 2026)."""
    major_lower = major_str.strip().lower()
    
    if grade == 2023 and major_lower in ["cs", "计算机", "计科"]:
        p = os.path.join(CURRICULUM_DIR, "2023_CS_SIST.json")
        if os.path.exists(p):
            return p

    if major_lower in MAJOR_ALIASES:
        p = os.path.join(CURRICULUM_DIR, MAJOR_ALIASES[major_lower])
        if os.path.exists(p):
            return p

    # Fuzzy match in curriculums directory
    for fname in os.listdir(CURRICULUM_DIR):
        if not fname.endswith(".json"):
            continue
        if str(grade) in fname and any(k in fname for k in [major_str, major_lower]):
            return os.path.join(CURRICULUM_DIR, fname)
            
    # Default to 2026_CS_SIST.json
    return os.path.join(CURRICULUM_DIR, "2026_CS_SIST.json")

def load_curriculum(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def format_cb_score(cb):
    if not cb or not cb.get("score_quality"):
        return "暂无评测"
    return f"质量⭐{cb['score_quality']:.1f} | 课业轻松度⭐{cb['score_workload']:.1f} | 给分⭐{cb['score_grade']:.1f} ({cb['comment_num']}条评语)"

def get_semester_name(sem_num):
    year = (sem_num - 1) // 3 + 1
    term_idx = (sem_num - 1) % 3
    term_names = ["秋季", "春季", "夏季"]
    year_names = ["大一", "大二", "大三", "大四"]
    return f"{year_names[min(year-1, 3)]}{term_names[term_idx]}学期 (学期 {sem_num})"

def cmd_roadmap(args):
    cur_path = resolve_curriculum(args.major, args.grade)
    curr = load_curriculum(cur_path)
    
    print("=" * 78)
    print(f"📖 上海科技大学【{curr['grade']}级 {curr['major']}】培养方案修课路线与指南")
    print(f"🏛️ 院系: {curr['institute']} | 🎓 学位: {curr['degree']} | 🎯 方向: {curr['track']}")
    print(f"📊 最低毕业学分要求: {curr['min_total_credits']} 学分")
    print("=" * 78)
    
    roadmap = curr.get("semester_roadmap", {})
    target_sem = str(args.semester) if args.semester else None
    
    sems_to_show = [target_sem] if target_sem and target_sem in roadmap else [str(i) for i in range(1, 9)]
    
    for s_str in sems_to_show:
        s_num = int(s_str)
        s_title = get_semester_name(s_num)
        courses = roadmap.get(s_str, [])
        if not courses and target_sem:
            print(f"\n[!] 第 {s_num} 学期在培养方案中暂未列出固定必修课，通常为专业选修、跨学科或毕业设计阶段。")
            continue
        elif not courses:
            continue
            
        total_cred = sum(c.get("credit", 0.0) for c in courses)
        print(f"\n### 🗓️ {s_title} (官方推荐修读: {len(courses)} 门, 约 {total_cred:.1f} 学分)")
        print("-" * 78)
        
        comp_courses = [c for c in courses if c.get("is_compulsory")]
        elec_courses = [c for c in courses if not c.get("is_compulsory")]
        
        if comp_courses:
            print("  📌 【必修/核心环节】:")
            for c in comp_courses:
                cb = c.get("coursebench")
                cb_str = format_cb_score(cb)
                c_name = cb.get("official_name") if cb and cb.get("official_name") else c["name"]
                print(f"    • {c_name} (`{c['code']}`, {c.get('credit', '?')}学分) - [{c.get('module', '必修')}]")
                print(f"      CourseBench: {cb_str}")
                
        if elec_courses:
            print("  💡 【推荐选修/任选课程】:")
            for c in elec_courses:
                cb = c.get("coursebench")
                cb_str = format_cb_score(cb)
                c_name = cb.get("official_name") if cb and cb.get("official_name") else c["name"]
                print(f"    • {c_name} (`{c['code']}`, {c.get('credit', '?')}学分) - [{c.get('module', '选修')}]")
                print(f"      CourseBench: {cb_str}")

    # General Education tips for this semester
    print("\n💡 【选课建议与负荷平衡提示】:")
    if args.semester == 2:
        print("  1. 春季学期数理与编程硬课较多（如编程、数分II、电路基础等），切忌堆叠过多硬核大课。")
        print("  2. 通识建议搭配 1 门给分好、负担轻的人文社科选修（如创意与艺术、经典导读或经管选修）来调剂课业负担。")
        print("  3. 体育建议选修羽毛球、网球、击剑等专项，提前完成 7 学分体育要求。")
    elif args.semester == 1:
        print("  1. 大一秋季学期为大学适应期，信息导论 (SI100B)、线性代数 (MATH1112) 与高数/数分均为基础核心。")
        print("  2. 注意思政课（思想道德与法治）与书院通识必修（心理健康、军事理论）的学分安排。")
    print("=" * 78)

def cmd_list(args):
    print("=" * 78)
    print("📚 上海科技大学已收录本科专业培养方案知识库")
    print("=" * 78)
    for fname in sorted(os.listdir(CURRICULUM_DIR)):
        if not fname.endswith(".json"):
            continue
        p = os.path.join(CURRICULUM_DIR, fname)
        with open(p, "r", encoding="utf-8") as f:
            d = json.load(f)
        print(f"• 【{d.get('grade')}级 {d.get('major')}】({d.get('curriculum_id')})")
        print(f"  - 学院: {d.get('institute')} | 方向: {d.get('track', '通用')} | 毕业学分: {d.get('min_total_credits')} 学分")
        print(f"  - 模块数: {len(d.get('modules', []))} | 方案课程库: {len(d.get('all_courses', []))} 门")
    print("=" * 78)

def main():
    parser = argparse.ArgumentParser(description="ShanghaiTech CourseBench Study Plan & Curriculum Recommendation Engine")
    subparsers = parser.add_subparsers(dest="subcommand", help="Sub-commands")
    
    # roadmap
    p_roadmap = subparsers.add_parser("roadmap", help="View semester study roadmap with CourseBench ratings")
    p_roadmap.add_argument("--major", required=True, help="Major name or code (e.g. 计算机, 物理, AI荣誉班, 生医工)")
    p_roadmap.add_argument("--grade", type=int, default=2026, help="Grade year (default: 2026)")
    p_roadmap.add_argument("--semester", type=int, default=None, help="Specific semester number (1 to 8)")
    
    # list
    p_list = subparsers.add_parser("list", help="List all parsed curriculum programs")
    
    args = parser.parse_args()
    if args.subcommand == "roadmap":
        cmd_roadmap(args)
    elif args.subcommand == "list":
        cmd_list(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
