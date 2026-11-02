# 🧑‍🎓 上海科技大学本科老学长智能助手 (ShanghaiTech Senior Skill)

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![ShanghaiTech](https://img.shields.io/badge/University-ShanghaiTech-red.svg)](https://www.shanghaitech.edu.cn/)
[![Courses Covered](https://img.shields.io/badge/Courses-151+-brightgreen.svg)]()
[![CourseBench Reviews](https://img.shields.io/badge/Reviews-2300+-orange.svg)]()
[![3+1 Programs](https://img.shields.io/badge/3+1%20Programs-19%20Official-blueviolet.svg)]()
[![Scholarship Guide](https://img.shields.io/badge/Exchange%20Scholarship-2025%20Policy-critical.svg)]()

> 专为上海科技大学（ShanghaiTech）本科生打造的**全能学业导师与通关伙伴**。  
> 融合 **CourseBench** 真实学生评价大数据、**全校 12 大本科专业官方培养方案**、各大公开课程通关资料库，以及**学校官方 3+1 国际交流项目与专项奖学金标准**。

---

## 🌟 核心特性 (Features)

### 1. 🌟 选课口碑与授课风格 (CourseBench Engine)
- 覆盖全校 **1190+ 门课程**、**2300+ 条真实同学评分与文字评语**。
- 四维评分雷达：**教学质量、课业负担、考核难度、给分优劣**（5.0满分制）。
- 智能过滤：**年份近者优先**（2024/2025/2026 近期学期优先展示），自动剔除无实质分析的极端情绪化宣泄。

### 2. 📚 备考通关与资料秒级直达 (Test-Taking Engine)
全面整合各大课程资料共享库，已为全校 **151+ 门核心与专业课程**建立极速倒排索引：
- **📝 历年期中期末真题**：收录 近至2025 最新考卷回忆版、试卷原题扫描件、答案解析与名师讲解视频（如 2025 数分I、2025 普物I、2025 线代I、CS100 2025 中期含答案）。包含其他高校试卷作为参考（交大，浙大，UCB，MIT等）。
- **💡 平时作业与官方解答**：各学期 Homework 题目、标准答案（Solutions）及配套测试用例包。
- **🖥️ 讲义课件与复习提纲**：官方 PPT 课件、Recitation 习题课讲义、学长手写高分思维导图。
- **🛠️ 实验与大作业代码**：学长通关仓库代码、图论/算法模板、大作业参考。

### 3. 🗺️ 全校专业官方修课路线图 (Curriculum Roadmaps)
- 完整录入 **2026 级全校 12 大本科专业官方培养方案**（SIST 计科/AI荣誉班/电子、IMS 数学/信计、SPST 物理/化学/材料、SLST 生科/生技、BME 生医工、SCA 工业设计）。
- 支持按学期（大一秋/春/夏至大四）一键推荐官方建议修课计划，并自动标注每门课的 CourseBench 口碑评分。

### 4. 🎓 EAMS 计划完成情况智能预审 (Degree Audit)
- 独家实现 **EAMS 预审“三层学分切分”**（纯已通过、在读修读中、真实待修硬性缺口）。
- **严格遵循防重复统计铁律**：严防把 EAMS 顶部已内含的在读学分做二次重复叠加，精准预警大四毕业论文（SI199 6学分）等硬性缺口。

### 5. 🌍 3+1 本科国际交流与专项奖学金把脉 (Study Abroad & Scholarship Engine)
- **19 项官方合作名校与项目全覆盖**：哈佛大学（VUS）、加州大学伯克利分校（COE、SCET、DATA、BICCEP、BBSA、BPIE、BHGAP、MATH、ID 9大方向）、哥伦比亚大学（SEAS UVSP）、宾夕法尼亚大学（LPS IGSP）、芝加哥大学、密歇根大学（LSA）、威斯康星麦迪逊（VISP）、UIUC、荷兰莱顿大学医学院（LUMC）、法国格勒诺布尔综合理工（Grenoble INP）、德雷塞尔大学等。
- **真实门槛与录取画像**：区分最低硬性 GPA 与**往届真实录取学分绩区间**，标注官方选拔名额、选课要求、基础学费参考与申报截止节点。
- **语言免除（Waiver）独家机制**：支持托福、雅思、多邻国、CET-6六级（伯克利BBSA接受520+）；特别固化**加州大学伯克利分校全系列项目不严格死卡英语标化，可通过 Berkeley 官方远程面试开具证明直接 Waive 掉语言要求**的重要内幕！
- **专项奖学金自动核算**：全面对接《上海科技大学本科生国际交流专项奖学金评定管理办法》（上科大教〔2025〕2 号），直连一类至五类项目资助标准（前 2%、前 3-7%、前 8-15% 档位，最高 8.3 万元/学期，全校 16 万元上限）。
- **三维背景智能匹配选校**：输入学生 GPA、语言成绩与专业，秒级划分为【核心适配 Target】、【稳妥保底 Safe】、【冲刺拔高 Reach】与【受限项 Conditional】。
- **🧑‍🎓 开放亲历经验插槽**：预留学生个人真实经验库（`data/exchange/experiences/`），支持后续持续载入海外选课、科研套磁进组、海外导师推荐信与国内学分转换实操。

---

## ⚡ 零外部依赖声明 (Zero Dependencies)

本仓库核心工具链全部使用 **Python 原生标准库**（`sqlite3`、`json`、`urllib`、`argparse`、`html.parser` 等）构建：
- ❌ **无需 `pip install`** 任何第三方庞大包
- ❌ **无需配置** 繁琐环境
- ✅ 任何安装了 Python 3.8+ 的 Mac / Windows / Linux 机器均可**克隆即跑、毫秒级响应**！

---

## 🚀 快速上手 (Quick Start)

### 模式 A：作为Agent技能使用 (推荐)

直接克隆至本机的 Skills 目录：

```bash
git clone https://github.com/XiongWenye/shanghaitech-senior.git ~/你的Agent Skill目录/shanghaitech-senior
```

重启 Agent 或刷新对话后，AI 即可化身为“上科大本科老学长”，自动在对话中响应：
- *“学长，CS100 怎么样？难不难？该怎么学？”*
- *“快期末考了，有没有大物I和高数I的历年真题卷？”*
- *“下学期计科大一春季选什么课好？帮我推荐个路线。”*
- *“帮我分析一下我的 EAMS 培养计划完成情况，我还差什么学分？”*
- *“学长，伯克利 3+1 怎么选？需要考托福吗？可以面试 Waive 吗？”*
- *“我 GPA 3.65、托福 102，能申哪些 3+1 项目？奖学金能拿多少？”*

---

### 模式 B：作为独立终端命令行工具使用 (Standalone CLI)

即使不借助 AI，你也可以在本地终端中直接运行老学长 CLI：

```bash
# 1. 克隆仓库
git clone https://github.com/XiongWenye/shanghaitech-senior.git
cd shanghaitech-senior

# 2. 老学长全景把脉 (口碑 + 备考真题资料包 + 避坑锦囊，支持自动识别 3+1 出国意图)
python3 scripts/senior.py ask "CS100"
python3 scripts/senior.py ask "普通物理I"
python3 scripts/senior.py ask "伯克利3+1"

# 3. 仅提取备考复习资料 (真题卷、作业答案、课件讲义)
python3 scripts/senior.py materials "高等数学I"
python3 scripts/senior.py materials "CS100" --refresh  # 强制同步最新资料

# 4. 一键同步上游课程资料库 (上游更新后自动感知，无需更新 Skill)
python3 scripts/senior.py sync --force

# 5. 查指定专业的学期推荐修课计划
python3 scripts/senior.py roadmap --major 计算机 --semester 2
python3 scripts/senior.py roadmap --major 电子 --semester 1

# 6. 模糊检索课程
python3 scripts/senior.py search "体系结构"

# 7. 3+1 国际交流项目与专项奖学金把脉 (名校大表、选校匹配、奖学金核算)
python3 scripts/senior.py 3plus1                       # 查看 19 个官方合作项目一览
python3 scripts/senior.py 3plus1 info 伯克利            # 查询伯克利各学院项目、选课与语言 Waiver
python3 scripts/senior.py 3plus1 info 哥大              # 查询哥伦比亚大学工程学院 SEAS 选拔
python3 scripts/senior.py 3plus1 match --gpa 3.65 --toefl 102 --major 计算机 # 智能三维背景定位选校
python3 scripts/senior.py 3plus1 scholarship           # 查看一类至五类专项奖学金标准与评定细则
python3 scripts/senior.py 3plus1 deadlines             # 查看全校 3+1 校内外申请截止时间轴
```

---

## 🔒 隐私与数据安全承诺 (Privacy & Security)

1. **绝无账号密码留存**：本工具绝不记录或上传任何同学的统一身份认证账号与密码。
2. **纯本地离线运算**：CourseBench 口碑数据库与培养方案均完整内置于本地 `data/` 中，所有计算在同学本地完成。
3. **EAMS 预审防泄露机制**：真实学籍导出的 HTML 文件已通过 `.gitignore` 严格拦截，绝不提交至公开仓库。

---

## 🤝 致谢与开源生态 (Acknowledgements)

感谢上海科技大学活跃的开源与学生互助生态，本项目的顺利建设离不开以下前辈开源成果的滋养与全校课程资料的无私共享：
- 🟢 **[i-TechX / iTechX](https://github.com/i-TechX/iTechX)**：全校课程综合库，收录完整历年课件、作业与标准答案。
- 🟠 **[XiongWenye / shanghaitech-course-database](https://github.com/XiongWenye/shanghaitech-course-database)**：数理核心、信院与大物独家期中期末真题回忆卷、考点速查与名师解析。
- 🟣 **[zsc2003 / courses-summary](https://github.com/zsc2003/courses-summary)**：信院/数学专业核心课程高分代码、Recitation 教程与通关经验。
- 🔵 **[skkk256 / ShanghaiTech-Courses](https://github.com/skkk256/ShanghaiTech-Courses)**：涵盖 SIST、创艺 SCA 设计、生医工 BME、通识社科等 50+ 门全流程资料。
- 🟡 **[wutianyuan1 / ShanghaiTech](https://github.com/wutianyuan1/ShanghaiTech)**：操作系统 Pintos 完整报告、CS 体系结构、无机化学、设计思维、强化学习等代码与实验。
- 🔴 **[profetia / shanghaitech](https://github.com/profetia/shanghaitech)**：并行计算、操作系统、数据可视化、生信开发等全套工程源码与文档。
- 🔷 **[GKxxUCAS / ShanghaiTech-CS100-Slides](https://github.com/GKxxUCAS/ShanghaiTech-CS100-Slides)**：CS100 计算机编程全套 29 讲高清课件、图解与核心知识点速查。
- 🟤 **[RulerFuhai / Shanghaitech-CHEM1100](https://github.com/RulerFuhai/Shanghaitech-CHEM1100)**：CHEM1100 2024-2025 秋普化实验 13 个实验完整高分实验报告范本、预习思考题与报告纸模板。
- 上海科技大学 CourseBench 平台全体贡献真实评课的同学们

---

## ☕ Buy me a coffee

如果你觉得本项目对你有帮助，欢迎请老学长喝杯咖啡以支持持续维护和更新！本人承诺**所有捐赠**将用于本项目维护及相关开源生态建设（如高价值历年真题/解答的**贡献者激励**）。

| 微信支付 (WeChat Pay) | 支付宝 (Alipay) |
| :---: | :---: |
| <img src="./assets/wechat.jpg" width="230" alt="微信支付收款码" /> | <img src="./assets/alipay.jpg" width="230" alt="支付宝收款码" /> |

## 📄 开源许可证 (License)

本项目基于 [MIT License](LICENSE) 开源。欢迎全校师生提交 Issue 与 Pull Request 共同完善！
