# Research Collab

统一维护的科研 Skill 集合，覆盖文献发现、证据阅读、方向判断、绘图、笔记和汇报。

[English](README.md) · [维护与安装](docs/maintenance.md) · [来源与依赖](docs/sources.md)

本次集合扩展为 **Unreleased**；既有 Paper Collab 正式包版本为 V1.2.1。
各 Skill 和证据 schema 保持独立版本，不因合并仓库统一改号。

| Skill | 用途 |
|---|---|
| paper-deep-reading | 单篇论文深读、主文件完整性与研究判断 |
| paper-presentation | 将已确认阅读产物转为汇报计划 |
| zotero-literature-note | 从用户选择的 Zotero 材料形成阅读笔记 |
| research-lookup-enhanced | 有边界的检索与可追溯证据包 |
| sciverse-research | Sciverse 支持语料中的证据及 Paper Schema 工作流 |
| research-opportunity-mapper | 正式研究路线比较、focus 与审计 |
| research-opportunity-mapper-quick | 独立调用的轻量研究机会探索 |
| sci-plot | 确定性科研数值绘图及导出检查 |
| literature-fulltext-acquisition | 实验性的授权全文获取编排 |

每个 Skill 只在 skills/<skill-name> 中维护。安装副本和 ZIP 都从这里生成；
第三方工具、运行环境、论文、真实报告、个人档案和历史 runs 不随集合迁入。

## 开始使用

在仓库根目录使用已有 Python 3.11+：

    python scripts/skills.py validate
    python scripts/skills.py package --output dist/research-collab-preview.zip
    python scripts/skills.py install --skill paper-deep-reading --skills-root <安装目录绝对路径> --dry-run

检查预览后去掉 --dry-run 执行安装，再用 check 核对。
--skill 可以重复；省略时选择全部九个，包括实验性的全文获取适配器。

安装工具检测已有文件差异、备份改动并写入来源提交与哈希记录。未知文件和
config/local.json 会保留；存在本地改动时暂停该组件，不强制覆盖。
旧安装首次接管需要经核对的本地基线，格式见维护指南。

安装不会自动安装依赖、注册 MCP、更新插件、访问 Zotero、发起检索或开启 Mapper。
普通检索与正式路线决策继续分别处理；Mapper 的证据、三门、Unknown、路线与阶段、
公平基线及读者报告一致性约束保持不变。

## 验证与限制

    python scripts/validate.py --plot-python <已有 Sci-Plot Python 路径>

现有回归和集合测试使用合成数据，不开展正式科研。历史 Mapper 回归须显式设置
MAPPER_LEGACY_WORKSPACE，并只读核对旧材料；公共测试不依赖这些材料。

Sciverse、Zotero、Paper Fetch、MinerU 等服务或工具仍需单独配置。全文获取适配器
目前面向 Windows / PowerShell 7，保留既有访问与输出保护；离线测试通过不代表
真实端到端下载已经验证。.paper-collab.yaml 输出偏好保持兼容。

本仓库沿用 MIT，并保留各组件版权与依赖归属。
