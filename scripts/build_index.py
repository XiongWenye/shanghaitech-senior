#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build Comprehensive Course Materials Index for ShanghaiTech
Aggregates resources from:
1. iTechX (file-base branch)
2. XiongWenye's shanghaitech-course-database
3. zsc2003's courses-summary
4. CourseBench database cross-referencing
"""

import os
import sys
import json
import sqlite3
import urllib.parse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CB_DB_PATH = DATA_DIR / "coursebench.db"
XW_LOCAL_PATH = Path("/Users/bearxiong/Documents/ShanghaiTech/shanghaitech-course-database")
ITECHX_PATHS_FILE = DATA_DIR / "itechx_paths.txt"
OUTPUT_INDEX_FILE = DATA_DIR / "materials_index.json"

ITECHX_BASE_URL = "https://github.com/i-TechX/iTechX/tree/file-base"
ITECHX_BLOB_URL = "https://github.com/i-TechX/iTechX/blob/file-base"
XW_BASE_URL = "https://github.com/XiongWenye/shanghaitech-course-database/tree/main"
XW_BLOB_URL = "https://github.com/XiongWenye/shanghaitech-course-database/blob/main"

# zsc2003 course mapping from courses-summary
ZSC_COURSES = {
    "SI100B": {
        "title": "Introduction to Information Science and Technology",
        "url": "https://github.com/zsc2003/ShanghaiTech-SI100B",
        "semesters": ["Fall 2021"],
        "category": "Foundational"
    },
    "CS100": {
        "title": "Introduction to Programming",
        "url": "https://github.com/zsc2003/ShanghaiTech-CS100",
        "semesters": ["Spring 2022", "Spring 2023 (tutorial)", "Spring 2024 (tutorial)"],
        "category": "Core CS"
    },
    "SI120": {
        "title": "Discrete Mathematics",
        "url": "https://github.com/zsc2003/ShanghaiTech-SI120",
        "semesters": ["Spring 2022"],
        "category": "Core CS"
    },
    "CS101": {
        "title": "Algorithm and Data Structures",
        "url": "https://github.com/zsc2003/ShanghaiTech-CS101",
        "semesters": ["Fall 2022", "Fall 2024 (tutorial)"],
        "category": "Core CS"
    },
    "CS171": {
        "title": "Computer Graphics",
        "url": "https://github.com/zsc2003/ShanghaiTech-CS171",
        "semesters": ["Fall 2022"],
        "category": "Elective CS"
    },
    "EE150": {
        "title": "Signals and Systems",
        "url": "https://github.com/zsc2003/ShanghaiTech-EE150",
        "semesters": ["Fall 2022"],
        "category": "Core EE"
    },
    "CS110": {
        "title": "Computer Architecture",
        "url": "https://github.com/zsc2003/ShanghaiTech-CS110",
        "semesters": ["Spring 2023"],
        "category": "Core CS"
    },
    "SI140A": {
        "title": "Probability & Statistics for EECS",
        "url": "https://github.com/zsc2003/ShanghaiTech-SI140A",
        "semesters": ["Spring 2023", "Spring 2024 (tutorial)"],
        "category": "Foundational"
    },
    "CS172": {
        "title": "Computer Vision",
        "url": "https://github.com/zsc2003/ShanghaiTech-CS172",
        "semesters": ["Fall 2023"],
        "category": "Elective CS"
    },
    "CS181": {
        "title": "Artificial Intelligence",
        "url": "https://github.com/zsc2003/ShanghaiTech-CS181",
        "semesters": ["Fall 2023"],
        "category": "Core CS"
    },
    "CS182": {
        "title": "Introduction to Machine Learning",
        "url": "https://github.com/zsc2003/ShanghaiTech-CS182",
        "semesters": ["Fall 2023", "Spring 2025 (tutorial)"],
        "category": "Core CS"
    },
    "MATH1112": {
        "title": "Linear Algebra (tutorial)",
        "url": "https://github.com/zsc2003/Shanghaitech-Linear-Algebra",
        "semesters": ["Fall 2023"],
        "category": "Foundational"
    },
    "SI152": {
        "title": "Numerical Optimization",
        "url": "https://github.com/zsc2003/ShanghaiTech-SI152",
        "semesters": ["Fall 2023"],
        "category": "Advanced Math"
    },
    "CS240": {
        "title": "Algorithm Design and Analysis",
        "url": "https://github.com/zsc2003/ShanghaiTech-CS240",
        "semesters": ["Spring 2024"],
        "category": "Advanced CS"
    },
    "CS270": {
        "title": "Digital Image Processing",
        "url": "https://github.com/zsc2003/ShanghaiTech-CS270",
        "semesters": ["Spring 2024"],
        "category": "Elective CS"
    },
    "CS282": {
        "title": "Machine Learning",
        "url": "https://github.com/zsc2003/ShanghaiTech-CS282",
        "semesters": ["Spring 2024"],
        "category": "Advanced CS"
    },
    "SI251": {
        "title": "Convex Optimization",
        "url": "https://github.com/zsc2003/ShanghaiTech-SI251",
        "semesters": ["Spring 2024"],
        "category": "Advanced Math"
    },
    "EE142": {
        "title": "Fundamentals of Information Theory",
        "url": "https://github.com/zsc2003/ShanghaiTech-EE142",
        "semesters": ["Fall 2024"],
        "category": "Core EE"
    },
    "SI151A": {
        "title": "Convex Optimization and Its Applications in Information Science",
        "url": "https://github.com/zsc2003/ShanghaiTech-SI151A",
        "semesters": ["Fall 2024"],
        "category": "Advanced Math"
    },
    "CS290T": {
        "title": "Project Practice for Reinforcement Learning",
        "url": "https://github.com/zsc2003/ShanghaiTech-CS290T",
        "semesters": ["Spring 2025"],
        "category": "Advanced CS"
    },
    "MATH1426": {
        "title": "Numerical Analysis",
        "url": "https://github.com/zsc2003/ShanghaiTech-MATH1426",
        "semesters": ["Spring 2025"],
        "category": "Advanced Math"
    },
    "SI199": {
        "title": "Bachelor's Thesis",
        "url": "https://github.com/zsc2003/ShanghaiTech-SI199",
        "semesters": ["Spring 2025"],
        "category": "Graduation"
    },
    "SI252": {
        "title": "Reinforcement Learning",
        "url": "https://github.com/zsc2003/ShanghaiTech-SI252",
        "semesters": ["Spring 2025"],
        "category": "Advanced CS"
    },
    # Tsinghua Master Courses (Advanced Topics)
    "74760174": {
        "title": "Advanced Numerical Analysis",
        "url": "https://github.com/zsc2003/Advanced-Numerical-Analysis",
        "semesters": ["Fall 2025"],
        "category": "Master Advanced Math"
    },
    "74760293": {
        "title": "Python Programming for Data and Computation",
        "url": "https://github.com/zsc2003/Python-Programming-for-Data-and-Computation",
        "semesters": ["Fall 2025"],
        "category": "Data & Python"
    },
    "74760303": {
        "title": "Introduction to Modern Artificial Intelligence",
        "url": "https://github.com/zsc2003/Introduction-to-Modern-Artificial-Intelligence",
        "semesters": ["Fall 2025"],
        "category": "Modern AI"
    },
    "84760144": {
        "title": "Machine Learning Theory",
        "url": "https://github.com/zsc2003/Machine-Learning-Theory",
        "semesters": ["Fall 2025"],
        "category": "ML Theory"
    },
    "84760513": {
        "title": "Online Learning and Decision-Making",
        "url": "https://github.com/zsc2003/Online-Learning-and-Decision-Making",
        "semesters": ["Fall 2025"],
        "category": "Online Learning"
    },
    "84761063": {
        "title": "Deep Learning",
        "url": "https://github.com/zsc2003/Deep-Learning",
        "semesters": ["Fall 2025"],
        "category": "Deep Learning"
    },
    "74760213": {
        "title": "Convex Optimization: Theory and Algorithms",
        "url": "https://github.com/zsc2003/Convex-Optimization-Theory-and-Algorithms",
        "semesters": ["Spring 2026"],
        "category": "Convex Optimization"
    },
    "80421534": {
        "title": "Optimization Algorithms for Machine Learning",
        "url": "https://github.com/zsc2003/Optimization-Algorithms-for-Machine-Learning",
        "semesters": ["Spring 2026"],
        "category": "Optimization for ML"
    },
    "80470253": {
        "title": "Deep Reinforcement Learning",
        "url": "https://github.com/zsc2003/Deep-Reinforcement-Learning",
        "semesters": ["Spring 2026"],
        "category": "Deep RL"
    },
    "84760773": {
        "title": "High Performance Computing and AI for Science",
        "url": "https://github.com/zsc2003/High-Performance-Computing-and-AI-for-Science",
        "semesters": ["Spring 2026"],
        "category": "HPC & AI4Science"
    },
    "84761173": {
        "title": "Algorithm Design",
        "url": "https://github.com/zsc2003/Algorithm-Design",
        "semesters": ["Spring 2026"],
        "category": "Algorithm Design"
    },
    "84760533": {
        "title": "Topics in Optimization",
        "url": "https://github.com/zsc2003/Topics-in-Optimization",
        "semesters": ["Fall 2026"],
        "category": "Topics in Optimization"
    }
}

# Aliases and colloquial keywords mapping
COLLOQUIAL_ALIASES = {
    "CS100": ["计编", "计算机编程", "程序设计", "程设", "C++", "Python", "Intro to Programming"],
    "CS101": ["数构", "数据结构", "算法与数据结构", "算法", "DSA", "Data Structures"],
    "CS110": ["计系", "体系结构", "计算机体系结构", "CA", "Computer Architecture"],
    "CS120": ["离散", "离散数学"],
    "SI120": ["离散", "离散数学"],
    "CS171": ["图形学", "计算机图形学", "CG", "Computer Graphics"],
    "CS172": ["视觉", "计算机视觉", "CV", "Computer Vision"],
    "CS181": ["人工智能", "AI", "人工智能I"],
    "CS182": ["机器学习", "ML", "机器学习引论"],
    "CS240": ["高算", "高级算法", "算法设计与分析"],
    "EE150": ["信号", "信号与系统", "Signals"],
    "SI140A": ["概统", "概率论", "概率统计", "概率论与数理统计", "Prob & Stat"],
    "MATH1111": ["数分1", "数分I", "数学分析I", "数学分析1"],
    "MATH1112": ["线代", "线性代数", "线性代数I", "Linear Algebra"],
    "GEMA1009": ["数分1", "数分I", "数学分析I"],
    "GEMA1010": ["数分2", "数分II", "数学分析II"],
    "GEMA1001": ["高数1", "高数I", "高等数学I"],
    "GEMA1002": ["高数2", "高数II", "高等数学II"],
    "GEMA1003": ["高数1", "高数I", "高等数学I"],
    "GEMA1004": ["高数2", "高数II", "高等数学II"],
    "PHYS1181": ["大物1", "大物I", "普通物理I", "普物1", "普物I"],
    "PHYS1183": ["大物2", "大物II", "普通物理II", "普物2", "普物II"],
    "PHYS1111": ["大物实验", "普通物理I实验", "大物实验1"],
    "CHEM1103": ["普化1", "普化I", "普通化学I"],
    "CHEM1111": ["普化2", "普化II", "普通化学II"],
    "CHEM1322": ["有机", "有机化学", "有机化学基础"],
    "BIO1006": ["分生", "分子生物学"],
    "BIO1024": ["分生实验", "分子生物学实验"],
    "BIO1003": ["生化1", "生化I", "生物化学I"],
    "BIO1004": ["生化2", "生化II", "生物化学II"],
    "GEHA1001": ["世通", "世界文明通论"],
    "GEHA1003": ["世通", "世界文明通论"],
    "GEHA1002": ["中公", "中通", "中华文明通论"],
    "GEHA1050": ["中公", "中通", "中华文明通论"],
    "ECON1001": ["经导", "经济学导论"],
    "CLEC1003": ["军理", "军事理论"],
    "SI152": ["数值优化", "数值最优化"],
    "SI251": ["凸优化", "Convex Optimization"],
    "SI151A": ["信息科学中的凸优化", "凸优化应用"],
    "SI199": ["毕业论文", "本科毕业设计", "毕设", "Thesis"]
}

# Chinese course name to Code resolver
ZH_TO_CODE = {
    "计算机编程": "CS100",
    "算法与数据结构": "CS101",
    "计算机体系结构": "CS110",
    "离散数学": "SI120",
    "计算机图形学": "CS171",
    "信号与系统": "EE150",
    "概率论与数理统计": "SI140A",
    "计算机视觉": "CS172",
    "人工智能I": "CS181",
    "机器学习引论": "CS182",
    "数学分析I": "GEMA1009",
    "数学分析II": "GEMA1010",
    "高等数学I": "GEMA1001",
    "高等数学II": "GEMA1003",
    "线性代数I": "MATH1112",
    "普通物理I": "PHYS1181",
    "普通物理II": "PHYS1183",
    "普通物理I实验": "PHYS1111",
    "普通化学I": "CHEM1103",
    "普通化学II": "CHEM1111",
    "有机化学基础": "CHEM1322",
    "有机化学基础实验": "CHEM1340",
    "生物化学I": "BIO1003",
    "生物化学II": "BIO1004",
    "生物化学I实验": "BIO1021",
    "生物化学II实验": "BIO1022",
    "分子生物学": "BIO1006",
    "分子生物学实验": "BIO1024",
    "细胞生物学": "BIO1005",
    "细胞生物学实验": "BIO1023",
    "遗传学": "BIO1007",
    "癌症生物学": "BIO1068",
    "神经科学导论": "BIO1102",
    "分子细胞神经科学": "BIO2053",
    "果蝇生物学": "BIO1223",
    "现代生命科学导论B": "BIO1002",
    "现代生命科学导论C": "BIO1011",
    "现代生物学实验理论": "BIO1026",
    "生命科学导论A": "BIO1012",
    "生命科学导论B": "BIO1013",
    "生命科学与人类文明": "SL1012",
    "半导体器件基础": "EE120",
    "量子力学I": "PHYS1521",
    "量子力学II": "PHYS1531",
    "广义相对论与宇宙学": "PHYS2517",
    "世界文明通论": "GEHA1003",
    "中华文明通论": "GEHA1050",
    "经济学导论": "ECON1001",
    "军事理论": "CLEC1003",
    "中外歌剧赏析": "CLGE1007"
}


def load_coursebench_db():
    courses = {}
    if not CB_DB_PATH.exists():
        return courses
    conn = sqlite3.connect(CB_DB_PATH)
    c = conn.cursor()
    c.execute("SELECT code, name, institute, credit, score_quality, score_workload, score_difficulty, score_grade FROM courses")
    for row in c.fetchall():
        code, name, inst, cr, sq, sw, sd, sg = row
        courses[code] = {
            "code": code,
            "name": name,
            "institute": inst,
            "credit": cr,
            "scores": {
                "quality": sq,
                "workload": sw,
                "difficulty": sd,
                "grade": sg
            }
        }
    conn.close()
    return courses


def parse_itechx():
    """Parse iTechX file tree into structured course materials."""
    if not ITECHX_PATHS_FILE.exists():
        return {}
    
    with open(ITECHX_PATHS_FILE, "r", encoding="utf-8") as f:
        paths = [line.strip() for line in f if line.strip()]

    itechx_data = {}
    for path in paths:
        parts = path.split("/")
        if len(parts) < 2 or parts[0] != "courses":
            continue
        
        course_code = parts[1]
        if course_code not in itechx_data:
            encoded_code = urllib.parse.quote(course_code)
            itechx_data[course_code] = {
                "repo_url": f"{ITECHX_BASE_URL}/courses/{encoded_code}",
                "semesters": set(),
                "categories": {
                    "exams": [],
                    "homework_solutions": [],
                    "homework": [],
                    "slides_notes": [],
                    "projects": [],
                    "recitations": [],
                    "others": []
                },
                "key_files": []
            }
        
        item = itechx_data[course_code]
        if len(parts) >= 3 and not parts[2].endswith((".jpg", ".json", ".md")):
            semester = parts[2]
            item["semesters"].add(semester)
            
            if len(parts) >= 4:
                cat_folder = parts[3]
                subpath = "/".join(parts[:4])
                encoded_subpath = urllib.parse.quote(subpath)
                folder_url = f"{ITECHX_BASE_URL}/{encoded_subpath}"
                
                cat_info = {
                    "semester": semester,
                    "folder": cat_folder,
                    "url": folder_url
                }
                
                # Deduplicated add to category
                def add_unique(cat_list, entry):
                    if not any(x["url"] == entry["url"] for x in cat_list):
                        cat_list.append(entry)

                cf_lower = cat_folder.lower()
                if "exam" in cf_lower or "考试" in cf_lower or "quiz" in cf_lower or "测验" in cf_lower:
                    if "solution" in cf_lower or "答案" in cf_lower:
                        add_unique(item["categories"]["homework_solutions"], cat_info)
                    else:
                        add_unique(item["categories"]["exams"], cat_info)
                elif "solution" in cf_lower or "答案" in cf_lower:
                    add_unique(item["categories"]["homework_solutions"], cat_info)
                elif "homework" in cf_lower or "作业" in cf_lower:
                    add_unique(item["categories"]["homework"], cat_info)
                elif "slide" in cf_lower or "课件" in cf_lower or "note" in cf_lower or "笔记" in cf_lower:
                    add_unique(item["categories"]["slides_notes"], cat_info)
                elif "recitation" in cf_lower or "tutorial" in cf_lower or "复习课" in cf_lower or "习题课" in cf_lower:
                    add_unique(item["categories"]["recitations"], cat_info)
                elif "project" in cf_lower or "设计" in cf_lower or "项目" in cf_lower:
                    add_unique(item["categories"]["projects"], cat_info)
                else:
                    add_unique(item["categories"]["others"], cat_info)
        
        # Check for standout key files (PDFs of finals/midterms or solutions)
        filename = parts[-1]
        fn_lower = filename.lower()
        if fn_lower.endswith((".pdf", ".docx", ".zip", ".md")):
            if any(k in fn_lower for k in ["final", "midterm", "期末", "期中", "exam", "solution", "答案", "summary"]):
                encoded_file_path = urllib.parse.quote(path)
                item["key_files"].append({
                    "name": filename,
                    "rel_path": path,
                    "url": f"{ITECHX_BLOB_URL}/{encoded_file_path}"
                })

    # Convert sets to sorted lists
    for code, d in itechx_data.items():
        d["semesters"] = sorted(list(d["semesters"]))
        # Keep top 12 representative key files
        d["key_files"] = d["key_files"][:12]

    return itechx_data


def parse_xiongwenye():
    """Parse XiongWenye's local shanghaitech-course-database directory."""
    if not XW_LOCAL_PATH.exists():
        return {}

    xw_data = {}
    for root, dirs, files in os.walk(XW_LOCAL_PATH):
        if ".git" in root:
            continue
        rel_root = os.path.relpath(root, XW_LOCAL_PATH)
        if rel_root == ".":
            continue
        
        course_name = rel_root.split("/")[0]
        if course_name not in xw_data:
            encoded_name = urllib.parse.quote(course_name)
            xw_data[course_name] = {
                "folder_name": course_name,
                "repo_url": f"{XW_BASE_URL}/{encoded_name}",
                "exams": [],
                "solutions": [],
                "slides_notes": [],
                "labs": [],
                "others": [],
                "total_files": 0
            }
        
        item = xw_data[course_name]
        for f in files:
            if f.startswith("."):
                continue
            item["total_files"] += 1
            full_rel = os.path.join(rel_root, f)
            encoded_rel = urllib.parse.quote(full_rel)
            file_url = f"{XW_BLOB_URL}/{encoded_rel}"
            
            file_info = {
                "name": f,
                "rel_path": full_rel,
                "url": file_url
            }
            
            fl = f.lower()
            if any(k in fl for k in ["期末", "期中", "试卷", "midterm", "final", "exam", "考试", "真题", "中大题", "选填"]):
                if any(k in fl for k in ["答案", "解析", "solution", "key", "评分标准"]):
                    item["solutions"].append(file_info)
                else:
                    item["exams"].append(file_info)
            elif any(k in fl for k in ["答案", "解析", "solution", "key"]):
                item["solutions"].append(file_info)
            elif any(k in fl for k in ["实验", "lab"]):
                item["labs"].append(file_info)
            elif any(k in fl for k in ["讲义", "课件", "ppt", "slide", "第", "章", "note", "笔记", "mp4"]):
                item["slides_notes"].append(file_info)
            else:
                item["others"].append(file_info)

    return xw_data


def build_unified_index():
    cb_courses = load_coursebench_db()
    itechx_data = parse_itechx()
    xw_data = parse_xiongwenye()

    all_course_codes = set()
    all_course_codes.update(cb_courses.keys())
    all_course_codes.update(itechx_data.keys())
    all_course_codes.update(ZSC_COURSES.keys())

    # Map XiongWenye courses to canonical codes
    xw_to_code = dict(ZH_TO_CODE)

    # Invert mapping to find courses for code
    code_to_xw = {}
    for zh, code in xw_to_code.items():
        if zh in xw_data:
            code_to_xw[code] = zh

    # Also handle courses in xw_data not yet explicitly mapped
    for folder in xw_data:
        if folder not in xw_to_code:
            # try finding in cb_courses by name
            for c_code, c_info in cb_courses.items():
                if c_info["name"] == folder or folder in c_info["name"]:
                    xw_to_code[folder] = c_code
                    code_to_xw[c_code] = folder
                    break

    all_course_codes.update(code_to_xw.keys())

    unified_catalog = {}

    for code in sorted(all_course_codes):
        cb_info = cb_courses.get(code, {})
        itechx_item = itechx_data.get(code)
        zsc_item = ZSC_COURSES.get(code)
        xw_folder = code_to_xw.get(code)
        xw_item = xw_data.get(xw_folder) if xw_folder else None

        # Determine if this course has any resources at all
        has_resources = bool(itechx_item or zsc_item or xw_item)
        if not has_resources:
            continue

        name_zh = cb_info.get("name") or (xw_folder if xw_folder else "")
        name_en = zsc_item.get("title") if zsc_item else ""
        institute = cb_info.get("institute", "上海科技大学")
        credit = cb_info.get("credit", 0.0)
        scores = cb_info.get("scores", {})

        # Build aliases list
        aliases = set()
        aliases.add(code.lower())
        aliases.add(code.upper())
        if name_zh:
            aliases.add(name_zh)
        if name_en:
            aliases.add(name_en.lower())
        
        # Add colloquial aliases
        if code in COLLOQUIAL_ALIASES:
            for al in COLLOQUIAL_ALIASES[code]:
                aliases.add(al.lower())
                aliases.add(al)

        course_entry = {
            "code": code,
            "name_zh": name_zh,
            "name_en": name_en,
            "institute": institute,
            "credit": credit,
            "cb_scores": scores,
            "aliases": sorted(list(aliases)),
            "resources": {}
        }

        # 1. iTechX
        if itechx_item:
            course_entry["resources"]["itechx"] = {
                "available": True,
                "repo_url": itechx_item["repo_url"],
                "semesters_count": len(itechx_item["semesters"]),
                "semesters": itechx_item["semesters"],
                "categories": itechx_item["categories"],
                "key_files": itechx_item["key_files"]
            }

        # 2. XiongWenye
        if xw_item:
            course_entry["resources"]["xiongwenye"] = {
                "available": True,
                "folder_name": xw_folder,
                "repo_url": xw_item["repo_url"],
                "total_files": xw_item["total_files"],
                "exams": xw_item["exams"][:15],
                "solutions": xw_item["solutions"][:10],
                "slides_notes": xw_item["slides_notes"][:10],
                "labs": xw_item["labs"][:10]
            }

        # 3. zsc2003
        if zsc_item:
            course_entry["resources"]["zsc2003"] = {
                "available": True,
                "title": zsc_item["title"],
                "repo_url": zsc_item["url"],
                "semesters": zsc_item["semesters"],
                "category": zsc_item["category"]
            }

        unified_catalog[code] = course_entry

    # Create alias inverted index for instant sub-millisecond lookup
    inverted_index = {}
    for code, data in unified_catalog.items():
        for al in data["aliases"]:
            clean_al = al.strip().lower()
            if clean_al not in inverted_index:
                inverted_index[clean_al] = []
            if code not in inverted_index[clean_al]:
                inverted_index[clean_al].append(code)

    final_payload = {
        "metadata": {
            "version": "1.0.0",
            "total_courses_with_materials": len(unified_catalog),
            "sources": {
                "itechx": {
                    "name": "iTechX 课程资源库",
                    "branch": "file-base",
                    "url": "https://github.com/i-TechX/iTechX/tree/file-base"
                },
                "xiongwenye": {
                    "name": "XiongWenye 上科大课程资料共享库",
                    "branch": "main",
                    "url": "https://github.com/XiongWenye/shanghaitech-course-database"
                },
                "zsc2003": {
                    "name": "zsc2003 本硕修课汇总与通关仓库",
                    "branch": "main",
                    "url": "https://github.com/zsc2003/courses-summary"
                }
            }
        },
        "courses": unified_catalog,
        "inverted_index": inverted_index
    }

    with open(OUTPUT_INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(final_payload, f, ensure_ascii=False, indent=2)

    print(f"Successfully generated index to {OUTPUT_INDEX_FILE}")
    print(f"Total courses indexed with materials: {len(unified_catalog)}")


if __name__ == "__main__":
    build_unified_index()
