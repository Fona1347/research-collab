# 更新日志

本文件记录 Sci Plot 面向用户和维护者的重要变化。版本号遵循语义化版本。

## [0.2.1] - 2026-09-23

- 在创建坐标轴时应用每个子图的样式，保留颜色、网格、字体与导出效果，继续遵循 CLI 的配置优先级。
- 验证与渲染共享柱状图和热图的数据检查，拒绝重复或不完整的映射；拒绝子图中无效的整图选项。
- 明确 spec 相对数据路径与 CLI 输出路径的解析基准。figure schema 保持为 1。
- 53 项离线单元测试通过，并对合成数据的 SVG/PNG 导出进行了查看；不据此声明所有平台或可选导出工具均已验证。

## [0.2.0] - 2026-07-23

本次更新聚焦配置复用和通用绘图体验：项目样式现在既能用于 Sci Plot 原生渲染，
也能显式用于普通 Matplotlib 与 3D 脚本；同时加入了严格、可复现的误差图支持。

### 更新重点

| 重点 | 现在的行为 | 带来的改善 |
|---|---|---|
| SciencePlots 默认启用 | `science + no-latex` 成为默认样式层，并作为核心依赖安装 | 新环境开箱即用，不再出现“默认开启但缺少依赖” |
| 项目配置可复用 | 新增 `project_style(project_root)` 和只读 `AppliedStyle` | 自定义 2D、3D 脚本可以复用主题、字体、调色板、尺寸、DPI 与 `rcparams` |
| 配置更透明 | `validate --project-root` 报告 `project_root`、`project_config` 和 `effective_render` | 渲染前即可确认实际生效的配置及其来源 |
| 显式误差图 | 新增 `errorbar`，支持 `yerr` 或 `ymin + ymax`，并支持分组 | 可以可靠表达 SD、SEM 或置信区间，不会自动猜测统计含义 |
| 模板更容易发现 | `list-templates` 同时显示模板说明、必需映射和可选映射 | 创建 figure spec 时不必再反复查找字段要求 |

### 新增

- 公开上下文管理器 `project_style(project_root)`；退出上下文后恢复原有
  Matplotlib 状态，并且不强制切换交互 backend。
- 冻结数据类 `AppliedStyle`，提供配置路径、调色板、宽高、DPI 和导出格式。
- `errorbar` 图表类型：
  - `x`、`y` 为必需映射；
  - `group` 为可选映射；
  - 不确定性必须在 `yerr` 与 `ymin + ymax` 之间二选一；
  - 必须使用 `labels.uncertainty` 明确标注 SD、SEM 或置信区间；
  - 拒绝负误差、缺失值、非有限值及不满足 `ymin <= y <= ymax` 的边界。
- 集中的小型 `TEMPLATE_CATALOG`，供 spec 验证和 CLI 模板查询共同使用。
- 独立的误差图数据与 figure spec 示例。
- 自定义 Matplotlib/3D 项目样式复用指南。

### 改进

- Sci Plot 原生 `render` 与公开样式上下文共用同一套内部样式组合逻辑，避免两条
  绘图路径逐渐产生差异。
- 开发版与打包版 `defaults.toml` 保持逐字节一致，`scienceplots = true`。
- 显式配置但未安装的 `chinese_font` 会在绘图前返回可操作的错误信息。
- SciencePlots 保留 `no-latex` 样式，默认使用时无需额外安装 LaTeX。
- README 增加误差图和自定义 Matplotlib/3D 的最小示例。

### 兼容性与边界

- figure spec 继续使用 `schema_version = 1`；原有 `line`、`bar`、`scatter`、
  `heatmap` 和 `multi_panel` 保持兼容。
- `scienceplots` extra 继续保留，兼容旧的安装命令；SciencePlots 本身现已属于核心
  依赖。可通过项目配置或 `--no-scienceplots` 显式关闭。
- `pubfig` 仍是可选的首选导出适配器，Matplotlib 仍是核心绘图引擎。
- `project_style()` 只负责样式复用，不接管自定义脚本的保存路径、防覆盖、输入指纹
  或出版 QA。
- `errorbar` 不排序、不聚合、不计算误差，也不推断统计检验或自动添加显著性星号。

### 升级提示

更新代码后，请在 Sci Plot 自己的虚拟环境中重新安装项目，以补齐新的核心依赖：

```powershell
python -m pip install -e ".[dev]"
```

如需 `pubfig` 适配器：

```powershell
python -m pip install -e ".[pubfig,dev]"
```

### 已验证

- Python 3.14.5 项目虚拟环境安装成功，`pip check` 通过。
- 47 项单元测试全部通过。
- SVG、PDF、PNG、TIFF 四格式实际渲染与 QA 通过；SVG 文字可编辑，TIFF 为 RGBA。
- 开发目录和精简工作区 Skill 快照均通过结构校验及 launcher 烟雾测试。
