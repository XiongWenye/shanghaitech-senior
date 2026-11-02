#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Query Course Materials for ShanghaiTech Courses
Quickly retrieves exam papers, solutions, homework, slides, and project code across:
- iTechX (file-base)
- XiongWenye shanghaitech-course-database
- zsc2003 courses-summary
"""

import os
import sys
import json
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_FILE = BASE_DIR / "data" / "materials_index.json"

sys.path.insert(0, str(BASE_DIR / "scripts"))
import materials_sync


def load_index(force_refresh: bool = False):
    try:
        return materials_sync.get_materials_index(force_refresh=force_refresh)
    except Exception as e:
        # Network fallback belongs to sync_catalog. Identity conflicts must be visible;
        # falling back here would hide corrupt mappings in an old baseline.
        print(f"Error loading index: {e}", file=sys.stderr)
        sys.exit(1)


def resolve_course_code(index, query):
    query = query.strip()
    q_lower = query.lower()
    if not q_lower:
        return None
    
    # 1. Exact match code
    for code in index["courses"]:
        if code.lower() == q_lower:
            return code
            
    # 2. Exact course name takes precedence over stale or ambiguous aliases.
    exact_names = [code for code, info in index["courses"].items()
                   if materials_sync.normalized_name(info.get("name_zh"))
                   == materials_sync.normalized_name(query)]
    if exact_names:
        return exact_names[0] if len(exact_names) == 1 else exact_names

    # 3. Inverted index match
    inverted = index.get("inverted_index", {})
    if q_lower in inverted and inverted[q_lower]:
        matches = [code for code in inverted[q_lower] if code in index["courses"]]
        if matches:
            return matches[0] if len(matches) == 1 else matches
        
    # 3. Substring match in inverted index or names
    candidates = []
    for alias, codes in inverted.items():
        if alias and (q_lower in alias or alias in q_lower):
            for c in codes:
                if c not in candidates:
                    candidates.append(c)
                    
    # 4. Check Chinese names
    for code, info in index["courses"].items():
        name_zh = info.get("name_zh", "").lower()
        if name_zh and (q_lower in name_zh or name_zh in q_lower):
            if code not in candidates:
                candidates.append(code)
                
    if materials_sync.is_lab_course(query):
        candidates = [code for code in candidates
                      if materials_sync.is_lab_course(index["courses"][code].get("name_zh"), code)]

    if len(candidates) == 1:
        return candidates[0]
    elif len(candidates) > 1:
        return candidates
        
    return None


def format_markdown_report(course):
    code = course["code"]
    name_zh = course.get("name_zh") or "未知课程"
    name_en = course.get("name_en") or ""
    inst = course.get("institute") or "上海科技大学"
    credit = course.get("credit", 0.0)
    scores = course.get("cb_scores", {})
    res = course.get("resources", {})

    lines = []
    lines.append(f"## 📚 【{code}】{name_zh} 完整备考与修课资料包")
    if name_en:
        lines.append(f"*{name_en}* | **开课单位**：{inst} | **学分**：{credit}学分\n")
    else:
        lines.append(f"**开课单位**：{inst} | **学分**：{credit}学分\n")

    # CourseBench Score Summary
    if scores and scores.get("quality"):
        sq = scores.get("quality", 0)
        sw = scores.get("workload", 0)
        sd = scores.get("difficulty", 0)
        sg = scores.get("grade", 0)
        lines.append(f"> 🌟 **CourseBench 口碑指数**：教学质量 `{sq:.1f}/5.0` | 课业负担 `{sw:.1f}/5.0` | 考核难度 `{sd:.1f}/5.0` | 给分情况 `{sg:.1f}/5.0`")
        lines.append("")

    # Source badges
    badges = []
    if res.get("itechx", {}).get("available"):
        badges.append("🟢 **iTechX 课程库** (课件/作业/标准答案/历年卷)")
    if res.get("xiongwenye", {}).get("available"):
        badges.append("🟠 **XiongWenye 资料库** (独家期中期末真题/回忆卷/解析)")
    if res.get("zsc2003", {}).get("available"):
        badges.append("🟣 **zsc2003 学长通关仓库** (高分代码/Recitation教程/复习提纲)")
    if res.get("skkk256", {}).get("available"):
        badges.append("🔵 **skkk256 全科修课资料库** (信院/创艺/生医工/通识社科全流程通关资料)")
    if res.get("wutianyuan1", {}).get("available"):
        badges.append("🟡 **wutianyuan1 课程仓库** (操作系统Pintos/体系结构/无机化学/设计思维/RL项目)")
    if res.get("profetia", {}).get("available"):
        badges.append("🔴 **profetia 课程项目库** (并行计算/OS/数据可视化/生信开发开源项目)")
    if res.get("gkxx_cs100", {}).get("available"):
        badges.append("🔷 **GKxxUCAS CS100课件精炼库** (29讲全套高清讲义/图解与知识点速查)")
    if res.get("rulerfuhai", {}).get("available"):
        badges.append("🟤 **RulerFuhai 普化实验高分库** (CHEM1100 2024-2025秋全套实验报告范本/思考题/数据模板)")
    lines.append("### 📦 收录资料库状态")
    for b in badges:
        lines.append(f"- {b}")
    lines.append("")

    # Section 1: Past Exams & Quizzes
    lines.append("### 📝 1. 历年真题与考试资料 (Past Exams & Quizzes)")
    has_exam = False
    
    # XiongWenye exams & solutions
    xw = res.get("xiongwenye")
    if xw and xw.get("exams"):
        for ex in xw["exams"]:
            fl = ex['name'].lower()
            if any(k in fl for k in ["cheatsheet", "cheat_sheet", "cheat sheet", "速查"]):
                lines.append(f"- 📑 **考前速查 / Cheat Sheet**：[{ex['name']}]({ex['url']})")
            elif any(k in fl for k in ["quiz", "小测", "测验"]):
                lines.append(f"- 📝 **随堂测验 / Quiz**：[{ex['name']}]({ex['url']})")
            else:
                lines.append(f"- 📄 **真题卷**：[{ex['name']}]({ex['url']})")
            has_exam = True
    if xw and xw.get("solutions"):
        for sol in xw["solutions"]:
            lines.append(f"- 🔑 **考卷解析与答案**：[{sol['name']}]({sol['url']})")
            has_exam = True

    # skkk256 exams & solutions
    sk = res.get("skkk256")
    if sk and sk.get("exams"):
        for ex in sk["exams"]:
            lines.append(f"- 📄 **skkk256 试卷/CheatSheet**：[{ex['name']}]({ex['url']})")
            has_exam = True
    if sk and sk.get("solutions"):
        for sol in sk["solutions"]:
            if any(k in sol['name'].lower() for k in ["exam", "final", "mid", "期末", "期中", "试卷", "cheatsheet"]):
                lines.append(f"- 🔑 **skkk256 考卷/解析**：[{sol['name']}]({sol['url']})")
                has_exam = True

    # wutianyuan1 exams
    wt = res.get("wutianyuan1")
    if wt and wt.get("exams"):
        for ex in wt["exams"]:
            lines.append(f"- 📑 **wutianyuan1 期末/速查资料**：[{ex['name']}]({ex['url']})")
            has_exam = True

    # iTechX exams
    itx = res.get("itechx")
    if itx and itx.get("categories", {}).get("exams"):
        for ex in itx["categories"]["exams"]:
            lines.append(f"- 📑 **iTechX 考卷目录**：[{ex['semester']} - {ex['folder']}]({ex['url']})")
            has_exam = True

    if not has_exam:
        lines.append("- *暂无独立切分的试卷文件，建议直接浏览下方共享库根目录。*")
    lines.append("")

    # Section 2: Homework & Official Solutions
    lines.append("### 📚 2. 平时作业与参考解答 (Homework & Solutions)")
    has_hw = False
    if itx:
        hw_sols = itx.get("categories", {}).get("homework_solutions", [])
        hws = itx.get("categories", {}).get("homework", [])
        for sol in hw_sols:
            lines.append(f"- 💡 **作业标准解答**：[{sol['semester']} - {sol['folder']}]({sol['url']})")
            has_hw = True
        for hw in hws:
            lines.append(f"- 📝 **平时作业题目**：[{hw['semester']} - {hw['folder']}]({hw['url']})")
            has_hw = True
    if sk and sk.get("solutions"):
        for sol in sk["solutions"]:
            if not any(k in sol['name'].lower() for k in ["exam", "final", "mid", "期末", "期中"]):
                lines.append(f"- 💡 **skkk256 作业参考解答**：[{sol['name']}]({sol['url']})")
                has_hw = True
    if sk and sk.get("homework"):
        for hw in sk["homework"][:6]:
            lines.append(f"- 📝 **skkk256 平时作业**：[{hw['name']}]({hw['url']})")
            has_hw = True
    if wt and wt.get("homework"):
        for hw in wt["homework"][:6]:
            lines.append(f"- 📝 **wutianyuan1 作业题目/代码**：[{hw['name']}]({hw['url']})")
            has_hw = True
    if wt and wt.get("solutions"):
        for sol in wt["solutions"][:6]:
            lines.append(f"- 💡 **wutianyuan1 作业解答**：[{sol['name']}]({sol['url']})")
            has_hw = True
    rf = res.get("rulerfuhai")
    if rf and rf.get("pre_lab_questions"):
        for pq in rf["pre_lab_questions"][:8]:
            lines.append(f"- 🧪 **普化实验预习思考题及答案**：[{pq['name']}]({pq['url']})")
            has_hw = True
    if not has_hw:
        lines.append("- *暂无单独分类的作业答案，可查看下方学长仓库或总库。*")
    lines.append("")

    # Section 3: Slides, Notes & Recitation Tutorials
    lines.append("### 🖥️ 3. 讲义课件与复习提纲 (Lecture Slides & Tutorials)")
    has_slides = False
    gk = res.get("gkxx_cs100")
    if gk and gk.get("lectures"):
        lines.append(f"- 🌟 **GKxxUCAS CS100 精炼课件全集**：共收录 {gk.get('total_lectures', 0)} 讲中英文课件与核心概念速查")
        for lec in gk["lectures"][:6]:
            kw_str = f"（关键词：{', '.join(lec.get('keywords', [])[:4])}）" if lec.get('keywords') else ""
            pdf_link = f" [📄 PDF]({lec['pdf_url']})" if lec.get('pdf_url') else ""
            lines.append(f"  - **[{lec['lecture']}: {lec['title']}]({lec['folder_url']})**{pdf_link} {kw_str}")
        if len(gk["lectures"]) > 6:
            lines.append(f"  - *... 更多 Lecture 0-28 详见 [GKxxUCAS 仓库主页]({gk['repo_url']})*")
        has_slides = True
    if itx and itx.get("categories", {}).get("slides_notes"):
        for sl in itx["categories"]["slides_notes"]:
            lines.append(f"- 📊 **教学课件 PPT**：[{sl['semester']} - {sl['folder']}]({sl['url']})")
            has_slides = True
    if itx and itx.get("categories", {}).get("recitations"):
        for rc in itx["categories"]["recitations"]:
            lines.append(f"- 👨‍🏫 **习题课与复习讲义**：[{rc['semester']} - {rc['folder']}]({rc['url']})")
            has_slides = True
    if xw and xw.get("slides_notes"):
        for sn in xw["slides_notes"]:
            lines.append(f"- 📖 **XiongWenye 讲义/提纲**：[{sn['name']}]({sn['url']})")
            has_slides = True
    if sk and sk.get("slides_notes"):
        for sn in sk["slides_notes"][:6]:
            lines.append(f"- 📊 **skkk256 讲义笔记**：[{sn['name']}]({sn['url']})")
            has_slides = True
    if wt and wt.get("slides_notes"):
        for sn in wt["slides_notes"][:6]:
            lines.append(f"- 📖 **wutianyuan1 讲义/文档**：[{sn['name']}]({sn['url']})")
            has_slides = True
    if not has_slides:
        lines.append("- *可直接在下方资料库主页中查阅课件。*")
    if xw and xw.get("others"):
        lines.append("\n**其他课程资料（按原文件名列出，内容尚未分类）**：")
        for file in xw["others"]:
            lines.append(f"- 📄 [{file['name']}]({file['url']})")
    lines.append("")

    # Section 4: Projects, Labs & Templates
    lines.append("### 💡 4. 实验报告与大作业设计 (Projects & Labs)")
    has_proj = False
    if rf and rf.get("reports"):
        lines.append(f"- 🏆 **RulerFuhai 普化实验高分报告范本**（2024-2025秋学期）：")
        for rep in rf["reports"][:8]:
            lines.append(f"  - 📑 [{rep['name']}]({rep['url']})")
        has_proj = True
    if rf and rf.get("templates"):
        for tmp in rf["templates"]:
            lines.append(f"- 📝 **实验报告纸模板/环境说明**：[{tmp['name']}]({tmp['url']})")
            has_proj = True
    pf = res.get("profetia")
    if pf and pf.get("projects"):
        lines.append(f"- 💻 **profetia 课程项目开源源码**（{pf.get('total_files', 0)} 个工程文件）：")
        for pr in pf["projects"][:6]:
            lines.append(f"  - 🛠️ [{pr['name']}]({pr['url']})")
        has_proj = True
    if wt and wt.get("projects"):
        for pr in wt["projects"][:6]:
            lines.append(f"- 🛠️ **wutianyuan1 课程大作业/项目**：[{pr['name']}]({pr['url']})")
            has_proj = True
    if wt and wt.get("labs"):
        for lb in wt["labs"][:6]:
            lines.append(f"- 🧪 **wutianyuan1 物理/化学实验数据**：[{lb['name']}]({lb['url']})")
            has_proj = True
    if sk and sk.get("projects"):
        for pr in sk["projects"][:6]:
            lines.append(f"- 🎨 **skkk256 课程设计与项目**：[{pr['name']}]({pr['url']})")
            has_proj = True
    if itx and itx.get("categories", {}).get("projects"):
        for pj in itx["categories"]["projects"]:
            lines.append(f"- 🛠️ **iTechX 课程设计/项目**：[{pj['semester']} - {pj['folder']}]({pj['url']})")
            has_proj = True
    if xw and xw.get("labs"):
        for lb in xw["labs"][:6]:
            lines.append(f"- 🧪 **XiongWenye 实验讲义/报告**：[{lb['name']}]({lb['url']})")
            has_proj = True
    if not has_proj:
        lines.append("- *该课程无大作业或实验材料，或已归并在作业目录中。*")
    lines.append("")

    # Section 5: Direct Repository Deep-links
    lines.append("### 🔗 5. 共享资料库一键直达 (Direct Repositories)")
    if itx and itx.get("repo_url"):
        lines.append(f"- 🌐 **[iTechX 课程资源主页]({itx['repo_url']})**（收录 {itx.get('semesters_count', 0)} 个学期教学档案）")
    if xw and xw.get("repo_url"):
        for folder, url in zip(xw.get("folder_names") or [xw.get("folder_name")],
                               xw.get("repo_urls") or [xw["repo_url"]]):
            lines.append(f"- 🌐 **[XiongWenye 上科大课程资料库 - {folder}]({url})**")
        lines.append(f"  共收录 {xw.get('total_files', 0)} 份资料。")
    zsc = res.get("zsc2003")
    if zsc and zsc.get("repo_url"):
        lines.append(f"- 🌐 **[zsc2003 专属修课与通关仓库]({zsc['repo_url']})**（包含 {', '.join(zsc.get('semesters', []))} 经验与高分代码）")
    if sk and sk.get("repo_url"):
        lines.append(f"- 🌐 **[skkk256 上科大修课仓库 - {sk.get('folder_name')}]({sk['repo_url']})**（收录 {sk.get('total_files', 0)} 份资料）")
    if wt and wt.get("repo_url"):
        lines.append(f"- 🌐 **[wutianyuan1 上科大课程仓库 - {wt.get('folder_name')}]({wt['repo_url']})**（收录 {wt.get('total_files', 0)} 份项目代码与文档）")
    if pf and pf.get("repo_url"):
        lines.append(f"- 🌐 **[profetia 课程项目代码库 - {pf.get('folder_name')}]({pf['repo_url']})**（收录 {pf.get('total_files', 0)} 个工程源码文件）")
    if gk and gk.get("repo_url"):
        lines.append(f"- 🌐 **[GKxxUCAS CS100 全套讲义精炼库]({gk['repo_url']})**（包含全套 29 讲 Slides 源码与关键词）")
    if rf and rf.get("repo_url"):
        lines.append(f"- 🌐 **[RulerFuhai CHEM1100 普化实验高分资料库]({rf['repo_url']})**（包含 13 个实验完整报告范本与预习题）")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="ShanghaiTech Course Materials Query Engine")
    parser.add_argument("--refresh", "-r", action="store_true", help="Force sync latest course database from upstream")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # get command
    get_p = subparsers.add_parser("get", help="Get complete materials for a course")
    get_p.add_argument("course", help="Course code (e.g. CS100) or Chinese name/alias (e.g. 计算机编程, 大物, 数分)")
    get_p.add_argument("--json", action="store_true", help="Output raw JSON instead of markdown")
    get_p.add_argument("--refresh", "-r", action="store_true", help="Force sync latest course database from upstream")

    # search command
    search_p = subparsers.add_parser("search", help="Fuzzy search courses in the database")
    search_p.add_argument("keyword", help="Search keyword")
    search_p.add_argument("--limit", type=int, default=10, help="Max results to display")
    search_p.add_argument("--refresh", "-r", action="store_true", help="Force sync latest course database from upstream")

    # list command
    list_p = subparsers.add_parser("list", help="List all courses with available materials")
    list_p.add_argument("--dept", help="Filter by department/institute keyword")
    list_p.add_argument("--refresh", "-r", action="store_true", help="Force sync latest course database from upstream")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    force_refresh = getattr(args, "refresh", False)
    index = load_index(force_refresh=force_refresh)

    if args.command == "get":
        target = resolve_course_code(index, args.course)
        if not target:
            print(f"❌ 未在资料库中找到与 '{args.course}' 匹配的课程。", file=sys.stderr)
            print("💡 建议：可使用 `python3 scripts/query_materials.py search <关键词>` 模糊检索课程代码。", file=sys.stderr)
            sys.exit(1)
        
        if isinstance(target, list):
            print(f"🔍 找到多个可能的匹配项，请输入具体课号或更精确的名称：")
            for c in target[:8]:
                info = index["courses"][c]
                print(f"  - [{c}] {info.get('name_zh')} ({info.get('institute')})")
            sys.exit(0)
            
        course = index["courses"][target]
        if args.json:
            print(json.dumps(course, ensure_ascii=False, indent=2))
        else:
            print(format_markdown_report(course))

    elif args.command == "search":
        kw = args.keyword.strip().lower()
        matches = []
        for code, info in index["courses"].items():
            name_zh = info.get("name_zh", "").lower()
            name_en = info.get("name_en", "").lower()
            aliases = [a.lower() for a in info.get("aliases", [])]
            inst = info.get("institute", "").lower()
            
            score = 0
            if kw == code.lower() or kw == name_zh:
                score = 100
            elif kw in code.lower() or kw in name_zh:
                score = 80
            elif any(kw in a for a in aliases):
                score = 60
            elif kw in name_en or kw in inst:
                score = 40
                
            if score > 0:
                matches.append((score, code, info))
                
        matches.sort(key=lambda x: x[0], reverse=True)
        results = matches[:args.limit]
        
        if not results:
            print(f"❌ 未找到包含关键词 '{args.keyword}' 的课程资料。")
            sys.exit(0)
            
        print(f"🔍 找到 {len(matches)} 门相关课程（展示前 {len(results)} 个）：\n")
        print(f"| 课号 | 课程名称 | 开课学院 | 包含资料库 | 常用别名 |")
        print(f"| :--- | :--- | :--- | :--- | :--- |")
        for _, code, info in results:
            res = info.get("resources", {})
            sources = []
            if res.get("itechx", {}).get("available"):
                sources.append("iTechX")
            if res.get("xiongwenye", {}).get("available"):
                sources.append("XiongWenye")
            if res.get("zsc2003", {}).get("available"):
                sources.append("zsc2003")
            if res.get("skkk256", {}).get("available"):
                sources.append("skkk256")
            if res.get("wutianyuan1", {}).get("available"):
                sources.append("wutianyuan1")
            if res.get("profetia", {}).get("available"):
                sources.append("profetia")
            if res.get("gkxx_cs100", {}).get("available"):
                sources.append("GKxxUCAS")
            if res.get("rulerfuhai", {}).get("available"):
                sources.append("RulerFuhai")
            s_str = ", ".join(sources)
            
            # colloquial aliases subset
            als = [a for a in info.get("aliases", []) if a.lower() != code.lower() and a != info.get("name_zh")][:3]
            als_str = "/".join(als) if als else "-"
            
            print(f"| **{code}** | {info.get('name_zh')} | {info.get('institute', '上海科技大学')} | {s_str} | {als_str} |")

    elif args.command == "list":
        dept_filter = args.dept.strip().lower() if args.dept else None
        count = 0
        print(f"📋 上海科技大学全课程复习与资料库清单：\n")
        print(f"| 课号 | 课程名称 | 学分 | 开课学院 | 资料来源 |")
        print(f"| :--- | :--- | :--- | :--- | :--- |")
        for code, info in sorted(index["courses"].items()):
            inst = info.get("institute", "上海科技大学")
            if dept_filter and dept_filter not in inst.lower() and dept_filter not in info.get("name_zh", "").lower():
                continue
            count += 1
            res = info.get("resources", {})
            sources = []
            if res.get("itechx", {}).get("available"):
                sources.append("iTechX")
            if res.get("xiongwenye", {}).get("available"):
                sources.append("XiongWenye")
            if res.get("zsc2003", {}).get("available"):
                sources.append("zsc2003")
            if res.get("skkk256", {}).get("available"):
                sources.append("skkk256")
            if res.get("wutianyuan1", {}).get("available"):
                sources.append("wutianyuan1")
            if res.get("profetia", {}).get("available"):
                sources.append("profetia")
            if res.get("gkxx_cs100", {}).get("available"):
                sources.append("GKxxUCAS")
            if res.get("rulerfuhai", {}).get("available"):
                sources.append("RulerFuhai")
            print(f"| **{code}** | {info.get('name_zh')} | {info.get('credit', 0)} | {inst} | {', '.join(sources)} |")
        print(f"\n共计 {count} 门课程具备完整资料。")


if __name__ == "__main__":
    main()
