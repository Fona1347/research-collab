# Sources, status and external dependencies

| Skill | Origin | Included work |
|---|---|---|
| paper-deep-reading | standalone skill module | Canonical public source and regression tests |
| paper-presentation | standalone skill module | Canonical public source and regression tests |
| research-opportunity-mapper | standalone skill module | Current full source and tests; private profiles and research cases remain local |
| research-opportunity-mapper-quick | standalone skill module | Current independent Skill; portable example paths |
| research-lookup-enhanced | standalone skill module | Current source, tests and parser adapter |
| sciverse-research | standalone skill module | Source plus the installed selection boundary |
| sci-plot | standalone skill module | Current working source and bundled src runtime |
| zotero-literature-note | standalone skill module | Public-ready canonical Skill and its copyright notice |
| literature-fulltext-acquisition | standalone skill module | Experimental Skill and guarded wrapper; upstream runtimes excluded |
| insight | standalone skill module | V2.4 source, including non-experimental paradigm calibration, bundled decision-interaction rules, and its [method attribution](../skills/insight/references/sources.md) |

Standalone development histories remain separate from this collection. Exact local paths,
private migration logs, and local workspace fixtures are intentionally excluded.

## Dependency attribution

- Insight bundles its single-question decision rules in `references/decision-interaction.md`
  (adapting to the host's native question interface or chat without depending on an external
  `grill-me` Skill), while attributing interaction principles to Google Antigravity's public
  `grill-me` rules.
- Sciverse and Paper Schema: external service/MCP capabilities, not an original
  server implementation in this collection.
- Zotero: external desktop software and connector. Library attachments remain read-only.
- Paper Fetch: external Dictation354/paper-fetch-skill project (Jifei Huang).
- MinerU: external parser/service and separately installed wrapper; remote upload
  requires the existing explicit authorization gate.
- Sci-Plot: original workflow/CLI with Matplotlib, NumPy, pandas, Pillow, openpyxl,
  SciencePlots and optional pubfig/SciPy dependencies. Their upstream licenses and
  pinned maintenance baseline remain in their own packages/source manifests.
- Full-text acquisition: external paper-search-mcp, openalex-official and InstSci
  runtimes; source versions and the compatibility patch are recorded separately.
- K-Dense sa.* Skills, sci-select, slides planning and other local adaptations are
  not included. They remain independent companions and retain their own attribution.

MIT covers the maintained collection source; it does not relicense these external
projects, scientific papers, user data, or remote-service content.
