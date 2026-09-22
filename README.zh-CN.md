# Research Collab

把文献发现、论文阅读、研究方向判断、科研绘图与汇报衔接起来的 **9 个科研 Skill**。每个 Skill 都可以单独调用，保留可追溯的来源、判断依据和产物。

[English](README.md) · [维护与安装](docs/maintenance.md) · [来源与依赖](docs/sources.md)

## 最简上手

需要 Git、Python 3.11+，以及能加载本地 Skill 的宿主。以下以 Codex 和 PowerShell 为例；macOS/Linux 可使用相同的 Python 命令，将目标参数换成自己的绝对路径。

### 1. 安装到你的科研项目

在用于保存工具源码的位置执行，将 `$skillsDir` 设为科研项目下 `.agents/skills` 的绝对路径：

```powershell
git clone https://github.com/Fona1347/research-collab.git
cd research-collab
$skillsDir = "D:/research-project/.agents/skills"

python scripts/skills.py install --skills-root "$skillsDir" --dry-run
```

确认预览的目标和改动后，执行安装并核对：

```powershell
python scripts/skills.py install --skills-root "$skillsDir"
python scripts/skills.py check --skills-root "$skillsDir"
```

这会安装全部 9 个 Skill，包含实验性的全文获取适配器；不会安装 Python 依赖、注册 MCP 或开启研究任务。只想试用一个时，在上述安装和检查命令中加 `--skill paper-deep-reading`。如果已有安装出现冲突，按[首次接管说明](docs/maintenance.md#adopt-an-existing-installation)核对差异，保留本地修改。

### 2. 开始第一次阅读

在 Codex 中打开上面的科研项目，附上或粘贴你已获得的**可读论文全文**，再发送：

```text
$paper-deep-reading 请基于我提供的论文全文，生成中文读者报告。
task=full-report，validation=fully-local，presentation_handoff=no。
输出父目录：D:/research-project/reports。
重点解释研究问题、方法、证据与局限，并标明材料没有覆盖的内容。
```

`fully-local` 适合先跑通本地阅读；需要补充外部证据时，再请求 `validation=standard`。若输入是 PDF，先准备下方的解析工具。完整报告完成后，从新建任务目录中的 `view-report.md` 开始阅读。

Codex 从项目的 `.agents/skills` 加载技能。CLI/IDE 可用 `$技能名` 显式调用；提供技能选择器的界面也可选择对应技能。安装后若未显示，重启 Codex 并检查打开的项目目录。详见 [OpenAI 技能加载与调用说明](https://learn.chatgpt.com/docs/build-skills)。

## 按任务选择 Skill

| 你要做什么 | Skill | 主要产物 |
|---|---|---|
| 查找论文、扩展查询、整理来源 | [research-lookup-enhanced](skills/research-lookup-enhanced/SKILL.md) | 可追溯的候选与证据包 |
| 从 Sciverse 语料获取证据段落或结构化阅读 | [sciverse-research](skills/sciverse-research/SKILL.md) | 带来源位置和完整性状态的证据 |
| 读懂一篇论文及其证据边界 | [paper-deep-reading](skills/paper-deep-reading/SKILL.md) | 读者报告与权威工作产物 |
| 从 Zotero 条目制作 Markdown 阅读笔记 | [zotero-literature-note](skills/zotero-literature-note/SKILL.md) | 可追溯的笔记与图片 |
| 比较研究方向、论证已选接口或审计现有方案 | [research-opportunity-mapper](skills/research-opportunity-mapper/SKILL.md) | 路线判断、验证计划与决策记录 |
| 快速探索研究机会 | [research-opportunity-mapper-quick](skills/research-opportunity-mapper-quick/SKILL.md) | 轻量机会地图 |
| 从数值数据生成科研图 | [sci-plot](skills/sci-plot/SKILL.md) | SVG/PDF/PNG/TIFF 与导出检查 |
| 把已完成的阅读材料转为汇报 | [paper-presentation](skills/paper-presentation/SKILL.md) | 汇报结构、讲稿与素材计划 |
| 编排已授权的全文获取 | [literature-fulltext-acquisition](skills/literature-fulltext-acquisition/SKILL.md) | 获取记录与明确的失败状态；**实验项** |

普通检索不会自动启动 Mapper。正式路线判断时，完整 Mapper 会根据决策需求推荐配置；已选接口、可用资源和排除方向都值得在请求中说明。汇报 Skill 消费已有阅读产物，最终 PPTX 制作需要另行选择演示工具。

## 推荐配置：按需补齐

### 固定输出位置，说明研究约束

在**科研工作区根目录**创建 `.paper-collab.yaml`，把示例替换为你自己的绝对路径：

```yaml
default_output_parent: 'D:/research-project/reports'
```

这是深读报告的默认父目录；每次任务会生成独立子目录。当前请求中明确指定的目录优先。它只保存路径偏好，不授予上传、下载或其他操作权限，也不会替代工作区要求的确认。

建议在项目说明或 `AGENTS.md` 中简要记录常用语言、研究对象、可用设备/计算资源、时间预算、排除方向，以及哪些材料允许联网或上传。把个人路径和未公开研究信息留在本地，不提交到公共仓库。这些背景有助于减少重复提问；无需填写一套固定问卷。

### 准备一条可用的 PDF 阅读路径

本地 PDF 路线通常需要 `pdfinfo`、`pdftoppm` 和 `pypdf`，`PyMuPDF` 可补充解析与视觉检查。已有 MinerU 时可接入授权的解析路径；公式、图表和版面仍需结合原文检查。

可在选定的 Python 环境中运行只读预检，沿用上方的安装目录变量：

```powershell
python "$skillsDir/paper-deep-reading/scripts/check_dependencies.py" --mode fully-local --input-kind pdf
```

预检会报告缺失项，不会替你安装软件。完整要求见[深读依赖说明](skills/paper-deep-reading/references/external-dependencies.md)。

### 按使用场景配置外部能力

| 场景 | 推荐配置 | 带来的改善 |
|---|---|---|
| 经常查找与交叉核对论文 | 给检索增强配置 `OPENALEX_API_KEY`、`SEMANTIC_SCHOLAR_API_KEY`；按需设置 `CROSSREF_MAILTO`、`UNPAYWALL_EMAIL` | 使用相应提供方的检索、元数据和开放获取定位能力 |
| 需要 Sciverse 证据段落或 Paper Schema | 单独连接 Sciverse MCP/API，配置 `SCIVERSE_API_TOKEN`，确认当前账号和工具可用范围 | 获取支持语料中的上下文与结构化信息 |
| 以 Zotero 为文献入口 | 配好 Zotero 桌面端及宿主的 Zotero 插件/连接器，提供目标条目 | 复用条目、附件、笔记和经过核验的解析缓存 |
| 需要 MinerU 解析 | 在检索增强安装目录的 `config/local.json` 中设置 `mineru_python`、`mineru_wrapper`，密钥使用环境变量 `MINERU_API_KEY` | 绑定已有解析环境，避免依赖某台机器的开发目录 |
| 使用实验性全文获取 | 在其安装目录的 `config/local.json` 中设置 `tools_root`、`protected_root`；需要已有外部工具及 Windows / PowerShell 7 | 使用随包包装脚本和已有输出保护 |

只配置你要使用的能力。在本检索适配器中，未配置密钥的 OpenAlex/Semantic Scholar 会明确跳过。Sciverse、Zotero、MinerU 与全文获取服务均不随 Skill 自动安装或启用。

本地运行时设置可以从各组件的 `config/local.example.json` 起步，已有配置应保留后再修改。真实密钥使用宿主支持的密钥存储或进程环境变量；不要写进 README、Skill、命令参数或公共日志。MinerU 远程解析仍须满足相应的来源与上传授权条件。

详细配置：[检索提供方](skills/research-lookup-enhanced/references/provider-matrix.md) · [解析器](skills/research-lookup-enhanced/references/document-parsers.md) · [Sciverse](skills/sciverse-research/references/mcp-upgrade-notes.md) · [全文获取](skills/literature-fulltext-acquisition/references/tools.md)。

### 经常绘图时，固定项目样式

为 Sci-Plot 选择具备其 [Python 依赖](skills/sci-plot/pyproject.toml)的环境，先检查：

```powershell
python "$skillsDir/sci-plot/scripts/check_environment.py" --require
```

在**绘图项目根目录**保存 `sci-plot.toml`，可从下面的配置开始：

```toml
[project]
name = "my-research"
output_dir = "figures"

[render]
theme = "paper"
scienceplots = true
formats = ["svg", "png"]
dpi = 300
```

渲染时明确项目根目录；命令行和 figure spec 中的设置优先。需要中文时，将 `render.chinese_font` 设为该环境实际安装的字体。使用安装包内的 `scripts/run_sci_plot.py`，可确保运行随包源码。更多示例见 [Sci-Plot 指南](skills/sci-plot/README.md)。

## 更新、打包与维护

以下命令在本仓库根目录执行；`$skillsDir` 仍指向科研项目的安装目录。

```powershell
python scripts/skills.py validate
python scripts/skills.py package --output dist/research-collab.zip
python scripts/skills.py package --skill paper-deep-reading --output dist/paper-deep-reading.zip
python scripts/skills.py install --skills-root "$skillsDir" --dry-run
python scripts/skills.py check --skills-root "$skillsDir"
```

更新时先在干净的维护克隆中拉取所需版本，再预览并执行安装。工具会备份改动、记录来源提交与哈希，并在发现本地漂移时暂停对应组件。生成包是分发产物；每个 Skill 的唯一维护源码位于 `skills/<skill-name>`。备份与恢复命令见[维护指南](docs/maintenance.md)。

`scripts/validate.py` 可运行组件回归；用 `--component` 选择范围，绘图测试可指定 `--plot-python`。Mapper 的真实历史回归需要显式的 `MAPPER_LEGACY_WORKSPACE`；未提供时使用公共合成材料并报告相关跳过项。测试不开展正式科研检索或真实论文下载。

## 状态与许可

集合整合仍为 **Unreleased**；既有 Paper Collab 正式包版本为 V1.2.1，各 Skill 和证据 schema 独立版本。全文获取继续标为实验项；离线检查通过不代表线上服务或真实下载已经验证。

采用 [MIT](LICENSE)，保留组件版权与[第三方归属](docs/sources.md)。论文、真实研究报告、个人档案、凭据和外部运行环境不属于公开分发内容。
