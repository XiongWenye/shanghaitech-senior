#!/usr/bin/env python3
"""
Generate standardized ShanghaiTech 2026 Curriculum JSONs for all 12 majors
from OCR JSON files, enriched with CourseBench course data.
"""

import os
import json
import re
import sqlite3

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
OCR_DIR = os.path.join(DATA_DIR, "ocr_json")
CURRICULUM_DIR = os.path.join(DATA_DIR, "curriculums")
DB_PATH = os.path.join(DATA_DIR, "coursebench.db")

os.makedirs(CURRICULUM_DIR, exist_ok=True)

COURSE_CODE_RE = re.compile(r'^[A-Z]{2,6}[0-9]{3,4}[A-Za-z0-9]*$')

FILE_MAPPING = {
    "2026_CS.json": {
        "id": "2026_CS_SIST",
        "major": "计算机科学与技术",
        "institute": "信息科学与技术学院",
        "track": "通用/各方向",
        "degree": "工学学士学位",
        "min_total_credits": 143,
        "filename": "2026_CS_SIST.json"
    },
    "2026_CS_AI.json": {
        "id": "2026_CS_AI_SIST",
        "major": "计算机科学与技术",
        "institute": "信息科学与技术学院",
        "track": "人工智能荣誉班",
        "degree": "工学学士学位",
        "min_total_credits": 143,
        "filename": "2026_CS_AI_SIST.json"
    },
    "2026_EE.json": {
        "id": "2026_EE_SIST",
        "major": "电子信息工程",
        "institute": "信息科学与技术学院",
        "track": "通用/各方向",
        "degree": "工学学士学位",
        "min_total_credits": 143,
        "filename": "2026_EE_SIST.json"
    },
    "2026_MATH.json": {
        "id": "2026_MATH_IMS",
        "major": "数学与应用数学",
        "institute": "数学科学研究所",
        "track": "通用/各方向",
        "degree": "理学学士学位",
        "min_total_credits": 145,
        "filename": "2026_MATH_IMS.json"
    },
    "2026_ICS.json": {
        "id": "2026_ICS_IMS",
        "major": "信息与计算科学",
        "institute": "数学科学研究所",
        "track": "数学与智能 / 计算金融",
        "degree": "理学学士学位",
        "min_total_credits": 145,
        "filename": "2026_ICS_IMS.json"
    },
    "2026_PHYS.json": {
        "id": "2026_PHYS_SPST",
        "major": "物理学",
        "institute": "物质科学与技术学院",
        "track": "凝聚态物理 / 光子科学 / 理论物理",
        "degree": "理学学士学位",
        "min_total_credits": 145,
        "filename": "2026_PHYS_SPST.json"
    },
    "2026_CHEM.json": {
        "id": "2026_CHEM_SPST",
        "major": "化学",
        "institute": "物质科学与技术学院",
        "track": "合成化学 / 材料化学 / 能源与催化化学 / 生物化学",
        "degree": "理学学士学位",
        "min_total_credits": 145,
        "filename": "2026_CHEM_SPST.json"
    },
    "2026_MSE.json": {
        "id": "2026_MSE_SPST",
        "major": "材料科学与工程",
        "institute": "物质科学与技术学院",
        "track": "纳米能源材料 / 微纳电子材料 / 生物材料",
        "degree": "工学学士学位",
        "min_total_credits": 145,
        "filename": "2026_MSE_SPST.json"
    },
    "2026_BIOSCI.json": {
        "id": "2026_BIOSCI_SLST",
        "major": "生物科学",
        "institute": "生命科学与技术学院",
        "track": "通用",
        "degree": "理学学士学位",
        "min_total_credits": 144,
        "filename": "2026_BIOSCI_SLST.json"
    },
    "2026_BIOTECH.json": {
        "id": "2026_BIOTECH_SLST",
        "major": "生物技术",
        "institute": "生命科学与技术学院",
        "track": "基因与细胞治疗 / 生物医学大数据",
        "degree": "理学学士学位",
        "min_total_credits": 144,
        "filename": "2026_BIOTECH_SLST.json"
    },
    "2026_BME.json": {
        "id": "2026_BME_BME",
        "major": "生物医学工程",
        "institute": "生物医学工程学院",
        "track": "智能医学影像 / 智慧医疗仪器 / 智能医学数据",
        "degree": "工学学士学位",
        "min_total_credits": 142,
        "filename": "2026_BME_BME.json"
    },
    "2026_ID.json": {
        "id": "2026_ID_SCA",
        "major": "工业设计",
        "institute": "创意与艺术学院",
        "track": "智能硬件产品 / 娱乐与互动设计",
        "degree": "工学学士学位",
        "min_total_credits": 151,
        "filename": "2026_ID_SCA.json"
    }
}

# Connect to database for course enrichment
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

def lookup_coursebench(code, name):
    # Try exact code match
    c.execute("SELECT id, name, score_quality, score_workload, score_difficulty, score_grade, comment_num, teachers, latest_semester FROM courses WHERE code = ?", (code,))
    row = c.fetchone()
    if not row:
        # Try like code
        c.execute("SELECT id, name, score_quality, score_workload, score_difficulty, score_grade, comment_num, teachers, latest_semester FROM courses WHERE code LIKE ? LIMIT 1", (f"%{code}%",))
        row = c.fetchone()
    if not row and name:
        # Try name match
        clean_n = name.replace("（含实验）", "").replace("(含实验)", "").replace("实验", "").strip()
        if len(clean_n) >= 2:
            c.execute("SELECT id, name, score_quality, score_workload, score_difficulty, score_grade, comment_num, teachers, latest_semester FROM courses WHERE name LIKE ? LIMIT 1", (f"%{clean_n}%",))
            row = c.fetchone()
            
    if row:
        return {
            "coursebench_id": row[0],
            "official_name": row[1],
            "score_quality": round(row[2], 2) if row[2] else 0.0,
            "score_workload": round(row[3], 2) if row[3] else 0.0,
            "score_difficulty": round(row[4], 2) if row[4] else 0.0,
            "score_grade": round(row[5], 2) if row[5] else 0.0,
            "comment_num": row[6] or 0,
            "teachers": row[7] or "",
            "latest_semester": row[8] or ""
        }
    return None

def process_major_ocr(ocr_filename, meta):
    ocr_path = os.path.join(OCR_DIR, ocr_filename)
    with open(ocr_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    courses = []
    seen_codes = set()
    current_module = "人文社科通识"

    for p in doc["pages"]:
        items = p["items"]
        code_candidates = [it for it in items if COURSE_CODE_RE.match(it["text"].strip()) and 0.18 < it["x"] < 0.28]
        code_candidates.sort(key=lambda it: it["y"])

        for ci in code_candidates:
            y = ci["y"]
            code = ci["text"].strip()
            row = [it for it in items if abs(it["y"] - y) < 0.015]

            # Detect module transition from column 1
            cat_it = [it["text"].strip() for it in row if it["x"] < 0.20]
            cat_str = "".join(cat_it)
            if any(k in cat_str for k in ["思政必修", "通识必修", "英语", "体育", "写作", "经典", "艺术", "创业", "数学", "物理", "化学", "生物", "信息", "自然科学", "专业必修", "专业限选", "专业选修", "任选", "毕业论文", "设计"]):
                current_module = cat_str

            # Name
            name_it = [it["text"].strip() for it in row if 0.28 <= it["x"] < 0.45]
            raw_name = "".join(name_it)
            clean_name = re.sub(r'^[0-9\*、\.\s]+', '', raw_name).strip()
            if not clean_name:
                clean_name = raw_name

            # Credit
            cred_it = [it["text"].strip() for it in row if 0.45 <= it["x"] < 0.50]
            credit = 0.0
            for ct in cred_it:
                m = re.search(r'([0-9]+(\.[0-9]+)?)', ct)
                if m:
                    credit = float(m.group(1))
                    break

            # Semester ticks (0.50 <= x < 0.69)
            sem_items = [it for it in row if 0.50 <= it["x"] < 0.695]
            semesters = []
            for si in sem_items:
                stext = si["text"].lower()
                if any(chk in stext for chk in ['v', '√', '1', 'n', 'く', '|', '/']):
                    col_idx = int((si["x"] - 0.502) / 0.0174) + 1
                    col_idx = max(1, min(11, col_idx))
                    if col_idx not in semesters:
                        semesters.append(col_idx)
            semesters.sort()

            # Compulsory
            comp_it = [it["text"].strip() for it in row if 0.69 <= it["x"] < 0.74]
            comp_text = "".join(comp_it)
            is_compulsory = "是" in comp_text or "必修" in comp_text

            # Department
            dept_it = [it["text"].strip() for it in row if 0.74 <= it["x"] < 0.82]
            dept = "".join(dept_it)

            # Notes
            note_it = [it["text"].strip() for it in row if it["x"] >= 0.82]
            notes = "".join(note_it)

            # CourseBench enrichment
            cb_info = lookup_coursebench(code, clean_name)

            course_entry = {
                "code": code,
                "name": clean_name,
                "credit": credit,
                "semesters": semesters,
                "is_compulsory": is_compulsory,
                "dept": dept,
                "module": current_module,
                "notes": notes
            }
            if cb_info:
                course_entry["coursebench"] = cb_info

            courses.append(course_entry)

    # Group courses into structured modules
    compulsory_list = [c for c in courses if c["is_compulsory"]]
    elective_list = [c for c in courses if not c["is_compulsory"]]

    # Organize semester recommended plan (semesters 1 to 8/11)
    semester_plan = {sem: [] for sem in range(1, 9)}
    for c in courses:
        for s in c["semesters"]:
            if 1 <= s <= 8:
                semester_plan[s].append({
                    "code": c["code"],
                    "name": c["name"],
                    "credit": c["credit"],
                    "is_compulsory": c["is_compulsory"]
                })

    result_json = {
        "curriculum_id": meta["id"],
        "grade": 2026,
        "institute": meta["institute"],
        "major": meta["major"],
        "track": meta["track"],
        "degree": meta["degree"],
        "min_total_credits": meta["min_total_credits"],
        "total_courses_count": len(courses),
        "total_compulsory_count": len(compulsory_list),
        "semester_recommended_plan": semester_plan,
        "compulsory_courses": compulsory_list,
        "all_courses": courses
    }

    out_file = os.path.join(CURRICULUM_DIR, meta["filename"])
    with open(out_file, "w", encoding="utf-8") as out_fp:
        json.dump(result_json, out_fp, ensure_ascii=False, indent=2)
    print(f"Generated {meta['filename']}: {len(courses)} courses ({len(compulsory_list)} compulsory)")

if __name__ == "__main__":
    for ocr_file, meta in FILE_MAPPING.items():
        process_major_ocr(ocr_file, meta)
    from clean_curriculums import clean_all_curriculums
    clean_all_curriculums()
