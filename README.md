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
- 每次从学校 EAMS 计划完成页面实时读取，在内存解析；登录 Cookie 可保留供后续查询，失效时重新登录。
- 严格遵循**“完成学分已内含在读课程”**的防重复叠加法则，精准切分“纯已通过”、“在读”与“硬性真实缺口”。

### 5. 🌍 3+1 本科国际交流与专项奖学金把脉 (Study Abroad & Scholarship Engine)
- **19 项官方合作名校与项目全覆盖**：哈佛大学（VUS）、加州大学伯克利分校（COE、SCET、DATA、BICCEP、BBSA、BPIE、BHGAP、MATH、ID 9大方向）、哥伦比亚大学（SEAS UVSP）、宾夕法尼亚大学（LPS IGSP）、芝加哥大学、密歇根大学（LSA）、威斯康星麦迪逊（VISP）、UIUC、荷兰莱顿大学医学院（LUMC）、法国格勒诺布尔综合理工（Grenoble INP）、德雷塞尔大学等。
- **真实门槛与录取画像**：区分最低硬性 GPA 与**往届真实录取学分绩区间**，标注官方选拔名额、选课要求、基础学费参考与申报截止节点。
- **语言免除（Waiver）机制**：支持托福、雅思、多邻国、CET-6六级（伯克利BBSA接受520+）；Berkeley可Waive
- **专项奖学金自动核算**：全面对接最新《上海科技大学本科生国际交流专项奖学金评定管理办法》
- **🧑‍🎓 开放亲历经验插槽**：预留学生个人真实经验库（`data/exchange/experiences/`），支持后续持续载入海外选课、科研套磁进组、海外导师推荐信与国内学分转换实操。

### 6. 📱 TechPie 深度集成校园服务 (TechPie Protocol Integrations)
- **🛡️ 学长 SKILL 第一要义：本地绝对零个人化信息，全量接入实时网络端口**：除独立保存的登录 Cookie 外，个人课表、作业、考场、成绩和签到记录仅在内存处理。所有个人状态查询（含 JSON 输出）均实时联网，失败不回退缓存。
- **🗺️ 校园楼宇地理坐标与课表 ICS 导出**：收录信息学院、创管学院、生命学院、物质学院、教学中心、体育馆等建筑高精度 GPS 经纬度，实时获取课表、校历与作息，向标准输出生成 iCalendar 内容（支持 iOS 结构化地图与出发提醒）。
- **📝 EAMS 考场与座位号看板**：一键查看期中与期末正式考试日程、考场教室及精确座位号，并支持向标准输出生成考试日历内容。
- **⏱️ 多源作业 Deadline 巡检看板**：跨平台聚合巡检 Blackboard、Gradescope、Hydro OJ 与 EAMS 考试日程，智能预警逾期与今日截止任务。
- **🏸 体育馆余场实时看板与避坑指南**：提供羽毛球、乒乓球、网球与匹克球在线余场查询，跨项目分别查询原生场地状态。
- **🎟️ xshdapp 校园活动打卡与讲座把脉**：实时展示活动签到流水；入场/离场时间与申请状态分别呈现，毕业达标要求需由学校当前方案确认。

---

## ⚡ 零外部依赖声明 (Zero Dependencies)

本仓库核心工具链全部使用 **Python 原生标准库**（`sqlite3`、`json`、`urllib`、`argparse`、`html.parser` 等）构建：
- ❌ **无需 `pip install`** 任何第三方庞大包
- ❌ **无需配置** 繁琐环境
- ✅ 公共资料查询可在 Python 3.8+ 的 Mac / Windows / Linux 运行；个人状态查询另需有效登录凭据与可用网络。

> 🪟 **Windows 环境编码特别提示 (Windows UTF-8 Notice)**：  
> Windows 终端（PowerShell / CMD）默认代码页（如 GBK / CP936）在输出 Emoji 或特殊字符时可能会遇到字符编码报错（`UnicodeEncodeError`）。各 Python 脚本内置了标准 I/O UTF-8 容错重构；在 Windows PowerShell 下运行前，推荐设置环境变量开启 Python 全局 UTF-8 模式：  
> ```powershell
> $env:PYTHONUTF8='1'
> ```  
> （CMD 终端执行 `set PYTHONUTF8=1`）。

---

## 🚀 快速上手 (Quick Start)

### 模式 A：作为Agent技能使用 (推荐)

直接克隆至本机的 Skills 目录：

```bash
git clone https://github.com/XiongWenye/shanghaitech-senior.git ~/你的Agent Skill目录/shanghaitech-senior
```

启用时先检查 Cookie：没有就自动打开登录终端，已有则直接复用。确认 Cookie 过期时也会弹出终端，用户直接填写手机号和验证码即可，无需输入命令或选择登录方式。同一次查询最多弹出一次；网络超时和 SSL 错误不触发重新登录。登录只认证并保存 Cookie，不自动查询 EAMS 或执行学分诊断；公共课程资料无需登录也可查询。

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

# 检查 Cookie；没有时弹出登录终端，已有则直接使用
python3 scripts/senior.py auth-status
python3 scripts/senior.py login  # 仅在未配置 Cookie 或会话已失效时运行

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


# 8. 课表日历导出与校园楼宇 GPS 经纬度查询
python3 scripts/senior.py schedule                     # 实时查询本学期选课与课表
python3 scripts/senior.py ics                          # 实时课表日历内容，仅标准输出
python3 scripts/senior.py location "信息学院"          # 查询信息学院精确坐标与 Apple 地图数据
python3 scripts/senior.py location "教学中心204"       # 查询公共教学中心建筑定位

# 9. EAMS 考场与座位号看板
python3 scripts/senior.py exams                        # 查询本学期期中期末考试时间、考场与座位号
python3 scripts/senior.py exams --ics                  # 实时考试日历内容，仅标准输出

# 10. 跨平台作业/考试 Deadline 巡检
python3 scripts/senior.py deadlines                    # 聚合巡检 Blackboard / Gradescope / Hydro / EAMS
python3 scripts/senior.py deadlines --pending-only     # 仅展示尚未完成的紧急 DDL

# 11. 体育馆余场实时看板与活动讲座打卡
python3 scripts/senior.py gym 网球                     # 查询室外网球场空闲时段与预约避坑
python3 scripts/senior.py gym 羽毛球                   # 查询室内羽毛球场余场
python3 scripts/senior.py activities                   # 查询实时签到流水与可确认的签到次数
```

---

## 🔒 隐私与数据安全承诺 (Privacy & Security)

1. **认证凭据例外**：仅登录 Cookie 保存在 `~/.config/shanghaitech-senior/session.cookie`，目录权限 `700`、文件权限 `600`。不会保存在仓库内。`senior.py logout` 可删除；失效时重新登录。
2. **个人查询结果不落盘**：课表、DDL、考场、成绩、学分与签到流水仅在内存处理；禁止本地个人快照、缓存回退与运行时 Demo。日历仅输出文本，CLI 不读写个人文件。
3. **实时且可核对**：每次标注来源与查询时间；空响应与查询失败分开报告。部分来源失败时完整状态未知，命令以非零状态退出。
4. **认证数据流透明**：登录和部分查询通过 GeekPie 的 TechPie 第三方代理转发至学校/课程平台；EAMS 计划完成表直接向学校读取。密码与验证码由用户在本机隐藏输入，不留存，也不要发给聊天助手。
5. **公共资料可本地存储**：CourseBench、公开培养方案、课程资料索引和公共校园坐标可保留；这些不代表用户本人的当前记录。

```bash
python3 scripts/senior.py auth-status --json          # 只返回 Cookie 是否存在，不联网、不弹窗
python3 scripts/senior.py login                       # 对话调用时打开终端，仅登录并保存 Cookie
python3 scripts/senior.py audit                       # 需要学分诊断时单独运行
python3 scripts/senior.py deadlines --pending-only     # 需要查看 DDL 时单独运行
python3 scripts/senior.py logout                      # 删除 Cookie
```

Gradescope 需进程环境 `GRADESCOPE_TOKEN`；Hydro 需 `HYDRO_TOKEN`、`HYDRO_DOMAINS`（逗号分隔）。独立平台凭据缺失会逐项报告，不能当作无待办。`--sync` 是兼容参数，实时联网始终开启。旧的 `--file`、`--input`、`--output` 及写入日历路径的用法已移除。

个人预约历史、提交预约及自动签到尚未提供 CLI，需通过学校对应在线应用操作。当前接口协议参考 [TechPie 上游源码](https://github.com/HeZeBang/TechPie-flutter/tree/ddaf2a95e83f116e0f48bb64013a32b7afdf8543/lib/services)；实际可用性取决于目标平台、有效会话及网络。

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
