#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ShanghaiTech Senior CLI (上科大老学长统一助手)
Unifies CourseBench course reviews, official curriculum planning, EAMS degree audit,
and multi-source course materials (iTechX, XiongWenye, zsc2003).
"""

import os
import sys
import json
import sqlite3
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CB_DB_PATH = DATA_DIR / "coursebench.db"
MATERIALS_INDEX_PATH = DATA_DIR / "materials_index.json"

sys.path.insert(0, str(BASE_DIR / "scripts"))
import query_course
import query_materials
import recommend_plan
import analyze_plan


def get_course_code_and_info(query):
    """Resolve query to canonical course code and data."""
    if not MATERIALS_INDEX_PATH.exists():
        return None, None
    with open(MATERIALS_INDEX_PATH, "r", encoding="utf-8") as f:
        mat_index = json.load(f)
        
    resolved = query_materials.resolve_course_code(mat_index, query)
    if isinstance(resolved, list) and resolved:
        resolved = resolved[0]
        
    if resolved and resolved in mat_index["courses"]:
        return resolved, mat_index["courses"][resolved]
        
    # Fallback to coursebench db
    conn = sqlite3.connect(CB_DB_PATH)
    c = conn.cursor()
    c.execute("SELECT code, name, institute, credit, score_quality, score_workload, score_difficulty, score_grade FROM courses WHERE code = ? COLLATE NOCASE", (query,))
    row = c.fetchone()
    if not row:
        c.execute("SELECT code, name, institute, credit, score_quality, score_workload, score_difficulty, score_grade FROM courses WHERE name = ? COLLATE NOCASE", (query,))
        row = c.fetchone()
    if not row:
        c.execute("SELECT code, name, institute, credit, score_quality, score_workload, score_difficulty, score_grade FROM courses WHERE name LIKE ? LIMIT 1", (f"%{query}%",))
        row = c.fetchone()
    conn.close()
    
    if row:
        code, name, inst, cr, sq, sw, sd, sg = row
        return code, {
            "code": code,
            "name_zh": name,
            "institute": inst,
            "credit": cr,
            "cb_scores": {"quality": sq, "workload": sw, "difficulty": sd, "grade": sg},
            "resources": {}
        }
        
    return None, None


def cmd_ask(query):
    """
    Comprehensive briefing combining:
    1. CourseBench reputation & teacher review summary (选课维度)
    2. Test-taking & exam materials (备考资料维度)
    3. Senior's Takeaway (学长心法)
    """
    code, mat_info = get_course_code_and_info(query)
    if not code:
        print(f"❌ 老学长在数据库中没有找到与 '{query}' 相关的课程信息。", file=sys.stderr)
        print("💡 建议使用 `python3 scripts/senior.py search <关键词>` 进行模糊搜索。", file=sys.stderr)
        return

    name_zh = mat_info.get("name_zh", "")
    inst = mat_info.get("institute", "上海科技大学")
    cr = mat_info.get("credit", 0.0)
    scores = mat_info.get("cb_scores", {})
    res = mat_info.get("resources", {})

    print(f"# 🧑‍🎓 老学长全景指南：【{code}】{name_zh}")
    print(f"**开课单位**：{inst} | **课程学分**：{cr} 学分\n")

    # 1. CourseBench 口碑与老学长评述
    print("## 🌟 维度一：课程口碑与选课评价 (CourseBench)")
    if scores and scores.get("quality"):
        sq = scores.get("quality", 0)
        sw = scores.get("workload", 0)
        sd = scores.get("difficulty", 0)
        sg = scores.get("grade", 0)
        print(f"> 📊 **学生真实评分**：教学质量 `{sq:.1f}/5.0` | 课业负担 `{sw:.1f}/5.0` | 考核难度 `{sd:.1f}/5.0` | 给分优劣 `{sg:.1f}/5.0`\n")
    else:
        print("> 📊 *该课程在 CourseBench 暂无足够数量评分。*\n")

    # Fetch recent comments from CourseBench DB
    try:
        conn = sqlite3.connect(CB_DB_PATH)
        c = conn.cursor()
        c.execute("""
            SELECT comments.semester, comments.teacher, comments.text, comments.score_quality, comments.score_grade
            FROM comments 
            JOIN courses ON comments.course_id = courses.id 
            WHERE courses.code = ? COLLATE NOCASE
            ORDER BY comments.semester DESC
            LIMIT 3
        """, (code,))
        comments = c.fetchall()
        conn.close()

        if comments:
            print("### 💬 往届学长真实就读评语精选 (近学期优先)：")
            for sem, tch, txt, cq, cg in comments:
                tch_str = f" | 教师：{tch}" if tch else ""
                clean_txt = txt.strip().replace("\n", " ")
                if len(clean_txt) > 140:
                    clean_txt = clean_txt[:137] + "..."
                print(f"- **[{sem}{tch_str}]**（质量 {cq:.1f}，给分 {cg:.1f}）：")
                print(f"  > “{clean_txt}”")
            print("")
    except Exception:
        pass

    # 2. 备考通关资料库
    print("## 📚 维度二：备考通关与资料直达包 (八大资料库)")
    has_res = any(v.get("available") for v in res.values())
    if not has_res:
        print("*本课程暂未被三大核心公开资料库收录，建议咨询任课教师或课程 TA。*\n")
    else:
        # Markdown report from query_materials
        report_md = query_materials.format_markdown_report(mat_info)
        # We can extract the material sections
        subsections = report_md.split("### 📝 1. 历年真题与考试资料")[1] if "### 📝 1. 历年真题与考试资料" in report_md else ""
        if subsections:
            print("### 📝 1. 历年真题与考试资料" + subsections)
        else:
            print(report_md)

    # 3. 老学长避坑锦囊
    print("## 💡 维度三：老学长避坑锦囊 (Senior's Takeaway)")
    # Generate tailored advice based on scores
    tips = []
    sw = scores.get("workload", 3.0)
    sd = scores.get("difficulty", 3.0)
    sg = scores.get("grade", 3.0)

    if sw >= 3.8:
        tips.append("⚠️ **工作量极大**：该课程作业/Project 耗时极长，务必提前规划 ddl，切忌堆积到最后一夜。")
    elif sw <= 2.2:
        tips.append("✨ **课业负担温和**：平时压力较小，适合搭配一门硬核专业课一起修读。")

    if sd >= 3.8:
        tips.append("🔥 **考试硬核度高**：考卷区分度大或覆盖面广，建议考前务必刷完上述历年真题回忆版！")
    
    if sg >= 4.0:
        tips.append("🎁 **给分较慷慨**：优秀率相对较高或只要平时认真即可保 GPA，属于高性价必修/选修。")
    elif sg <= 3.0:
        tips.append("🚨 **给分严格/卡绩点**：给分偏严格或压分，期中期末绝不能掉以轻心，扣分点多在细节。")

    # Specific advice for big courses
    if code in ["CS100", "CS101", "CS110"]:
        tips.append("💻 **代码与平时分**：平时编程作业占比极大且自带测试用例，务必保证全 AC，平时分拉满是保 A 的基本盘。")
    elif "PHYS" in code or "大物" in name_zh:
        tips.append("📐 **大物通关秘诀**：多做往年期中和期末卷（特别是 XiongWenye 库里的 2024/2025 最新卷），题型规律性很强。")
    elif "MATH" in code or "GEMA" in code or any(k in name_zh for k in ["高等数学", "数学分析", "线性代数"]):
        tips.append("✍️ **数理基础必胜法**：吃透习题课 (Recitation) 讲义中的例题和自编答案，考前多练大题书写规范。")

    if "CHEM" in code or "化" in name_zh:
        tips.append("🥽 **普化与实验高分心得**：实验预习思考题一定要在进实验室前写好；参考 RulerFuhai 的高分实验报告范本规范书写原始数据记录与误差分析，格式严谨平时分保 A！")
    elif code == "CS130" or "操作系统" in name_zh:
        tips.append("⚙️ **操作系统通关建议**：Pintos Project 是挂科重灾区，参考 wutianyuan1 与 profetia 开源框架和报告，提前动手梳理 Thread / Userprog / VM 逻辑！")
    elif "ARTS" in code or "设计" in name_zh:
        tips.append("🎨 **创艺SCA课程心得**：期末大作业（游戏/交互原型/三维模型/用户体验方案）占比极高，参考 skkk256 与 profetia 优秀作品与排版！")
    elif any(k in code for k in ["GEHA", "GESS", "CLGE"]) or any(k in name_zh for k in ["文明", "纲要", "马原", "毛概", "经导", "托克维尔"]):
        tips.append("📖 **通识人文社科避坑指南**：马原/毛概/近纲/通识课考前务必背诵题库和历年回忆卷，大论文按学术格式规范引用！")
    if not tips:
        tips.append("按部就班紧跟任课老师教学节奏，课后及时整理 PPT 讲义与习题即可稳过！")

    for t in tips:
        print(f"- {t}")
    print("")


def main():
    parser = argparse.ArgumentParser(
        description="ShanghaiTech Senior Assistant (上海科技大学老学长统一助手)",
        formatter_class=argparse.RawTextHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # ask (Dual Mode: CourseBench + Materials)
    ask_p = subparsers.add_parser("ask", help="老学长综合全景把脉 (口碑评价 + 备考真题资料 + 避坑锦囊)")
    ask_p.add_argument("course", help="课程代码 (如 CS100) 或中文名/别名 (如 计算机编程, 大物, 数分, 线代)")

    # materials (Test-Taking Materials)
    mat_p = subparsers.add_parser("materials", help="仅查询备考复习资料 (真题、作业解答、课件、代码)")
    mat_p.add_argument("course", help="课程代码或名称")
    mat_p.add_argument("--json", action="store_true", help="输出机器可读 JSON")

    # review (CourseBench Review)
    rev_p = subparsers.add_parser("review", help="仅查询 CourseBench 口碑评分与学生文字评价")
    rev_p.add_argument("course", help="课程代码或名称")

    # roadmap (Curriculum Roadmap)
    plan_p = subparsers.add_parser("roadmap", help="查看专业学期官方培养方案推荐修课路线")
    plan_p.add_argument("--major", required=True, help="专业名称 (如 计算机, 电子, 物理, 工业设计)")
    plan_p.add_argument("--grade", default="2026", help="年级 (默认 2026)")
    plan_p.add_argument("--semester", type=int, help="推荐学期 (1-8)")

    # audit (EAMS Degree Plan Audit)
    audit_p = subparsers.add_parser("audit", help="EAMS 培养方案计划完成情况毕业智能诊断")
    audit_p.add_argument("--file", default=str(DATA_DIR / "my_plan_completion.html"), help="EAMS 导出的 HTML 计划文件")
    audit_p.add_argument("--major", help="强制指定对比专业")
    audit_p.add_argument("--grade", help="强制指定对比年级")

    # search
    search_p = subparsers.add_parser("search", help="模糊全局搜索课程 (同时检索 CourseBench 与资料库)")
    search_p.add_argument("keyword", help="搜索关键词")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "ask":
        cmd_ask(args.course)
    elif args.command == "materials":
        # Delegate to query_materials
        sys.argv = ["query_materials.py", "get", args.course]
        if args.json:
            sys.argv.append("--json")
        query_materials.main()
    elif args.command == "review":
        sys.argv = ["query_course.py", "detail", args.course]
        query_course.main()
    elif args.command == "roadmap":
        sys.argv = ["recommend_plan.py", "roadmap", "--major", args.major, "--grade", args.grade]
        if args.semester:
            sys.argv.extend(["--semester", str(args.semester)])
        recommend_plan.main()
    elif args.command == "audit":
        sys.argv = ["analyze_plan.py", "--file", args.file]
        if args.major:
            sys.argv.extend(["--major", args.major])
        if args.grade:
            sys.argv.extend(["--grade", args.grade])
        analyze_plan.main()
    elif args.command == "search":
        sys.argv = ["query_materials.py", "search", args.keyword]
        query_materials.main()


if __name__ == "__main__":
    main()
