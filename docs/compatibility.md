# Compatibility and capability index

This index describes the v2.0.0 collection. Pin the release tag or a reviewed Git
commit for a reproducible snapshot; component versions and evidence schemas are independent.
Installing a Skill does not install its dependencies or grant data/service access.

| Skill | Version / contract baseline | Needed for the task | Offline coverage |
|---|---|---|---|
| paper-deep-reading | Paper Collab V1.2.1 lineage; evidence v1.1; semantic-footnote-v1 | Readable text or an authorized PDF route; discovery/full text for external validation | Canonical integrity, preflight, citations, Mapper API integration |
| paper-presentation | Paper Collab lineage; v1.1 + legacy v1.0.x input | Completed reading package; separate presentation tool for PPTX | Gates, gaps, stale/dangling traces, legacy manual-review routing |
| research-lookup-enhanced | 0.3.0 lineage; existing evidence records | Provider credentials as documented; pypdf for local PDF; optional parser/HTML libraries | Mock providers, input/cache binding, DNS/redirect/robots boundaries, offline smoke |
| sciverse-research | 0.1.1; existing evidence-record schema | Authorized Sciverse MCP/API and local token for live work | Routing cases and contract/reference checks |
| research-opportunity-mapper | 2.2.0; schema 2.0 | Explicit Mapper invocation; authorized evidence companions as needed | Landscape/focus/audit, IDs/gates/reader projection, old formats, canonical handoff |
| research-opportunity-mapper-quick | Independent Quick; schema 1.2 | Explicit Quick invocation; authorized evidence routes | Coherent/explicit date, no overwrite, incomplete-template rejection |
| sci-plot | 0.2.1; figure schema 1 | Python 3.11+ and declared plotting dependencies; optional pubfig | Actual plots/exports, panel styles, precedence, input/output guards |
| zotero-literature-note | 0.3.0-beta | Selected Zotero item/connector; authorized parser as needed | Release payload, references, policy/templates (PowerShell 7) |
| literature-fulltext-acquisition | Experimental adapter; existing upstream lock | Windows + PowerShell 7, configured tools and entitlement | Fake-executable guards; configured runtime help only, no live retrieval |

Historical version labels describe lineage, not new releases. Without an independent
semantic version, use the collection commit. Sci-Plot's patch records executable
behavior changes; no evidence schema changed.

Python 3.11+ is the collection CLI floor. CI declares Ubuntu/Python 3.11 and
Windows/Python 3.14; inspect the Actions result for a commit before claiming those
environments passed. It uses ordinary `pull_request` events, read-only repository
permission, no research credentials, and pinned official
[checkout](https://github.com/actions/checkout) and
[setup-python](https://github.com/actions/setup-python) actions. Only disposable CI
runners install declared test dependencies; local validation/install never does.

`python scripts/validate.py --component NAME` accepts `collection`, `reading`,
`presentation`, `mapper`, `quick`, `lookup`, `sciverse`, `plot`, `zotero` or
`acquisition`. Default: all. Mapper integration automatically uses the sibling
canonical checker; `ROM_CANONICAL_CHECKER` is an explicit override. Missing
PowerShell 7 blocks a selected PowerShell check with a reason. Unconfigured live
acquisition and absent real history are skips, not successful live checks.

Legacy archive format 1 remains readable by manifest/hashes. Without
`distribution.json` an old archive cannot retroactively prove that each member was
explicitly approved. New source/packages/installations require the inventory.
Legitimate old backups remain usable, but restoration now requires the original
`--skills-root` and verifies paths and receipt ownership before writing.

See [maintenance](maintenance.md), [attribution](sources.md), and
[bounded semantic evaluation](evaluation/README.md). Structural passes do not prove
scientific truth, source independence, permission to transmit material or support
for every host/plugin version.
