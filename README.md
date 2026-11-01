# 🧑‍🎓 上海科技大学本科老学长智能助手 (ShanghaiTech Senior Skill)

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![ShanghaiTech](https://img.shields.io/badge/University-ShanghaiTech-red.svg)](https://www.shanghaitech.edu.cn/)
[![Courses Covered](https://img.shields.io/badge/Courses-118+-brightgreen.svg)]()
[![CourseBench Reviews](https://img.shields.io/badge/Reviews-2300+-orange.svg)]()

> **“选课不踩坑，复习有真题，作业有答案，毕业不延毕。”**  
> 专为上海科技大学（ShanghaiTech）本科生打造的**全能学业导师与通关伙伴**。融合 **CourseBench** 真实学生评价大数据、**全校 12 大本科专业官方培养方案**，以及三大开源课程资料库。

---

## 🌟 核心特性 (Features)

### 1. 🌟 选课口碑与授课风格 (CourseBench Engine)
- 覆盖全校 **1190+ 门课程**、**2300+ 条真实同学评分与文字评语**。
- 四维评分雷达：**教学质量、课业负担、考核难度、给分优劣**（5.0满分制）。
- 智能过滤：**年份近者优先**（2024/2025/2026 近期学期优先展示），自动剔除无实质分析的极端情绪化宣泄。

### 2. 📚 备考通关与资料秒级直达 (Test-Taking Engine)
全面整合三大主流上科大课程资料共享库，已为全校 **118+ 门核心课程**建立倒排索引：
- **📝 历年期中期末真题**：收录 近至2025 最新考卷回忆版、试卷原题扫描件、答案解析与名师讲解视频（如 2025 数分I、2025 普物I、2025 线代I、CS100 2025 中期含答案）。包含其他高校试卷作为参考（交大，浙大，UCB，MIT等）
- **💡 平时作业与官方解答**：各学期 Homework 题目、标准答案（Solutions）及配套测试用例包。
- **🖥️ 讲义课件与复习提纲**：官方 PPT 课件、Recitation 习题课讲义、学长手写高分思维导图。
- **🛠️ 实验与大作业代码**：学长通关仓库代码、图论/算法模板、大作业参考。

### 3. 🗺️ 全校专业官方修课路线图 (Curriculum Roadmaps)
- 完整录入 **2026 级全校 12 大本科专业官方培养方案**（SIST 计科/AI荣誉班/电子、IMS 数学/信计、SPST 物理/化学/材料、SLST 生科/生技、BME 生医工、SCA 工业设计）。
- 支持按学期（大一秋/春/夏至大四）一键推荐官方建议修课计划，并自动标注每门课的 CourseBench 口碑评分。

### 4. 🎓 EAMS 计划完成情况智能预审 (Degree Audit)
- 独家实现 **EAMS 预审“三层学分切分”**（纯已通过、在读修读中、真实待修硬性缺口）。
- **严格遵循防重复统计铁律**：严防把 EAMS 顶部已内含的在读学分做二次重复叠加，精准预警大四毕业论文（SI199 6学分）等硬性缺口。

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

---

### 模式 B：作为独立终端命令行工具使用 (Standalone CLI)

即使不借助 AI，你也可以在本地终端中直接运行老学长 CLI：

```bash
# 1. 克隆仓库
git clone https://github.com/XiongWenye/shanghaitech-senior.git
cd shanghaitech-senior

# 2. 老学长全景把脉 (口碑 + 备考真题资料包 + 避坑锦囊)
python3 scripts/senior.py ask "CS100"
python3 scripts/senior.py ask "普通物理I"
python3 scripts/senior.py ask "线代"

# 3. 仅提取备考复习资料 (真题卷、作业答案、课件讲义)
python3 scripts/senior.py materials "高等数学I"

# 4. 查指定专业的学期推荐修课计划
python3 scripts/senior.py roadmap --major 计算机 --semester 2
python3 scripts/senior.py roadmap --major 电子 --semester 1

# 5. 模糊检索课程
python3 scripts/senior.py search "体系结构"
```

---

## 🔒 隐私与数据安全承诺 (Privacy & Security)

1. **绝无账号密码留存**：本工具绝不记录或上传任何同学的统一身份认证账号与密码。
2. **纯本地离线运算**：CourseBench 口碑数据库与培养方案均完整内置于本地 `data/` 中，所有计算在同学本地完成。
3. **EAMS 预审防泄露机制**：真实学籍导出的 HTML 文件已通过 `.gitignore` 严格拦截，绝不提交至公开仓库。

---

## 🤝 致谢与开源生态 (Acknowledgements)

感谢上海科技大学活跃的开源与学生互助生态，本项目的顺利建设离不开以下前辈开源成果的滋养：
- [i-TechX / iTechX](https://github.com/i-TechX/iTechX)
- [XiongWenye / shanghaitech-course-database](https://github.com/XiongWenye/shanghaitech-course-database)
- [zsc2003 / courses-summary](https://github.com/zsc2003/courses-summary)
- 上海科技大学 CourseBench 平台全体贡献真实评课的同学们

---

## ☕ Buy me a coffee

如果你觉得本项目对你有帮助，欢迎请老学长喝杯咖啡以支持持续维护和更新！本人承诺**所有捐赠**将用于本项目维护及相关开源生态建设（如高价值历年真题/解答的**贡献者激励**）。

| 微信支付 (WeChat Pay) | 支付宝 (Alipay) |
| :---: | :---: |
| <img src="./assets/wechat.jpg" width="230" alt="微信支付收款码" /> | <img src="./assets/alipay.jpg" width="230" alt="支付宝收款码" /> |

## 📄 开源许可证 (License)

本项目基于 [MIT License](LICENSE) 开源。欢迎全校师生提交 Issue 与 Pull Request 共同完善！
