#!/usr/bin/env python3
"""Parse a fresh official EAMS completion page and compare available public curricula."""

import sys
import os
import json
import re
import argparse
from html.parser import HTMLParser

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPTS_DIR, "..", "data")
CURRICULUM_DIR = os.path.join(DATA_DIR, "curriculums")
DEFAULT_CURRICULUM = os.path.join(CURRICULUM_DIR, "2026_CS_SIST.json")

MAJOR_MAPPING = {
    "cs": "2026_CS_SIST.json",
    "计算机": "2026_CS_SIST.json",
    "计算机科学与技术": "2026_CS_SIST.json",
    "计科": "2026_CS_SIST.json",
    "ai": "2026_CS_AI_SIST.json",
    "ai班": "2026_CS_AI_SIST.json",
    "人工智能": "2026_CS_AI_SIST.json",
    "人工智能荣誉班": "2026_CS_AI_SIST.json",
    "ee": "2026_EE_SIST.json",
    "电子": "2026_EE_SIST.json",
    "电子信息": "2026_EE_SIST.json",
    "电子信息工程": "2026_EE_SIST.json",
    "math": "2026_MATH_IMS.json",
    "数学": "2026_MATH_IMS.json",
    "数学与应用数学": "2026_MATH_IMS.json",
    "ics": "2026_ICS_IMS.json",
    "信计": "2026_ICS_IMS.json",
    "信息与计算科学": "2026_ICS_IMS.json",
    "phys": "2026_PHYS_SPST.json",
    "物理": "2026_PHYS_SPST.json",
    "物理学": "2026_PHYS_SPST.json",
    "chem": "2026_CHEM_SPST.json",
    "化学": "2026_CHEM_SPST.json",
    "mse": "2026_MSE_SPST.json",
    "材料": "2026_MSE_SPST.json",
    "材料科学与工程": "2026_MSE_SPST.json",
    "biosci": "2026_BIOSCI_SLST.json",
    "生科": "2026_BIOSCI_SLST.json",
    "生物科学": "2026_BIOSCI_SLST.json",
    "biotech": "2026_BIOTECH_SLST.json",
    "生技": "2026_BIOTECH_SLST.json",
    "生物技术": "2026_BIOTECH_SLST.json",
    "bme": "2026_BME_BME.json",
    "生医工": "2026_BME_BME.json",
    "生物医学工程": "2026_BME_BME.json",
    "id": "2026_ID_SCA.json",
    "工设": "2026_ID_SCA.json",
    "工业设计": "2026_ID_SCA.json",
    "创艺": "2026_ID_SCA.json"
}

def resolve_curriculum_path(major_str=None, grade=None):
    from live_session import LiveQueryError
    if not major_str or grade is None:
        raise LiveQueryError("学籍年级或专业缺失，不能默认套用计科培养方案")
    major = major_str.strip().lower()
    template = MAJOR_MAPPING.get(major)
    if not template:
        raise LiveQueryError("本地公开培养方案库未匹配到该专业，请核对 EAMS 官方模块")
    filename = template.replace("2026_", str(grade) + "_", 1)
    path = os.path.join(CURRICULUM_DIR, filename)
    if not os.path.isfile(path):
        raise LiveQueryError(f"公开培养方案库缺少 {grade} 级对应文件，请核对 EAMS 官方模块")
    return path

class SimpleTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.current_cell = []
        self.current_row = []
        self.rows = []

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.in_table = True
        elif tag == "tr":
            self.in_row = True
            self.current_row = []
        elif tag in ["td", "th"]:
            self.in_cell = True
            self.current_cell = []

    def handle_endtag(self, tag):
        if tag in ["td", "th"]:
            self.in_cell = False
            cell_text = "".join(self.current_cell).strip()
            self.current_row.append(cell_text)
        elif tag == "tr":
            self.in_row = False
            if self.current_row:
                self.rows.append(self.current_row)
        elif tag == "table":
            self.in_table = False

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell.append(data)

def parse_html_plan(html_content):
    """
    Parses HTML page from EAMS myPlanCompl.action.
    Accurately extracts:
    1. Header statistics (要求学分, 完成学分, 实修学分, GPA, 审核结果)
    2. Truly completed courses (有成绩, 是否通过=是, 非在读)
    3. In-progress courses (在读, 成绩=--, 正在修读)
    4. Unfulfilled courses (否, 未修)
    IMPORTANT: EAMS '完成学分' in header ALREADY includes in-progress courses in pre-audit!
    """
    # 1. Parse header
    header_info = {
        "req_credits": None,
        "compl_credits": None,
        "actual_credits": None,
        "gpa": None,
        "audit_result": "",
        "major": "",
        "dept": "",
        "grade": None,
        "name": "",
        "student_id": ""
    }
    
    m_req = re.search(r'要求学分/完成学分/实修学分:.*?<td[^>]*>([0-9]+(?:\.[0-9]+)?)(?:&nbsp;|\s)*/(?:&nbsp;|\s)*([0-9]+(?:\.[0-9]+)?)(?:&nbsp;|\s)*/(?:&nbsp;|\s)*([0-9]+(?:\.[0-9]+)?)</td>', html_content, re.S)
    if m_req:
        header_info["req_credits"] = float(m_req.group(1))
        header_info["compl_credits"] = float(m_req.group(2))
        header_info["actual_credits"] = float(m_req.group(3))
        
    m_gpa = re.search(r'GPA:.*?<td[^>]*>([0-9\.]+)</td>', html_content, re.S)
    if m_gpa:
        header_info["gpa"] = float(m_gpa.group(1))
        
    m_audit = re.search(r'审核结果:.*?<td[^>]*>(.*?)</td>', html_content, re.S)
    if m_audit:
        header_info["audit_result"] = re.sub(r'&nbsp;|\s+', ' ', m_audit.group(1)).strip()

    m_grade = re.search(r'年级:.*?<td[^>]*class=\"content\"[^>]*>([0-9]{4})', html_content, re.S)
    if m_grade:
        header_info["grade"] = int(m_grade.group(1))

    m_major = re.search(r'专业/专业方向:.*?<td[^>]*class=\"content\"[^>]*>(.*?)</td>', html_content, re.S)
    if m_major:
        header_info["major"] = re.sub(r'&nbsp;|\s+', ' ', m_major.group(1)).strip()

    m_dept = re.search(r'院系:.*?<td[^>]*class=\"content\"[^>]*>(.*?)</td>', html_content, re.S)
    if m_dept:
        header_info["dept"] = re.sub(r'&nbsp;|\s+', ' ', m_dept.group(1)).strip()

    m_name = re.search(r'姓名:.*?<td[^>]*class=\"content\"[^>]*>(.*?)</td>', html_content, re.S)
    if m_name:
        header_info["name"] = re.sub(r'&nbsp;|\s+', ' ', m_name.group(1)).strip()

    m_sid = re.search(r'学号:.*?<td[^>]*class=\"content\"[^>]*>(.*?)</td>', html_content, re.S)
    if m_sid:
        header_info["student_id"] = re.sub(r'&nbsp;|\s+', ' ', m_sid.group(1)).strip()

    # 2. Parse table rows
    parser = SimpleTableParser()
    parser.feed(html_content)
    
    completed_courses = {}
    in_progress_courses = {}
    unfulfilled_courses = {}
    
    for cells in parser.rows:
        if len(cells) < 7:
            continue
        
        # Check if any cell matches course code pattern (e.g. CS100, MATH1112, GEHA1050)
        code_idx = -1
        for idx, text in enumerate(cells):
            clean_text = text.strip()
            if re.match(r"^[A-Z]{2,6}[0-9]{3,4}[A-Za-z0-9]*(\.[0-9]{2})?$", clean_text):
                code_idx = idx
                break
                
        if code_idx != -1:
            raw_code = cells[code_idx].split(".")[0]
            name = cells[code_idx + 1] if code_idx + 1 < len(cells) else ""
            
            # Extract credit (from compl_cred or actual_cred or req_cred)
            credit = 0.0
            for cell_text in cells[code_idx+1:]:
                clean_c = cell_text.strip()
                if re.match(r"^[0-9]+(\.[0-9]+)?$", clean_c):
                    val = float(clean_c)
                    if val > 0:
                        credit = val
                        break
            
            row_str = " ".join(cells)
            is_in_progress = any(kw in row_str for kw in ["正在修读", "在读", "修读中", "本学期"])
            
            # Check grade or pass status
            # Col 6 is grade, Col 7 is pass status in standard EAMS
            grade = ""
            for c in cells[code_idx+1:]:
                if re.match(r"^(A[\+\-]?|B[\+\-]?|C[\+\-]?|D[\+\-]?|P|[6-9][0-9]|100)$", c.strip()):
                    grade = c.strip()
                    break
            
            is_explicit_no = any(c.strip() == "否" for c in cells)
            is_explicit_yes = any(c.strip() == "是" for c in cells)
            
            course_obj = {
                "code": raw_code,
                "name": name,
                "credit": credit,
                "grade": grade,
                "raw_cells": cells
            }
            
            if is_in_progress:
                in_progress_courses[raw_code] = course_obj
            elif not is_explicit_no and (grade or is_explicit_yes):
                completed_courses[raw_code] = course_obj
            else:
                unfulfilled_courses[raw_code] = course_obj

    return completed_courses, in_progress_courses, header_info

def analyze_plan_gap(completed_courses, in_progress_courses, curriculum_path=DEFAULT_CURRICULUM, header_info=None):
    with open(curriculum_path, "r", encoding="utf-8") as f:
        curriculum = json.load(f)
        
    all_taken_codes = set(completed_courses.keys()).union(set(in_progress_courses.keys()))
    
    total_earned_credits = sum(c.get("credit", 0.0) for c in completed_courses.values())
    total_in_progress_credits = sum(c.get("credit", 0.0) for c in in_progress_courses.values())
    
    modules_analysis = []
    
    for mod in curriculum.get("modules", []):
        mod_name = mod["name"]
        req_cred = mod.get("required_credits", 0.0)
        
        # Check compulsory courses
        missing_compulsory = []
        completed_compulsory = []
        for cc in mod.get("compulsory_courses", []):
            code = cc["code"]
            if code in completed_courses:
                completed_compulsory.append((cc, "completed"))
            elif code in in_progress_courses:
                completed_compulsory.append((cc, "in_progress"))
            else:
                missing_compulsory.append(cc)
                
        # Check choice groups
        choice_status = []
        for cg in mod.get("choice_groups", []):
            cg_name = cg["name"]
            cg_req = cg["required_credits"]
            satisfied = False
            taken_in_group = []
            for opt in cg["options"]:
                opt_codes = opt["code"].split("+")
                if all(cd in all_taken_codes for cd in opt_codes):
                    satisfied = True
                    taken_in_group.append(opt)
            choice_status.append({
                "group_name": cg_name,
                "required_credits": cg_req,
                "satisfied": satisfied,
                "taken": taken_in_group,
                "options": cg["options"]
            })

        # Calculate module elective credits taken
        elective_taken_credits = 0.0
        for ec in mod.get("elective_pool", []):
            if isinstance(ec, dict):
                ecode = ec.get("code")
                ecred = ec.get("credit", 2.0)
            else:
                ecode = str(ec)
                ecred = 2.0
            if not ecode:
                continue
            if ecode in completed_courses:
                elective_taken_credits += completed_courses[ecode].get("credit", ecred)
            elif ecode in in_progress_courses:
                elective_taken_credits += in_progress_courses[ecode].get("credit", ecred)
            
        modules_analysis.append({
            "name": mod_name,
            "required_credits": req_cred,
            "elective_taken_credits": elective_taken_credits,
            "missing_compulsory": missing_compulsory,
            "completed_compulsory": completed_compulsory,
            "choice_status": choice_status,
            "module_def": mod
        })
        
    return {
        "curriculum": curriculum,
        "header_info": header_info or {},
        "total_earned_credits": total_earned_credits,
        "total_in_progress_credits": total_in_progress_credits,
        "min_total_credits": curriculum.get("min_total_credits", 143),
        "modules_analysis": modules_analysis,
        "completed_count": len(completed_courses),
        "in_progress_count": len(in_progress_courses)
    }

def generate_personalized_recommendation_report(analysis, target_semester="spring"):
    header = analysis["header_info"]
    curriculum = analysis["curriculum"]
    lines = ["# EAMS 实时计划完成情况", f"年级：{header.get('grade')} | 专业：{header.get('major')}"]
    for key, label in (("req_credits", "官方要求学分"), ("compl_credits", "官方预审完成学分（含在读）"),
                       ("actual_credits", "官方实修学分"), ("gpa", "GPA")):
        if header.get(key) is not None:
            lines.append(f"- {label}：{header[key]}")
    lines.append(f"- 官方审核状态：{header.get('audit_result') or '页面未提供'}")
    lines.append(f"- 课程行解析的已通过学分：{analysis['total_earned_credits']:.1f}")
    lines.append(f"- 课程行解析的在读学分：{analysis['total_in_progress_credits']:.1f}")
    lines.append("预审完成学分已包含在读课程，不能再次叠加。模块认定及抵扣以本次 EAMS 原始表格为准。")
    if not curriculum:
        lines.append("公开培养方案比对暂不可用：" + analysis["comparison_error"])
        return "\n".join(lines)
    lines.append(f"\n公开培养方案比对：{curriculum.get('grade')} 级 {curriculum.get('major')}。以下为待核对项目，需结合 EAMS 模块认定确认。")
    for module in analysis["modules_analysis"]:
        for course in module["missing_compulsory"]:
            lines.append(f"- {module['name']}：页面未识别到 {course['code']} {course['name']} 的通过或在读记录")
        for group in module["choice_status"]:
            if not group["satisfied"]:
                lines.append(f"- {module['name']} / {group['group_name']}：需核对课程组抵扣")
    return "\n".join(lines)


def main():
    from live_session import LiveQueryError
    from sync_my_plan import sync_and_audit
    parser = argparse.ArgumentParser(description="实时查询并分析 EAMS 官方计划完成情况；不读取本地档案")
    parser.add_argument("--major", help="显式指定比对专业")
    parser.add_argument("--grade", type=int, help="显式指定比对年级")
    parser.add_argument("--sync", action="store_true", help="兼容参数；每次均实时查询")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        sync_and_audit(major=args.major, grade=args.grade, as_json=args.json)
    except LiveQueryError as error:
        print(f"查询失败：{error}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
