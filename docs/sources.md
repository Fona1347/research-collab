# Sources, status and external dependencies

| Skill | Previous maintenance project | Included work |
|---|---|---|
| paper-deep-reading | paper-collab-skills | Existing public main; older paper-collab does not override it |
| paper-presentation | paper-collab-skills | Existing public main |
| research-opportunity-mapper | research_map | Current full source and tests; private profile and research-case content remain local |
| research-opportunity-mapper-quick | research_map | Current independent Skill; portable example paths |
| research-lookup-enhanced | research-lookup_enhanced | Current source, tests and parser adapter |
| sciverse-research | sciverse_skill | Source plus the newer installed selection boundary |
| sci-plot | Sci-Plot | Current working source including uncommitted fixes; bundled src runtime |
| zotero-literature-note | zotero-literature-note | Public-ready canonical Skill and its copyright notice |
| literature-fulltext-acquisition | literature-acquisition | Experimental Skill and guarded wrapper; upstream runtimes excluded |

Source histories stay in the old repositories. Exact local paths, initial commit IDs,
hash inventories, reviewed drift and recovery locations are private migration records.

## Dependency attribution

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
