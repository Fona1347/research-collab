> Component manual. The collection's docs/maintenance.md supersedes the old standalone publish/validate scripts.

# Research Lookup Enhanced：快速上手

<p align="center">
  <a href="QUICKSTART.md">English</a> |
  <a href="QUICKSTART.zh-CN.md">简体中文</a> |
  <a href="README.zh-CN.md">技术 README</a>
</p>

<!-- 请与 QUICKSTART.md 同步维护。 -->

这是一份面向人类用户的使用教程。把任意 `text` 代码块原样复制到 Codex/ChatGPT 的输入框即可；`$research-lookup-enhanced` 用于明确指定本地 Skill。除非提示词明确要求写入证据包，否则结果可以直接返回对话。

## 目录

- [30 秒开始](#30-秒开始)
- [第一次使用：确认 Skill 与数据源](#第一次使用确认-skill-与数据源)
- [一条好提示词的最短结构](#一条好提示词的最短结构)
- [A. 发现与核验论文](#a-发现与核验论文)
- [B. 限定范围与提高覆盖](#b-限定范围与提高覆盖)
- [C. 全文、证据与写作产物](#c-全文证据与写作产物)
- [D. 引用关系、相似推荐与 SPECTER2](#d-引用关系相似推荐与-specter2)
- [E. 批量检索与审计](#e-批量检索与审计)
- [直接使用 CLI](#直接使用-cli)
- [如何阅读证据包](#如何阅读证据包)
- [能力边界](#能力边界)

## 30 秒开始

最短可用调用只有一句：

```text
用 $research-lookup-enhanced 调研「CRISPR 碱基编辑治疗镰状细胞病」。
```

未指定等级时，Agent 会为普通科研问题选择 `standard`。如果你想保留完整检索过程和机器可读结果：

```text
用 $research-lookup-enhanced 对「CRISPR 碱基编辑治疗镰状细胞病」做 standard 调研，生成可追溯证据包，并保存到本项目的 artifacts/quickstart-scd。
```

你通常会得到规范化参考文献、数据源 provenance、检索覆盖、字段冲突、排序理由和 search ledger；只有明确要求且满足 OA/安全门时才处理全文。

## 第一次使用：确认 Skill 与数据源

### 1. 检查本地 Skill

如果 Skill 已发布到工作区，直接在输入框中测试：

```text
请用 $research-lookup-enhanced 简短说明它适用于哪些科研检索任务，以及哪些任务不应调用它；不要发起网络请求。
```

Skill 只适用于科研主题、研究问题、论文/标识符检索和学术证据整理。新闻、商品、通用网页和代码检索不属于它的范围。

### 2. 检查数据源配置

```text
用 $research-lookup-enhanced 检查当前数据源配置状态；只显示 configured 或 not configured，不显示任何密钥，也不要执行论文检索。
```

本地 CLI 等价命令：

```powershell
.\.venv\Scripts\python.exe `
  .\skills\research-lookup-enhanced\scripts\research_lookup.py `
  --show-provider-status
```

| 数据源 | 最少配置 | 主要用途 |
|---|---|---|
| Crossref | 无 | DOI 与出版元数据 |
| Europe PMC | 无 | 生物医学、PMID/PMCID、JATS、引用关系 |
| OpenAlex | `OPENALEX_API_KEY` | 跨学科发现、标识符、引用关系 |
| Semantic Scholar | `SEMANTIC_SCHOLAR_API_KEY` | 语义元数据、引用关系、seed 推荐 |
| Unpaywall | `UNPAYWALL_EMAIL` | DOI 对应的合法 OA 地址 |
| Easy Scholar | `EASYSCHOLAR_SECRET_KEY` | 可选 venue 指标增强 |
| MinerU | `MINERU_API_KEY` 加显式远程授权 | 仅处理已确认 OA 的 PDF |

程序读取环境变量，不会自动加载 `.env`。状态为 `configured` 只表示变量非空，不代表 key、配额或账户权限已经通过实时验证。不要在提示词、命令参数、Markdown 或 Git 中粘贴真实密钥。

### 3. 从源码运行时创建虚拟环境

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

`pip install -e .` 安装开发依赖和项目 metadata，不会创建全局 CLI；仍应按源码路径调用 `research_lookup.py`。需要更好的本地 HTML 或 PDF fallback 时，再安装 `.[html]` 或 `.[markitdown]`。

### 4. 一次完成离线预检

```text
用 $research-lookup-enhanced 为「柔性铁电器件用于非易失存储」做运行前预检：检查 provider 环境变量是否配置、当前 Python/虚拟环境、本地 HTML/MarkItDown/pypdf 依赖和输出目录 artifacts/preflight 是否已存在或非空；再生成 query plan。不要发起学术 API 请求，不显示密钥，也不要创建、删除或覆盖文件。
```

这条提示词验证本地准备情况，但不会证明 key、配额或远端账户可用。实时健康检查必须由用户另行明确要求，并继续遵守各数据源限速。

## 一条好提示词的最短结构

可以把所有常见请求压缩成这个“十字交叉”模板：

```text
用 $research-lookup-enhanced，[quick / standard / deep]：
[科研问题、主题或 DOI/PMID/PMCID/arXiv 标识符]；
[日期、领域、论文类型、OA、数量等约束]；
[需要的输出：简短列表 / 引用邻域 / 证据包 / 全文摘录]；
[安全边界：是否允许远程解析或模型下载]。
```

真正最短的形式仍然是：

```text
用 $research-lookup-enhanced 查「你的科研问题」。
```

### 如何选择调研等级

| 等级 | 什么时候用 | 自然语言关键词 | 不会自动做什么 |
|---|---|---|---|
| `quick` | 已知论文、少量核心文献、快速核验 | “快速”“找几篇”“核验这个 DOI” | 不默认全文，不默认 Easy Scholar |
| `standard` | 普通科研问题、多源证据检索 | “调研”“查找相关证据” | 不会自动变成系统综述 |
| `deep` | 更广覆盖、更多 fallback、复杂证据整理 | “全面检索”“深度调研”“追踪引用” | 不自动解析全文、上传 PDF、选 seed 或下载模型 |

独立 CLI 的 `auto` 是显式选项，用确定性本地规则逐条判断。通过 Agent 使用时，直接在自然语言里说明深度更清晰；不确定时使用 `standard`。

## A. 发现与核验论文

### A1. 快速找少量核心论文

适合刚进入一个主题，先获得可读的入口文献。

```text
用 $research-lookup-enhanced，quick：找出「柔性压力传感器用于步态监测」最相关的 10 篇核心论文；保留 DOI 或 PMID，简要说明每篇为什么相关。
```

边界：`target references` 是覆盖目标，不保证恰好输出该数量；数据源返回不足时不会用低质量记录凑数。

### A2. 对一个科研问题做标准调研

```text
用 $research-lookup-enhanced，standard：调研「二维铁电材料中的极化涡旋如何影响非易失存储器件」；多源检索、去重并解释排序，给出可追溯参考文献。
```

如果需要文件产物，直接补充输出位置：

```text
用 $research-lookup-enhanced，standard：调研「二维铁电材料中的极化涡旋如何影响非易失存储器件」；把证据包保存到本项目的 artifacts/polar-vortex-memory。
```

### A3. 核验 DOI、PMID、PMCID 或 arXiv 论文

```text
用 $research-lookup-enhanced，quick：核验 DOI:10.1038/s41586-020-2649-2 的题名、作者、期刊、发表日期、稳定标识符和 OA 状态；保留不同数据源的字段冲突。
```

最短形式：

```text
用 $research-lookup-enhanced 查 DOI:10.1038/s41586-020-2649-2。
```

“已找到元数据”不代表“已阅读全文”。要求输出时应保留 `identifier-verified`、`abstract-verified` 或 `full-text-extracted` 等验证状态。

### A4. 只找合法开放获取地址

```text
用 $research-lookup-enhanced 查找 DOI:10.1038/s41586-020-2649-2 的合法开放获取版本；逐条说明 OA 地址来自哪个数据源，不使用未标记为 OA 的下载来源。
```

Unpaywall 只根据 DOI 做 OA 定位，不参与主题发现或相关性排序。

## B. 限定范围与提高覆盖

### B1. 日期、学科、论文类型和 OA 过滤

```text
用 $research-lookup-enhanced，standard：查找 2022-01-01 之后关于「single-cell spatial transcriptomics benchmarking」的 Biology 论文；优先原始研究与综述，在数据源支持时请求开放获取过滤，并在结果中说明哪些约束不是全局硬过滤；生成 coverage 报告。
```

过滤条件会映射到支持它的数据源；无法可靠映射的领域名称只作为排序上下文，不会伪装成数据源过滤器。

### B2. 最低引用量只作为辅助过滤

```text
用 $research-lookup-enhanced 查找「solid-state battery interface stability」中至少被引用 20 次的论文；引用量只用于筛选和低权重辅助排序，不要把高引用量称为高证据质量。
```

不同数据源的引用量不直接可比，结果中会分别保留。

### B3. 深度覆盖

```text
用 $research-lookup-enhanced，deep：全面检索「CRISPR base editing 的 off-target effects in hematopoietic stem cells」；扩大多源覆盖和 fallback，报告未覆盖问题与数据源故障；不要自动解析全文或上传 PDF。
```

`deep` 增加预算、结果上限和 fallback 空间，但不授予全文或远程处理权限。

### B4. 查找支持、反对与不显著结果

```text
用 $research-lookup-enhanced，deep：查找「经颅交流电刺激改善工作记忆」的支持结果、反对结果、不显著结果和失败研究；逐条区分原文证据、摘要证据与推断，不要把候选模式称为科学共识。
```

这能帮助整理矛盾信号，但不是自动化系统综述、风险偏倚评估或最终共识判断。
## C. 全文、证据与写作产物

### C1. 只处理开放获取全文，并保持本地解析

```text
用 $research-lookup-enhanced，standard：检索「single-cell spatial transcriptomics 的 benchmark 方法」；只解析明确开放获取的全文，提取方法、关键结果、限制和带定位符的摘录；仅使用本地解析器，不上传到远程服务；把证据包保存到本项目的 artifacts/spatial-benchmark-fulltext。
```

全文抽取要求证据包目录，用来保存原文件、哈希和 parser ledger。HTML/JATS 在本地解析；OA PDF 会尝试已安装的 MarkItDown，最后回退到低结构保真的 `pypdf`。

### C2. 明确允许 MinerU 远程解析

只有你接受 OA PDF 被上传到远程服务时，才复制下面的提示词：

```text
用 $research-lookup-enhanced 解析「柔性铁电器件」的开放获取全文。我明确允许把已确认开放获取的 PDF 上传到 MinerU 远程解析服务；记录每次解析尝试、输出和降级原因；把结果保存到本项目的 artifacts/ferroelectric-mineru。
```

这段明确授权应映射为 `--extract-fulltext --allow-remote-parser`。`deep`、`auto`、reason 文本或仅配置 `MINERU_API_KEY` 都不能代替上传授权。

### C3. 为论文写作生成证据包

```text
用 $research-lookup-enhanced，standard：围绕「柔性铁电器件用于非易失存储」生成论文写作证据包；分别整理 Introduction、Methods rationale 和 Discussion 可用的来源，输出 BibTeX、证据矩阵、coverage 和 claim-source 对应关系；不要把外部文献写成我的实验 Results。
```

如果希望审计每句话的证据等级：

```text
用 $research-lookup-enhanced 检索「研究问题」，并把所有候选陈述标成 full-text evidence、abstract evidence、metadata 或 inference；每条保留 reference ID 与 locator。
```

确定性报告负责组织来源证据，不自动推断共识、因果关系或临床建议。

## D. 引用关系、相似推荐与 SPECTER2

### D0. 先记住两个方向

```text
前向引用：后来的论文 -> 引用了 -> seed 论文
后向参考文献：seed 论文 -> 引用了 -> 更早的论文
```

当前 `--citation-seed` 会在有能力且仍有预算的数据源上同时尝试这两个方向。每个方向是有界、单页、单跳获取，不保证穷尽全部引用，也不会递归生成完整引文网络。不要依据结果 envelope 顶层的 `citations` 列表判断方向；应读取每条记录的 citation/reference facet 和 search ledger。

### D1. 获取双向引用邻域

```text
用 $research-lookup-enhanced 以 DOI:10.1002/adma.202522292 为 seed，同时检索前向引用和后向参考文献；严格分成两组，保留每条记录的数据源和 citation/reference facet；不要把相似推荐当成引用关系。
```

图扩展使用发现阶段剩余的路由预算。预算不足或数据源不可用时，应读取 `search-ledger.json` 中的跳过原因，而不是把空结果写成“全球没有引用”。

### D2. 最终只展示一个方向

```text
用 $research-lookup-enhanced 以 DOI:10.1002/adma.202522292 为 seed；最终只展示后来引用它的论文，也就是前向引用，并说明检索日期、数据源和未检出边界。
```

```text
用 $research-lookup-enhanced 以 DOI:10.1002/adma.202522292 为 seed；最终只展示它引用的论文，也就是后向参考文献，并按研究主题分组。
```

注意：CLI 目前没有 citations-only 或 references-only 参数。即使最终只展示一组，底层 `--citation-seed` 仍可能请求两个方向；“只展示”是呈现层过滤，不代表减少了数据源调用。

### D3. 用相关/不相关 seed 找相似论文

```text
用 $research-lookup-enhanced 研究「freestanding ferroelectric vortex devices」；以 DOI:10.1002/adma.202522292 作为相关 seed、DOI:10.1038/s41586-020-2649-2 作为不相关 seed，查找相似论文；把 Semantic Scholar 推荐结果与真实引用关系分开，并保留推荐顺序。
```

该能力依赖已配置的 Semantic Scholar。推荐顺序表示 provider ranking，不是 citation edge，也没有可伪造的原生数值相关性分数。

### D4. 用本地已有 SPECTER2 辅助重排

```text
用 $research-lookup-enhanced 检索「目标主题」，并使用本地已经存在的 SPECTER2 模型对候选论文做语义相似度辅助重排；如果模型或依赖缺失，不要下载，记录错误并回退到默认可解释排序。
```

SPECTER2 在当前实现中是低权重排序信号，不会自动做向量聚类、主题命名或引用图构建。只有你明确接受模型与依赖下载时，才授权 `--allow-model-download`。

### D5. 根据已验证关系画图

```text
用 $research-lookup-enhanced 以 DOI:10.1002/adma.202522292 为 seed 获取引用邻域，然后画 Mermaid 关系图：真实引用边用实线箭头，Semantic Scholar 推荐或 SPECTER2 相似关系用虚线；图例中明确区分前向引用、后向参考文献和语义相似，不要把人工分组称为向量聚类。
```

Skill 当前返回论文记录及 citation/reference facet，不直接产出独立 edge-list 或图文件。图的布局和主题标签属于后续呈现层，必须保留关系类型和证据来源。

## E. 批量检索与审计

### E1. 先看计划，不联网

```text
用 $research-lookup-enhanced 只生成「柔性石墨烯传感器用于帕金森病步态监测」的检索计划，不发起任何学术 API 请求；展示原始问题、研究等级、查询变体、provider route、过滤条件和预算。
```

这对应 `--show-query-plan`，适合在消耗配额前检查自然语言是否被正确解释。

### E2. 批量处理多个科研问题

```text
用 $research-lookup-enhanced 分别处理以下问题；每条独立选择 research level、独立计算预算并生成独立 coverage，不共享上一条的配置：
1. 柔性压力传感器用于步态监测
2. CRISPR base editing 的 off-target effects
3. 单细胞空间转录组 benchmark 方法
```

batch 中 Provider client 和缓存可以共享，但每条查询的 `EffectiveRunConfig` 必须独立。

### E3. 审计为什么结果少

```text
用 $research-lookup-enhanced 审计这次检索为什么结果不足：检查 provider 配置、查询变体、过滤条件、全局/数据源预算、stable identifier 覆盖率、fallback 触发和 search ledger；不要凭结果数量猜测原因。
```

### E4. 审计全文为什么降级

```text
用 $research-lookup-enhanced 解释这次全文处理为什么降级；读取 extraction-ledger.json 和逐文档 parser-ledger.json，列出 OA gate、远程授权、缺失依赖、解析错误与实际选中解析器。
```

## 直接使用 CLI

以下命令均从项目根目录运行。

### 查看帮助与配置

```powershell
.\.venv\Scripts\python.exe `
  .\skills\research-lookup-enhanced\scripts\research_lookup.py --help

.\.venv\Scripts\python.exe `
  .\skills\research-lookup-enhanced\scripts\research_lookup.py `
  --show-provider-status
```

### 离线预览计划

```powershell
.\.venv\Scripts\python.exe `
  .\skills\research-lookup-enhanced\scripts\research_lookup.py `
  "柔性石墨烯传感器用于帕金森病步态监测" `
  --research-level standard `
  --show-query-plan
```

### 标准检索并写出证据包

```powershell
.\.venv\Scripts\python.exe `
  .\skills\research-lookup-enhanced\scripts\research_lookup.py `
  "CRISPR base editing for sickle cell disease" `
  --research-level standard `
  --after-date 2020-01-01 `
  --packet-dir artifacts\sickle-cell `
  --json
```

### 明确 OA 全文，仅本地解析

```powershell
.\.venv\Scripts\python.exe `
  .\skills\research-lookup-enhanced\scripts\research_lookup.py `
  "single-cell spatial transcriptomics benchmarking" `
  --open-access-only `
  --extract-fulltext `
  --packet-dir artifacts\spatial-fulltext
```

如需 MinerU，必须显式追加 `--allow-remote-parser` 并提前配置 `MINERU_API_KEY`。不要因为选择 `deep` 就追加该参数。

### 引用与参考文献双向扩展

```powershell
.\.venv\Scripts\python.exe `
  .\skills\research-lookup-enhanced\scripts\research_lookup.py `
  "ferroelectric vortex devices" `
  --citation-seed DOI:10.1002/adma.202522292 `
  --graph-limit 50 `
  --packet-dir artifacts\vortex-citation-neighborhood
```

该命令会尝试两个方向，不是只查前向引用。

### Semantic Scholar seed 推荐

```powershell
.\.venv\Scripts\python.exe `
  .\skills\research-lookup-enhanced\scripts\research_lookup.py `
  "freestanding ferroelectric vortex devices" `
  --positive-seed DOI:10.1002/adma.202522292 `
  --negative-seed DOI:10.1038/s41586-020-2649-2 `
  --graph-limit 50 `
  --packet-dir artifacts\seed-recommendations
```

### batch 中逐条 auto 判断

```powershell
.\.venv\Scripts\python.exe `
  .\skills\research-lookup-enhanced\scripts\research_lookup.py `
  --batch `
    "DOI:10.1038/s41586-020-2649-2" `
    "调研柔性传感器用于步态监测" `
    "全面检索 CRISPR off-target evidence" `
  --research-level auto `
  --packet-dir artifacts\batch-demo
```

Agent 通常应直接传入结构化的非 `auto` 等级；`auto` 主要服务于独立 CLI。

## 如何阅读证据包

建议按以下顺序：

1. `coverage.json`：先看结果是否达到覆盖目标，以及哪些数据源缺失。
2. `search-ledger.json`：确认等级、变体、路由、预算、fallback、graph 与错误。
3. `references.json`：检查稳定标识符、字段来源、冲突和排序组成项。
4. `evidence-matrix.json`：核对摘录、locator、来源类型和验证状态。
5. `packet.md`：阅读人类可读汇总。
6. `references.bib`：导入文献管理或写作工具。
7. `extraction-ledger.json` / `parser-ledger.json`：全文处理时检查 OA 与解析路径。
8. `research-report.md`：将其视为确定性证据整理，不是自动生成的科学结论。

## 能力边界

- 不处理通用 Web、新闻、商品或代码搜索。
- 不把 metadata-only 或 abstract-only 记录描述成全文审阅。
- 不绕过 paywall，只处理明确合法 OA 的位置。
- 不自动上传 PDF；MinerU 必须得到逐次明确授权。
- 不根据引用次数断言论文质量。
- 不把 Semantic Scholar 推荐或 SPECTER2 相似度画成引用边。
- 不声称单页引用扩展是完整图谱或全部引用。
- 不把人工主题分组声称为 SPECTER2 聚类。
- 不把确定性报告中的候选模式称为科学共识。
- 正式 PRISMA screening、排除理由和 risk-of-bias 应交给专门的系统综述工具。

需要研究实现或提交 PR 时，请转到 [README.zh-CN.md](README.zh-CN.md)。
