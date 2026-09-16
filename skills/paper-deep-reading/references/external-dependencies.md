# External Dependency Preflight

This is the single maintenance source for external dependencies recommended by `paper-deep-reading`. The Skill instructions define when the checks run; this table defines what each dependency means, what can replace it, and what the user may need to do.

## Status vocabulary

Use only these statuses in preflight reports:

| Status | Meaning |
| --- | --- |
| `PASS` | The applicable dependency is available and the check found enough evidence to use it. |
| `MISSING` | The applicable dependency is not installed, configured, or discoverable. |
| `BLOCKED` | The check cannot proceed without an agent-side capability check, permission, or external configuration. |
| `OPTIONAL` | The dependency is unavailable or not needed for the selected route, but the workflow may continue with the stated limitation. |
| `NOT-APPLICABLE` | The selected validation mode does not use this dependency. |

## Dependency table

| 分类 | 依赖 | 检查项 | 触发模式 | 缺失后的 fallback | 用户动作 |
| --- | --- | --- | --- | --- | --- |
| 必须（能力） | 已授权的发现/身份与可读全文路线 | agent 确认可执行学术发现、来源身份核验与全文读取；可由不同已授权工具组合完成 | `standard` | 仅在所有等价路线均不可用时阻断受影响外部核验；可选择较窄模式 | 确认现有可用路线，无需安装某个指定供应商 |
| 首选发现 | `research-lookup-enhanced` | Skill 可发现；HTTP fetch；Crossref、OpenAlex、Semantic Scholar 等接口可调用 | 外部发现时 | 已确认的 Sciverse 或平台学术/Web 路线 | 按需启用，缺失本身不降低科学置信度 |
| 可选增强 | `sciverse-research` | Skill、Sciverse MCP tools、`SCIVERSE_API_TOKEN`；`semantic_search`、`search_papers`、`read_content` | 语料覆盖或定位证据有增益时 | 已授权的出版社全文、PDF 或其他完整来源 | 按需配置；agent 仅查 token 存在性；不强制申请服务 |
| 必须（至少一条 PDF 路线） | `mineru-pdf`（首选） | Skill、MinerU wrapper、Python runtime、`MINERU_API_KEY`；上传和网络权限仍须符合当前授权 | PDF 输入的解析 | 使用本地 `pdf` fallback；若两条路线都不可用则阻断 PDF 依赖型任务 | 安装/启用 `mineru-pdf`，配置 wrapper 和 MinerU key；不要让 agent 代为上传或改凭据 |
| 必须/fallback | `pdf` | `pdfinfo`、`pdftoppm`、`pypdf`；建议 `PyMuPDF/fitz`；agent 可发现对应 PDF Skill | PDF 输入的本地解析、渲染和视觉 QA | 无 MinerU 且本地组件不足时阻断 PDF 依赖型任务；缺少单个视觉组件时显式降级 QA | 安装 Poppler、`pypdf` 和建议的 `PyMuPDF`，并启用对应 PDF Skill |
| 强烈推荐（能力） | 来源与定位可追溯性 | 保留 stable ID、locator、实际内容与 query provenance；Sciverse 是可选实现 | 外部证据记录 | 使用 DOI/出版社、完整 PDF/HTML 和可人工核验定位；内容与定位等价时不降级 | 只对实际缺失的证据/定位降低相应主张强度 |
| 条件性 | `paper-fetch-skill` | Skill 可发现；具体来源路线按其自身 gate 检查 | 已知论文需要身份解析或合法全文获取，且用户未提供可接受来源 | 使用用户提供的 PDF/全文或已确认的 OA 位置；不阻断不需要取全文的 standard 流程 | 按需启用 `paper-fetch-skill`；不绕过登录、付费墙或访问控制 |
| 条件性 | `parallel-web` / `research-lookup` | `parallel-cli`、`PARALLEL_API_KEY`；`research-lookup` 的深度/学术路线可选 `OPENROUTER_API_KEY` | 开放式网页检索、官方/出版社页面抓取、深度研究 | 使用 `research-lookup-enhanced`、用户提供的来源或平台 Web fallback；不阻断基础 DOI/OA/候选文献流程 | 按需安装 Skill/CLI 并配置相应 API key；缺失时接受检索范围降级 |
| 条件性 | `zotero:Zotero` | Zotero Desktop、local API、用户明确授权的只读权限 | Zotero 输入、索引全文或本地证据 | 使用用户提供的 PDF/全文和公开来源；不启用 Zotero | 用户明确授权后再配置 Zotero；agent 不执行写入、导入、标签、删除或上传 |
| 下游 | `paper-presentation` | presentation Skill 可发现；其自身依赖按需检查 | 组会、汇报、答辩或教学 handoff | 不生成 presentation handoff，仍可完成论文精读 | 需要汇报规划时按需安装 `paper-presentation` |

## Mode policy

| 模式 | 外部依赖策略 | PDF 依赖策略 |
| --- | --- | --- |
| `standard` | 发现/身份与可读全文两类能力必需；Lookup 首选、Sciverse 可选；不以供应商存在性评科学可信度 | PDF 输入需可用解析路线；完整非 PDF 全文不需 PDF parser |
| `main-paper-only` | 不因 Sciverse、`research-lookup-enhanced`、`paper-fetch-skill`、`parallel-web` 或 `research-lookup` 缺失而阻断；不获取辅助来源 | PDF 输入仍需本地或明确授权的解析路线 |
| `fully-local` | 不使用网络工具或上传；外部检索和 Sciverse 为 `NOT-APPLICABLE` | 仅使用本地 PDF 路线；缺失时阻断 PDF 依赖型任务并说明限制 |
| `plan-only` | 不执行外部检索、MCP 读取、Zotero 或解析 | `NOT-APPLICABLE` |
| `custom` | 根据已解析权限显式设置 `--custom-scope`；保留 Run Contract 中的 custom 和实际限制 | 默认不检查远程上传路线；仅已有明确上传授权时加 `--allow-remote-parsing`；fully-local/plan-only 不接受该标志 |

## Agent-side checks

`scripts/check_dependencies.py` 只做本地、无网络检查。agent 还必须从自身的 Skill/tool 目录确认：

1. `research-lookup-enhanced` 是否可调用以及是否有 HTTP fetch 能力；
2. `sciverse-research` 是否可调用；
3. Sciverse MCP 是否实际暴露 `semantic_search`、`search_papers`、`read_content`，以及图像/资源任务所需的 `get_resource`；
4. `mineru-pdf`、`pdf`、`parallel-web`、`research-lookup` 和 `paper-presentation` 是否可发现。

脚本无法证明 MCP server 已连接。agent 完成工具目录检查后，应以合并结果替换相应的 `BLOCKED` 状态，而不是把文件系统检查误报为 MCP 已可用。

## Running the preflight

From the installed `paper-deep-reading` directory:

```text
python scripts/check_dependencies.py --mode standard
python scripts/check_dependencies.py --mode fully-local
python scripts/check_dependencies.py --mode main-paper-only
python scripts/check_dependencies.py --mode main-paper-only --input-kind pdf
python scripts/check_dependencies.py --mode plan-only
python scripts/check_dependencies.py --mode standard --json
python scripts/check_dependencies.py --mode standard --json --agent-check research-lookup-enhanced.skill --agent-check research-lookup-enhanced.http-fetch --agent-check sciverse-research.skill --agent-check sciverse.mcp-tools
```

The script is read-only and uses only the Python standard library. It checks command availability, import discoverability, environment-variable presence, and locally discoverable Skill files. `--input-kind pdf` makes a PDF route a required check in `main-paper-only` and `fully-local`; the default `unknown` keeps it conditional until the source type is resolved. The repeated `--agent-check` flags merge capabilities that the agent has independently confirmed from its Skill/tool catalog. They must not be used as guesses. The script never prints the value of `SCIVERSE_API_TOKEN`, `MINERU_API_KEY`, `PARALLEL_API_KEY`, or `OPENROUTER_API_KEY`.

Without an agent-confirmed discovery/identity route and readable-full-text route, `standard` remains `BLOCKED` with exit code `1`. An equivalent route can be confirmed with `--agent-check external-discovery.route --agent-check external-fulltext.route`. These flags attest capability availability, not that a specific source was read or that new actions are authorized.

For a locally parsed, publicly validated custom run, for example:

```text
python scripts/check_dependencies.py --mode custom --custom-scope standard --input-kind pdf --json --agent-check external-discovery.route --agent-check external-fulltext.route
```

This does not enable remote parsing, SI, downloads, Zotero, or broader search permission. Set the projection from the permission table before checking; do not choose a broader projection to make the preflight pass. JSON schema version 2 preserves `mode` as requested and adds `effective_mode`, `remote_parsing_applicable` and `permissions_granted_by_preflight=false`.
