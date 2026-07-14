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
| 必须 | `paper-lookup` | Skill 可发现；可用 HTTP fetch；Crossref、OpenAlex、Semantic Scholar 等 DOI/OA/引用接口可调用 | `standard` | 外部核验阻断；可改用 `main-paper-only` 或 `fully-local` | 安装 `paper-lookup` 或启用 agent 的 HTTP 能力；按需配置数据库 API key |
| 必须 | `sciverse-research` | Skill、Sciverse MCP tools、`SCIVERSE_API_TOKEN`；标准工具包括 `semantic_search`、`search_papers`、`read_content` | `standard` | 标准外部证据验证阻断；可改用不依赖外部验证的模式 | 从 Sciverse 官网申请 API，并由用户配置 MCP 与 token；agent 只检查 token 是否存在 |
| 必须（至少一条 PDF 路线） | `mineru-pdf`（首选） | Skill、MinerU wrapper、Python runtime、`MINERU_API_KEY`；上传和网络权限仍须符合当前授权 | PDF 输入的解析 | 使用本地 `pdf` fallback；若两条路线都不可用则阻断 PDF 依赖型任务 | 安装/启用 `mineru-pdf`，配置 wrapper 和 MinerU key；不要让 agent 代为上传或改凭据 |
| 必须/fallback | `pdf` | `pdfinfo`、`pdftoppm`、`pypdf`；建议 `PyMuPDF/fitz`；agent 可发现对应 PDF Skill | PDF 输入的本地解析、渲染和视觉 QA | 无 MinerU 且本地组件不足时阻断 PDF 依赖型任务；缺少单个视觉组件时显式降级 QA | 安装 Poppler、`pypdf` 和建议的 `PyMuPDF`，并启用对应 PDF Skill |
| 强烈推荐 | `sciverse-research` provenance 能力 | `semantic_search`、`search_papers`、`read_content`；图像/资源任务还需 `get_resource`；保留 source ID、locator 和 query provenance | 标准外部证据记录；图像或资源核验 | 允许继续时降低证据可追溯性，并明确标注降级 | 完成 Sciverse MCP 配置，确认所需工具在 agent 工具目录中暴露 |
| 条件性 | `parallel-web` / `research-lookup` | `parallel-cli`、`PARALLEL_API_KEY`；`research-lookup` 的深度/学术路线可选 `OPENROUTER_API_KEY` | 开放式网页检索、官方/出版社页面抓取、深度研究 | 使用 `paper-lookup`、用户提供的来源或平台 Web fallback；不阻断基础 DOI/OA/候选文献流程 | 按需安装 Skill/CLI 并配置相应 API key；缺失时接受检索范围降级 |
| 条件性 | `zotero:Zotero` | Zotero Desktop、local API、用户明确授权的只读权限 | Zotero 输入、索引全文或本地证据 | 使用用户提供的 PDF/全文和公开来源；不启用 Zotero | 用户明确授权后再配置 Zotero；agent 不执行写入、导入、标签、删除或上传 |
| 下游 | `paper-presentation` | presentation Skill 可发现；其自身依赖按需检查 | 组会、汇报、答辩或教学 handoff | 不生成 presentation handoff，仍可完成论文精读 | 需要汇报规划时按需安装 `paper-presentation` |

## Mode policy

| 模式 | 外部依赖策略 | PDF 依赖策略 |
| --- | --- | --- |
| `standard` | `paper-lookup`、Sciverse Skill/MCP/token 和可用 HTTP 路线是硬依赖；`parallel-web` / `research-lookup` 不设为硬依赖 | MinerU 或本地 PDF fallback 至少一条可用；优先 MinerU |
| `main-paper-only` | 不因 Sciverse、`paper-lookup`、`parallel-web` 或 `research-lookup` 缺失而阻断；不获取辅助来源 | PDF 输入仍需本地或明确授权的解析路线 |
| `fully-local` | 不使用网络工具或上传；外部检索和 Sciverse 为 `NOT-APPLICABLE` | 仅使用本地 PDF 路线；缺失时阻断 PDF 依赖型任务并说明限制 |
| `plan-only` | 不执行外部检索、MCP 读取、Zotero 或解析 | `NOT-APPLICABLE` |

## Agent-side checks

`scripts/check_dependencies.py` 只做本地、无网络检查。agent 还必须从自身的 Skill/tool 目录确认：

1. `paper-lookup` 是否可调用以及是否有 HTTP fetch 能力；
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
python scripts/check_dependencies.py --mode standard --json --agent-check paper-lookup.skill --agent-check paper-lookup.http-fetch --agent-check sciverse-research.skill --agent-check sciverse.mcp-tools
```

The script is read-only and uses only the Python standard library. It checks command availability, import discoverability, environment-variable presence, and locally discoverable Skill files. `--input-kind pdf` makes a PDF route a required check in `main-paper-only` and `fully-local`; the default `unknown` keeps it conditional until the source type is resolved. The repeated `--agent-check` flags merge capabilities that the agent has independently confirmed from its Skill/tool catalog. They must not be used as guesses. The script never prints the value of `SCIVERSE_API_TOKEN`, `MINERU_API_KEY`, `PARALLEL_API_KEY`, or `OPENROUTER_API_KEY`.

Until the agent supplies the HTTP and MCP confirmations, a `standard` run intentionally remains `BLOCKED` with exit code `1`.
