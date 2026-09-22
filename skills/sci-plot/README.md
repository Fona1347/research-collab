# Sci Plot

Sci Plot 是 Research Collab 集合中面向精确科研数值图的 Python 包与 Codex Skill。
它使用版本化 figure spec、只读数据加载、确定性 Matplotlib 渲染和安全导出，
生成 SVG、PDF、PNG 与 TIFF；安装兼容的 `pubfig` 后可优先使用其导出适配层。
SciencePlots 是默认启用的核心样式依赖，并通过 `no-latex` 兼容层避免要求 LaTeX。

本次版本的重点变化见 [CHANGELOG.md](CHANGELOG.md)。

> 本 README 只服务于开发者和维护者。Agent 的运行契约以
> [SKILL.md](SKILL.md) 和 `references/` 为准。维护源码位于集合仓库的
> skills/sci-plot；安装副本由集合工具生成。

## 第一次使用：从示例数据生成科研图

下面用仓库自带的实验数据生成一张分组折线图。下面的相对路径以 Skill 包根目录
为基准。在任意工作目录可使用包内 scripts/run_sci_plot.py 的绝对路径调用，
它优先加载随包源码，避免借用旧开发仓库的 editable 安装。

注册为 Codex Skill 后，最简单的入口是直接描述任务：

> 使用 Sci Plot，以当前仓库为项目根目录。先检查
> `examples/data/response.csv`，再按 `examples/figure.spec.json` 生成分组折线图，
> 导出 SVG、PDF、PNG 和 TIFF，并报告实际输出位置与 QA 结果。

Agent 会按“检查数据 → 验证 spec → 安全渲染 → 导出与 QA”的流程执行。下面的 CLI
步骤演示同一过程，便于首次理解和复现。

### 1. 在自己的虚拟环境中安装

```powershell
python -m pip install -e .
```

这会安装 Sci Plot 的核心依赖，包括 Matplotlib 和 SciencePlots。`pubfig` 仍是可选
组件，不影响完成这个示例。

### 2. 检查输入数据

```powershell
python -m sci_plot inspect-data examples/data/response.csv
```

该命令只读检查列名、数据类型、形状和缺失值，不会修改原始 CSV。示例数据包含
`time`、`response` 和 `condition` 三列。

### 3. 了解并验证 figure spec

[examples/figure.spec.json](examples/figure.spec.json) 描述“画什么”和“如何导出”，
其中最关键的部分是：

```json
{
  "kind": "line",
  "data": {"path": "data/response.csv"},
  "mapping": {"x": "time", "y": "response", "group": "condition"},
  "export": {
    "path": "outputs/response",
    "formats": ["svg", "pdf", "png", "tiff"]
  }
}
```

figure spec 内的数据路径和 `export.path` 相对路径都以该 spec 所在目录为基准；命令行 `--output` 相对路径以当前工作目录为基准，跨目录调用时宜给绝对输出路径。`--project-root` 仍限定允许写入的范围。先验证文件、列映射和配置：

```powershell
python -m sci_plot validate examples/figure.spec.json --project-root .
```

看到 `"valid": true` 后即可渲染。

### 4. 渲染并查看结果

```powershell
python -m sci_plot render examples/figure.spec.json --project-root .
```

结果位于 `examples/outputs/`：

```text
response.svg
response.pdf
response.png
response.tiff
```

重复运行不会静默覆盖已有图片；默认会为发生冲突的一组输出追加统一时间戳。

### 5. 换成自己的数据

复制示例 spec，然后按需修改：

- `kind`：`line`、`bar`、`scatter`、`heatmap`、`errorbar` 或 `multi_panel`；
- `data.path`：自己的 CSV、TSV、JSON、XLSX、NPY 或 NPZ；
- `mapping`：数据中的 x、y、分组或热图列；
- `labels` 和 `style`：标题、单位、主题和图形尺寸；
- `export`：输出位置、SVG/PDF/PNG/TIFF 格式和 DPI。

然后依次运行 `inspect-data`、`validate` 和 `render`。也可以临时用 CLI 覆盖 spec，
例如只导出 Nature 风格的 SVG 和 PNG：

```powershell
python -m sci_plot render examples/figure.spec.json --project-root . `
  --output figures/response --theme nature --format svg --format png
```

查看当前支持的图表模板：

```powershell
python -m sci_plot list-templates
```

## 多子图样式

每个 panels 条目可以用 style 覆盖 theme、style、palette、font_size、chinese_font、
grid、scienceplots 和适用于子图的 rcparams。子图会在自己的样式上下文中创建，
因此配色、网格、边框和字体能够一起生效。显式 CLI 配置仍具有最高优先级。
backend、width_mm、height_mm、dpi、formats 以及 figure/savefig rcparams 属于整张图，
放在顶层配置；放入子图时会明确报错。palette 用于折线、散点、柱形和误差图；
热图使用 viridis 数值色图，不能通过子图的 palette 改变其含义。

validate 与 render 共用数据几何检查：重复的柱形类别、缺少的分组组合、
重复/不完整热图网格和过小的子图布局都会在绘图前报告，不会自动聚合或填补。

## 显式误差图

`errorbar` 只绘制已经给出的误差，不计算或猜测统计量。使用 `yerr` 表示对称误差，
或者同时提供 `ymin` 与 `ymax`；并用 `labels.uncertainty` 说明它是 SD、SEM 还是
置信区间：

```json
{
  "kind": "errorbar",
  "mapping": {
    "x": "time",
    "y": "response",
    "yerr": "sd",
    "group": "condition"
  },
  "labels": {"uncertainty": "SD"}
}
```

完整示例见 [examples/errorbar.spec.json](examples/errorbar.spec.json)。

## 自定义 Matplotlib 与 3D 脚本

普通 Python 脚本不会自动读取 `sci-plot.toml`。需要复用项目主题、字体、调色板、
物理尺寸和 DPI 时，显式使用公开上下文：

```python
from pathlib import Path

import matplotlib.pyplot as plt
from sci_plot import project_style

with project_style(Path(".")) as style:
    fig = plt.figure()
    ax = fig.add_subplot(projection="3d")
```

该上下文只应用样式，不接管自定义脚本的保存路径、防覆盖或 QA。原生 figure spec
仍是需要完整安全导出和验证时的首选路径。

## 职责边界

| 层级 | 职责 |
|---|---|
| Sci Plot 核心 | figure spec、常见表格/数组数据读取、line/bar/scatter/heatmap/errorbar/multi-panel、Matplotlib + SciencePlots、项目主题、安全导出、运行日志、基础 QA |
| 可选 Python 适配 | `pubfig` 导出与主题适配、SciPy 扩展 |
| 可选 Skill 协作 | 完整 EDA、统计推断、功效/样本量、实验设计、投稿级图形审查 |
| 非核心范围 | 概念图、机制图、实验方案本身、自动统计推断、自动添加显著性星号 |

Sci Plot 不会从原始数据猜测统计检验，也不会自行添加 `*`、`**`、`***`。
误差范围、显著性、回归区间等统计几何必须来自用户给定信息或明确的统计分析结果。

## 依赖模型

### Python 运行依赖

核心依赖由 [pyproject.toml](pyproject.toml) 声明：

- `matplotlib`
- `numpy`
- `pandas`
- `openpyxl`（XLSX）
- `pillow`（栅格导出与 QA）
- `SciencePlots`（默认 `science` + `no-latex` 样式）

可选 extras：

- `pubfig`：兼容的 `pubfig 0.3.x` 存在时优先使用；缺失时回退到 Matplotlib；
- `scienceplots`：保留的兼容 extra；SciencePlots 已属于核心依赖；
- `stats`：安装 SciPy，供明确需要的统计型扩展使用；
- `dev`：安装测试依赖。

候选科研 Skill 不是 Python 库，不属于 `pyproject.toml` 依赖。它们也不会因为写入
TOML 字符串而自动安装、发现或运行。

### Skill 协作

协作时必须使用 Skill frontmatter 中的 canonical name，而不是本地目录名：

| Canonical Skill name | 使用条件 | 默认策略 |
|---|---|---|
| `exploratory-data-analysis` | 用户明确要求全面探索、质量诊断或选图建议 | 可选；普通 `inspect-data` 不触发 |
| `statistical-analysis` | 已有数据需要检验、回归、效应量、置信区间或显著性 | 可选；先分析，后绘图 |
| `statistical-power` | 样本量、power、MDE 或 power curve | 可选；向 Sci Plot 交付数值表 |
| `experimental-design` | 数据采集前的随机化、分组、阻断或 DOE | 独立上游流程；仅在明确请求时使用 |
| `nature-figure` | 投稿级、多面板或指定期刊的最终审查 | 可选；基础 QA 仍由 Sci Plot 完成 |
| `scientific-visualization` | 用户明确点名且需要其专有参考内容 | 不设为默认路由，避免与 Sci Plot / `nature-figure` 重叠 |

本地目录 `sa.statistical-analysis`、`ns.nature-figure` 等只是存储目录名；实际路由名
分别是 `statistical-analysis`、`nature-figure`。执行时还必须以当前会话的可用
Skill 清单为准，不能仅凭目录存在就假定可调用。

详细的输入输出契约和降级行为见
[references/routing.md](references/routing.md)。

## 开发与可选组件

维护或测试项目时，可以安装开发依赖：

```powershell
python -m pip install -e ".[dev]"
```

需要可选绘图适配时，可在获得环境修改授权后安装对应 extra：

```powershell
python -m pip install -e ".[pubfig,dev]"
```

安装项目后，`sci-plot ...` 与 `python -m sci_plot ...` 等价。

## 配置与安全

配置优先级为：

```text
CLI > figure spec > 项目 sci-plot.toml > 内置默认值
```

- 输入文件始终只读；转换在内存中完成或写入新的派生文件；
- 默认禁止覆盖，冲突时为同批输出追加统一时间戳；
- 工作区外输出必须显式使用 `--allow-external-output`；
- TIFF 由 Sci Plot 的 Pillow 适配层输出并验证为 RGBA；
- 普通 render 不安装包、不升级环境、不自动应用上游更新。

## 主要目录

```text
SKILL.md                 Agent 核心契约
agents/openai.yaml       Skill 显示元数据
src/sci_plot/            Python 包与 CLI
config/defaults.toml     可读的默认配置基线
references/              按需加载的路由、适配与 QA 契约
upstream/sources.toml    上游版本检查/批准清单
examples/                示例 figure spec 与数据
```

上游维护采用“只读检查、人工审核、明确批准”的方式。`source check` 不会修改运行
环境；`source update` 只记录已经审查的不可变引用，不会偷偷升级 Python 包或改写
适配代码。详见
[references/source-maintenance.md](references/source-maintenance.md)。

## 验证

测试保留在集合仓库的 tests/sci-plot。以下维护命令在集合仓库根目录执行：

```powershell
python scripts/validate.py --component plot --plot-python <已有绘图环境的Python路径>
```

发布或启用为 Codex Skill 前，还应验证 `SKILL.md` frontmatter、资源路径、CLI、四种
导出格式和安装包烟雾测试。开发仓库中的 README 不参与 Agent 路由。
