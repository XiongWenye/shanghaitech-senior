#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ShanghaiTech 3+1 International Exchange Query Tool (3+1 国际交流项目与奖学金助手)
Parses and queries official 3+1 exchange programs, scholarship policies,
historical admission GPA ranges, language requirements, and student experiences.
"""

import os
import sys
import json
import argparse
import re
from pathlib import Path

# Ensure UTF-8 output across platforms, especially on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "exchange"
PROGRAMS_FILE = DATA_DIR / "programs.json"
SCHOLARSHIP_FILE = DATA_DIR / "scholarship_policy.json"
EXPERIENCES_DIR = DATA_DIR / "experiences"


def load_programs():
    if not PROGRAMS_FILE.exists():
        print(f"❌ 找不到项目数据文件: {PROGRAMS_FILE}", file=sys.stderr)
        return []
    with open(PROGRAMS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_scholarship_policy():
    if not SCHOLARSHIP_FILE.exists():
        print(f"❌ 找不到奖学金政策文件: {SCHOLARSHIP_FILE}", file=sys.stderr)
        return {}
    with open(SCHOLARSHIP_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_student_experiences():
    """Load student experience files if available."""
    experiences = {}
    if not EXPERIENCES_DIR.exists():
        return experiences
    
    for f in EXPERIENCES_DIR.glob("*.json"):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                if isinstance(data, list):
                    for item in data:
                        pid = item.get("program_id") or item.get("id")
                        if pid:
                            experiences.setdefault(pid, []).append(item)
                elif isinstance(data, dict):
                    pid = data.get("program_id") or data.get("id")
                    if pid:
                        experiences.setdefault(pid, []).append(data)
        except Exception:
            pass

    for f in EXPERIENCES_DIR.glob("*.md"):
        # Allow markdown note files named by school/id, e.g. berkeley_coe.md
        pass

    return experiences


def find_programs(query, programs):
    """Fuzzy match program by id, school name, program name, country, or department."""
    query_str = str(query).strip()
    query_lower = query_str.lower()
    results = []
    
    # Exact ID match
    if query_str.isdigit():
        target_id = int(query_str)
        for p in programs:
            if p.get("id") == target_id:
                return [p]

    aliases = {
        "ucb": "加州大学伯克利分校",
        "berkeley": "加州大学伯克利分校",
        "伯克利": "加州大学伯克利分校",
        "harvard": "哈佛大学",
        "哈佛": "哈佛大学",
        "umich": "密歇根大学",
        "密西根": "密歇根大学",
        "密歇根": "密歇根大学",
        "wisconsin": "威斯康星大学麦迪逊分校",
        "uw-madison": "威斯康星大学麦迪逊分校",
        "麦迪逊": "威斯康星大学麦迪逊分校",
        "uiuc": "伊利诺伊大学厄巴纳-香槟分校",
        "香槟": "伊利诺伊大学厄巴纳-香槟分校",
        "lumc": "荷兰莱顿大学医学院",
        "莱顿": "荷兰莱顿大学医学院",
        "drexel": "德雷塞尔大学",
        "德雷塞尔": "德雷塞尔大学",
        "芝大": "芝加哥大学",
        "芝加哥": "芝加哥大学",
        "uchicago": "芝加哥大学",
        "columbia": "哥伦比亚大学",
        "哥大": "哥伦比亚大学",
        "哥伦比亚": "哥伦比亚大学",
        "grenoble": "法国格勒诺布尔综合理工学院",
        "格勒": "法国格勒诺布尔综合理工学院",
        "upenn": "宾夕法尼亚大学",
        "宾大": "宾夕法尼亚大学",
        "penn": "宾夕法尼亚大学",
        "coe": "工程学院",
        "scet": "创新创业",
        "data": "数据科学",
        "biccep": "化学学院",
        "bbsa": "生命科学",
        "bpie": "物理专业",
        "bhgap": "商学院",
        "lps": "通识学院",
        "seas": "工程学院"
    }

    target_alias = aliases.get(query_lower)

    for p in programs:
        match_score = 0
        p_name = p.get("school_name", "").lower()
        p_title = p.get("title", "").lower()
        p_sub = p.get("sub_program", "").lower()
        p_dept = p.get("department_info", "").lower()
        majors = " ".join(p.get("suitable_majors", [])).lower()
        tracks = " ".join(p.get("sub_tracks", [])).lower()

        # If direct alias match found
        if target_alias:
            if target_alias in p_name:
                match_score += 20
            elif target_alias in p_sub or target_alias in p_title or target_alias in tracks:
                match_score += 15

        # Check direct substring
        if query_lower in p_name:
            match_score += 10
        elif query_lower in p_title or query_lower in p_sub:
            match_score += 8
        elif query_lower in p_dept or query_lower in tracks:
            match_score += 5
        elif query_lower in majors:
            match_score += 3

        if match_score > 0:
            results.append((match_score, p))

    results.sort(key=lambda x: x[0], reverse=True)
    # If the top result has significantly higher score (e.g. >= 20 vs < 15), return only top group
    if results and results[0][0] >= 15:
        top_score = results[0][0]
        results = [r for r in results if r[0] == top_score or r[0] >= 15]

    return [item[1] for item in results]


def cmd_list(programs, major_filter=None, tier_filter=None, country_filter=None):
    """List 3+1 programs with optional filters."""
    filtered = programs
    if major_filter:
        major_filter = major_filter.lower()
        filtered = [p for p in filtered if any(major_filter in m.lower() for m in p.get("suitable_majors", [])) or "全校各专业" in p.get("suitable_majors", [])]
    if tier_filter:
        filtered = [p for p in filtered if tier_filter in p.get("scholarship_tier", "")]
    if country_filter:
        filtered = [p for p in filtered if country_filter in p.get("country", "")]

    print(f"# 🌍 上海科技大学 3+1 国际交流项目一览表 (共 {len(filtered)} 项)")
    print(f"> 数据基线：官方 2026 秋批次大表 & 上科大教〔2025〕2 号专项奖学金标准\n")

    print("| 序号 | 合作高校与项目 | 交流方向 / 学院 | 名额 | 最低GPA要求 | 录取历史GPA | 语言要求概览 | 奖学金档位 |")
    print("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    for p in filtered:
        pid = p["id"]
        title = p["title"].split(" (")[0]
        sub = p["sub_program"]
        quota = p["quota"].replace("\n", " ")
        gpa = p["gpa_requirement"].split(" ")[0].replace("GPA≥", "≥").replace("GPA", "")
        hist_gpa = p["historical_gpa_range"] or "New"
        lang_short = p["language_requirement"].split("\n")[0].strip()
        if p.get("interview_waiver") or "加州大学伯克利分校" in p.get("school_name", ""):
            lang_short += " (可面试Waive)"
        tier = p["scholarship_tier"]
        print(f"| **{pid}** | {title} | {sub} | {quota} | `{gpa}` | `{hist_gpa}` | {lang_short} | **{tier}** |")

    print("\n💡 **提示**：查看某高校项目完整详情（学费、选课、申请渠道与避坑），请执行：")
    print("`python3 scripts/senior.py 3plus1 info <高校名/序号>` (例如：`senior.py 3plus1 info 伯克利` 或 `senior.py 3plus1 info 17`)")


def cmd_info(query, programs):
    """Show detailed briefing for a specific program."""
    matched = find_programs(query, programs)
    if not matched:
        print(f"❌ 老学长没有找到与 '{query}' 相关的 3+1 国际交流项目。", file=sys.stderr)
        print("💡 建议使用 `python3 scripts/senior.py 3plus1 list` 查看全校官方项目清单。", file=sys.stderr)
        return

    exp_map = load_student_experiences()

    for p in matched:
        pid = p["id"]
        print(f"# 🏛️ 3+1 深度把脉：【项目 {pid}】{p['title']}")
        print(f"**合作高校**：{p['school_name']} | **所属国家**：{p['country']} | **交流学制**：{p['calendar']} ({p['duration']})\n")

        if p.get("interview_waiver") or "加州大学伯克利分校" in p.get("school_name", ""):
            print("> 🌟 **老学长特快提点 (Berkeley 语言 Waiver 机制)**：加州大学伯克利分校（UC Berkeley）全系列项目**并不严格要求英语标化成绩**！若暂无托福/雅思/多邻国成绩或成绩未达标，完全可以通过参加 Berkeley 官方远程面试（Online Interview），由外方开具英语能力证明直接 **Waive 掉语言成绩**！\n")

        print("## 📋 一、基本申请条件与录取画像")
        print(f"- 👥 **选拔名额**：{p['quota']}")
        print(f"- 🎯 **适配专业**：{', '.join(p['suitable_majors'])}")
        print(f"- 📊 **最低 GPA 门槛**：`{p['gpa_requirement']}`")
        print(f"- 📈 **往届录取学分绩区间**：`{p['historical_gpa_range']}`")
        print(f"- 🗣️ **语言成绩要求**：\n```text\n{p['language_requirement']}\n```")
        if p.get("sub_tracks"):
            print(f"- 🔀 **开设子方向 (Tracks)**：")
            for t in p["sub_tracks"]:
                print(f"  - {t}")

        print("\n## 💰 二、学费参考与专项奖学金资助")
        print(f"- 💵 **官方学费参考**：{p['tuition_reference']}")
        print(f"- 🏠 **住宿资讯**：{p['housing']}")
        print(f"- 🏆 **上科大专项奖学金认定**：**{p['scholarship_tier']}项目**")
        print(f"  - 🥇 **前 2% 综合评价**：`{p['scholarship_amounts'].get('top_2%', 0)} 万元 / 学期`")
        print(f"  - 🥈 **前 3-7% 综合评价**：`{p['scholarship_amounts'].get('top_3_7%', 0)} 万元 / 学期`")
        print(f"  - 🥉 **前 8-15% 综合评价**：`{p['scholarship_amounts'].get('top_8_15%', 0)} 万元 / 学期`")
        print(f"  > *注：综合评价前15%学生可享，在校期间仅限获评一次，累计奖学金总额原则上不超过 16 万元。*")

        print("\n## 📅 三、关键时间节点与申报流程")
        print(f"- 📌 **上科大校内申请截止**：`{p['internal_deadline']}`")
        print(f"- 🌐 **外方网申/报送截止**：`{p['external_deadline']}`")
        print(f"- ✈️ **对方开学/教学周起始**：`{p['start_time']}`")
        print(f"- 📝 **官方申报渠道**：\n```text\n{p['application_channel']}\n```")

        print("\n## 📚 四、课程学分与官方链接")
        print(f"- 📖 **学分修读规范**：{p['credits_info']}")
        if p.get("notes"):
            print(f"- ⚠️ **官方特别注意事项**：\n> {p['notes']}")
        print(f"- 🔗 **官方信息与选课网址**：\n```text\n{p['urls']}\n```")

        # Student Experiences Section
        print("\n## 🧑‍🎓 五、老学长亲历经验与避坑锦囊 (Senior's Experience)")
        experiences = exp_map.get(pid, [])
        if experiences:
            for exp in experiences:
                author = exp.get("author", "匿名学长/学姐")
                major = exp.get("major", "")
                year = exp.get("year", "")
                print(f"### 💬 【{year}届 {major} {author}】分享：")
                if exp.get("course_advice"):
                    print(f"- **选课体验**：{exp['course_advice']}")
                if exp.get("research_lab"):
                    print(f"- **科研/进组**：{exp['research_lab']}")
                if exp.get("credit_transfer"):
                    print(f"- **学分认定与转回**：{exp['credit_transfer']}")
                if exp.get("living_tips"):
                    print(f"- **生活与租房**：{exp['living_tips']}")
        else:
            print("> 💡 **老学长提示**：本模块官方基础信息已固化核对。学生个人历届亲身选课与就读经验（就读难度、套磁进组几率、学分转换回国实操）将通过开放经验库陆续载入！欢迎已交流返校的学长学姐在 `data/exchange/experiences/` 提供第一手分享。")

        print("\n" + "="*70 + "\n")


def cmd_scholarship(school_query=None):
    """Show official scholarship policy and breakdown."""
    policy = load_scholarship_policy()
    print(f"# 🎓 《{policy.get('title', '上海科技大学本科生国际交流专项奖学金评定管理办法')}》")
    print(f"> 文号：`{policy.get('doc_number')}` | 施行日期：`{policy.get('effective_date')}` | 主管机构：`{policy.get('governing_body')}`\n")

    three_p = policy.get("three_plus_one", {})
    print("## 🏅 一、3+1 国际交流项目奖学金标准")
    print(f"**参评资格**：{three_p.get('description')}")
    print(f"**评定方式**：{three_p.get('evaluation_basis')}\n")

    print("| 项目档位 | 覆盖合作高校与项目 | 前 2% 资助 | 前 3-7% 资助 | 前 8-15% 资助 |")
    print("| :--- | :--- | :--- | :--- | :--- |")
    for tier_name, tier_info in three_p.get("tiers", {}).items():
        schools_str = "、".join(tier_info["schools_covered"])
        awards = tier_info["awards"]
        print(f"| **{tier_name}** | {schools_str} | `{awards.get('top_2%')} 万元/学期` | `{awards.get('top_3_7%')} 万元/学期` | `{awards.get('top_8_15%')} 万元/学期` |")

    print("\n## 📌 二、三大核心红线与评定细则")
    print(f"1. **总额封顶红线**：原则上学生在校期间获得国际交流专项奖学金总额**不超过人民币 16 万元**。")
    print(f"2. **困难学生特殊资助**：{policy.get('special_financial_aid')}")
    print(f"3. **不重复资助原则**：{policy.get('duplicate_funding_rule')}")
    print(f"4. **结项认定要求**：每年 6 月组织评定，学生需在规定节点提交**交流成绩单**与**项目小结**认定已结项，方可参评。")

    summer_c = policy.get("summer_courses", {})
    print("\n## ☀️ 三、海外暑期课程项目奖学金 (附参考)")
    for item in summer_c.get("items", []):
        p_names = "、".join(item["projects"])
        keys = [k for k in item.keys() if k != "projects"]
        details = ", ".join([f"{k}: {item[k]}万元" for k in keys])
        print(f"- **{p_names}**：{details}")

    summer_r = policy.get("summer_research", {})
    print("\n## 🔬 四、海外暑期科研项目奖学金 (附参考)")
    print(f"> {summer_r.get('description')}")
    for region, amt in summer_r.get("tiers", {}).items():
        print(f"- **{region}**：`{amt} 万元`")


def cmd_match(programs, gpa=None, toefl=None, ielts=None, duolingo=None, major=None):
    """Recommend and classify 3+1 programs based on student profile."""
    print(f"# 🎯 3+1 项目智能定位与匹配分析")
    print(f"> 你的背景：GPA: `{gpa or '未指定'}` | 托福: `{toefl or '未指定'}` | 雅思: `{ielts or '未指定'}` | 多邻国: `{duolingo or '未指定'}` | 专业: `{major or '未指定'}`\n")

    recommended = []
    reach = []
    safe = []
    conditional = []

    for p in programs:
        pid = p["id"]
        title = p["title"]
        min_gpa_match = re.search(r"(\d+\.\d+)", p["gpa_requirement"])
        min_gpa = float(min_gpa_match.group(1)) if min_gpa_match else 3.0

        hist_range = p.get("historical_gpa_range", "")
        hist_low = None
        if "-" in hist_range:
            parts = hist_range.split("-")
            try:
                hist_low = float(parts[0].strip())
            except Exception:
                pass

        # Check major suitability
        major_match = True
        if major:
            suitable = [m.lower() for m in p.get("suitable_majors", [])]
            major_match = any(major.lower() in m for m in suitable) or "全校各专业" in p.get("suitable_majors", [])

        # Check GPA
        gpa_pass = True if gpa is None else (gpa >= min_gpa)

        # Check language
        lang_text = p.get("language_requirement", "")
        lang_pass = True
        if toefl or ielts or duolingo:
            has_lang_condition = False
            # check toefl
            t_match = re.search(r"toefl.*?(\d+)", lang_text, re.IGNORECASE)
            t_min = int(t_match.group(1)) if t_match else None
            # check ielts
            i_match = re.search(r"ielts.*?(\d+\.?\d*)", lang_text, re.IGNORECASE)
            if not i_match:
                i_match = re.search(r"雅思.*?(\d+\.?\d*)", lang_text)
            i_min = float(i_match.group(1)) if i_match else None
            # check duolingo
            d_match = re.search(r"duolingo.*?(\d+)", lang_text, re.IGNORECASE)
            d_min = int(d_match.group(1)) if d_match else None

            # Evaluation
            pass_any = False
            if toefl and t_min and toefl >= t_min:
                pass_any = True
            if ielts and i_min and ielts >= i_min:
                pass_any = True
            if duolingo and d_min and duolingo >= d_min:
                pass_any = True

            if (t_min or i_min or d_min) and not pass_any:
                lang_pass = False

        # Berkeley Special Policy: Standardized English tests are not strictly required,
        # can be waived via Berkeley Online Interview!
        is_berkeley = "加州大学伯克利分校" in p.get("school_name", "") or p.get("interview_waiver", False)
        waiver_applied = False
        if not lang_pass and is_berkeley:
            lang_pass = True
            waiver_applied = True

        item_summary = {
            "p": p,
            "min_gpa": min_gpa,
            "hist_range": hist_range,
            "major_match": major_match,
            "waiver_applied": waiver_applied
        }

        if gpa_pass and lang_pass and major_match:
            quota_text = p.get("quota", "")
            if "暂无限制" in quota_text or "15-30" in quota_text or "30名" in quota_text:
                safe.append(item_summary)
            elif gpa and hist_low and gpa >= hist_low:
                recommended.append(item_summary)
            else:
                reach.append(item_summary)
        else:
            reason = []
            if not gpa_pass:
                reason.append(f"GPA未达门槛({min_gpa})")
            if not lang_pass:
                reason.append("语言成绩暂不满足要求")
            if not major_match:
                reason.append("专业方向非核心对口")
            item_summary["reason"] = ", ".join(reason)
            conditional.append(item_summary)

    # Output sections
    if recommended:
        print("### 🟢 【推荐核心适配 (Target)】（硬指标达标，历届录取高度匹配）")
        for item in recommended:
            p = item["p"]
            waiver_tag = " ✨【可面试Waive语言】" if item.get("waiver_applied") else ""
            print(f"- **【{p['id']}】{p['title']}**（名额: {p['quota']} | 历史GPA: `{p['historical_gpa_range']}` | 奖学金: **{p['scholarship_tier']}**）{waiver_tag}")

    if safe:
        print("\n### 🛡️ 【稳妥保底/充足名额 (Safe & Broad)】（名额充裕或录取极度友好）")
        for item in safe:
            p = item["p"]
            waiver_tag = " ✨【可面试Waive语言】" if item.get("waiver_applied") else ""
            print(f"- **【{p['id']}】{p['title']}**（名额: {p['quota']} | 最低GPA: `{p['gpa_requirement']}` | 奖学金: **{p['scholarship_tier']}**）{waiver_tag}")

    if reach:
        print("\n### 🚀 【冲刺拔高 (Reach)】（达到官方最低门槛，但历史录取竞争激烈）")
        for item in reach:
            p = item["p"]
            waiver_tag = " ✨【可面试Waive语言】" if item.get("waiver_applied") else ""
            print(f"- **【{p['id']}】{p['title']}**（历史GPA: `{p['historical_gpa_range']}` | 门槛: `{p['gpa_requirement']}` | 奖学金: **{p['scholarship_tier']}**）{waiver_tag}")

    if conditional and (gpa or toefl or ielts or duolingo or major):
        print("\n### ⚠️ 【暂需补齐条件 / 跨专业受限 (Conditional)】")
        for item in conditional[:5]:
            p = item["p"]
            print(f"- **【{p['id']}】{p['title']}**：{item.get('reason')}")


def cmd_deadlines(programs):
    """Show timeline of 3+1 exchange application deadlines."""
    print("# ⏰ 2026-2027 3+1 国际交流项目申报关键时间轴")
    print("> 建议提前完成托福/雅思标化考试，校内选拔由教务处与外事部门组织。\n")

    print("| 序号 | 合作高校与项目 | 校内申请截止 (上科大) | 外方报送/网申截止 | 开学周 | 申请渠道 |")
    print("| :--- | :--- | :--- | :--- | :--- | :--- |")
    for p in programs:
        pid = p["id"]
        title = p["school_name"] + " - " + p["sub_program"]
        in_ddl = p["internal_deadline"] or "详见通知"
        ex_ddl = p["external_deadline"].replace("\n", " ")
        start = p["start_time"].replace("\n", " ")
        channel = p["application_channel"].split("\n")[0]
        print(f"| {pid} | {title} | **{in_ddl}** | {ex_ddl} | {start} | {channel} |")


def main():
    parser = argparse.ArgumentParser(description="上海科技大学 3+1 国际交流项目与奖学金助手")
    subparsers = parser.add_subparsers(dest="command")

    # list
    list_p = subparsers.add_parser("list", help="查看所有官方 3+1 国际交流项目")
    list_p.add_argument("--major", help="按专业筛选 (如 计算机, 物理, 生命, 工业设计)")
    list_p.add_argument("--tier", help="按奖学金档位筛选 (如 一类, 二类, 三类, 五类)")
    list_p.add_argument("--country", help="按国家筛选 (如 美国, 荷兰, 法国)")

    # info
    info_p = subparsers.add_parser("info", help="查看某高校/项目的详细档案 (学费、GPA、选课、奖学金、避坑)")
    info_p.add_argument("query", help="高校名称、项目名或编号 (如 伯克利, 哈佛, 哥大, UIUC, 17)")

    # scholarship
    sch_p = subparsers.add_parser("scholarship", help="查看国际交流专项奖学金官方评定办法与金额表")
    sch_p.add_argument("--school", help="查询特定高校的奖学金级别")

    # match
    match_p = subparsers.add_parser("match", help="智能推荐与背景定位匹配")
    match_p.add_argument("--gpa", type=float, help="当前绩点 (如 3.65)")
    match_p.add_argument("--toefl", type=int, help="托福总分 (如 102)")
    match_p.add_argument("--ielts", type=float, help="雅思总分 (如 7.5)")
    match_p.add_argument("--duolingo", type=int, help="多邻国总分 (如 130)")
    match_p.add_argument("--major", help="当前专业 (如 计算机, 电子, 物理, 生命)")

    # deadlines
    subparsers.add_parser("deadlines", help="查看所有项目申报截止时间轴")

    args = parser.parse_args()
    programs = load_programs()

    if not args.command or args.command == "list":
        cmd_list(programs, major_filter=getattr(args, "major", None), tier_filter=getattr(args, "tier", None), country_filter=getattr(args, "country", None))
    elif args.command == "info":
        cmd_info(args.query, programs)
    elif args.command == "scholarship":
        cmd_scholarship(school_query=getattr(args, "school", None))
    elif args.command == "match":
        cmd_match(programs, gpa=args.gpa, toefl=args.toefl, ielts=args.ielts, duolingo=args.duolingo, major=args.major)
    elif args.command == "deadlines":
        cmd_deadlines(programs)


if __name__ == "__main__":
    main()
