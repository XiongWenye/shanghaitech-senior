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
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw_repos"
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
    "SI199": ["毕业论文", "本科毕业设计", "毕设", "Thesis"],
    "EE140": ["通原", "通信原理", "通信", "Principle of Communication", "Comm"],
    "EE160": ["控原", "控制原理", "控制", "Feedback Control"],
    "SI100B": ["信导", "信息导论", "信息科学技术导论", "信息科学与技术导论", "Intro to IST"],
    "GESS1028": ["思修", "思想道德与法治", "思政", "道德与法治", "Ethics and Law"],

    "ARTS1303": ["Unity游戏创作", "Unity", "游戏创作"],
    "ARTS1407": ["用户体验与创新设计", "用户体验", "UX", "创新设计"],
    "ARTS1421": ["交互设计概论", "交互设计", "IxD"],
    "ARTS1422": ["数据可视化", "可视化", "Data Viz", "Vis"],
    "ARTS1423": ["交互产品设计", "产品设计"],
    "ARTS1424": ["三维视觉概念设计", "三维概念设计", "3D视觉"],
    "ARTS1426": ["混合现实设计", "MR设计", "VR", "AR"],
    "ARTS1431": ["增材制造", "3D打印"],
    "ARTS1701": ["设计思维:产品与交互设计的创新方案", "设计思维", "创新方案"],
    "BIO2084": ["人工智能蛋白质设计", "AI蛋白质设计", "蛋白设计"],
    "BME1304": ["脑科学与脑疾病", "脑科学"],
    "BME1312": ["人工智能在医学影像中的应用", "医学影像AI", "医学影像", "MedImg"],
    "BME2003": ["神经信号的采集与人机智能技术概览", "神经信号"],
    "CLGE1005": ["中国殷周青铜器的起源与文化", "青铜器"],
    "CS121": ["并行计算", "并行", "Parallel Computing"],
    "CS130": ["操作系统", "操作系统I", "OS", "Pintos", "Operating Systems"],
    "CS177H": ["生物信息学：软件开发与应用", "生信软件开发", "生物信息学", "Bioinformatics"],
    "CS233": ["医疗信息物理融合系统的软件开发与验证", "医疗CPS", "CPS"],
    "CS275": ["计算机动画与物理仿真", "物理仿真", "计算机动画", "Animation"],
    "CS280": ["深度学习", "DL", "Deep Learning"],
    "CS284": ["SLAM", "同时定位与建图"],
    "EE142": ["基础信息论", "信息论", "Information Theory"],
    "EE150L": ["信号与系统实验", "信号实验"],
    "GEHA1004": ["科技文明通论", "科通", "科技文明"],
    "GEHA1121": ["基础英语I", "英语1", "英语I"],
    "GEHA1124": ["小说阅读与批评", "小说阅读"],
    "GEHA1132": ["基础英语II人文阅读", "基础英语II", "人文阅读"],
    "GEHA1162": ["后殖民时代的南亚", "南亚历史", "南亚"],
    "GEHA1174": ["美国文学与美国梦的始与终", "美国文学"],
    "GEHA1203": ["中国历史地理", "历史地理"],
    "GESS1018": ["中国近代史纲要", "近纲", "近代史纲要", "史纲", "纲要"],
    "GESS1023": ["毛概", "毛泽东思想和中国特色社会主义理论体系概论"],
    "GESS1027": ["马克思主义原理", "马原", "马哲"],
    "GESS1029": ["托克维尔《论美国的民主》精读", "托克维尔", "论美国的民主"],
    "MT1013": ["法治与社会"],
    "CHEM1100": ["普化实验", "普化I实验", "普通化学实验", "普通化学I实验", "CHEM1111L", "CHEM1101"],
    "CHEM1301": ["无机化学", "无机化学基础", "Inorganic Chemistry"],
    "SI114H": ["计算科学与工程", "CSE", "Computational Science"],
    "SEMI1101": ["设计思维", "设计思维与创新设计", "Design Thinking"],
    "CS188": ["人工智能与强化学习项目", "Holdem", "AI项目"],
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
    "通信原理": "EE140",
    "控制原理": "EE160",
    "信息科学技术导论": "SI100B",
    "信息科学与技术导论": "SI100B",
    "思想道德与法治": "GESS1028",
    "思修": "GESS1028",
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
    "中外歌剧赏析": "CLGE1007",

    "Unity游戏创作": "ARTS1303",
    "用户体验与创新设计": "ARTS1407",
    "交互设计概论": "ARTS1421",
    "数据可视化": "ARTS1422",
    "交互产品设计": "ARTS1423",
    "三维视觉概念设计": "ARTS1424",
    "混合现实设计": "ARTS1426",
    "增材制造": "ARTS1431",
    "设计思维:产品与交互设计的创新方案": "ARTS1701",
    "人工智能蛋白质设计": "BIO2084",
    "脑科学与脑疾病": "BME1304",
    "人工智能在医学影像中的应用": "BME1312",
    "神经信号的采集与人机智能技术概览": "BME2003",
    "中国殷周青铜器的起源与文化": "CLGE1005",
    "并行计算": "CS121",
    "操作系统I": "CS130",
    "操作系统": "CS130",
    "生物信息学：软件开发与应用": "CS177H",
    "医疗信息物理融合系统的软件开发与验证": "CS233",
    "计算机动画与物理仿真": "CS275",
    "深度学习": "CS280",
    "SLAM": "CS284",
    "基础信息论": "EE142",
    "信号与系统实验": "EE150L",
    "科技文明通论": "GEHA1004",
    "基础英语I": "GEHA1121",
    "小说阅读与批评": "GEHA1124",
    "基础英语II人文阅读": "GEHA1132",
    "后殖民时代的南亚": "GEHA1162",
    "美国文学与美国梦的始与终": "GEHA1174",
    "中国历史地理": "GEHA1203",
    "中国近代史纲要": "GESS1018",
    "毛概": "GESS1023",
    "马克思主义原理": "GESS1027",
    "托克维尔《论美国的民主》精读": "GESS1029",
    "法治与社会": "MT1013",
    "普通化学I实验": "CHEM1100",
    "普通化学实验": "CHEM1100",
    "无机化学": "CHEM1301",
    "计算科学与工程": "SI114H",
    "设计思维": "SEMI1101",
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
            if is_exam_file(full_rel):
                if is_solution_file(full_rel):
                    item["solutions"].append(file_info)
                else:
                    item["exams"].append(file_info)
            elif is_solution_file(full_rel):
                item["solutions"].append(file_info)
            elif any(k in fl for k in ["实验", "lab"]):
                item["labs"].append(file_info)
            elif any(k in fl for k in ["讲义", "课件", "ppt", "slide", "第", "章", "note", "笔记", "mp4"]):
                item["slides_notes"].append(file_info)
            else:
                item["others"].append(file_info)

    return xw_data


SKKK_BASE_URL = "https://github.com/skkk256/ShanghaiTech-Courses/tree/main"
SKKK_BLOB_URL = "https://github.com/skkk256/ShanghaiTech-Courses/blob/main"
WTY_BASE_URL = "https://github.com/wutianyuan1/ShanghaiTech/tree/main"
WTY_BLOB_URL = "https://github.com/wutianyuan1/ShanghaiTech/blob/main"
PF_BASE_URL = "https://github.com/profetia/shanghaitech/tree/main"
PF_BLOB_URL = "https://github.com/profetia/shanghaitech/blob/main"
GK_BASE_URL = "https://github.com/GKxxUCAS/ShanghaiTech-CS100-Slides/tree/main"
GK_BLOB_URL = "https://github.com/GKxxUCAS/ShanghaiTech-CS100-Slides/blob/main"
RF_BASE_URL = "https://github.com/RulerFuhai/Shanghaitech-CHEM1100/tree/main"
RF_BLOB_URL = "https://github.com/RulerFuhai/Shanghaitech-CHEM1100/blob/main"


def is_exam_file(path):
    fl = path.lower()
    clean_fl = re.sub(r'examples?', '', fl)
    if any(k in clean_fl for k in ['final', 'midterm', '期末', '期中', '试卷', '考试', '真题', 'cheatsheet', 'cheat sheet', 'cheat_sheet', '速查', 'quiz', '小测', '测验']):
        return True
    if re.search(r'[\W_]exam[\W_.]', clean_fl) or clean_fl.endswith(('exam.pdf', 'exam.docx', 'exam.md')):
        return True
    return False

def is_solution_file(path):
    fl = path.lower()
    if any(k in fl for k in ['solution', 'solutions', 'answer', 'answers', '答案', '解析', '评分标准']):
        return True
    if re.search(r'[\W_](sol|ans|key)[\W_.]', fl):
        return True
    if fl.endswith(('_sol.pdf', '-sol.pdf', '_ans.pdf', '-ans.pdf', '_key.pdf', '-key.pdf', '_sol.docx', '-sol.docx')):
        return True
    return False

def parse_skkk256():
    tree_file = RAW_DIR / "skkk256_ShanghaiTech-Courses.json"
    if not tree_file.exists():
        return {}
    with open(tree_file, "r", encoding="utf-8") as f:
        tree = json.load(f)
    courses = {}
    for item in tree:
        if item.get("type") != "blob":
            continue
        parts = item["path"].split("/")
        if len(parts) < 2:
            continue
        folder = parts[0]
        code = folder.split("-")[0].strip()
        name_zh = folder.split("-")[1].strip() if "-" in folder else ""
        if code not in courses:
            courses[code] = {
                "folder": folder,
                "name_zh": name_zh,
                "repo_url": f"{SKKK_BASE_URL}/{urllib.parse.quote(folder)}",
                "exams": [],
                "solutions": [],
                "homework": [],
                "projects": [],
                "slides_notes": [],
                "key_files": [],
                "total_files": 0
            }
        entry = courses[code]
        entry["total_files"] += 1
        fn = parts[-1]
        enc_path = urllib.parse.quote(item["path"])
        file_info = {
            "name": fn,
            "rel_path": item["path"],
            "url": f"{SKKK_BLOB_URL}/{enc_path}"
        }
        fl = item["path"].lower()
        if is_exam_file(item["path"]):
            if is_solution_file(item["path"]):
                entry["solutions"].append(file_info)
            else:
                entry["exams"].append(file_info)
        elif is_solution_file(item["path"]):
            entry["solutions"].append(file_info)
        elif any(k in fl for k in ["hw", "homework", "assignment", "作业"]):
            entry["homework"].append(file_info)
        elif any(k in fl for k in ["slide", "note", "讲义", "课件", "ppt"]):
            entry["slides_notes"].append(file_info)
        elif any(k in fl for k in ["project", "proj", "设计", "大作业"]):
            entry["projects"].append(file_info)
        else:
            if fn.endswith((".pdf", ".docx", ".zip", ".md", ".ipynb")):
                entry["key_files"].append(file_info)
    return courses

def parse_wutianyuan1():
    tree_file = RAW_DIR / "wutianyuan1_ShanghaiTech.json"
    if not tree_file.exists():
        return {}
    with open(tree_file, "r", encoding="utf-8") as f:
        tree = json.load(f)
    wt_map = {
        "CHEM1301-Inorganic-Chemistry": "CHEM1301",
        "CS100-Computer-Programming": "CS100",
        "CS100-Computer-Programming-2021": "CS100",
        "CS101-Algorithm&Data-structures": "CS101",
        "CS110-Computer-Architecture": "CS110",
        "CS130-Operating-Systems": "CS130",
        "CS181-Artificial-Intelligence": "CS181",
        "CS233-Software-Development&Validation-for-Medical-Cyber-Physical-Systems": "CS233",
        "CS240-Algorithm-Design&Analysis": "CS240",
        "CS270-Digital-Image-Processing": "CS270",
        "CS275-Computer-Animation&Physical-Simulation": "CS275",
        "PHYS1101-General-Physics": "PHYS1181",
        "SEMI1101-Design-Thinking": "SEMI1101",
        "SI100-Intro-to-Information-Science": "SI100B",
        "SI114H-Computational science and engineering": "SI114H",
        "SI199-Thesis": "SI199",
        "SI252-Reinforcement-Learning": "SI252"
    }
    courses = {}
    for item in tree:
        if item.get("type") != "blob":
            continue
        parts = item["path"].split("/")
        if len(parts) < 2:
            continue
        top = parts[0]
        if top not in wt_map:
            continue
        code = wt_map[top]
        if code not in courses:
            courses[code] = {
                "folder": top,
                "repo_url": f"{WTY_BASE_URL}/{urllib.parse.quote(top)}",
                "exams": [],
                "solutions": [],
                "homework": [],
                "projects": [],
                "slides_notes": [],
                "labs": [],
                "key_files": [],
                "total_files": 0
            }
        entry = courses[code]
        entry["total_files"] += 1
        fn = parts[-1]
        enc_path = urllib.parse.quote(item["path"])
        file_info = {
            "name": fn,
            "rel_path": item["path"],
            "url": f"{WTY_BLOB_URL}/{enc_path}"
        }
        fl = item["path"].lower()
        if is_exam_file(item["path"]):
            if is_solution_file(item["path"]):
                entry["solutions"].append(file_info)
            else:
                entry["exams"].append(file_info)
        elif is_solution_file(item["path"]):
            entry["solutions"].append(file_info)
        elif any(k in fl for k in ["hw", "homework", "作业"]):
            entry["homework"].append(file_info)
        elif any(k in fl for k in ["lab", "实验"]):
            entry["labs"].append(file_info)
        elif any(k in fl for k in ["slide", "note", "讲义", "课件"]):
            entry["slides_notes"].append(file_info)
        elif any(k in fl for k in ["proj", "project", "pintos", "code", "final", "thesis"]):
            entry["projects"].append(file_info)
        else:
            if fn.endswith((".pdf", ".docx", ".circ", ".py", ".cpp", ".ipynb")):
                entry["key_files"].append(file_info)
    return courses

def parse_profetia():
    tree_file = RAW_DIR / "profetia_shanghaitech.json"
    if not tree_file.exists():
        return {}
    with open(tree_file, "r", encoding="utf-8") as f:
        tree = json.load(f)
    pf_map = {
        "arts1422": "ARTS1422",
        "cs120": "CS120",
        "cs121": "CS121",
        "cs130": "CS130",
        "cs177h": "CS177H",
        "cs188": "CS188",
        "si100b": "SI100B"
    }
    courses = {}
    for item in tree:
        if item.get("type") != "blob":
            continue
        parts = item["path"].split("/")
        if len(parts) < 2:
            continue
        top = parts[0].lower()
        if top not in pf_map:
            continue
        code = pf_map[top]
        if code not in courses:
            courses[code] = {
                "folder": parts[0],
                "repo_url": f"{PF_BASE_URL}/{urllib.parse.quote(parts[0])}",
                "projects": [],
                "key_files": [],
                "total_files": 0
            }
        entry = courses[code]
        entry["total_files"] += 1
        fn = parts[-1]
        enc_path = urllib.parse.quote(item["path"])
        file_info = {
            "name": fn,
            "rel_path": item["path"],
            "url": f"{PF_BLOB_URL}/{enc_path}"
        }
        if fn.endswith((".md", ".py", ".c", ".cpp", ".h", ".sh", ".json", ".pdf", ".html", ".js")):
            if len(entry["projects"]) < 20:
                entry["projects"].append(file_info)
        entry["key_files"].append(file_info)
    return courses

def parse_gkxx():
    tree_file = RAW_DIR / "GKxxUCAS_ShanghaiTech-CS100-Slides.json"
    summary_file = RAW_DIR / "gkxx_summary.json"
    if not tree_file.exists():
        return None
    summary_data = {}
    if summary_file.exists():
        with open(summary_file, "r", encoding="utf-8") as f:
            summary_data = json.load(f)
    with open(tree_file, "r", encoding="utf-8") as f:
        tree = json.load(f)
    lectures = {}
    slides_notes = []
    for item in tree:
        if item.get("type") != "blob":
            continue
        parts = item["path"].split("/")
        if len(parts) >= 2 and parts[0].startswith("l") and parts[0][1:].isdigit():
            lec_id = int(parts[0][1:])
            if lec_id not in lectures:
                sum_info = summary_data.get(str(lec_id), {})
                title = sum_info.get("title") or f"Lecture {lec_id}"
                keywords = sum_info.get("keywords", [])
                lectures[lec_id] = {
                    "lecture": f"Lecture {lec_id}",
                    "title": title,
                    "folder": parts[0],
                    "folder_url": f"{GK_BASE_URL}/{parts[0]}",
                    "pdf_url": None,
                    "md_url": None,
                    "keywords": keywords[:10]
                }
            fn = parts[-1]
            enc_path = urllib.parse.quote(item["path"])
            url = f"{GK_BLOB_URL}/{enc_path}"
            if fn.endswith(".pdf"):
                lectures[lec_id]["pdf_url"] = url
                slides_notes.append({
                    "name": f"L{lec_id} {lectures[lec_id]['title']} (PDF)",
                    "url": url
                })
            elif fn.endswith(".md"):
                lectures[lec_id]["md_url"] = url
    sorted_lectures = [lectures[k] for k in sorted(lectures.keys())]
    return {
        "repo_url": "https://github.com/GKxxUCAS/ShanghaiTech-CS100-Slides",
        "total_lectures": len(sorted_lectures),
        "lectures": sorted_lectures,
        "slides_notes": slides_notes
    }

def parse_rulerfuhai():
    tree_file = RAW_DIR / "RulerFuhai_Shanghaitech-CHEM1100.json"
    if not tree_file.exists():
        return None
    with open(tree_file, "r", encoding="utf-8") as f:
        tree = json.load(f)
    reports = []
    pre_lab_questions = []
    templates = []
    experiments = {}
    for item in tree:
        if item.get("type") != "blob":
            continue
        path = item["path"]
        parts = path.split("/")
        fn = parts[-1]
        enc_path = urllib.parse.quote(path)
        url = f"{RF_BLOB_URL}/{enc_path}"
        file_info = {"name": fn, "rel_path": path, "url": url}
        if len(parts) == 1:
            if any(k in fn for k in ["模板", "云桌面", "密码"]):
                templates.append(file_info)
        else:
            exp_folder = parts[0]
            if exp_folder not in experiments:
                enc_folder = urllib.parse.quote(exp_folder)
                experiments[exp_folder] = {
                    "folder": exp_folder,
                    "url": f"{RF_BASE_URL}/{enc_folder}",
                    "files": []
                }
            experiments[exp_folder]["files"].append(file_info)
            fl = fn.lower()
            if "预习思考题" in fl or "预习" in fl:
                pre_lab_questions.append(file_info)
            elif fl.endswith((".pdf", ".docx")) and ("实验" in fl or "报告" in fl):
                reports.append(file_info)
    return {
        "repo_url": "https://github.com/RulerFuhai/Shanghaitech-CHEM1100",
        "reports": reports,
        "pre_lab_questions": pre_lab_questions,
        "templates": templates,
        "experiments": experiments
    }



def build_unified_index():
    cb_courses = load_coursebench_db()
    itechx_data = parse_itechx()
    xw_data = parse_xiongwenye()
    skkk_data = parse_skkk256()
    wty_data = parse_wutianyuan1()
    profetia_data = parse_profetia()
    gkxx_data = parse_gkxx()
    rulerfuhai_data = parse_rulerfuhai()

    all_course_codes = set()
    all_course_codes.update(cb_courses.keys())
    all_course_codes.update(itechx_data.keys())
    all_course_codes.update(ZSC_COURSES.keys())
    all_course_codes.update(skkk_data.keys())
    all_course_codes.update(wty_data.keys())
    all_course_codes.update(profetia_data.keys())
    if gkxx_data:
        all_course_codes.add("CS100")
    if rulerfuhai_data:
        all_course_codes.add("CHEM1100")

    # Map XiongWenye courses to canonical codes
    xw_to_code = dict(ZH_TO_CODE)
    code_to_xw = {}
    for zh, code in xw_to_code.items():
        if zh in xw_data:
            code_to_xw[code] = zh

    for folder in xw_data:
        if folder not in xw_to_code:
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
        sk_item = skkk_data.get(code)
        wt_item = wty_data.get(code)
        pf_item = profetia_data.get(code)
        gk_item = gkxx_data if code == "CS100" else None
        rf_item = rulerfuhai_data if code in ["CHEM1100", "CHEM1111L"] else None

        has_resources = bool(itechx_item or zsc_item or xw_item or sk_item or wt_item or pf_item or gk_item or rf_item)
        if not has_resources:
            continue

        name_zh = cb_info.get("name")
        if not name_zh:
            if sk_item and sk_item.get("name_zh"):
                name_zh = sk_item["name_zh"]
            elif xw_folder:
                name_zh = xw_folder
            elif code in ZH_TO_CODE.values():
                for zh, c in ZH_TO_CODE.items():
                    if c == code:
                        name_zh = zh
                        break
        if not name_zh:
            name_zh = code

        name_en = zsc_item.get("title") if zsc_item else ""
        institute = cb_info.get("institute", "上海科技大学")
        credit = cb_info.get("credit", 0.0)
        scores = cb_info.get("scores", {})

        aliases = set()
        aliases.add(code.lower())
        aliases.add(code.upper())
        if name_zh:
            aliases.add(name_zh)
        if name_en:
            aliases.add(name_en.lower())
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

        # 4. skkk256
        if sk_item:
            course_entry["resources"]["skkk256"] = {
                "available": True,
                "folder_name": sk_item["folder"],
                "repo_url": sk_item["repo_url"],
                "total_files": sk_item["total_files"],
                "exams": sk_item["exams"][:15],
                "solutions": sk_item["solutions"][:15],
                "homework": sk_item["homework"][:10],
                "slides_notes": sk_item["slides_notes"][:10],
                "projects": sk_item["projects"][:10],
                "key_files": sk_item["key_files"][:10]
            }

        # 5. wutianyuan1
        if wt_item:
            course_entry["resources"]["wutianyuan1"] = {
                "available": True,
                "folder_name": wt_item["folder"],
                "repo_url": wt_item["repo_url"],
                "total_files": wt_item["total_files"],
                "exams": wt_item["exams"][:10],
                "solutions": wt_item["solutions"][:10],
                "homework": wt_item["homework"][:10],
                "projects": wt_item["projects"][:10],
                "slides_notes": wt_item["slides_notes"][:10],
                "labs": wt_item["labs"][:10]
            }

        # 6. profetia
        if pf_item:
            course_entry["resources"]["profetia"] = {
                "available": True,
                "folder_name": pf_item["folder"],
                "repo_url": pf_item["repo_url"],
                "total_files": pf_item["total_files"],
                "projects": pf_item["projects"][:15],
                "key_files": pf_item["key_files"][:10]
            }

        # 7. GKxxUCAS CS100
        if gk_item:
            course_entry["resources"]["gkxx_cs100"] = {
                "available": True,
                "repo_url": gk_item["repo_url"],
                "total_lectures": gk_item["total_lectures"],
                "lectures": gk_item["lectures"],
                "slides_notes": gk_item["slides_notes"]
            }

        # 8. RulerFuhai CHEM1100
        if rf_item:
            course_entry["resources"]["rulerfuhai"] = {
                "available": True,
                "repo_url": rf_item["repo_url"],
                "reports": rf_item["reports"][:15],
                "pre_lab_questions": rf_item["pre_lab_questions"][:15],
                "templates": rf_item["templates"],
                "experiments_count": len(rf_item["experiments"])
            }

        unified_catalog[code] = course_entry

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
            "version": "2.0.0",
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
                },
                "skkk256": {
                    "name": "skkk256 上科大四年全科修课资料库",
                    "branch": "main",
                    "url": "https://github.com/skkk256/ShanghaiTech-Courses"
                },
                "wutianyuan1": {
                    "name": "wutianyuan1 上科大课程与项目代码仓库",
                    "branch": "main",
                    "url": "https://github.com/wutianyuan1/ShanghaiTech"
                },
                "profetia": {
                    "name": "profetia 本科大作业与课程项目归档库",
                    "branch": "main",
                    "url": "https://github.com/profetia/shanghaitech"
                },
                "gkxx": {
                    "name": "GKxxUCAS CS100 编程导论全套课件精炼库",
                    "branch": "main",
                    "url": "https://github.com/GKxxUCAS/ShanghaiTech-CS100-Slides"
                },
                "rulerfuhai": {
                    "name": "RulerFuhai 普通化学I实验高分实验报告与资料库",
                    "branch": "main",
                    "url": "https://github.com/RulerFuhai/Shanghaitech-CHEM1100"
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
