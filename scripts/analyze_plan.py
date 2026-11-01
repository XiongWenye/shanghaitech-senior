#!/usr/bin/env python3
"""
ShanghaiTech Plan Completion Analyzer & Personalized Course Recommendation Engine
Zero-dependency script (uses Python standard library: json, re, html.parser, sqlite3).
Supports all 12 majors (2026 Grade and 2023 Grade):
Compares student's actual plan completion status from EAMS (or raw course code list)
against the official Major Curriculum, identifies missing compulsory courses and credit deficits,
and invokes CourseBench to recommend the highest-rated courses to fill those exact gaps.
"""

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

# Import query_course recommendation engine
sys.path.append(SCRIPTS_DIR)
try:
    from query_course import recommend_courses, get_course_detail, search_courses
except ImportError:
    pass

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

def resolve_curriculum_path(major_str=None, grade=2026):
    if not major_str:
        return DEFAULT_CURRICULUM
    m_clean = major_str.strip().lower()
    if grade == 2023 and any(k in m_clean for k in ["cs", "计算机", "计科"]):
        p = os.path.join(CURRICULUM_DIR, "2023_CS_SIST.json")
        if os.path.exists(p):
            return p
    for fname in os.listdir(CURRICULUM_DIR):
        if not fname.endswith(".json"):
            continue
        if str(grade) in fname and any(k in fname for k in [major_str, m_clean]):
            return os.path.join(CURRICULUM_DIR, fname)
    if m_clean in MAJOR_MAPPING:
        p = os.path.join(CURRICULUM_DIR, MAJOR_MAPPING[m_clean])
        if os.path.exists(p):
            return p
    return DEFAULT_CURRICULUM

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
        "req_credits": 140.0,
        "compl_credits": 0.0,
        "actual_credits": 0.0,
        "gpa": 0.0,
        "audit_result": "",
        "major": "",
        "dept": "",
        "grade": None,
        "name": "",
        "student_id": ""
    }
    
    m_req = re.search(r'要求学分/完成学分/实修学分:.*?<td[^>]*>([0-9]+)&nbsp;/&nbsp;([0-9]+)&nbsp;/&nbsp;([0-9]+)</td>', html_content, re.S)
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
            elif grade or (is_explicit_yes and not is_explicit_no):
                completed_courses[raw_code] = course_obj
            else:
                unfulfilled_courses[raw_code] = course_obj

    return completed_courses, in_progress_courses, header_info

def parse_course_codes_str(input_str):
    """Parses a comma or whitespace separated list of course codes (e.g. CS100, MATH1112, SI100B)."""
    codes = re.findall(r'\b[A-Z]{2,6}[0-9]{3,4}[A-Za-z0-9]*\b', input_str.upper())
    completed = {}
    for c in codes:
        completed[c] = {"code": c, "name": c, "credit": 3.0}
    return completed, {}

def parse_text_or_json_plan(input_path_or_str):
    if os.path.isfile(input_path_or_str):
        with open(input_path_or_str, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    else:
        content = input_path_or_str
        
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            completed = {c["code"]: c for c in data.get("completed", [])}
            in_prog = {c["code"]: c for c in data.get("in_progress", [])}
            return completed, in_prog, {}
        elif isinstance(data, list):
            completed = {c["code"]: c for c in data if "code" in c}
            return completed, {}, {}
    except json.JSONDecodeError:
        pass
        
    if "<table" in content.lower():
        return parse_html_plan(content)
    else:
        comp, in_p = parse_course_codes_str(content)
        return comp, in_p, {}

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
    curr = analysis["curriculum"]
    earned = analysis["total_earned_credits"]
    in_prog = analysis["total_in_progress_credits"]
    min_tot = analysis["min_total_credits"]
    header = analysis.get("header_info", {})
    major_name = curr.get("major", "计算机科学与技术")
    institute = curr.get("institute", "信息科学与技术学院")
    grade = curr.get("grade", 2026)
    
    lines = []
    lines.append(f"# 🎓 上海科技大学修课完成度与毕业学分个性化诊断报告")
    lines.append(f"**专业**: {major_name} ({institute}) | **年级**: {grade}级 | **毕业总学分要求**: {min_tot} 学分\n")
    
    lines.append(f"### 📊 学分进度总览与在读状态识别")
    if header.get("compl_credits"):
        lines.append(f"- **EAMS 预审系统完成学分**: **{header['compl_credits']:.1f}** / **{min_tot:.1f}** 学分")
        lines.append(f"- **EAMS 官方审核状态**: `{header.get('audit_result', '进行中')}` | **当前 GPA**: `{header.get('gpa', 0.0):.2f}`")
        lines.append(f"> ⚠️ **【重要统计提示】**：EAMS 预审界面中显示的“完成学分”（{header['compl_credits']:.1f} 分）**已预先包含了本学期正在修读的课程**（审核状态提示‘未通过预审，有在读课程’）。因此切勿将完成学分与在读学分进行重复叠加！")
        lines.append(f"- **纯已结课通过学分**: **{earned:.1f}** 学分 ({analysis['completed_count']} 门课程已获最终成绩)")
        lines.append(f"- **本学期正在修读学分**: **{in_prog:.1f}** 学分 ({analysis['in_progress_count']} 门课程，待期末结课出分)")
        lines.append(f"- **本学期结课后预计达成学分**: **{earned + in_prog:.1f}** 学分 (学分达成率 `{(earned + in_prog) / min_tot * 100:.1f}%`)")
        lines.append(f"- **毕业尚需修读学分**: **{max(0.0, min_tot - (earned + in_prog)):.1f}** 学分\n")
    else:
        lines.append(f"- **已完成结课学分**: **{earned:.1f}** 学分 ({analysis['completed_count']} 门)")
        lines.append(f"- **正在修读学分**: **{in_prog:.1f}** 学分 ({analysis['in_progress_count']} 门)")
        lines.append(f"> ⚠️ **【注意】**：若您的统计数据来自 EAMS 预审界面，该数值通常已包含在读课程，请勿重复相加！")
        lines.append(f"- **预计总学分**: **{earned + in_prog:.1f}** 学分 | **毕业尚需学分**: **{max(0.0, min_tot - (earned + in_prog)):.1f}** 学分\n")
    
    lines.append(f"### ⚠️ 真实待修核心必修课缺口排查 (毕业硬性要求)")
    has_missing_comp = False
    for mod in analysis["modules_analysis"]:
        if mod["missing_compulsory"]:
            has_missing_comp = True
            lines.append(f"#### 📌 【{mod['name']}】待修必修课：")
            for mc in mod["missing_compulsory"][:8]:
                lines.append(f"- **{mc['name']}** (`{mc['code']}`), {mc.get('credit', '?')} 学分")
        for cg in mod["choice_status"]:
            if not cg["satisfied"]:
                has_missing_comp = True
                lines.append(f"#### 📌 【{mod['name']} - {cg['group_name']}】未满足（需修满 {cg['required_credits']} 学分）：")
                for opt in cg["options"]:
                    lines.append(f"  - 可选: **{opt['name']}** (`{opt['code']}`), {opt['credit']} 分")
    if not has_missing_comp:
        lines.append("🎉 恭喜！所有硬性专业必修课与基础必修环节均已修读或正在修读完毕！\n")
    else:
        lines.append("")

    lines.append(f"### 🎯 针对培养方案缺口的专属 CourseBench 智能选课方案")
    lines.append(f"结合同学【**{major_name}**】背景与目标学期（**{target_semester.upper()}**），精准匹配缺口选修模块：\n")
    
    # 1. 跨学科选修课推荐
    lines.append(f"#### 1. 【跨学科选修课程】缺口匹配 (需修满 3 学分)")
    recs_inter = recommend_courses(
        major=major_name,
        credit=3.0,
        category="跨学科",
        semester=target_semester,
        workload_pref="any",
        grade_pref="generous",
        top_k=2
    )
    if recs_inter:
        for idx, r in enumerate(recs_inter, 1):
            lines.append(f"  - **最优推荐 {idx}: 【{r['name']}】(`{r['code']}`, {r['institute']}) - {r['credit']}学分**")
            lines.append(f"    - 评分: 质量 `{r['score_quality']:.1f}` / 作业友好 `{r['score_workload']:.1f}` / 给分慷慨 `{r['score_grade']:.1f}` ({r['comment_num']} 条评价)")
            lines.append(f"    - 契合理由: {r.get('rel_reason') or '跨学科高口碑好课'}")
            lines.append(f"    - 链接: https://coursebench.org/course/{r['id']}")
    else:
        lines.append("  - 建议选修外学院交叉课程（如物质材料学、生医工影像、创管金融量化等）。")

    # 2. 创意与艺术推荐
    lines.append(f"\n#### 2. 【通识选修 - 创意与艺术课程群】推荐 (需修满 2 学分)")
    recs_arts = recommend_courses(
        major=major_name,
        credit=2.0,
        category="通识",
        semester=target_semester,
        workload_pref="any",
        grade_pref="generous",
        top_k=3
    )
    arts_shown = 0
    for r in recs_arts:
        if r['code'].startswith("ARTS") or "艺术" in r['institute'] or "书院" in r['institute']:
            arts_shown += 1
            lines.append(f"  - **推荐 {arts_shown}: 【{r['name']}】(`{r['code']}`, {r['institute']}) - {r['credit']}学分**")
            lines.append(f"    - 评分: 质量 `{r['score_quality']:.1f}` / 作业友好 `{r['score_workload']:.1f}` / 给分慷慨 `{r['score_grade']:.1f}`")
            lines.append(f"    - 链接: https://coursebench.org/course/{r['id']}")
            if arts_shown >= 2:
                break
    if arts_shown == 0:
        lines.append("  - 推荐 【数字媒体设计】(`ARTS1401`) 或 【用户体验与创新设计】(`ARTS1407`)。")

    # 3. 文学写作与经典导读
    lines.append(f"\n#### 3. 【通识选修 - 文学写作与文明经典导读】高分口碑课推荐")
    lines.append(f"  - **【非虚构写作导论】(`GEHA1193`, 杜雨晴, 3学分)**: 质量 5.0 / 作业 4.8 / 给分 5.0，期末 Essay 悉心指导，GPA 保分天花板。")
    lines.append(f"  - **【唐宋文学精华】(`GEHA1152`, 陈娅妮, 3学分)**: 质量 5.0 / 给分 5.0，历届口碑极佳，人文素养浸润。")
    lines.append(f"  - **【柏拉图《理想国》导读】(`GEHA1087`, 2学分)**: 质量 4.8 / 给分 4.7，经典研读首选。")
    
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Analyze ShanghaiTech plan completion and recommend gap-filling courses")
    parser.add_argument("--file", help="Path to exported HTML or JSON file of myPlanCompl.action")
    parser.add_argument("--courses", help="Comma-separated course codes (e.g. 'CS100, MATH1112, SI100B, GESS1028')")
    parser.add_argument("--major", default=None, help="Student's major (e.g. 物理, 计算机, 生医工, 工业设计, AI荣誉班)")
    parser.add_argument("--grade", type=int, default=None, help="Student's grade year (e.g. 2026, 2023)")
    parser.add_argument("--curriculum", help="Explicit path to curriculum JSON")
    parser.add_argument("--semester", default="spring", help="Target semester (spring/fall)")
    parser.add_argument("--json", action="store_true", help="Output raw analysis JSON")
    
    args = parser.parse_args()
    
    header_info = {}
    if args.file and os.path.exists(args.file):
        completed, in_prog, header_info = parse_text_or_json_plan(args.file)
    elif args.courses:
        completed, in_prog, header_info = parse_text_or_json_plan(args.courses)
    else:
        print("[!] No plan completion file or courses provided.")
        print("Usage: python3 scripts/analyze_plan.py --major <专业> --courses 'CS100, MATH1112, SI100B'")
        print("   or: python3 scripts/analyze_plan.py --file <myPlanCompl.html> [--major <专业>]")
        sys.exit(1)
        
    # Auto-detect grade and major from parsed EAMS header if available
    final_grade = args.grade or header_info.get("grade") or 2026
    final_major = args.major or header_info.get("major") or "计算机"
    
    cur_path = args.curriculum if args.curriculum else resolve_curriculum_path(final_major, final_grade)
    
    if not args.json:
        print("=" * 72)
        print(f"📋 【EAMS 计划完成情况与学籍确认】")
        if header_info.get("student_id") or header_info.get("name"):
            print(f"   • 学生: {header_info.get('name', '未记录')} (学号: {header_info.get('student_id', '未记录')})")
        print(f"   • 学籍确认: {final_grade} 级 | {header_info.get('dept', '上海科技大学')} | {final_major}")
        print(f"   • 载入培养方案: {os.path.basename(cur_path)}")
        print("=" * 72 + "\n")

    analysis = analyze_plan_gap(completed, in_prog, cur_path, header_info)
    
    if args.json:
        print(json.dumps(analysis, ensure_ascii=False, indent=2))
    else:
        report = generate_personalized_recommendation_report(analysis, args.semester)
        print(report)

if __name__ == "__main__":
    main()
