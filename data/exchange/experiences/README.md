# 上海科技大学 3+1 国际交流学生亲历经验库 (Student Experiences)

本目录为 **3+1 国际交流个人经验分享** 的开放扩展口。

老学长助手现已全面固化**学校官方 19 项 3+1 交流项目**与**国际交流专项奖学金评定标准**。后续收集到的学生真实就读体验、选课避坑、海外科研套磁、学分转回实操、以及海外租房生活经验，均可按照本目录规范沉淀为结构化数据，供学弟学妹在咨询时即时调取！

---

## 📂 文件组织方式

支持两种录入方式（系统会自动扫描并载入）：

### 方式一：JSON 结构化录入 (推荐，便于 CLI 自动化索引)
在 `data/exchange/experiences/` 下新建或编辑 JSON 文件（例如 `experiences_2025.json`、`ucb_coe_experiences.json`），内容为符合规范的 JSON 列表：

```json
[
  {
    "program_id": 2,
    "school_name": "加州大学伯克利分校",
    "track": "工程学院 (COE) - CS 方向",
    "author": "2021级 信息学院学长",
    "exchange_year": "2024-2025",
    "exchange_term": "一学年 (秋+春)",
    "profile_at_apply": {
      "gpa": 3.75,
      "toefl": 105,
      "major": "计算机科学与技术"
    },
    "course_advice": "选课优先抢 CS162 和 CS189，虽然负担极重，但授课质量顶尖；注意先修课要求，建议提前开好上科大中英文 Syllabus。",
    "research_lab": "秋季学期第 3 周通过发 Cold Email 成功进入 BAIR 实验室做具身智能科研，学期末拿到了教授的强推推荐信。",
    "credit_transfer": "伯克利 4 units 对应上科大 4 学分，专业选修课转回非常顺利，大四毕业设计在海外远程开题并答辩完成。",
    "living_tips": "伯克利租房建议尽早找南门 (Southside) 或北门 (Northside)，月租约 $1200-$1600；办 J1 签证可以合法在校内科研进组。",
    "takeaway": "3+1 是本科期间最值得的投资，不仅开拓了国际学术视野，对申博/申硕有决定性帮助！"
  }
]
```

### 方式二：Markdown 逐校深度笔记
在 `data/exchange/experiences/` 下以项目编号或高校拼音命名（例如 `p02_ucb_coe.md`、`p01_harvard.md`），书写学长学姐长篇经验贴。

---

## 🎯 字段规范速查表

| 字段名 | 类型 | 说明 | 示例 |
| :--- | :--- | :--- | :--- |
| `program_id` | `int` | 对应官方大表项目编号 (1-19) | `2` (UCB COE), `1` (Harvard) |
| `school_name`| `string` | 高校名称 | `"加州大学伯克利分校"` |
| `track` | `string` | 所修学院/专业方向 | `"COE EECS"` |
| `author` | `string` | 分享人署名/年级/专业（可匿名） | `"2021级 SIST 张学长"` |
| `exchange_year` | `string` | 交流学年 | `"2024-2025"` |
| `exchange_term` | `string` | 交流学期 | `"秋学期" / "一学年"` |
| `profile_at_apply` | `object` | 申请时三维背景 | `{"gpa": 3.72, "toefl": 103}` |
| `course_advice` | `string` | 选课体验与课业难度避坑 | 针对课程负荷、考核特点的评价 |
| `research_lab` | `string` | 海外科研、进组与推荐信经验 | 如何套磁、进组感受、推荐信获取 |
| `credit_transfer` | `string` | 学分认定与国内毕业衔接 | 课程对应关系、毕设协同安排 |
| `living_tips` | `string` | 住宿租房、签证、生活成本 | 租房安全区域、开销参考 |
| `takeaway` | `string` | 学长心法与给学弟学妹的建议 | 总结性建议 |
