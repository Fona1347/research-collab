# 中文快速使用指南

这个 Skill 将宽泛领域、已选方向、关键证据或既有 run，转化为可验证、可执行、可追溯的科研决策。它不是“热门方向生成器”，也不把检索未命中当成首创证明。

## Contents（目录）

- [核心逻辑](#核心逻辑)
- [先选模式、发现视角和领域 lens](#先选模式发现视角和领域-lens)
- [配置预检与用户确认](#配置预检与用户确认)
- [直接用自然语言调用](#直接用自然语言调用)
- [初始化 schema 2 run](#初始化-schema-2-run)
- [创建父子 run](#创建父子-run)
- [各模式产物差异](#各模式产物差异)
- [证据可信度怎么用](#证据可信度怎么用)
- [领域 lens 与本地能力画像](#领域-lens-与本地能力画像)
- [执行与验证](#执行与验证)
- [什么时候路由给其他工作流](#什么时候路由给其他工作流)
- [常见错误](#常见错误)

## 核心逻辑

所有模式都保留同一个交集：

`持久性瓶颈 × 可证伪的因果/物理机制 × 可迁移能力 × 有边界证据支持的开放位置`

同时遵守：

- 先定义决策、状态、机制、指标、预算和边界，再搜索候选路线；
- 分开写 `Evidence`、`Inference` 和 `Recommendation`；
- 顶刊、近期热点和高被引只用于前沿态势感知，不能直接提升科学可信度；
- 没搜到只能说明当前检索没有命中，不能推出“无人研究”或“首创”；
- 材料/器件 proxy 不得未经中间验证直接外推到阵列、IC 或 workload；
- `Reported / Assumed / Unknown` 能力不得写成 `Observed`。

## 先选模式、发现视角和领域 lens

### 四种正式模式

| 模式 | 什么时候用 | 核心结果 | 不应强制 |
|---|---|---|---|
| `landscape` | 领域很宽，需要比较方向和建立组合 | 广域地图、范围相称的 breadth gate、0/1/若干条实质路线 | 不应提前锁定一个材料或器件。 |
| `focus` | 已选一个 branch、机制接口或候选路线 | 选定接口的路线论证、比较/退路设计、阶段门和结果解释 | 不强制低/中/高三条路线，也不重做全领域 breadth。 |
| `evidence-audit` | 要补证、审查关键论文或判断主张可信度 | 逐 claim 可信度、允许表述、缺口和升级/推翻条件 | 不给论文整体打分，不静默改父 run。 |
| `run-audit` | 要审查一个已有 run 或报告 | 完整性与对抗审计、`Keep / Downgrade / Revise / Kill` | 不把风险清单当作完成，不修改父 run。 |

`auto` 只表示“请 Skill 帮我路由”。它不是正式模式，也不能写入最终 `task_mode`。路由完成后必须落到上面四种模式之一。

### 三种正交发现视角

| Lens | 入口 | 必须补上的约束 |
|---|---|---|
| `frontier-led` | 近期权威综述、roadmap、代表性顶级期刊/会议和原始研究 | 补经典定义、直接近邻、负面/限制证据和强基线；热度不等于可信度。 |
| `gray-space-led` | 需求—原语、机制—操作、材料—读出、器件—系统等 mismatch | 两侧正证据、最近邻和有边界缺口；零命中不等于空白。 |
| `balanced` | 独立建立 frontier radar 与 mismatch ledger 后合并 | 默认选择；同时做确认与证伪。 |

模式回答“要产出什么”，discovery lens 回答“从哪里发现候选”，domain
lens 回答“用哪些状态变量、混淆因素、跨层桥和基线来审查”。三者正交：
每个 run 持久化一个正式模式、一个 discovery lens、一个主 domain lens，
并只在真实接口增加次级 domain lens。

## 配置预检与用户确认

当用户调用 Skill 执行科研决策，但没有明确确认全部配置轴时，先根据当前
请求、上下文、已知需求、条件、边界、能力状态、决策期限和大致方向给出一次
简短配置预检。此时先不检索、不初始化 run、不创建文件。

`auto` 只能写成 `requested_mode=auto`。预检同时给出预计解析到的正式模式，
不能推荐或持久化 `task_mode=auto`。

例如，用户已有“铁电动态畴用于片上在线学习、三个月概念验证”的明确方向时：

```text
【配置建议】

- requested_mode：auto
- 预计 task_mode：focus
  原因：已有明确方向，需要形成可执行的局部路线和决定性实验。
- discovery_lens：balanced
  原因：需要同时检查近期前沿与器件—算法—系统之间的未闭合接口。
- primary_domain_lens：materials-ferroelectric
  原因：核心状态变量、机制与混杂因素来自铁电材料和畴动力学。
- secondary_domain_lens：neuromorphic-system
  原因：在线学习价值需要跨到系统层并接受同预算基线审查。
- routing_confidence：high

【是否采用以上配置？】
请回复：
```

预期用户回复：

```text
是
```

用户也可以覆盖其中一项：

```text
否；改为 discovery_lens=gray-space-led
```

用户确认后再执行研究。若用户已经明确给出并确认全部适用配置，或明确要求
“直接执行/无需确认”，可跳过暂停。配置确认不等于授权读取未声明的本地资料、
访问外部系统或替用户选择未指定的持久化输出路径。

## 直接用自然语言调用

### 自动路由

```text
使用 $research-opportunity-mapper 处理下面的科研决策：
【自然语言描述任务】。

请先判断正式模式是 landscape、focus、evidence-audit 还是 run-audit，
再独立选择 frontier-led、gray-space-led 或 balanced。auto 只作为请求状态，
不要持久化。再选择并持久化一个主 domain lens；专用 lens 不适用时用
generic-physical-engineering，只有完整填写十项 Common Lens Interface 时才用
custom。先显示配置建议、每项的一句理由和路由置信度，并询问
“是否采用以上配置”；等待用户确认后再初始化 run，并按对应模式完成报告和
审计底稿。
```

### 广域地图

```text
调研“可重构铁电计算硬件”，用于选择博士课题和一年平台路线。
使用 landscape + balanced。先比较瓶颈、状态操作和机制家族，不要从偏好的
材料开始；使用 materials-ferroelectric 主 domain lens。最后保留有证据的实质
路线，允许为零、一或若干条，不为风险分档凑数，并让每条路线拥有自己的执行行、正/负/歧义结果和停止条件。
```

### 聚焦深挖

```text
把“PTO/STO 相边界状态到 FTJ 电学读出”作为已有 branch 深挖。
使用 focus + gray-space-led。允许零、一或若干条实质候选；有候选时给一条主路线，
保留最强比较设计、fallback、强基线、替代机制和阶段门，不为补角色另造C-ID。
各实际候选拥有执行行和正/负/歧义结果；若全淘汰，给有界停止理由及下一项信息核查。
```

### 补全证据链

```text
对【父 run 或报告】中的【B-### / M-### / S-### / CL-### 关键主张】补全证据链。
使用 evidence-audit + balanced。检索直接支持、限制/反例、独立复现、
最强基线和相邻工作，逐 claim 给 High / Moderate / Low / Insufficient、
硬上限原因、允许表述和升级/推翻条件。父 run 只读；如判断变化，在子 run
中给 Keep / Downgrade / Revise / Kill。每条 Evidence 记录必须列出已有
Claim IDs 和一个 stance；supports 进入支持列表，limits/contradicts 进入限制
列表；mixed 可同时链接两侧，但其限制成分仍约束硬上限和允许表述；context
不得用于抬高可信度。
```

### 审计已有 run

```text
审计【已有 run 路径】，使用 run-audit + balanced。不要重写父 run，也不要
只列风险。检查 lineage、跨文件 ID/引用、证据上限、开放位置、因果机制、
能力夸大、proxy 到系统的跳跃、基线公平性和主报告一致性；每个关键问题给
Keep / Downgrade / Revise / Kill 及修复动作。检查八个精确攻击面，并拒绝
把 wrong-role 文件、正文、注释、代码块或 reader table 中的 ID 当成权威定义。
```

更多可复制提示词见 [prompt-library.md](prompt-library.md)。

## 初始化 schema 2 run

在 Skill 目录中执行。下面命令创建 `landscape + balanced` 的 schema 2 run：

```powershell
python scripts/init_run.py `
  --domain "可重构铁电计算硬件" `
  --short-task-name "reconfigurable-ferroelectric-hardware" `
  --mode landscape `
  --lens balanced `
  --domain-lens materials-ferroelectric `
  --language zh-CN `
  --evidence-window "2023:2026" `
  --as-of-date "2026-07-31" `
  --output "<research-workspace>\runs"
```

初始化器会选择相应模式和语言的 artifact profile，并生成 schema 2 manifest。具体产物、字段、ID 和兼容规则以 [schemas.md](schemas.md) 为准，不要从本指南复制旧的固定文件假设。

### 从自然语言 `auto` 路由后初始化

`--requested-mode auto` 用于记录原始请求；`--mode` 必须是已经解析出的正式模式：

```powershell
python scripts/init_run.py `
  --domain "可调超表面研究机会" `
  --short-task-name "tunable-metasurface" `
  --requested-mode auto `
  --mode landscape `
  --lens frontier-led `
  --domain-lens wave-metasurface `
  --request "从近年前沿出发建立广域地图" `
  --routing-reason "尚未选择具体机制或 branch" `
  --routing-confidence high `
  --language zh-CN `
  --output "<research-workspace>\runs"
```

不要尝试 `--mode auto`；初始化器会拒绝它。

测试或回放需要确定性时间时，可显式传入 `--date` 和 `--created-at`。普通运行让脚本生成当前时间即可。

## 创建父子 run

父 run 始终只读。子 run 保存父 run 的标识、快照和继承关系；不要靠绝对路径作为唯一 lineage。相关规则见 [schemas.md](schemas.md) 和 [run-modes.md](run-modes.md)。

### 从 landscape branch 创建 focus 子 run

```powershell
python scripts/init_run.py `
  --domain "PTO/STO 相边界到 FTJ 读出" `
  --short-task-name "pto-sto-ftj-focus" `
  --mode focus `
  --lens gray-space-led `
  --domain-lens materials-ferroelectric `
  --parent-run "<research-workspace>\runs\父run目录" `
  --workspace-root "<research-workspace>" `
  --selected-branch "BR-003" `
  --inherit-claim "M-004" `
  --inherit-evidence "E-017" `
  --language zh-CN `
  --output "<research-workspace>\runs"
```

如果父 run 不包含所选 branch，或 lineage 无法核验，初始化/验证应失败或明确标为未解析，而不是伪造继承。

### 为父 run 创建 evidence-audit 子 run

```powershell
python scripts/init_run.py `
  --domain "关键机制主张补证" `
  --short-task-name "mechanism-evidence-audit" `
  --mode evidence-audit `
  --lens balanced `
  --domain-lens generic-physical-engineering `
  --parent-run "<research-workspace>\runs\父run目录" `
  --workspace-root "<research-workspace>" `
  --inherit-claim "M-004" `
  --inherit-evidence "E-017" `
  --language zh-CN `
  --output "<research-workspace>\runs"
```

没有父 run 时，evidence-audit 至少需要一个明确的只读 context source 或 capability profile，并在 intake 中定义要审查的原子主张。

### 为父 run 创建 run-audit 子 run

```powershell
python scripts/init_run.py `
  --domain "既有科研地图对抗审计" `
  --short-task-name "existing-run-audit" `
  --mode run-audit `
  --lens balanced `
  --domain-lens generic-physical-engineering `
  --parent-run "<research-workspace>\runs\父run目录" `
  --workspace-root "<research-workspace>" `
  --language zh-CN `
  --output "<research-workspace>\runs"
```

`run-audit` 必须有父 run；审计结果写入子 run，不原地修改审计对象。
初始化后先生成父 run 的机器真值投影：

```powershell
python scripts/parent_audit.py "<research-workspace>\runs\父run目录"
```

将输出中的 `artifact_projection`、`manifest_projection`、`id_projection`
和 `citation_projection` 完整写入子 run 对应表格。validator 会重新计算并逐行比较。
`citation_projection` 审的是父报告引用，不是审计报告自己的参考文献。父 run
即使缺文件也可被审计，但初始化后发生增删改会使快照失效；任何机器发现的
完整性失败都必须进入 `Downgrade / Revise / Kill` 决策。Schema 2 的 ID
只有在 manifest 声明的权威 artifact role 中、紧随注册 marker 的第一张表、
精确 ID 列里才算定义；其他位置出现同形字符串不能修复 dangling ID。

## 各模式产物差异

所有模式都提供“人读主报告 + 可审计工作层”，但工作层的角色和完成门不同：

- `landscape` 保存广域 breadth、映射和三风险组合；
- `focus` 保存局部替代图、claim—mechanism 图、主协议、比较路线和 fallback；
- `evidence-audit` 保存 claim register、证据角色、可信度裁决、矛盾和补证计划；
- `run-audit` 保存 lineage/完整性、证据/机制/能力/跨层攻击及决策处置。

不要假定四种模式必须拥有同样的正文标题、路线数量或 breadth 计数。权威产物合同见 [schemas.md](schemas.md)，权威模式完成门见 [run-modes.md](run-modes.md)。

## 证据可信度怎么用

可信度评估的是**原子主张**，不是论文整体：

```text
Claim + scope/regime
→ 支持与限制证据
→ 直接性和全文核验
→ 方法能否回答该 claim
→ 独立性/复现、一致性和适用性
→ High / Moderate / Low / Insufficient
→ 硬上限原因
→ 当前允许表述
→ 升级或推翻条件
```

Evidence 的 `Claim IDs` 是机器关系，不是主题标签。每个 ID 必须已有权威
原子 claim 定义；同一行的 stance 对所有列出的 claims 必须一致。若一篇论文
支持 M-001 但限制 S-001，应拆成两条 Evidence 记录。允许的 stance 为：

- `supports`：进入该 claim 的 Supporting Evidence IDs；
- `limits`、`contradicts`：进入 Limiting Evidence IDs；
- `mixed`：可同时进入 Supporting 与 Limiting Evidence IDs，但不能当作无保留
  支持，限制成分仍约束 confidence cap 和允许表述；
- `context`：只作定义、背景或 frontier salience，不能进入支持/限制列表。

几个重要上限：

- 关键支持只有 metadata、摘要或未核验上下文：不能标 `High`；
- 全部是间接证据或跨越未验证 proxy：最多 `Low`；
- 有未解决的直接冲突：最多 `Moderate`；
- 单篇强论文可支持边界很窄的存在性结论，但不能自动证明普适机制、泛化或系统优势；
- 引用信号无法核验时写 `unavailable`，不能估算。

完整规则见 [evidence-confidence.md](evidence-confidence.md)。

## 领域 lens 与本地能力画像

按需加载 [domain-lenses.md](domain-lenses.md) 中的一个主 lens 和必要的次级 lens：

- `generic-physical-engineering`
- `custom`（必须在 `domain_lens_notes` 完整填写十项 Common Lens Interface）
- `materials-ferroelectric`
- `multiphysics-modeling`
- `semiconductor-device`
- `integrated-circuit`
- `neuromorphic-system`
- `wave-metasurface`

把主 lens、去重后的次级 lens 和 custom notes 写入 manifest；不要只在提示词
里口头选择。更换 domain lens 会改变混淆因素、基线和跨层合同，应作为显式
revision，而不是静默切换。

每次跨层都要标出最后直接验证层和下一缺失桥。例如：相场结果不能自动变成器件结果，单器件不能自动变成阵列/IC 结果，周期 unit-cell 全波仿真不能自动变成有限口径实测性能。

如果使用 `profiles/local-capability-profile.md`，把它当作有日期的 intake prior，而不是科学证据。运行时重新确认软件、样品、工艺、仪器、合作与时间条件。

## 执行与验证

推荐顺序：

1. 路由正式 mode、discovery lens，并选择主/次 domain lenses。
2. 初始化对应 schema 2 artifact profile。
3. 填写决策、能力与边界，不先提出偏好方向。
4. 定义状态、机制、指标、预算和最后已验证层。
5. 按 mode × lens 设计检索和 claim register。
6. 完成证据、因果图、模式分支和可改变决策的红队。八个攻击面全部保留，
   每条攻击进入人读 impact 表；每个非 Keep 攻击必须改变受影响主决策，
   同一目标采用最强处置：Kill > Revise > Downgrade > Keep。
7. 综合面向读者的报告，不拼接内部文件。
8. 严格验证：

```powershell
python scripts/validate_run.py "<research-workspace>\runs\目标run" --strict
```

验证通过表示结构、引用和合同一致性满足检查，不表示科学结论绝对正确、方向绝对首创或实验必然成功。

交付时先给人读主报告，再把工作层作为审计入口。主报告至少要讲清楚：是什么、为什么必要且及时、需要了解什么、SOTA 各类方法为什么仍没解决瓶颈、推荐怎么做、正/负/歧义结果分别能说明什么、什么条件会降级或停止。

## 什么时候路由给其他工作流

- 用户主要要系统综述、PRISMA 或穷尽式筛选：路由 `literature-review`；
- 用户主要要精读一篇或少数论文的图、表、方法与公式：路由 `paper-deep-reading`；
- 路线已选定，需要随机化、分组、阻断、对照和测量计划：路由 `experimental-design`；
- endpoint、效应、方差、层级和设计已经稳定，需要样本量/功效：路由 `statistical-power`。

这些工作流的结果可以回到父 `focus` 或 `evidence-audit`，但必须保留来源、假设和 handoff，不用一段不可追溯的总结替代。详见 [orchestration.md](orchestration.md)。

## 常见错误

- 把 `auto` 写成持久模式，而不是先路由再初始化；
- 让 focus 或 audit 通过 landscape 的低/中/高组合门；
- 用顶刊、高被引或近期性替代 claim-level 可信度；
- 因为精确查询零命中就写“空白”或“首创”；
- 只有模拟或 proxy，却在主报告写成真实器件、阵列或系统收益；
- 把学习、计划或可能获得的合作能力写成已经成熟；
- 红队漏掉八个攻击面之一，或只增加风险文字而没有把非 Keep 处置传播到主决策；
- evidence-audit 或 run-audit 直接改写父 run；
- 在错误 artifact role、正文或 reader 表里重复一个 ID，并把它当作权威定义；
- 仿生工作使用“大脑更好，所以硬件复刻更好”的先验，或把数学 state update
  与算法合并，缺少去生物标签问题、同预算非仿生强基线和原则特异性消融；
- 生物前提已经触发审查，却把整条 bio translation 写成 `not applicable`。
