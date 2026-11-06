#!/usr/bin/env python3
"""
Comprehensive Curriculum Builder for ShanghaiTech 2026 Training Programs
Combines OCR items, text checkmarks, image checkmarks, and CourseBench database.
Produces standardized, rich JSON models for all 12 majors in data/curriculums/.
"""

import os
import json
import re
import sqlite3
import pypdf
import io
from PIL import Image

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
OCR_DIR = os.path.join(DATA_DIR, "ocr_json")
CURRICULUM_DIR = os.path.join(DATA_DIR, "curriculums")
PDF_DIR = os.path.join(os.path.dirname(__file__), "..", "培养方案")
DB_PATH = os.path.join(DATA_DIR, "coursebench.db")

COURSE_CODE_RE = re.compile(r'^[A-Z]{2,6}[0-9]{3,4}[A-Za-z0-9]*$')

# 12 Majors metadata
MAJORS_META = [
    {
        "id": "2026_CS_SIST",
        "ocr_file": "2026_CS.json",
        "pdf_file": "2026级本科计算机科学与技术专业培养方案.pdf",
        "institute": "信息科学与技术学院",
        "major": "计算机科学与技术",
        "track": "通用/各方向",
        "degree": "工学学士学位",
        "min_total_credits": 143,
        "interdisciplinary_prefixes": ["CHEM", "MSE", "PHYS", "BIO", "BME", "MATH", "ARTS", "ECON"],
        "out_file": "2026_CS_SIST.json"
    },
    {
        "id": "2026_CS_AI_SIST",
        "ocr_file": "2026_CS_AI.json",
        "pdf_file": "2026级本科计算机科学与技术专业（人工智能荣誉班）培养方案.pdf",
        "institute": "信息科学与技术学院",
        "major": "计算机科学与技术",
        "track": "人工智能荣誉班",
        "degree": "工学学士学位",
        "min_total_credits": 143,
        "interdisciplinary_prefixes": ["CHEM", "MSE", "PHYS", "BIO", "BME", "MATH", "ARTS", "ECON"],
        "out_file": "2026_CS_AI_SIST.json"
    },
    {
        "id": "2026_EE_SIST",
        "ocr_file": "2026_EE.json",
        "pdf_file": "2026级本科电子信息工程专业培养方案.pdf",
        "institute": "信息科学与技术学院",
        "major": "电子信息工程",
        "track": "通用/各方向",
        "degree": "工学学士学位",
        "min_total_credits": 143,
        "interdisciplinary_prefixes": ["CHEM", "MSE", "PHYS", "BIO", "BME", "MATH", "ARTS", "ECON"],
        "out_file": "2026_EE_SIST.json"
    },
    {
        "id": "2026_MATH_IMS",
        "ocr_file": "2026_MATH.json",
        "pdf_file": "2026级本科数学与应用数学专业培养方案.pdf",
        "institute": "数学科学研究所",
        "major": "数学与应用数学",
        "track": "基础数学 / 应用数学",
        "degree": "理学学士学位",
        "min_total_credits": 145,
        "interdisciplinary_prefixes": ["CS", "SI", "EE", "PHYS", "CHEM", "MSE", "BIO", "BME", "ECON"],
        "out_file": "2026_MATH_IMS.json"
    },
    {
        "id": "2026_ICS_IMS",
        "ocr_file": "2026_ICS.json",
        "pdf_file": "2026级本科信息与计算科学专业培养方案.pdf",
        "institute": "数学科学研究所",
        "major": "信息与计算科学",
        "track": "数学与智能 / 计算金融",
        "degree": "理学学士学位",
        "min_total_credits": 145,
        "interdisciplinary_prefixes": ["PHYS", "CHEM", "MSE", "BIO", "BME", "ARTS"],
        "out_file": "2026_ICS_IMS.json"
    },
    {
        "id": "2026_PHYS_SPST",
        "ocr_file": "2026_PHYS.json",
        "pdf_file": "2026级本科物理学专业培养方案.pdf",
        "institute": "物质科学与技术学院",
        "major": "物理学",
        "track": "凝聚态物理 / 光子科学 / 理论物理",
        "degree": "理学学士学位",
        "min_total_credits": 145,
        "interdisciplinary_prefixes": ["CS", "SI", "EE", "BIO", "BME", "MATH", "ARTS", "ECON"],
        "out_file": "2026_PHYS_SPST.json"
    },
    {
        "id": "2026_CHEM_SPST",
        "ocr_file": "2026_CHEM.json",
        "pdf_file": "2026级本科化学专业培养方案.pdf",
        "institute": "物质科学与技术学院",
        "major": "化学",
        "track": "合成化学 / 材料化学 / 能源与催化化学 / 生物化学",
        "degree": "理学学士学位",
        "min_total_credits": 145,
        "interdisciplinary_prefixes": ["CS", "SI", "EE", "BIO", "BME", "MATH", "ARTS", "ECON"],
        "out_file": "2026_CHEM_SPST.json"
    },
    {
        "id": "2026_MSE_SPST",
        "ocr_file": "2026_MSE.json",
        "pdf_file": "2026级本科材料科学与工程专业培养方案.pdf",
        "institute": "物质科学与技术学院",
        "major": "材料科学与工程",
        "track": "纳米能源材料 / 微纳电子材料 / 生物材料",
        "degree": "工学学士学位",
        "min_total_credits": 145,
        "interdisciplinary_prefixes": ["CS", "SI", "EE", "BIO", "BME", "MATH", "ARTS", "ECON"],
        "out_file": "2026_MSE_SPST.json"
    },
    {
        "id": "2026_BIOSCI_SLST",
        "ocr_file": "2026_BIOSCI.json",
        "pdf_file": "2026级本科生物科学专业培养方案.pdf",
        "institute": "生命科学与技术学院",
        "major": "生物科学",
        "track": "基础生命科学 / 交叉前沿",
        "degree": "理学学士学位",
        "min_total_credits": 144,
        "interdisciplinary_prefixes": ["CS", "SI", "EE", "PHYS", "MSE", "MATH", "ARTS", "ECON"],
        "out_file": "2026_BIOSCI_SLST.json"
    },
    {
        "id": "2026_BIOTECH_SLST",
        "ocr_file": "2026_BIOTECH.json",
        "pdf_file": "2026级本科生物技术专业培养方案.pdf",
        "institute": "生命科学与技术学院",
        "major": "生物技术",
        "track": "基因与细胞治疗 / 生物医学大数据",
        "degree": "理学学士学位",
        "min_total_credits": 144,
        "interdisciplinary_prefixes": ["CS", "SI", "EE", "PHYS", "MSE", "MATH", "ARTS", "ECON"],
        "out_file": "2026_BIOTECH_SLST.json"
    },
    {
        "id": "2026_BME_BME",
        "ocr_file": "2026_BME.json",
        "pdf_file": "2026级本科生物医学工程专业培养方案.pdf",
        "institute": "生物医学工程学院",
        "major": "生物医学工程",
        "track": "智能医学影像 / 智慧医疗仪器 / 智能医学数据",
        "degree": "工学学士学位",
        "min_total_credits": 142,
        "interdisciplinary_prefixes": ["CHEM", "MSE", "PHYS", "MATH", "ARTS", "ECON"],
        "out_file": "2026_BME_BME.json"
    },
    {
        "id": "2026_ID_SCA",
        "ocr_file": "2026_ID.json",
        "pdf_file": "2026级本科工业设计专业培养方案.pdf",
        "institute": "创意与艺术学院",
        "major": "工业设计",
        "track": "智能硬件产品 / 娱乐与互动设计",
        "degree": "工学学士学位",
        "min_total_credits": 151,
        "interdisciplinary_prefixes": ["CS", "SI", "EE", "CHEM", "MSE", "PHYS", "BIO", "BME", "MATH", "ECON"],
        "out_file": "2026_ID_SCA.json"
    }
]

# Database connection
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

def get_coursebench_data(code, name):
    cur.execute("SELECT * FROM courses WHERE code = ?", (code,))
    row = cur.fetchone()
    if not row:
        cur.execute("SELECT * FROM courses WHERE code LIKE ? LIMIT 1", (f"%{code}%",))
        row = cur.fetchone()
    if not row and name:
        clean_n = name.replace("（含实验）", "").replace("(含实验)", "").replace("实验", "").strip()
        if len(clean_n) >= 2:
            cur.execute("SELECT * FROM courses WHERE name LIKE ? LIMIT 1", (f"%{clean_n}%",))
            row = cur.fetchone()
    if row:
        return {
            "coursebench_id": row["id"],
            "official_name": row["name"],
            "score_quality": round(row["score_quality"] or 0.0, 2),
            "score_workload": round(row["score_workload"] or 0.0, 2),
            "score_difficulty": round(row["score_difficulty"] or 0.0, 2),
            "score_grade": round(row["score_grade"] or 0.0, 2),
            "comment_num": row["comment_num"] or 0,
            "teachers": row["teachers"] or "",
            "latest_semester": row["latest_semester"] or "",
            "semesters_history": row["semesters"] or ""
        }
    return None

def standardize_module_name(raw_name):
    """Classifies raw module string into standard curriculum module category."""
    if not raw_name:
        return "专业选修"
    if "思政必修" in raw_name or "思想政治理论课" in raw_name:
        return "思想政治理论课-必修"
    if "思政选修" in raw_name:
        return "思想政治理论课-选修"
    if "通识必修" in raw_name:
        return "通识必修"
    if "英语" in raw_name:
        return "通识选修-大学英语"
    if "体育" in raw_name:
        return "通识选修-大学体育"
    if "写作" in raw_name or "文学" in raw_name:
        return "通识选修-文学与写作"
    if "经典" in raw_name or "文明" in raw_name:
        return "通识选修-文明经典导读"
    if "艺术" in raw_name or "创意" in raw_name:
        return "通识选修-创意与艺术"
    if "创业" in raw_name or "创新" in raw_name:
        return "通识选修-创新创业"
    if any(k in raw_name for k in ["数学课", "物理课", "化学课", "生物课", "信息课", "自然科学", "科学基础"]):
        return "自然科学基础"
    if "专业必修" in raw_name or "专业基础必修" in raw_name:
        return "专业必修"
    if "专业限选" in raw_name or "限选" in raw_name:
        return "专业限选"
    if "方向" in raw_name:
        return f"专业选修-{raw_name.strip()}"
    if "跨学科" in raw_name:
        return "跨学科选修"
    if "任选" in raw_name or "任意选修" in raw_name:
        return "任意选修"
    if "毕业设计" in raw_name or "毕业论文" in raw_name:
        return "综合实践与毕业论文"
    return "专业选修"

def process_major(meta):
    print(f"--> Processing {meta['id']} ({meta['major']})...")
    ocr_path = os.path.join(OCR_DIR, meta["ocr_file"])
    with open(ocr_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    all_courses = []
    current_module = "通识必修"

    for p in doc["pages"]:
        items = p["items"]
        code_candidates = [it for it in items if COURSE_CODE_RE.match(it["text"].strip()) and 0.18 < it["x"] < 0.28]
        code_candidates.sort(key=lambda it: it["y"])

        for ci in code_candidates:
            y = ci["y"]
            code = ci["text"].strip()
            row = [it for it in items if abs(it["y"] - y) < 0.015]

            # Detect module transition
            cat_it = [it["text"].strip() for it in row if it["x"] < 0.20]
            cat_str = "".join(cat_it)
            if any(k in cat_str for k in ["思政", "通识", "英语", "体育", "写作", "经典", "艺术", "创业", "数学", "物理", "化学", "生物", "信息", "自然科学", "专业必修", "专业限选", "专业选修", "任选", "毕业论文", "设计"]):
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

            # Semester checkmarks (0.50 <= x < 0.69)
            sem_items = [it for it in row if 0.50 <= it["x"] < 0.695]
            semesters = []
            for si in sem_items:
                stext = si["text"].lower()
                if any(chk in stext for chk in ['v', '√', '1', 'n', 'く', '|', '/']):
                    col_idx = int((si["x"] - 0.502) / 0.0174) + 1
                    col_idx = max(1, min(11, col_idx))
                    if col_idx not in semesters:
                        semesters.append(col_idx)

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

            std_module = standardize_module_name(current_module)

            # Enrichment
            cb_data = get_coursebench_data(code, clean_name)

            course_obj = {
                "code": code,
                "name": clean_name,
                "credit": credit,
                "semesters": semesters,
                "is_compulsory": is_compulsory,
                "dept": dept,
                "raw_module": current_module,
                "module": std_module,
                "notes": notes
            }
            if cb_data:
                course_obj["coursebench"] = cb_data
                # If semesters was empty, infer from coursebench historical terms
                if not semesters and cb_data.get("semesters_history"):
                    hist = cb_data["semesters_history"]
                    inferred_sems = []
                    if "01" in hist and 1 not in inferred_sems:
                        inferred_sems.append(1) # Fall
                    if "02" in hist and 2 not in inferred_sems:
                        inferred_sems.append(2) # Spring
                    course_obj["inferred_terms"] = inferred_sems

            all_courses.append(course_obj)

    # Build Module definitions
    module_dict = {}
    for c in all_courses:
        mod = c["module"]
        if mod not in module_dict:
            module_dict[mod] = {
                "name": mod,
                "required_credits": 0.0,
                "compulsory_courses": [],
                "elective_pool": []
            }
        if c["is_compulsory"]:
            module_dict[mod]["compulsory_courses"].append({
                "code": c["code"],
                "name": c["name"],
                "credit": c["credit"],
                "semesters": c["semesters"],
                "dept": c["dept"],
                "notes": c["notes"]
            })
            module_dict[mod]["required_credits"] += c["credit"]
        else:
            module_dict[mod]["elective_pool"].append({
                "code": c["code"],
                "name": c["name"],
                "credit": c["credit"],
                "dept": c["dept"]
            })

    # Standard credit requirements per module if 0
    cred_reqs = {
        "思想政治理论课-必修": 15.0,
        "思想政治理论课-选修": 2.0,
        "通识必修": 13.0,
        "通识选修-大学英语": 7.0,
        "通识选修-大学体育": 7.0,
        "通识选修-文学与写作": 3.0,
        "通识选修-文明经典导读": 2.0,
        "通识选修-创意与艺术": 2.0,
        "通识选修-创新创业": 2.0,
        "自然科学基础": 30.0 if "CS" in meta["id"] else 35.0,
        "专业必修": 20.0 if "CS" in meta["id"] else 28.0,
        "专业限选": 9.0,
        "跨学科选修": 3.0,
        "任意选修": 9.0
    }
    for mname, mdef in module_dict.items():
        if mdef["required_credits"] == 0.0 and mname in cred_reqs:
            mdef["required_credits"] = cred_reqs[mname]

    # Semester Roadmap (1 to 8)
    semester_roadmap = {str(sem): [] for sem in range(1, 9)}
    for c in all_courses:
        for s in c["semesters"]:
            if 1 <= s <= 8:
                semester_roadmap[str(s)].append({
                    "code": c["code"],
                    "name": c["name"],
                    "credit": c["credit"],
                    "is_compulsory": c["is_compulsory"],
                    "module": c["module"],
                    "coursebench": c.get("coursebench")
                })

    curriculum_json = {
        "curriculum_id": meta["id"],
        "grade": 2026,
        "institute": meta["institute"],
        "major": meta["major"],
        "track": meta["track"],
        "degree": meta["degree"],
        "min_total_credits": meta["min_total_credits"],
        "interdisciplinary_prefixes": meta["interdisciplinary_prefixes"],
        "summary_requirements": {
            "人文社科通识总学分": 53.0,
            "思想政治理论课": 17.0,
            "通识必修": 13.0,
            "大学英语": 7.0,
            "大学体育": 7.0,
            "人文写作": 3.0,
            "文明经典导读": 2.0,
            "创意与艺术": 2.0,
            "创新创业": 2.0,
            "毕业要求总学分": meta["min_total_credits"]
        },
        "modules": list(module_dict.values()),
        "semester_roadmap": semester_roadmap,
        "all_courses": all_courses
    }

    out_path = os.path.join(CURRICULUM_DIR, meta["out_file"])
    with open(out_path, "w", encoding="utf-8") as out_fp:
        json.dump(curriculum_json, out_fp, ensure_ascii=False, indent=2)
    print(f"  [✓] Successfully saved {meta['out_file']} ({len(all_courses)} courses, {len(curriculum_json['modules'])} modules)")

if __name__ == "__main__":
    for meta in MAJORS_META:
        process_major(meta)
    print("\nAll 12 Curriculums successfully built and saved in data/curriculums/")
    from clean_curriculums import clean_all_curriculums
    clean_all_curriculums()
