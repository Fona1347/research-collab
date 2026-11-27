# Bilingual Academic Citation Prose Rules

Choose between **Mode 1 (Rigorous Academic Narrative)** and **Mode 2 (Lightweight Marker-Only)** based on context and user intent.

---

## Mode 1: Rigorous Academic Narrative Mode (Default for Formal Writing & Surveys)

Automatically match the **primary language of the document** (Chinese vs. English). Strip raw parenthetical dumps `(Author et al., *Journal* 2024; DOI: 10.xxxx/...)`, inline `DOI:` strings, and code-backtick shorthands (`` `Cover 1965` ``) from body prose.

### 1.1 Chinese Academic Prose (`中文严谨学术语态`)

Use two complementary patterns naturally so sentences stay concise and readable:

1. **Non-Integral Clause-End Citation (`句末/分句末客观引述`, Most Common)**:
   State the scientific claim directly and place the citation marker **immediately before** the clause/sentence punctuation (`，`/`；`/`。`/`：`):
   - ✅ `自注意力架构能够在无需循环结构的情况下并行建模长程依赖[^1][^2]。`
   - ❌ `自注意力架构能够在无需循环结构的情况下并行建模长程依赖。[^1][^2]` *(forbidden: marker after period)*
   - ❌ `自注意力架构能够并行建模长程依赖（Vaswani et al., 2017）[^2]。` *(forbidden: redundant author-year dump)*

2. **Integral Author-Subject Citation (`主语叙述性引述`, For Landmark Works)**:
   Match the author count of the cited bibliography entry accurately (never write `et al.` in Chinese prose!):
   - **1 author**: `Cover 证明了高维非线性特征投影的线性可分性定理[^1]。` *(never add `等` to a single-author paper!)*
   - **2 authors**: `Hohenberg 与 Halperin 系统分类了临界动力学普适类[^2]。` *(use `与` or `和`, never `&` or `and` in Chinese prose)*
   - **3 or more authors**: `Horsman 等给出了物理系统构成计算的抽象理论框架[^3]。`

3. **Table Cell Citations (`表格内精简引述`)**:
   - Author column: `Cover[^1]；Vaswani 等[^2]` (use `；` between distinct works).
   - Preprint modality note (when needed): keep concise plain text (`预印本` or table column `验证层级`), never clutter prose with raw `arXiv:xxxx` IDs already present in `[^k]:`.

---

### 1.2 English Academic Prose (`English Rigorous Academic Style`)

Match IEEE / Nature Reviews academic English conventions:

1. **Non-Integral Citation**:
   - **Scheme A (`[^1]` superscript)**: Place tight at the end of the clause **before** `.` / `,` / `;` for consistent Markdown/Typora rendering:
     `Self-attention architectures model long-range dependencies in parallel without recurrence[^1][^2].`
   - **Schemes B/C/E (`[1]` flat IEEE bracket)**: Precede `[1]` with a regular space and place **before** punctuation:
     `Self-attention architectures model long-range dependencies in parallel without recurrence [1], [2].`
2. **Integral Citation**:
   - **1 author**: `Cover demonstrated that...[^1]` (or `In [1], Cover demonstrated that...` for flat IEEE Scheme B/E).
   - **2 authors**: `Hohenberg and Halperin classified dynamic critical phenomena...[^2]`
   - **>= 3 authors**: `Horsman *et al.* formalized when a physical system performs computation[^3].` *(italicize `*et al.*` with period)*

---

## Mode 2: Lightweight Preserve-Prose Mode (`普通轻量模式`)

Use when the user wants **pure hoverable jump-and-return footnotes + formatted bottom bibliography** on existing reading notes or frozen prose without altering sentence wording:

1. **Zero Wording Mutation**: Do not rewrite nouns, verbs, or sentence structure.
2. **Clean Marker Substitution**:
   - Replace `(Author et al., 2024)` / `[12]` / `[@Key]` directly at its exact clause position with the target scheme marker (`[^k]`), cleaning up only surrounding empty parentheses or orphaned spaces so no punctuation scars (`()` / `（）` / ` 。`) remain.
3. **Renumber & Append List**: Renumber `1..N` strictly by first appearance and append `## 参考文献（References）` (or `## References`) at the end.

---

## Placement Prohibitions (All Modes)

Never place citation markers (`[^k]`, `[[k]](#ref-k)`, `[k]`) inside:
- Markdown headings (`#`, `##`, `###`) or Table of Contents links;
- Inline math `$...$` or display math `$$...$$` blocks;
- Inline code spans `` `...` `` or fenced code blocks (including ```` ```mermaid ```` diagrams — inside Mermaid labels, write plain text like `Cover (1965)` without `[^k]`).
