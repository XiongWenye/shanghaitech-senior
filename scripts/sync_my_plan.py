#!/usr/bin/env python3
"""
ShanghaiTech Real-time Plan Completion & Course History Sync Engine.
Integrates with TechPie backend to query multi-semester course enrollments,
fills official course credits from CourseBench DB, and generates
accurate graduation plan progress.
"""

import os
import sys
import json
import time
import re
import sqlite3
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Tuple, Any

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPTS_DIR, "..", "data")
COOKIE_PATH = os.path.join(DATA_DIR, "eams_cookie.txt")
SCHEDULE_PATH = os.path.join(DATA_DIR, "my_schedule.json")
PLAN_COMPL_JSON_PATH = os.path.join(DATA_DIR, "my_plan_completion.json")
CB_DB_PATH = os.path.join(DATA_DIR, "coursebench.db")

TECHPIE_EAMS_AUTH_URL = "https://techpie.geekpie.club/api/auth/third-party/eams"
TECHPIE_SEMESTERS_URL = "https://techpie.geekpie.club/api/schedule/semesters"
TECHPIE_COURSE_TABLE_URL = "https://techpie.geekpie.club/api/schedule/course_table"
TECHPIE_EXAM_TABLE_URL = "https://techpie.geekpie.club/api/schedule/exam_table"

def get_tgc(cookie: Optional[str] = None) -> Optional[str]:
    """Retrieve raw TGC string from argument, file, or env."""
    raw = cookie or os.environ.get("CASTGC") or os.environ.get("EAMS_COOKIE")
    if not raw and os.path.exists(COOKIE_PATH):
        try:
            with open(COOKIE_PATH, "r", encoding="utf-8") as f:
                raw = f.read().strip()
        except Exception:
            pass
    if not raw:
        return None
    raw = raw.strip()
    if "CASTGC=" in raw:
        for part in raw.split(";"):
            part = part.strip()
            if part.startswith("CASTGC="):
                return part.split("=", 1)[1].strip()
    return raw

def exchange_eams_cookies(tgc: str) -> Optional[str]:
    """Exchange TGC for active EAMS cookies via TechPie proxy."""
    req = urllib.request.Request(
        TECHPIE_EAMS_AUTH_URL,
        data=json.dumps({"tgc": tgc}).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "TechPie-SeniorSkill/2.0",
        }
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                if res.get("success") and "data" in res:
                    return res["data"]["raw"]["cookies"]
        except Exception as e:
            if attempt < 2:
                time.sleep(1)
            else:
                print(f"⚠️ EAMS 会话认证换取失败: {e}", file=sys.stderr)
    return None

def extract_course_code(raw_name: str, raw_code: str = "") -> str:
    """Robustly extract canonical course code from name or code field."""
    if raw_code and re.match(r'^[A-Z]{2,6}[0-9]{3,4}[A-Za-z0-9]*$', raw_code.split(".")[0].strip().upper()):
        return raw_code.split(".")[0].strip().upper()
    
    # Try finding standard course pattern in raw_name e.g. BIO1011.02, CS100, GEHA1003
    matches = re.findall(r'\b([A-Z]{2,6}[0-9]{3,4}[A-Za-z0-9]*)(?:\.[0-9]{2})?\b', raw_name.upper())
    if matches:
        return matches[-1]
    
    return raw_name.strip()

def lookup_course_credit_and_zh_name(code: str, conn: Optional[sqlite3.Connection] = None) -> Tuple[float, str]:
    """Lookup credit and Chinese course name from CourseBench sqlite database."""
    if not conn:
        return 3.0, ""
    try:
        cur = conn.cursor()
        cur.execute("SELECT credit, name FROM courses WHERE code = ? COLLATE NOCASE", (code,))
        row = cur.fetchone()
        if row:
            cred = float(row[0]) if row[0] is not None else 3.0
            name = row[1] if row[1] else ""
            return cred, name
    except Exception:
        pass
    return 3.0, ""

def fetch_all_semesters_courses(cookies: str, student_id: str) -> Tuple[Dict[str, Any], Dict[str, Any], List[Dict[str, Any]]]:
    """
    Fetch course tables across all enrolled semesters.
    Returns (completed_dict, in_progress_dict, current_semester_courses_list).
    """
    conn = None
    if os.path.exists(CB_DB_PATH):
        try:
            conn = sqlite3.connect(CB_DB_PATH)
        except Exception:
            pass

    # 1. Fetch semesters metadata
    req_sem = urllib.request.Request(
        TECHPIE_SEMESTERS_URL,
        data=json.dumps({"cookies": cookies, "studentId": student_id}).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"}
    )
    default_semester = "282"
    semesters_map = {}
    try:
        with urllib.request.urlopen(req_sem, timeout=15) as resp:
            sem_res = json.loads(resp.read().decode("utf-8"))
            if sem_res.get("success"):
                default_semester = str(sem_res["data"].get("defaultSemester") or "282")
                semesters_map = sem_res["data"].get("semesters", {})
    except Exception as e:
        print(f"⚠️ 学期目录拉取异常，使用默认学期 {default_semester}: {e}", file=sys.stderr)

    # Flatten relevant semesters for the student (from 2023 onwards for grade 2023)
    target_terms = []
    for year in sorted(semesters_map.keys()):
        parts = year.split("-")
        if parts and parts[0].isdigit() and int(parts[0]) >= 2023:
            term_dict = semesters_map[year]
            if isinstance(term_dict, dict):
                for term_no, sem_id in sorted(term_dict.items()):
                    target_terms.append((f"{year}-{term_no}", str(sem_id)))

    if not target_terms:
        target_terms = [
            ("2023-2024-1", "222"),
            ("2023-2024-2", "223"),
            ("2023-2024-3", "224"),
            ("2024-2025-1", "242"),
            ("2024-2025-2", "243"),
            ("2024-2025-3", "244"),
            ("2025-2026-1", "262"),
            ("2025-2026-2", "263"),
            ("2025-2026-3", "264"),
            ("2026-2027-1", "282"),
        ]

    completed_courses: Dict[str, Dict[str, Any]] = {}
    in_progress_courses: Dict[str, Dict[str, Any]] = {}
    current_schedule_courses: List[Dict[str, Any]] = []

    print(f"🔄 正在同步学号 {student_id} 历届学期实际修读课程与课表...")

    for term_label, sem_id in target_terms:
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Connection": "close",
            "User-Agent": "TechPie-SeniorSkill/2.0",
        }
        success_term = False
        for attempt in range(2):
            try:
                req_c = urllib.request.Request(
                    TECHPIE_COURSE_TABLE_URL,
                    data=json.dumps({
                        "cookies": cookies,
                        "studentId": student_id,
                        "semester_id": sem_id,
                        "table_id": "std"
                    }).encode("utf-8"),
                    headers=headers
                )
                with urllib.request.urlopen(req_c, timeout=15) as resp_c:
                    c_data = json.loads(resp_c.read().decode("utf-8"))
                    if not c_data.get("success"):
                        break
                    courses = c_data.get("data", {}).get("courses", [])
                    if not courses:
                        success_term = True
                        break

                    if sem_id == default_semester:
                        current_schedule_courses = courses

                    term_unique = {}
                    for c in courses:
                        raw_name = c.get("name", "")
                        code = extract_course_code(raw_name, c.get("courseCode", ""))
                        if code not in term_unique:
                            cred, zh_name = lookup_course_credit_and_zh_name(code, conn)
                            display_name = zh_name if zh_name else (raw_name.split("(")[0].strip() if "(" in raw_name else raw_name)
                            term_unique[code] = {
                                "code": code,
                                "name": display_name,
                                "raw_name": raw_name,
                                "teachers": c.get("teachers", ""),
                                "classroom": c.get("classroom", ""),
                                "semester": term_label,
                                "semester_id": sem_id,
                                "credit": cred,
                            }

                    if sem_id == default_semester:
                        in_progress_courses.update(term_unique)
                        print(f"  ⚡ 【{term_label} (当前学期)】发现 {len(term_unique)} 门正在修读课程")
                    else:
                        completed_courses.update(term_unique)
                        print(f"  ✅ 【{term_label}】同步 {len(term_unique)} 门已修读课程")
                    success_term = True
                    break
            except Exception as e:
                if attempt == 0:
                    time.sleep(0.8)
                else:
                    print(f"  ⚠️ 拉取 {term_label} ({sem_id}) 课表跳过: {e}", file=sys.stderr)
        time.sleep(0.3)

    if conn:
        conn.close()

    return completed_courses, in_progress_courses, current_schedule_courses

def save_sync_data(
    completed_courses: Dict[str, Dict[str, Any]],
    in_progress_courses: Dict[str, Dict[str, Any]],
    current_schedule_courses: List[Dict[str, Any]],
    student_id: str,
    major: str = "计算机科学与技术",
    grade: int = 2026,
    name: str = "上科大学子",
    dept: str = "信息科学与技术学院"
):
    """Save parsed plan data and schedule to data files."""
    os.makedirs(DATA_DIR, exist_ok=True)

    tot_comp_cred = sum(c.get("credit", 0.0) for c in completed_courses.values())
    tot_prog_cred = sum(c.get("credit", 0.0) for c in in_progress_courses.values())

    plan_data = {
        "student_id": student_id,
        "name": name,
        "major": major,
        "dept": dept,
        "grade": grade,
        "compl_credits": tot_comp_cred,
        "in_progress_credits": tot_prog_cred,
        "completed": list(completed_courses.values()),
        "in_progress": list(in_progress_courses.values()),
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(PLAN_COMPL_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(plan_data, f, ensure_ascii=False, indent=2)

    if current_schedule_courses:
        sched_data = {
            "semester_id": "282",
            "student_id": student_id,
            "courses": current_schedule_courses,
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(SCHEDULE_PATH, "w", encoding="utf-8") as f:
            json.dump(sched_data, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 培养方案修课档案已生成！")
    print(f"   • 已修完课程: {len(completed_courses)} 门 ({tot_comp_cred:.1f} 学分)")
    print(f"   • 本学期在读课程: {len(in_progress_courses)} 门 ({tot_prog_cred:.1f} 学分)")
    print(f"   • 存储位置: {PLAN_COMPL_JSON_PATH}")

def sync_and_audit(cookie: Optional[str] = None, student_id: Optional[str] = None, major: Optional[str] = None, grade: Optional[int] = None) -> bool:
    tgc = get_tgc(cookie)
    if not tgc:
        print("❌ 未检测到 CASTGC 统一认证凭据，无法执行在线同步。")
        print("学长 SKILL 第一要义：本地零个人化虚假数据，所有个人学业与选课档案必须通过网络端口实时查询。")
        print("👉 请先运行 `python3 scripts/senior.py login` 登录。")
        return False

    # Dynamically extract student profile from live EAMS session if not provided
    name = "上科大学子"
    dept = "信息科学与技术学院"
    if not student_id or not major or not grade:
        try:
            import eams_session
            profile = eams_session.get_student_profile(tgc)
            if profile:
                student_id = student_id or profile.get("student_id")
                name = profile.get("name") or name
                major = major or profile.get("major") or "计算机科学与技术"
                grade = grade or profile.get("grade") or 2026
                dept = profile.get("dept") or dept
        except Exception:
            pass

    if not student_id:
        print("❌ 无法从在线 EAMS 会话中解析学生学号，请传入 --student-id 参数。")
        return False

    final_major = major or "计算机科学与技术"
    final_grade = grade or 2026

    cookies = exchange_eams_cookies(tgc)
    if not cookies:
        print("❌ 换取 EAMS 会话失败，请检查统一认证凭据是否已过期。")
        return False

    completed, in_prog, sched = fetch_all_semesters_courses(cookies, student_id=student_id)
    save_sync_data(completed, in_prog, sched, student_id=student_id, major=final_major, grade=final_grade, name=name, dept=dept)
    return True

if __name__ == "__main__":
    sync_and_audit()
