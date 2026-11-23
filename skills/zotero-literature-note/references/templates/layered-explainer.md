# Layered Explainer Template

Use this for complex, technical, formula-heavy, figure-heavy, or teaching-oriented notes.

```markdown
# {paper_short_title} 阅读笔记

## 1. TL;DR

用 5-8 句话概括论文问题、方法、核心结果、贡献和主要 caution。

## 2. 文献信息

- Title:
- Authors:
- Journal / Year:
- DOI:
- Zotero item key:
- BibTeX key:

## 3. 论文故事线

解释作者如何从问题出发，构造方法，验证结果，并推向贡献。

## 4. 关键概念与模型

分层解释核心概念、模型假设、变量、公式和适用边界。

## 5. 图表导读

先插入高价值 cropped figure or selected panel crop，再解释。rendered full PDF page 只在裁图会丢失关键上下文或裁图失败时作为显式 fallback 插入，并需要在正文标注 fallback 性质。默认使用 Typora-friendly HTML：

```html
<img src="./{note-filename-without-.md}.assets/fig1-short-label.png" alt="Fig. 1: short label" style="zoom:67%;" />
```

### Fig. {n}: {short_label}

<img src="./{note-filename-without-.md}.assets/{figure-file}.png" alt="Fig. {n}: {short_label}" style="zoom:{zoom-percent}%;" />

- 读图问题：
- caption 证据：
- 正文解释：
- 视觉观察：
- 支持的结论：
- 证据资产：cropped figure / cropped panel / rendered page fallback
- fallback 说明：仅当插入 rendered page fallback 时填写，说明为什么没有使用 crop
- caution：

### Fig. {n}{panel}: {panel_short_label}

<img src="./{note-filename-without-.md}.assets/{panel-file}.png" alt="Fig. {n}{panel}: {panel_short_label}" style="zoom:{zoom-percent}%;" />

- panel 读图问题：
- visual observation：
- 与 full figure 的关系：
- caution：

## 6. annotation 问题解释

围绕用户 annotation 或 Zotero notes 中的问题逐条解释。

## 7. 贡献与局限

把贡献、证据强度、仍不确定之处分开写。

## 8. 附录

放复杂公式、长图解、相关文献比较或扩展问题。

## 9. 参考文献

列出主文献和实际使用过的高权重相关文献。
```
