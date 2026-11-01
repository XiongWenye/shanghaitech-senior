#!/usr/bin/env python3
"""
ShanghaiTech Coursebench Data Synchronization Script
Fetches course list, comments, and teacher groups from Coursebench API,
and compiles them into a fast SQLite database and unified JSON export.
"""

import sys
import os
import json
import sqlite3
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

API_ENDPOINTS = [
    "https://coursebench.zambar.dev",
    "https://coursebench.org"
]

def fetch_json(url, retries=3, timeout=10):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "CoursebenchSkill/1.0 (ShanghaiTech Agent)"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if not data.get("error", True):
                    return data.get("data")
        except Exception as e:
            if attempt == retries - 1:
                pass
            time.sleep(0.3 * (attempt + 1))
    return None

def get_base_url():
    for base in API_ENDPOINTS:
        try:
            req = urllib.request.Request(f"{base}/v1/course/all", headers={"User-Agent": "CoursebenchSkill/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    if not data.get("error", True):
                        return base
        except Exception:
            continue
    return API_ENDPOINTS[0]

def init_db(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            code TEXT NOT NULL,
            institute TEXT,
            credit REAL,
            comment_num INTEGER DEFAULT 0,
            score_quality REAL DEFAULT 0,
            score_workload REAL DEFAULT 0,
            score_difficulty REAL DEFAULT 0,
            score_grade REAL DEFAULT 0,
            teachers TEXT,
            semesters TEXT,
            latest_semester INTEGER,
            updated_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY,
            course_id INTEGER,
            group_id INTEGER,
            teacher_name TEXT,
            title TEXT,
            content TEXT,
            semester INTEGER,
            post_time INTEGER,
            score_quality REAL DEFAULT 0,
            score_workload REAL DEFAULT 0,
            score_difficulty REAL DEFAULT 0,
            score_grade REAL DEFAULT 0,
            user_year INTEGER,
            is_anonymous INTEGER,
            like_count INTEGER DEFAULT 0,
            dislike_count INTEGER DEFAULT 0,
            FOREIGN KEY (course_id) REFERENCES courses (id)
        )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_courses_code ON courses(code)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_courses_name ON courses(name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_courses_institute ON courses(institute)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_courses_credit ON courses(credit)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_comments_course ON comments(course_id)")

    conn.commit()
    return conn

def sync_data(output_dir="data"):
    os.makedirs(output_dir, exist_ok=True)
    db_path = os.path.join(output_dir, "coursebench.db")
    json_path = os.path.join(output_dir, "coursebench_export.json")

    base_url = get_base_url()
    print(f"[*] Using Coursebench API: {base_url}")

    print("[*] Fetching all courses...")
    raw_courses = fetch_json(f"{base_url}/v1/course/all")
    if not raw_courses:
        print("[!] Failed to fetch course list. Aborting.")
        return False

    print(f"[+] Total courses loaded: {len(raw_courses)}")
    courses_with_comments = [c for c in raw_courses if c.get("comment_num", 0) > 0]
    print(f"[+] Courses with comments to crawl: {len(courses_with_comments)}")

    all_comments_by_course = {}
    print(f"[*] Fetching comments concurrently with 20 workers...")
    start_t = time.time()

    def fetch_course_comments(course):
        cid = course["id"]
        comments = fetch_json(f"{base_url}/v1/comment/course/{cid}")
        return cid, comments or []

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(fetch_course_comments, c): c["id"] for c in courses_with_comments}
        completed = 0
        total = len(courses_with_comments)
        for future in as_completed(futures):
            cid, comments = future.result()
            all_comments_by_course[cid] = comments
            completed += 1
            if completed % 100 == 0 or completed == total:
                print(f"    Progress: {completed}/{total} courses ({completed*100//total}%)")

    total_comments = sum(len(c) for c in all_comments_by_course.values())
    print(f"[+] Finished fetching {total_comments} comments in {time.time()-start_t:.2f}s")

    print("[*] Writing to SQLite database...")
    conn = init_db(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM comments")
    cur.execute("DELETE FROM courses")

    now_iso = datetime.now().isoformat()
    export_data = []

    for c in raw_courses:
        cid = c["id"]
        name = c.get("name", "").strip()
        code = c.get("code", "").strip()
        institute = c.get("institute", "").strip()
        credit = float(c.get("credit", 0.0) or 0.0)
        comment_num = int(c.get("comment_num", 0) or 0)
        score = c.get("score") or [0, 0, 0, 0]

        comments = all_comments_by_course.get(cid, [])
        semesters = sorted(list({cm.get("semester") for cm in comments if cm.get("semester")}))
        semesters_str = ",".join(str(s) for s in semesters)
        latest_semester = semesters[-1] if semesters else None

        teachers_set = set()
        for cm in comments:
            group = cm.get("group") or {}
            for t in group.get("teachers", []):
                tname = t.get("name", "").strip()
                if tname and tname != "其他":
                    teachers_set.add(tname)
        teachers_str = ", ".join(sorted(teachers_set))

        cur.execute("""
            INSERT INTO courses (
                id, name, code, institute, credit, comment_num,
                score_quality, score_workload, score_difficulty, score_grade,
                teachers, semesters, latest_semester, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cid, name, code, institute, credit, comment_num,
            score[0], score[1], score[2], score[3],
            teachers_str, semesters_str, latest_semester, now_iso
        ))

        # Insert comments
        course_comments_export = []
        for cm in comments:
            cm_id = cm.get("id")
            title = cm.get("title", "") or ""
            content = cm.get("content", "") or ""
            semester = cm.get("semester")
            post_time = cm.get("post_time")
            cm_score = cm.get("score") or [0, 0, 0, 0]
            group = cm.get("group") or {}
            group_id = group.get("id")
            cm_teachers = ", ".join(t.get("name", "") for t in group.get("teachers", []) if t.get("name"))
            user = cm.get("user") or {}
            user_year = user.get("year")
            is_anon = 1 if cm.get("is_anonymous", False) or user is None else 0
            likes = cm.get("like", 0) or 0
            dislikes = cm.get("dislike", 0) or 0

            cur.execute("""
                INSERT INTO comments (
                    id, course_id, group_id, teacher_name, title, content,
                    semester, post_time, score_quality, score_workload,
                    score_difficulty, score_grade, user_year, is_anonymous,
                    like_count, dislike_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cm_id, cid, group_id, cm_teachers, title, content,
                semester, post_time, cm_score[0], cm_score[1],
                cm_score[2], cm_score[3], user_year, is_anon,
                likes, dislikes
            ))

            course_comments_export.append({
                "id": cm_id,
                "title": title,
                "content": content,
                "semester": semester,
                "score": cm_score,
                "teacher": cm_teachers,
                "user_year": user_year,
                "is_anonymous": bool(is_anon),
                "likes": likes,
                "dislikes": dislikes
            })

        export_data.append({
            "id": cid,
            "name": name,
            "code": code,
            "institute": institute,
            "credit": credit,
            "comment_num": comment_num,
            "score": score,
            "teachers": sorted(list(teachers_set)),
            "semesters": semesters,
            "latest_semester": latest_semester,
            "comments": course_comments_export
        })

    conn.commit()
    conn.close()
    print(f"[+] SQLite database written successfully: {db_path}")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "updated_at": now_iso,
            "total_courses": len(export_data),
            "courses_with_comments": len(courses_with_comments),
            "total_comments": total_comments,
            "courses": export_data
        }, f, ensure_ascii=False, indent=2)
    print(f"[+] Unified JSON export written: {json_path}")
    print("[*] Sync completed successfully!")
    return True

if __name__ == "__main__":
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "data"
    sync_data(out_dir)
