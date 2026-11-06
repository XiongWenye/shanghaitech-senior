#!/usr/bin/env python3
"""
Curriculum Data Cleaner for ShanghaiTech 2026 Training Programs.
Repairs OCR errors, garbled characters, row concatenations, and department misspellings
using CourseBench official course metadata and rule-based fallbacks.
"""

import os
import json
import glob
import re
import sqlite3

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
CURRICULUM_DIR = os.path.join(DATA_DIR, "curriculums")
DB_PATH = os.path.join(DATA_DIR, "coursebench.db")

# Code fixes for common OCR prefix/character misrecognitions
CODE_FIXES = {
    "IARTS1407": "ARTS1407",
    "IARTS1439": "ARTS1439",
    "IGEHA1074": "GEHA1074",
    "IMATH1311": "MATH1311",
    "IMSE1705": "MSE1705",
    "IMISE1705": "MSE1705",
    "IMSE1325": "MSE1325",
    "IMSE1514": "MSE1514",
    "IMSE2302": "MSE2302",
    "IMSE2509": "MSE2509",
    "IMT1023": "MT1023",
    "IMT1032": "MT1032",
    "IMT1034": "MT1034",
    "ISP2006": "SP2006",
    "MISE1715": "MSE1715",
    "n06zE": "EE290U",
}

# Manual verified mappings for courses absent from CourseBench or severely corrupted in OCR
MANUAL_MAPPING = {
    # Sports Interest Series (CLPE1048-1062)
    "CLPE1048": ("健康体适能", "上道书院"),
    "CLPE1049": ("击剑运动", "上道书院"),
    "CLPE1050": ("健美操运动", "上道书院"),
    "CLPE1051": ("篮球运动", "上道书院"),
    "CLPE1052": ("乒乓球运动", "上道书院"),
    "CLPE1053": ("拳击运动", "上道书院"),
    "CLPE1054": ("跆拳道运动", "上道书院"),
    "CLPE1055": ("网球运动", "上道书院"),
    "CLPE1056": ("游泳运动", "上道书院"),
    "CLPE1057": ("羽毛球运动", "上道书院"),
    "CLPE1058": ("足球运动", "上道书院"),
    "CLPE1059": ("武术运动", "上道书院"),
    "CLPE1060": ("瑜伽运动", "上道书院"),
    "CLPE1061": ("匹克球运动", "上道书院"),
    "CLPE1062": ("赛艇运动", "上道书院"),

    # SIST courses
    "CS110P": ("计算机体系结构课程设计", "信息科学与技术学院"),
    "CS130P": ("操作系统课程设计", "信息科学与技术学院"),
    "CS133H": ("C++进阶编程", "信息科学与技术学院"),
    "CS150": ("数据库与数据挖掘", "信息科学与技术学院"),
    "CS190A": ("音频内容分析导论", "信息科学与技术学院"),
    "CS220": ("计算机网络II", "信息科学与技术学院"),
    "CS290A": ("交互式计算机图形学", "信息科学与技术学院"),
    "CS291B": ("人工智能蛋白质设计", "信息科学与技术学院"),
    "EE111P": ("电路基础课程设计", "信息科学与技术学院"),
    "EE218P": ("数字VLSI设计课程设计", "信息科学与技术学院"),
    "EE290U": ("网络理论与分析", "信息科学与技术学院"),
    "EE290V": ("集成电路设计流程", "信息科学与技术学院"),
    "EE290Z": ("电力电子产品的电磁兼容", "信息科学与技术学院"),
    "EE291G": ("卫星控制与导航系统", "信息科学与技术学院"),
    "SI132": ("线性代数在信息科学中的应用", "信息科学与技术学院"),
    "SI160": ("高阶机器人设计与集成", "信息科学与技术学院"),
    "SI214H": ("偏微分方程数值解（H）", "信息科学与技术学院"),

    # Math & Natural sciences
    "GEMA1201": ("概率论与数理统计及其应用", "数学科学研究所"),
    "MATH1413": ("偏微分方程II", "数学科学研究所"),
    "PHYS1554": ("晶体衍射与衍射成像技术", "物质科学与技术学院"),
    "CHEM2512": ("生物体系物理化学研究方法", "物质科学与技术学院"),
    "BT2003": ("神经信号采集与人机智能技术概览", "生命科学与技术学院"),

    # Humanities & Ideology
    "GEHA1282": ("西方政治哲学经典导读", "人文科学研究院"),
    "GEHA1296": ("《老子》与中国哲学", "人文科学研究院"),
    "GEHA1303": ("1770年到1920年间的美国史", "人文科学研究院"),
    "GEHA1304": ("数字人文：英国小说的兴起", "人文科学研究院"),
    "GEHA1306": ("启蒙时代：现代世界的诞生", "人文科学研究院"),
    "GEHA1307": ("莎士比亚《李尔王》", "人文科学研究院"),
    "GEHA1309": ("全球视野下的科技进步", "人文科学研究院"),
    "MT1021": ("习近平新时代中国特色社会主义思想概论", "思想政治理论课教研部"),
    "MT1023": ("毛泽东思想和中国特色社会主义理论体系概论", "思想政治理论课教研部"),
    "MT1032": ("中华优秀传统文化中的心性理论与实践", "思想政治理论课教研部"),
    "MT1034": ("马克思同时代德国唯物主义与共产主义经典著作导读", "思想政治理论课教研部"),

    # College & Arts
    "CLPS1003": ("大学生心理健康", "上道书院"),
    "ARTS1452": ("物性的叙事：当代首饰的痕迹与秩序", "创意与艺术学院"),
    "SMRT1133": ("综合设计II：产品设计", "创意与艺术学院"),
    "SMRT1134": ("综合设计III：交互设计", "创意与艺术学院"),
    "SMRT1137": ("综合设计IV：情感设计", "创意与艺术学院"),
    "SMRT1138": ("综合设计V：系统设计", "创意与艺术学院"),
}

def clean_dept_str(dept):
    if not dept or dept == "未知单位":
        return dept
    d = dept.replace("学阮", "学院").replace("斫究院", "研究院").replace("艺木学院", "艺术学院")
    d = d.replace("上道予院", "上道书院").replace("上道书院上道书院", "上道书院")
    if "思想政治" in d or "理论课教" in d:
        return "思想政治理论课教研部"
    if "物质科学" in d:
        return "物质科学与技术学院"
    if "生命科学" in d:
        return "生命科学与技术学院"
    if "信息科学" in d:
        return "信息科学与技术学院"
    if "人文科学" in d:
        return "人文科学研究院"
    if "创意与艺" in d or "创艺" in d:
        return "创意与艺术学院"
    return d

def normalize_course_code(code):
    fixed = CODE_FIXES.get(code, code)
    if fixed.startswith("BI0"):
        fixed = "BIO" + fixed[3:]
    return fixed

def load_cb_courses(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        SELECT code, name, institute, score_quality, score_workload, score_difficulty, score_grade,
               comment_num, teachers, latest_semester, semesters, id
        FROM courses
    """)
    rows = c.fetchall()
    conn.close()

    cb_map = {}
    for r in rows:
        cb_map[r[0]] = {
            "name": r[1],
            "institute": r[2],
            "score_quality": round(r[3], 2) if r[3] else 0.0,
            "score_workload": round(r[4], 2) if r[4] else 0.0,
            "score_difficulty": round(r[5], 2) if r[5] else 0.0,
            "score_grade": round(r[6], 2) if r[6] else 0.0,
            "comment_num": r[7] or 0,
            "teachers": r[8] or "",
            "latest_semester": r[9] or "",
            "semesters_history": r[10] or "",
            "coursebench_id": r[11]
        }
    return cb_map

def clean_all_curriculums():
    cb_courses = load_cb_courses(DB_PATH)
    files = sorted(glob.glob(os.path.join(CURRICULUM_DIR, "2026_*.json")))
    print(f"Found {len(files)} curriculum files to process in {CURRICULUM_DIR}...")

    stats = {
        "files_processed": 0,
        "code_fixes": 0,
        "name_fixes": 0,
        "dept_fixes": 0,
        "cb_enrichments": 0
    }

    for fpath in files:
        with open(fpath, "r", encoding="utf-8") as fp:
            data = json.load(fp)

        course_clean_map = {}

        # 1. Clean all_courses
        for c in data.get("all_courses", []):
            old_code = c["code"]
            old_name = c["name"]
            old_dept = c.get("dept", "")

            new_code = normalize_course_code(old_code)
            new_name = old_name
            new_dept = clean_dept_str(old_dept)

            cb_data = cb_courses.get(new_code)
            if cb_data:
                new_name = cb_data["name"]
                if cb_data["institute"] and cb_data["institute"] != "未知单位":
                    new_dept = cb_data["institute"]
                
                # Update/enrich coursebench entry
                c["coursebench"] = {
                    "coursebench_id": cb_data["coursebench_id"],
                    "official_name": cb_data["name"],
                    "score_quality": cb_data["score_quality"],
                    "score_workload": cb_data["score_workload"],
                    "score_difficulty": cb_data["score_difficulty"],
                    "score_grade": cb_data["score_grade"],
                    "comment_num": cb_data["comment_num"],
                    "teachers": cb_data["teachers"],
                    "latest_semester": cb_data["latest_semester"],
                    "semesters_history": cb_data["semesters_history"]
                }
                stats["cb_enrichments"] += 1
            elif new_code in MANUAL_MAPPING:
                m_name, m_dept = MANUAL_MAPPING[new_code]
                new_name = m_name
                if m_dept:
                    new_dept = m_dept
            else:
                new_dept = clean_dept_str(old_dept)

            if new_code != old_code:
                c["code"] = new_code
                stats["code_fixes"] += 1
            if new_name != old_name:
                c["name"] = new_name
                stats["name_fixes"] += 1
            if new_dept != old_dept:
                c["dept"] = new_dept
                stats["dept_fixes"] += 1

            course_clean_map[old_code] = (new_code, new_name, new_dept, c.get("coursebench"))
            course_clean_map[new_code] = (new_code, new_name, new_dept, c.get("coursebench"))

        # 2. Clean modules
        modules = data.get("modules", [])
        mod_list = modules if isinstance(modules, list) else list(modules.values()) if isinstance(modules, dict) else []
        for mod_data in mod_list:
            for item in mod_data.get("compulsory_courses", []):
                code = item.get("code")
                if code in course_clean_map:
                    nc, nn, nd, _ = course_clean_map[code]
                    item["code"] = nc
                    item["name"] = nn
                    item["dept"] = nd
                else:
                    item["name"] = item.get("name", "")
                    item["dept"] = clean_dept_str(item.get("dept", ""))
            for item in mod_data.get("elective_pool", []):
                code = item.get("code")
                if code in course_clean_map:
                    nc, nn, nd, _ = course_clean_map[code]
                    item["code"] = nc
                    item["name"] = nn
                    item["dept"] = nd
                else:
                    item["name"] = item.get("name", "")
                    item["dept"] = clean_dept_str(item.get("dept", ""))

        # 3. Clean semester_roadmap
        roadmap = data.get("semester_roadmap", {})
        if isinstance(roadmap, dict):
            for sem_idx, sem_courses in roadmap.items():
                for item in sem_courses:
                    code = item["code"]
                    if code in course_clean_map:
                        nc, nn, nd, cb_info = course_clean_map[code]
                        item["code"] = nc
                        item["name"] = nn
                        if cb_info:
                            item["coursebench"] = cb_info

        # Save cleaned file
        with open(fpath, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)

        stats["files_processed"] += 1
        print(f"  [✓] Successfully cleaned {os.path.basename(fpath)}")

    print("\n" + "=" * 60)
    print("Curriculum Cleanup Summary:")
    print(f"  Files processed: {stats['files_processed']}")
    print(f"  Course codes repaired: {stats['code_fixes']}")
    print(f"  Course names repaired: {stats['name_fixes']}")
    print(f"  Departments repaired: {stats['dept_fixes']}")
    print(f"  CourseBench enrichments synced: {stats['cb_enrichments']}")
    print("=" * 60)

if __name__ == "__main__":
    clean_all_curriculums()
