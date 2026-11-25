# 见微（Insight）V2.5

**见微（`insight`）** 是一个独立、跨宿主的研究写作与立论 Skill：帮你从专业直觉、文献和已有材料中提炼值得写的主张，把观点充分展开成清晰有力的论证，并按任务轻重自动选择**直接编辑、共同立论**或**独立红蓝审查**。英文写作与中译英时自动按需加载母语顶刊级英文学术表达层，纯中文任务零额外开销。

无需安装 `research-collab` 其余 Skills，无外部插件或 MCP 硬依赖，兼容 Codex、Claude Code、Antigravity、Cursor、DeepSeek Harness 及纯聊天会话。

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/architecture-dark.svg" />
  <source media="(prefers-color-scheme: light)" srcset="assets/architecture-light.svg" />
  <img alt="见微 Insight V2.5 架构图" src="assets/architecture-light.svg" width="100%" />
</picture>

> 本 README 面向试用者与维护者；Agent 的运行契约以 [SKILL.md](SKILL.md) 及 `references/` 为准。

---

## 适用范围与学科定位

- **主推场景**：实验科学、工程计算、定量实证社科与生物医学研究——主打**去防御保真润色、算式/方向/因果防顺从拦截、双体裁自动分流、从直觉与文献立论**。
- **人文 / 法学 / 纯数学 / 质性研究推荐模式**：推荐使用**轻量去防御编辑、双体裁交付与单题拦截**；V2.4 已内置非实验范式豁免（纯数学不强加数值实验验证、质性访谈不外推总体发生率或强补定量/干预未来方向、人文与法教义学改用文本互证与要件涵摄并允许正文辩证交锋）。
- **专项任务边界**：系统综述 / Meta 分析（如 PRISMA）须满足全面检索召回与偏倚/异质性评估，不按“近邻+反例”直接定稿；审稿回复（Rebuttal）按审稿人具体质疑正面作答。

---

## 一句话安装试用

直接复制下面这段发给你的 Agent（具备终端与文件读写权限）：

```text
insight skill 辅助科研写作与立论，从文献和直觉中探索值得发展的观点、展开成清晰有力的论证，并做论证修复与反 AI 防御性写作润色，让表达更开放、具体、少绕弯。

请从 https://github.com/Fona1347/research-collab 只安装 `skills/insight` 到当前工具的 skills 目录并验证可用（临时目录拉取、不装其他 skills 和依赖、不覆盖已有配置，遇目录选择或冲突先问我，装完告诉我怎么调用）。
```

也可以在克隆本仓库后，用内置脚本安装到任意目标 Skills 目录（Python 3.11+）：

```powershell
python scripts/skills.py install --skill insight --skills-root "<你的 skills 绝对路径>" --dry-run
python scripts/skills.py install --skill insight --skills-root "<你的 skills 绝对路径>"
python scripts/skills.py check --skill insight --skills-root "<你的 skills 绝对路径>"
```

---

## 4 大核心场景动态演示

以下演示覆盖「从直觉找观点 → 把一句话展开成完整论证 → 去掉防御腔 → 拦截并修好数据漏洞」四个高频场景，**全程输出连贯学术段落而非分块要点**：

### 场景 01 · 一个模糊直觉，变成立得住的主张
给它你的直觉和几篇文献，它先对照前作找出真正新的地方，你选定方向后它写成立论段落。

![场景 01 · 一个模糊直觉，变成立得住的主张](assets/01-idea-exploration.gif)

### 场景 02 · 一句干巴巴的话，展开成完整论证
把“可能有帮助”这类空泛表述，展开成有主张、有证据、有机理、有反例、有边界的连贯段落，同时不夸大证据强度。

![场景 02 · 一句干巴巴的话，展开成完整论证](assets/02-argument-expansion.gif)

### 场景 03 · 去掉防御腔，数字一个不动
删掉“尚存局限”“初步参考”这类客套话，原始数值和适用条件原样保留。

![场景 03 · 去掉防御腔，数字一个不动](assets/03-anti-defensive-polish.gif)

### 场景 04 · 论证有漏洞，先指出来，再帮你修好
发现数据算反或结果不显著，不用备注糊弄过去，也不擅自替你改主线；你定好方向后，它写出站得住的结果段。

![场景 04 · 论证有漏洞，先指出来，再帮你修好](assets/04-flaw-repair.gif)

> **关于内部讨论稿与正式投稿稿的分流**：面向重大投稿或复杂立论时，见微还支持先做独立的立论与挑刺、等你拍板后再动笔；需要内部审阅时，证据出处与待核对事项集中放在文末，切到正式投稿稿后则将适用边界自然融入正文，不留任何内部标记或 AI 局限八股（完整路由见顶部架构图）。

---

## 典型用法

调用方式随宿主而异（例如 Codex 使用 `$insight`，其他宿主直接提及 `insight` 或描述写作任务即可）：

- **轻量编辑（直出，不打扰）**
  > 用 `insight` 润色下面这段讨论（目标是英文顶刊投稿），去掉防御性套话，但保持原来的证据强度和适用条件。
- **共同立论（直觉 + 文献，一次只问一个关键取舍）**
  > 用 `insight` 帮我从这几篇文献里提炼一个研究展望主张：我怀疑瓶颈在界面耦合而不是材料本身，先对照最接近的前作再给候选方向。
- **独立红蓝审查（隔离上下文 + 人工拍板 + 脱敏一次成稿）**
  > 用 `insight` 走完整红蓝审查写一篇面向基金评审的立项依据，所有材料在下方，先出论点和审计结果让我拍板再成稿。

---

## 模块与文件地图

按需加载设计，普通润色不会把整套红蓝协议塞进上下文：

| 模块 | 文件 | 何时加载 | 职责 |
| --- | --- | --- | --- |
| 入口分流 | [SKILL.md](SKILL.md) | 始终加载 | 按改动范围、主张成熟度、实质分歧决定工作量，含非实验范式豁免 |
| 表达与体裁 | [references/expression.md](references/expression.md) | 所有路线 | 按句子功能校准中英文表达、算式/方向复核、区分内部审阅与正式投稿体裁 |
| 英文学术表达 | [references/english-prose.md](references/english-prose.md) | 交付含英文时 | 英文编辑深度、信息流、证据强度动词、防译文腔与 6 学科期刊语体（纯中文任务不加载） |
| 发现与论证 | [references/argument.md](references/argument.md) | 扩写 / 修复 / 立论 | 直觉具体化、跨学科范式校准、连接理由、段落展开与紧缩候选交付 |
| 文献立论 | [references/literature.md](references/literature.md) | 文献找观点 / 展望 | 对照最接近前作、识别推断增量、无检索防幻觉门禁与 PRISMA 边界 |
| 主线程协调 | [references/coordination.md](references/coordination.md) | 立论 / 分歧 / 审查 | 维护有效决定、待答事项、压缩稳健性与版本边界 |
| 单项决策 | [references/decision-interaction.md](references/decision-interaction.md) | 确需用户拍板时 | 一次一题、推荐优先，自动适配宿主原生问答或纯聊天 |
| 完整审查协议 | [references/protocol.md](references/protocol.md) | 完整红蓝路线 | 独立蓝方 / 红方（P0–P2）/ 人工关卡 / 隔离成稿 / 表达强度有限核查 |
| 方法来源 | [references/sources.md](references/sources.md) | 维护或询问依据时 | 上游方法借鉴与取舍说明 |
