#!/usr/bin/env python3
"""
ShanghaiTech Coursebench Query & Recommendation Engine
Provides CLI tools for:
1. Search course by name, code, teacher, or keyword
2. Detail course evaluation (ratings, workload, grading, teacher quality, real reviews)
3. Intelligent multi-criteria course recommendation (major, credit, interdisciplinary, semester, workload, grade)
"""

import sys
import os
import argparse
import sqlite3
import json
import re
from datetime import datetime

# Ensure UTF-8 output across platforms, especially on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "coursebench.db")

# Major to institute / prefix mapping
MAJOR_INSTITUTE_MAP = {
    "计算机": ("信息科学与技术学院", ["CS", "SI"]),
    "计算机科学与技术": ("信息科学与技术学院", ["CS", "SI"]),
    "cs": ("信息科学与技术学院", ["CS", "SI"]),
    "ai": ("信息科学与技术学院", ["CS", "SI"]),
    "ai班": ("信息科学与技术学院", ["CS", "SI"]),
    "人工智能": ("信息科学与技术学院", ["CS", "SI"]),
    "人工智能荣誉班": ("信息科学与技术学院", ["CS", "SI"]),
    "软件": ("信息科学与技术学院", ["CS", "SI"]),
    "电子": ("信息科学与技术学院", ["EE", "SI"]),
    "ee": ("信息科学与技术学院", ["EE", "SI"]),
    "电子信息": ("信息科学与技术学院", ["EE", "SI"]),
    "电子信息工程": ("信息科学与技术学院", ["EE", "SI"]),
    "信息": ("信息科学与技术学院", ["CS", "SI", "EE"]),
    "物理": ("物质科学与技术学院", ["PHYS", "MS"]),
    "物理学": ("物质科学与技术学院", ["PHYS", "MS"]),
    "化学": ("物质科学与技术学院", ["CHEM"]),
    "材料": ("物质科学与技术学院", ["MSE"]),
    "材料科学与工程": ("物质科学与技术学院", ["MSE"]),
    "生物": ("生命科学与技术学院", ["BIO", "BT"]),
    "生物科学": ("生命科学与技术学院", ["BIO"]),
    "生科": ("生命科学与技术学院", ["BIO"]),
    "生物技术": ("生命科学与技术学院", ["BT", "BIO"]),
    "生技": ("生命科学与技术学院", ["BT", "BIO"]),
    "生医工": ("生物医学工程学院", ["BME"]),
    "bme": ("生物医学工程学院", ["BME"]),
    "生物医学工程": ("生物医学工程学院", ["BME"]),
    "数学": ("数学科学研究所", ["MATH", "GEMA"]),
    "数学与应用数学": ("数学科学研究所", ["MATH", "GEMA"]),
    "信计": ("数学科学研究所", ["MATH", "GEMA", "SI"]),
    "信息与计算科学": ("数学科学研究所", ["MATH", "GEMA", "SI"]),
    "工业设计": ("创意与艺术学院", ["SMRT", "ARTS", "ENT", "MECH"]),
    "工设": ("创意与艺术学院", ["SMRT", "ARTS", "ENT", "MECH"]),
    "创艺": ("创意与艺术学院", ["SMRT", "ARTS", "ENT", "MECH"]),
    "创管": ("创业与管理学院", ["ECON", "FINA", "MGMT", "ENT"]),
    "管理": ("创业与管理学院", ["ECON", "FINA", "MGMT", "ENT"]),
    "人文": ("人文科学研究院", ["GEHA"])
}

# Major relevance keywords/patterns
MAJOR_RELEVANCE_PATTERNS = {
    "计算机": [
        ("ARTS1422", 1.8, "数据可视化，计算与设计交叉"),
        ("GEHA1134", 1.7, "逻辑导论，离散数学与计算机理论基础"),
        ("ECON1103", 1.8, "经济学导论：信息技术产业，IT与经济交叉"),
        ("MATH1222", 1.5, "微分方程与应用数学"),
        ("MATH1233", 1.5, "拓扑学导论，理论计算几何基础"),
        ("BIO1044", 1.4, "RNA生物学，生物信息学计算交叉"),
        ("BME1062", 1.5, "生命组学，大数据与生物计算"),
        ("MSE1701", 1.5, "计算材料学，科学计算与模拟"),
        ("FINA", 1.3, "金融计量与量化方向"),
        ("GEHA1152", 1.2, "唐宋文学精华，极高口碑人文选修"),
        ("GEHA1193", 1.2, "非虚构写作，提升表达与论文撰写"),
    ],
    "物理": [
        ("SI114H", 1.8, "计算科学与工程，信息学院高质量交叉课"),
        ("CS100", 1.7, "计算机编程，夯实科学计算编码基础"),
        ("MATH1213", 1.6, "数学物理方法，理论物理数学基石"),
        ("MSE1701", 1.5, "计算材料学，物化材交叉前沿"),
        ("ECON1103", 1.4, "经济学导论：信息技术产业"),
        ("GEHA1193", 1.3, "非虚构写作导论，GPA保分好课"),
    ],
    "生医工": [
        ("CS100", 1.8, "计算机编程，医学图像算法与工程核心技能"),
        ("EE111", 1.7, "电路基础，医疗仪器与传感器硬件基石"),
        ("ARTS1422", 1.6, "数据可视化，生物医疗数据展示与UI"),
        ("BIO1003", 1.5, "生物化学，医工结合生命基础"),
        ("GEHA1193", 1.3, "非虚构写作导论，高口碑保GPA"),
    ],
    "工业设计": [
        ("CS100", 1.8, "计算机编程，智能硬件与交互设计编程基础"),
        ("CS160", 1.8, "人机交互，体验设计与界面前沿"),
        ("ENTR1006", 1.6, "商业决策与技术创新，设计与创业商业落地"),
        ("SI261", 1.5, "物联网技术与应用，智能硬件联动"),
        ("GEHA1152", 1.3, "唐宋文学精华，东方美学灵感"),
    ],
    "数学": [
        ("CS101", 1.8, "算法与数据结构，计算数学与离散算法核心"),
        ("CS182", 1.8, "机器学习引论，统计学习与优化交叉"),
        ("FINA", 1.6, "金融与量化分析，数学人才高薪走向"),
        ("PHYS1302", 1.5, "理论力学，经典动力系统物理载体"),
    ]
}

def get_db():
    if not os.path.exists(DB_PATH):
        print(f"[!] Database not found at {DB_PATH}. Please run sync_data.py first.", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def format_semester(sem_code):
    s = str(sem_code)
    if len(s) == 6:
        year = s[:4]
        term = s[4:]
        term_map = {"01": "秋季", "02": "春季", "03": "夏季"}
        return f"{year}{term_map.get(term, term)}"
    return s

def is_extreme_emotional_comment(title, content, like_count=0, dislike_count=0):
    """
    Identifies unconstructive or extreme emotional venting comments.
    Filters out:
    1. Empty or trivial comments (< 6 characters).
    2. Pure emotional venting / insults lacking academic or coursework substance.
    3. Extremely short emotional outbursts.
    4. Severely downvoted comments.
    """
    text = ((title or '') + ' ' + (content or '')).strip()
    clean_text = re.sub(r'\s+', '', text)
    if len(clean_text) < 6:
        return True, "内容过短或无实质文字"
    
    # Severe downvote ratio
    if dislike_count >= 5 and dislike_count > like_count * 2:
        return True, "负反馈/点踩较多，参考价值偏低"
    
    extreme_keywords = [
        '依托答辩', '傻逼', 'sb', '司马', '死妈', '恶心死', '狗都不选',
        '纯纯的垃圾', '快跑快跑', '人渣', '去死', '下头', '烂课'
    ]
    has_extreme_kw = any(kw in text.lower() for kw in extreme_keywords)
    
    substantive_keywords = [
        '考试', '作业', '期末', '期中', '平时', '讲课', '内容', '实验',
        '给分', '考核', '难度', '知识', 'project', 'lab', 'ppt',
        '代码', '学分', '老师', '教学', '收获', '难度', '课件', '教材', '编程'
    ]
    has_substance = any(sk in text.lower() for sk in substantive_keywords)
    
    if has_extreme_kw and not has_substance:
        return True, "包含极端情绪化词汇且缺乏课程实质分析"
    
    if len(clean_text) < 25 and has_extreme_kw:
        return True, "过短的极端宣泄性评论"
        
    return False, None

def search_courses(query, limit=10):
    conn = get_db()
    cur = conn.cursor()
    like_query = f"%{query.strip()}%"
    cur.execute("""
        SELECT id, name, code, institute, credit, comment_num,
               score_quality, score_workload, score_difficulty, score_grade,
               teachers, semesters
        FROM courses
        WHERE name LIKE ? OR code LIKE ? OR teachers LIKE ? OR institute LIKE ?
        ORDER BY comment_num DESC, score_quality DESC
        LIMIT ?
    """, (like_query, like_query, like_query, like_query, limit))
    return [dict(row) for row in cur.fetchall()]

def get_course_detail(course_identifier):
    conn = get_db()
    cur = conn.cursor()
    
    # Try by ID, Code, or Name
    if str(course_identifier).isdigit():
        cur.execute("SELECT * FROM courses WHERE id = ?", (int(course_identifier),))
    else:
        cur.execute("SELECT * FROM courses WHERE code = ? OR name = ?", (course_identifier, course_identifier))
    
    course = cur.fetchone()
    if not course:
        # Fuzzy match
        cur.execute("SELECT * FROM courses WHERE name LIKE ? OR code LIKE ? LIMIT 1", 
                    (f"%{course_identifier}%", f"%{course_identifier}%"))
        course = cur.fetchone()
    
    if not course:
        return None
    
    course_dict = dict(course)
    cid = course_dict["id"]
    
    cur.execute("""
        SELECT id, title, content, semester, post_time,
               score_quality, score_workload, score_difficulty, score_grade,
               teacher_name, user_year, is_anonymous, like_count, dislike_count
        FROM comments
        WHERE course_id = ?
        ORDER BY semester DESC, post_time DESC
    """, (cid,))
    
    comments = [dict(row) for row in cur.fetchall()]
    for cm in comments:
        is_ext, reason = is_extreme_emotional_comment(
            cm.get("title"), cm.get("content"),
            cm.get("like_count", 0), cm.get("dislike_count", 0)
        )
        cm["is_extreme"] = is_ext
        cm["filter_reason"] = reason
    course_dict["comments"] = comments
    return course_dict

def recommend_courses(
    major="计算机",
    credit=3.0,
    category="跨学科",
    semester="fall",
    workload_pref="any",
    grade_pref="generous",
    top_k=3
):
    conn = get_db()
    cur = conn.cursor()
    
    student_institute, prefixes = MAJOR_INSTITUTE_MAP.get(major.lower(), (None, []))
    
    query = """
        SELECT id, name, code, institute, credit, comment_num,
               score_quality, score_workload, score_difficulty, score_grade,
               teachers, semesters, latest_semester
        FROM courses
        WHERE comment_num > 0
    """
    params = []
    
    # Credit filter (+- 0.5)
    if credit:
        query += " AND credit >= ? AND credit <= ?"
        params.extend([credit - 0.5, credit + 0.5])
    
    # Category filter
    if category in ["跨学科", "interdisciplinary"]:
        if student_institute:
            query += " AND institute != ?"
            params.append(student_institute)
        # Exclude unknown
        query += " AND institute != '未知单位'"
        # Exclude prefix
        for pref in prefixes:
            query += f" AND code NOT LIKE '{pref}%'"
    elif category in ["通识", "general"]:
        query += " AND (institute LIKE '%书院%' OR institute LIKE '%人文%' OR code LIKE 'GE%')"
    elif category in ["专业选修", "major"]:
        if student_institute:
            query += " AND institute = ?"
            params.append(student_institute)
    
    cur.execute(query, params)
    candidates = [dict(r) for r in cur.fetchall()]
    
    # Target semester analysis:
    # 01 = Fall, 02 = Spring, 03 = Summer
    target_term = "01" if semester.lower() in ["fall", "autumn", "秋", "秋季", "202401", "202501", "202601"] else \
                  "02" if semester.lower() in ["spring", "春", "春季", "202402", "202502", "202602"] else \
                  "03" if semester.lower() in ["summer", "夏", "夏季"] else None
    
    scored_candidates = []
    
    relevance_rules = MAJOR_RELEVANCE_PATTERNS.get(major.lower(), [])
    
    for c in candidates:
        semesters_list = c["semesters"].split(",") if c["semesters"] else []
        
        # 1. Semester matching factor
        sem_offered = True
        sem_bonus = 0.0
        if target_term:
            has_target = any(s.endswith(target_term) for s in semesters_list)
            if has_target:
                sem_bonus = 1.0
            else:
                # If course has comments across multiple years and NEVER offered in this term, penalize
                if len(semesters_list) >= 2:
                    sem_offered = False
                    sem_bonus = -2.0
                else:
                    sem_bonus = -0.5
        
        # 2. Score dimensions
        q = c["score_quality"] or 0
        w = c["score_workload"] or 0
        g = c["score_grade"] or 0
        d = c["score_difficulty"] or 0
        
        # Workload preference adjustments (5 = lightest, 1 = heaviest)
        w_score = w
        if workload_pref == "light" and w < 4.0:
            w_score *= 0.7
        elif workload_pref == "heavy":
            w_score = 5.0 - abs(w - 2.5)
        
        # Grade preference
        g_score = g
        if grade_pref == "generous" and g < 4.2:
            g_score *= 0.7
            
        # 3. Review reliability bonus
        rev_count = c["comment_num"]
        credibility = min(rev_count, 8) / 8.0  # scale 0 to 1
        
        # 4. Major relevance bonus
        rel_bonus = 0.0
        rel_reason = ""
        for rule_code, boost, reason in relevance_rules:
            if c["code"].startswith(rule_code) or rule_code in c["code"] or rule_code in c["name"]:
                rel_bonus = boost
                rel_reason = reason
                break
        
        # Composite score calculation
        # Weights: Quality 30%, Grading 30%, Workload 20%, Credibility 10%, Major relevance & Semester 10%
        composite = (
            q * 0.30 +
            g_score * 0.30 +
            w_score * 0.20 +
            credibility * 0.5 +
            rel_bonus * 0.6 +
            sem_bonus * 0.4
        )
        
        c["composite_score"] = round(composite, 2)
        c["rel_reason"] = rel_reason
        c["sem_offered_match"] = sem_offered
        c["sem_list_formatted"] = [format_semester(s) for s in semesters_list]
        scored_candidates.append(c)
    
    # Sort descending
    scored_candidates.sort(key=lambda x: x["composite_score"], reverse=True)
    top_results = scored_candidates[:top_k]
    
    # Enrich top results with top constructive comments (prioritizing recent semesters)
    for res in top_results:
        cid = res["id"]
        cur.execute("""
            SELECT title, content, semester, score_quality, score_workload, score_grade, teacher_name, like_count, dislike_count
            FROM comments
            WHERE course_id = ?
            ORDER BY semester DESC, post_time DESC
        """, (cid,))
        raw_comments = [dict(row) for row in cur.fetchall()]
        valid_comments = []
        for rc in raw_comments:
            is_ext, _ = is_extreme_emotional_comment(
                rc.get("title"), rc.get("content"),
                rc.get("like_count", 0), rc.get("dislike_count", 0)
            )
            if not is_ext:
                valid_comments.append(rc)
                
        # Prioritize recent constructive comments, fallback to raw if needed
        chosen_comments = valid_comments[:3] if valid_comments else raw_comments[:3]
        res["sample_comments"] = chosen_comments
        res["filtered_comments_count"] = len(raw_comments) - len(valid_comments)
        for sc in res["sample_comments"]:
            sc["semester_formatted"] = format_semester(sc["semester"])
    
    return top_results

def print_detail_markdown(course):
    print(f"# 课程评价报告: {course['name']} ({course['code']})\n")
    print(f"- **开课学院**: {course['institute']}")
    print(f"- **学分**: {course['credit']} 学分")
    print(f"- **主讲教师**: {course['teachers'] or '见各学期教学班'}")
    print(f"- **CourseBench 链接**: https://coursebench.org/course/{course['id']}")
    print(f"- **历史开课学期**: {', '.join(format_semester(s) for s in (course['semesters'] or '').split(',')) if course['semesters'] else '暂无数据'}")
    print()
    
    # Ratings
    q = course['score_quality']
    w = course['score_workload']
    d = course['score_difficulty']
    g = course['score_grade']
    print("## 核心评分 (满分 5.0)")
    print(f"| 评价维度 | 得分 | 评价标准与解读 |")
    print(f"| :--- | :---: | :--- |")
    print(f"| **综合质量** | **{q:.2f}** | {'⭐️⭐️⭐️⭐️⭐️ 极佳' if q >= 4.5 else '⭐️⭐️⭐️⭐️ 良好' if q >= 3.8 else '一般'} |")
    print(f"| **作业与工作量** | **{w:.2f}** | {'极其轻松/轻量' if w >= 4.5 else '适中偏轻' if w >= 3.8 else '工作量较大' if w >= 2.5 else '高负荷硬课'} (注: 分数越高越轻松) |")
    print(f"| **考核难度** | **{d:.2f}** | {'考核友好/合理' if d >= 4.5 else '难度适中' if d >= 3.8 else '考核硬核有挑战'} (注: 分数越高越温和) |")
    print(f"| **给分情况** | **{g:.2f}** | {'给分极好/优秀率高' if g >= 4.5 else '给分正常/良好' if g >= 3.8 else '给分严格/偏杀手'} |")
    print()

    comments = course.get("comments", [])
    valid_comments = [c for c in comments if not c.get("is_extreme")]
    filtered_num = len(comments) - len(valid_comments)
    print(f"## 同学真实评价 (共 {len(comments)} 条评论，年份近者优先展示)")
    if filtered_num > 0:
        print(f"> 💡 **客观评价过滤**：已智能剔除 {filtered_num} 条极端情绪化/无实质分析的评论，以下优先展示近期客观反馈。\n")
        
    display_comments = valid_comments if valid_comments else comments
    if not display_comments:
        print("该课程暂无同学提交评价。")
        return
    
    for idx, cm in enumerate(display_comments, 1):
        sem_str = format_semester(cm.get("semester"))
        t_name = cm.get("teacher_name") or course['teachers'] or "任课教师"
        title = cm.get("title") or "评价"
        print(f"### 评价 {idx}: {title}")
        print(f"- **学期**: {sem_str} | **任课教师**: {t_name}")
        scores = f"质量:{cm['score_quality']:.1f} | 作业:{cm['score_workload']:.1f} | 考核:{cm['score_difficulty']:.1f} | 给分:{cm['score_grade']:.1f}"
        print(f"- **学生打分**: {scores}")
        print()
        print(f"> {cm['content'].strip()}")
        print()

def print_recommend_markdown(recommendations, major, credit, semester, category):
    print(f"# 智能选课推荐方案")
    print(f"**目标画像**: {major}专业同学 | **需求学分**: {credit}学分 | **类别**: {category} | **目标学期**: {semester}\n")
    print(f"根据 CourseBench 历史评价数据（**年份近的评价优先，已剔除极端情绪化评论**）、开课学期规律、给分口碑、工作量负担以及与【{major}】专业的交叉适配度，精选推荐以下课程：\n")
    
    for idx, c in enumerate(recommendations, 1):
        print(f"---")
        print(f"## 推荐 {idx}: 【{c['name']}】({c['code']}) - {c['institute']}")
        print(f"- **学分**: {c['credit']} 学分")
        print(f"- **任课教师**: {c['teachers'] or '多位教师'}")
        print(f"- **评分画像**: 综合质量 `{c['score_quality']:.1f}` / 作业友好度 `{c['score_workload']:.1f}` / 考核难度 `{c['score_difficulty']:.1f}` / 给分慷慨度 `{c['score_grade']:.1f}` (累计 {c['comment_num']} 条评价)")
        print(f"- **历史开课规律**: {', '.join(c['sem_list_formatted'])}")
        if c.get("rel_reason"):
            print(f"- **专业契合度**: 💡 {c['rel_reason']}")
        print()
        print(f"### 推荐理由分析")
        # Generate multi-angle reason
        reasons = []
        if c['score_grade'] >= 4.5:
            reasons.append("给分极好，历届同学反馈均分高或优秀率充裕，不伤 GPA。")
        if c['score_workload'] >= 4.2:
            reasons.append("工作量友好，平时课业负担轻，适合搭配专业硬课协同选修。")
        elif c['score_workload'] <= 2.5:
            reasons.append("课程含金量高但有一定大作业/Project工作量，注重动手实践。")
        if c['score_quality'] >= 4.8:
            reasons.append("教师教学质量与口碑极佳，课堂反馈热烈。")
        print("1. " + "\n2. ".join(reasons))
        print()
        print(f"### 往届同学真实反馈摘要")
        for sc in c.get("sample_comments", []):
            content_snippet = sc['content'].strip()
            if len(content_snippet) > 200:
                content_snippet = content_snippet[:200] + "..."
            print(f"- **[{sc['semester_formatted']} {sc['teacher_name'] or ''}] {sc['title']}**")
            print(f"  > \"{content_snippet}\"")
        print(f"\n- **CourseBench 页面**: https://coursebench.org/course/{c['id']}\n")

def main():
    parser = argparse.ArgumentParser(description="Coursebench Query & Recommendation")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Search
    search_parser = subparsers.add_parser("search", help="Search courses")
    search_parser.add_argument("query", help="Course name, code, teacher, or institute")
    search_parser.add_argument("--limit", type=int, default=10, help="Max results")
    search_parser.add_argument("--json", action="store_true", help="Output JSON")
    
    # Detail
    detail_parser = subparsers.add_parser("detail", help="Get course details and reviews")
    detail_parser.add_argument("course", help="Course name, code, or ID")
    detail_parser.add_argument("--json", action="store_true", help="Output JSON")
    
    # Recommend
    rec_parser = subparsers.add_parser("recommend", help="Recommend courses")
    rec_parser.add_argument("--major", default="计算机", help="Student major")
    rec_parser.add_argument("--credit", type=float, default=3.0, help="Required credits")
    rec_parser.add_argument("--category", default="跨学科", choices=["跨学科", "通识", "专业选修", "all"], help="Category")
    rec_parser.add_argument("--semester", default="fall", help="Target semester (fall/spring/any)")
    rec_parser.add_argument("--workload", default="any", choices=["any", "light", "heavy"], help="Workload preference")
    rec_parser.add_argument("--grade", default="generous", choices=["any", "generous", "fair"], help="Grade preference")
    rec_parser.add_argument("--top", type=int, default=3, help="Number of recommendations")
    rec_parser.add_argument("--json", action="store_true", help="Output JSON")

    args = parser.parse_args()
    
    if args.command == "search":
        results = search_courses(args.query, args.limit)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            print(f"Found {len(results)} matches for '{args.query}':\n")
            for r in results:
                print(f"- [{r['code']}] {r['name']} ({r['institute']}, {r['credit']}分) | 评分: 质量{r['score_quality']:.1f}/工作量{r['score_workload']:.1f}/给分{r['score_grade']:.1f} ({r['comment_num']}条评价) | 教师: {r['teachers']}")
    
    elif args.command == "detail":
        course = get_course_detail(args.course)
        if not course:
            print(f"[!] Course '{args.course}' not found.", file=sys.stderr)
            sys.exit(1)
        if args.json:
            print(json.dumps(course, ensure_ascii=False, indent=2))
        else:
            print_detail_markdown(course)
            
    elif args.command == "recommend":
        recs = recommend_courses(
            major=args.major,
            credit=args.credit,
            category=args.category,
            semester=args.semester,
            workload_pref=args.workload,
            grade_pref=args.grade,
            top_k=args.top
        )
        if args.json:
            print(json.dumps(recs, ensure_ascii=False, indent=2))
        else:
            print_recommend_markdown(recs, args.major, args.credit, args.semester, args.category)
            
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
