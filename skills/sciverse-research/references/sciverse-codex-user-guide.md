# 在 Codex 中使用 Sciverse

Sciverse 在 Codex 里主要用于科研文献检索、证据片段查找、论文元数据筛选、原文上下文扩展、图片资源读取和引用关系分析。它适合做有来源约束的科研问答、文献列表整理、小型综述和后续论文阅读准备。

使用时不需要在提示词里写 API Token。Token 由 Codex MCP 配置在后台读取 Windows 用户级环境变量 `SCIVERSE_API_TOKEN`。不要把 token 粘贴到聊天、文件、日志或截图里。

## 留档文件速查

Sciverse 相关长期记录都在 `<skill-root>/references/`：

| 文件 | 用途 |
|---|---|
| `mcp-upgrade-notes.md` | 实现路径、当前配置、MCP 升级记录、Windows 修复和维护规则。 |
| `sciverse-api.md` | Sciverse REST endpoint、MCP 工具映射、鉴权和错误处理。 |
| `sciverse-validation-test.md` | 凭据、REST API、MCP 配置和工具暴露的复查步骤。 |
| `sciverse-codex-user-guide.md` | 当前这份用户使用说明。 |

正常使用只需要看本文件；配置坏了或升级 MCP 时，再看 `mcp-upgrade-notes.md` 和 `sciverse-validation-test.md`。

## 1. 快速开始

先确认 MCP 是否可用：

```text
/mcp
```

如果看到 `sciverse`，并且状态类似 enabled、authenticated 或可用，就可以开始用。

也可以直接测试：

```text
Use sciverse list_catalog.
```

如果返回字段目录，说明 Sciverse MCP 已经可调用。

最小可用检索：

```text
Use sciverse search_papers to search graphene battery cycle stability since 2022, page size 3.
Return title, DOI, year, venue, and why each paper is relevant.
```

最小证据检索：

```text
Use sciverse semantic_search to find evidence about Transformer attention mechanism.
Return 3 evidence chunks with title, doc_id, chunk_id, offset, year, and venue when available.
```

## 2. 什么时候用哪个工具

| 目标 | 优先工具 | 说明 |
|---|---|---|
| 查论文列表、做表格、按年份/期刊/作者过滤 | `search_papers` | 返回结构化论文元数据。 |
| 查某个科学问题的证据片段 | `semantic_search` | 返回 RAG 风格证据 chunk。 |
| 不确定字段名或过滤符 | `list_catalog` | 先查 schema，再构造过滤条件。 |
| 扩展某个 chunk 附近的原文上下文 | `read_content` | 需要 `doc_id`，通常配合 `offset`。 |
| 读取图、表、图片附件 | `get_resource` | 只使用 Sciverse 返回的相对路径。 |
| 查引用、参考文献、相关论文 | `list_paper_relations` | 需要 `unique_id`，不要传 `doc_id`。 |
| 读取已解析 AI 论文的结构对象、证据和受限图谱 | Paper Schema BETA | 需要 Paper Schema Skill/API 权限；不替代全量元数据或开放式语义检索。 |

简单判断：

- 要“有哪些论文”：用 `search_papers`。
- 要“文献里具体怎么说”：用 `semantic_search`。
- 要“这个字段该怎么过滤”：用 `list_catalog`。
- 要“别只看短片段，读上下文”：用 `read_content`。
- 要“它引用了谁/谁引用它”：用 `list_paper_relations`。
- 要“这篇已解析论文有哪些问题、方法组件、结果、内部关系或结构证据”：用 Paper Schema（如果当前环境已装载）。

## 2.1 Paper Schema BETA：什么时候使用

官网新增的 Paper Schema 是面向已完成 Schema 抽取论文的结构化阅读能力。它把 18 个 REST 操作收敛为 9 个按意图组织的工具，覆盖：

- 论文 Schema 能力发现；
- 结构化论文搜索和相关论文发现；
- Problem、Component、Finding、Measure、Resource、Reference 等 Entity；
- 单篇论文内部的 Entity-to-Entity Relation；
- 完整引用列表、已解析 citation graph；
- 公式、表格、结果、比较、资源和引用语义等 Evidence；
- provenance 回溯、单篇论文内检索和受限上下文 hydrate；
- `overview`、`survey`、`benchmark`、`method`、`reproduction` 材料包。

推荐判断：

```text
要查全量论文、作者或期刊统计       -> search_papers
要在大范围语料中找开放式证据       -> semantic_search
要读一篇已解析论文的结构化对象     -> Paper Schema
要核验结构对象对应的原文           -> Paper Schema provenance / read_content
```

Paper Schema 的边界：

- 只覆盖已经完成 Schema 抽取的论文；空结果只能说明当前已解析语料未命中。
- `entity_id` 只在对应 `schema_id` 内稳定；跨论文 Entity 搜索是语义相似，不是全局实体对齐。
- 内部 `Relation` 与论文间 `Citation` 不是同一种关系。
- Citation graph 只包含已解析的论文级引用边；未解析引用仍应保留在引用列表中。
- 返回 `partial=true`、`truncated=true` 或 `warnings` 时，必须在输出中说明结果可能不完整。

本 Skill 包含 Paper Schema 规则；实际可用工具以当前会话为准。需要使用时，先确认 Paper Schema Skill/API 能力是否可用并获得账号权限。

官方接入指南还列出 `npx skills add https://sciverse.space`、OpenClaw/ClawHub、Claude Plugin、手动 Skill、SDK 和 MCP 等装载路径。本集合只维护工作流 Skill；应检查当前主机的服务配置，不应把 OpenClaw 专用命令直接当作 Codex 安装命令。

## 3. 常见使用场景

### 3.1 查论文列表

适合找一批论文、按年份/期刊/DOI/venue 过滤，或者做表格。

```text
Use sciverse search_papers to search papers about graphene battery cycle stability since 2022.
Return 5 papers with title, DOI, year, venue, and a short reason why each is relevant.
```

中文也可以：

```text
使用 sciverse search_papers 检索 2022 年以来关于 graphene battery cycle stability 的论文。
返回 5 篇，包含标题、DOI、年份、期刊/会议，以及每篇为什么相关。
```

带结构化限制：

```text
Use sciverse search_papers to find papers about CRISPR delivery in Nature journals from 2020 to 2025.
Return title, DOI, year, venue, authors if available, and abstract summary.
Sort by year descending.
```

### 3.2 找证据片段

适合问具体科学问题，需要可引用证据，而不是只要论文列表。

```text
Use sciverse semantic_search to find evidence about whether graphene improves battery cycle stability.
Return the most relevant chunks with title, DOI, doc_id, chunk_id, offset, page_no if available.
Separate evidence from inference.
```

中文：

```text
使用 sciverse semantic_search 查找 graphene 是否提升 battery cycle stability 的证据片段。
请保留 title、DOI、doc_id、chunk_id、offset、page_no，并区分“证据”和“推理”。
```

更严格的证据输出：

```text
Use sciverse semantic_search to answer this scientific question:
<question>

Return:
- 5 evidence chunks
- title, DOI if available, doc_id, chunk_id, offset, page_no, year, venue
- what the evidence directly says
- what is only an inference

Do not make claims unsupported by the returned evidence.
```

### 3.3 先查字段，再精确过滤

适合你不确定 Sciverse 支持哪些字段名、过滤符、排序字段。

```text
Use sciverse list_catalog to inspect available paper metadata fields.
Then tell me which fields should be used to filter by publication year, DOI, venue, citation count, and open access status.
```

然后再让 Codex 用字段检索：

```text
Based on the Sciverse catalog, use search_papers to find 2024+ gold open-access Nature papers about protein design.
Explain which fields and operators you used.
```

### 3.4 扩展原文上下文

当 `semantic_search` 返回了 `doc_id` 和 `offset`，可以继续读原文附近内容，避免只凭短片段下结论。

```text
Use sciverse read_content to expand the context around this result:
doc_id: <paste doc_id>
offset: <paste offset>
limit: 3000

Then summarize only what the source text supports.
```

如果你希望 Codex 自动衔接：

```text
Use sciverse semantic_search for <question>.
Pick the two strongest chunks.
For each chunk that has doc_id and offset, use read_content to expand context before summarizing.
```

### 3.5 查引用、参考文献、相关论文

如果结果里有 `unique_id`，可以查引用关系。

查参考文献：

```text
Use sciverse list_paper_relations for this paper:
unique_id: <paste unique_id>
relation: REFERENCES

Return referenced papers with title, DOI, year, and venue when available.
```

查引用它的论文：

```text
Use sciverse list_paper_relations for this paper:
unique_id: <paste unique_id>
relation: CITATIONS

Return citing papers with title, DOI, year, venue, and why they may matter.
```

查相关论文：

```text
Use sciverse list_paper_relations for this paper:
unique_id: <paste unique_id>
relation: RELATED_WORKS

Group related works by topic if possible.
```

### 3.6 读取图表或附件

如果 `read_content` 返回的 Markdown 里有类似图片引用，才使用 `get_resource`。

```text
Use sciverse read_content for this doc_id and inspect whether the returned Markdown contains figure or table image references.
If it contains a relative image path, use sciverse get_resource with that exact relative path.
Do not pass absolute paths, URLs, backslashes, or paths containing ..
```

## 4. 推荐提示词模板

### 4.1 快速找论文

```text
Use sciverse search_papers to find recent papers about <topic>.
Filters:
- year >= <year>
- page_size = <N>

Return:
- title
- DOI
- year
- venue
- why it is relevant
```

### 4.2 找证据并保留来源

```text
Use sciverse semantic_search to find evidence about <scientific question>.
Return the top <N> evidence chunks.

For each result, include:
- title
- DOI if available
- doc_id
- chunk_id
- offset
- page_no if available
- year
- venue
- quoted or summarized evidence

Then separate:
1. Evidence
2. Inference
3. Remaining uncertainty
```

### 4.3 先查字段再检索

```text
Use sciverse list_catalog first to identify the correct fields for <filter goal>.
Then use sciverse search_papers with those fields to search <topic>.
Explain which fields and operators were used.
```

### 4.4 从检索到小型综述

```text
Use Sciverse MCP tools to produce a source-grounded mini literature review on <topic>.

Workflow:
1. Use list_catalog if field names are uncertain.
2. Use search_papers to get a structured paper set.
3. Use semantic_search to retrieve evidence chunks.
4. Use read_content for important claims that need more context.
5. Preserve provenance: DOI, title, doc_id, chunk_id, offset, page_no, year, venue.
6. Do not invent papers, DOIs, authors, or results.

Output:
- Key findings
- Evidence table
- Conflicting evidence
- Gaps and next search directions
```

### 4.5 生成可复查证据表

```text
Use sciverse semantic_search and search_papers for <topic>.
Build an evidence table with columns:
- Claim
- Evidence summary
- Title
- DOI
- Year
- Venue
- doc_id
- chunk_id
- offset
- Confidence: high / medium / low

Only include claims directly supported by retrieved evidence.
```

## 5. 深度工作流

### 5.1 从问题到可靠答案

推荐流程：

1. 用 `semantic_search` 找候选证据。
2. 对关键 chunk 用 `read_content` 扩展上下文。
3. 用 `search_papers` 补充论文元数据。
4. 如果字段不确定，插入 `list_catalog`。
5. 输出时分成“证据、推理、建议、未解决问题”。

可复制提示词：

```text
Use Sciverse MCP tools to answer this question:
<question>

Process:
1. Use semantic_search to retrieve relevant evidence chunks.
2. Use read_content for the strongest chunks that include doc_id and offset.
3. Use search_papers if paper-level metadata is missing.
4. Preserve DOI, title, doc_id, chunk_id, offset, page_no, year, and venue when available.
5. Separate evidence, inference, recommendation, and uncertainty.
```

### 5.2 从种子论文扩展文献网络

适合你已经有 DOI、标题或某篇核心论文。

```text
Use sciverse search_papers to find this seed paper:
<title or DOI>

Then use list_paper_relations with its unique_id to retrieve:
1. REFERENCES
2. CITATIONS
3. RELATED_WORKS

Summarize the surrounding literature network and identify the most relevant follow-up papers.
```

### 5.3 做选题预研

```text
Use Sciverse MCP tools to perform a preliminary research scan on <topic>.

Return:
- 5 representative papers
- 5 evidence chunks
- main research directions
- common methods
- unresolved gaps
- 3 search queries for deeper follow-up

Rules:
- Use search_papers for paper list.
- Use semantic_search for evidence.
- Use read_content when a claim depends on a short chunk.
- Preserve provenance.
```

## 6. 输出要求建议

如果你希望结果更可复查，可以在提示词末尾加：

```text
Output requirements:
- Keep evidence and inference separate.
- Include DOI, title, year, venue, doc_id, chunk_id, offset, and page_no when available.
- Mark missing provenance fields as unavailable instead of inventing them.
- Do not fabricate papers, citations, DOIs, authors, statistics, or experimental results.
- If evidence is weak or conflicting, say so explicitly.
```

如果你希望结果更像表格：

```text
Return the result as a Markdown table.
Columns: title, DOI, year, venue, evidence, doc_id, chunk_id, offset, relevance.
```

如果你希望结果更像综述：

```text
Write the answer in sections:
1. Short answer
2. Evidence
3. Interpretation
4. Conflicting or weak evidence
5. Follow-up search directions
```

## 7. 常见问题

### `/mcp` 能看到 sciverse，但工具不能用

可能是当前会话没有加载最新 MCP tools。重新打开一个新的 Codex 会话后再试：

```text
Use sciverse list_catalog.
```

### 不知道该用哪个字段过滤

先让 Codex 调：

```text
Use sciverse list_catalog and identify fields for <your filter need>.
```

### 找到了 chunk，但不敢直接下结论

继续读上下文：

```text
Use sciverse read_content around the returned doc_id and offset before making a conclusion.
```

### 结果没有 DOI 或页码

不要让 Codex 补编。要求它写：

```text
Mark unavailable provenance fields as unavailable. Do not infer missing DOI or page numbers.
```

## 8. 使用原则

- 找论文列表：优先 `search_papers`。
- 找证据片段：优先 `semantic_search`。
- 不确定字段：先 `list_catalog`。
- 要更完整上下文：用 `read_content`。
- 查图表/附件：只对 Sciverse 返回的相对路径用 `get_resource`。
- 查引用关系：用 `list_paper_relations`。
- 永远保留来源信息，不要编造 DOI、论文、作者、统计数据或实验结果。

一句话版：在 Codex 里直接说 `Use sciverse ...`，让它调用对应 MCP 工具；如果是科研问答，优先要求保留 DOI、`doc_id`、`chunk_id`、`offset`、页码、年份和期刊信息。
