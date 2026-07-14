[English](README.md) | [简体中文](README.zh-CN.md)

# Paper Collab Skills

Paper Collab 是一个仅包含源码的 Agent Skills 小型套件，用于可追溯的单篇论文精读与演示规划。

当前包版本：`V1.2.1`

## 包含的 Skill

- `paper-deep-reading`：协调 PDF 优先的论文阅读、证据记录、核验边界、中文读者报告、确定性运行目录命名和主 PDF 归档。
- `paper-presentation`：把边界明确的深读产物转换为可追溯的演示方案、讲者备注或论文卡片，不重新执行检索。

演示 Skill 有意与深读 Skill 配套，建议同时安装。

## 仓库结构

```text
skills/
  paper-deep-reading/
    SKILL.md
    agents/openai.yaml
    references/
  paper-presentation/
    SKILL.md
    agents/openai.yaml
```

仓库不包含运行服务、依赖安装器、论文 PDF、报告产物、Zotero 数据或本机专用配置。

## 安装

将所需 Skill 目录完整复制到兼容代理环境使用的 skills 目录。对于 Codex，建议同时安装到：

```text
<codex-skills-dir>/paper-deep-reading
<codex-skills-dir>/paper-presentation
```

也可以让支持 Skill 安装的代理执行：

```text
从 https://github.com/Fona1347/paper-collab-skills 安装两个 Agent Skill，
随后验证 paper-deep-reading 和 paper-presentation，但不要运行真实论文任务。
```

安装 Skill 不代表授予 Zotero、本地 PDF、网络服务、外部解析器或输出目录的访问权限。实际权限仍由用户指令和工作区规则决定。

## 输出配置

可在工作区根目录创建 `.paper-collab.yaml`，提供绝对默认输出父目录：

```yaml
default_output_parent: 'D:\paper-reports'
```

该文件仅表示本机路径偏好，不授予任何权限，并已被 Git 忽略。用户本次明确指定的完整运行目录始终优先。

自动运行目录使用以下格式：

```text
Zotero：
<item-key>-<first-author-full-name>_<year>_<journal-or-publisher>-<short-title>

其他输入：
<first-author-full-name>-<year>-<journal-or-publisher>-<short-title>
```

主 PDF 可用时，Skill 会在已批准的运行目录中复制归档为 `<task_name>.pdf`。Zotero 源条目和附件保持只读，绝不直接重命名或修改。

## 快速开始

```text
使用 $paper-deep-reading 精读 <PDF、DOI、标题或 Zotero item key>。
创建研究产物前，先向我显示解析后的输出目录。
```

```text
使用 $paper-presentation 将已经批准的 paper-deep-reading 产物转换为
组会演示方案，不重新执行检索。
```

## 版本兼容性

`V1.2.1` 是软件包发布版本。规范报告产物继续使用 `evidence_contract: v1.1`；后者是证据数据结构版本，不是软件包版本。`paper-presentation` 仍保留对 V1.0.x 历史产物的只读兼容路径。

## 安全与隐私

不要提交论文、报告、Zotero 导出、本机配置、凭据、缓存或用户专用路径。私密漏洞报告方式见 [SECURITY.md](SECURITY.md)。

## 许可证

MIT，详见 [LICENSE](LICENSE)。
