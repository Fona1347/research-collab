# Architecture

## Repository boundary

`src/research-lookup-enhanced/` is the only editable Skill package. The workspace
Skill directory is a generated publication artifact. Project documentation,
environment examples, smoke checks, and release scripts live outside the package.

```mermaid
flowchart LR
    S["src/research-lookup-enhanced<br/>only editable Skill source"]
    V["scripts/validate.ps1"]
    P["scripts/publish.ps1"]
    A[".agents/skills/research-lookup-enhanced<br/>published artifact"]
    S --> V
    S --> P --> A
    A --> C["publish.ps1 -Check"]
    S --> C
```

## Retrieval flow

The local query builder is deterministic and preserves the user's original query.
It creates a capped set of variants, records filters and intent, recommends a
capability route, and supplies a global/provider request budget. It does not depend
on an LLM or a translation service. A hosting Agent or other caller may provide one
explicit English scholarly query for a low-confidence Chinese or mixed-language
query; the planner validates and audits that input without replacing the original.
The selected English variant is also used for textual relevance ranking so English
retrieval is not scored against Chinese character tokens.

```mermaid
flowchart TD
    A{"Scientific research or<br/>paper-lookup task?"}
    A -- "No" --> X["Do not invoke this Skill"]
    A -- "Yes" --> Q["Original query"]
    Q --> L["Per-query ResearchLevelResolver<br/>quick / standard / deep"]
    L --> C["Profile defaults + inferred intent<br/>+ explicit overrides + hard gates"]
    C --> B["Deterministic QueryPlan"]
    B --> R1["Stage 1: targeted capability route"]
    R1 --> C1{"Coverage sufficient?"}
    C1 -- "No" --> R2["Stage 2: general scholarly fallback<br/>original + conservative broad query"]
    C1 -- "Yes" --> M["Merge and preserve conflicts"]
    R2 --> C2{"Unique count, identifiers,<br/>provider health sufficient?"}
    C2 -- "No" --> R3["Stage 3: one bounded coverage pass"]
    C2 -- "Yes" --> M
    R3 --> M
    M --> O["Unpaywall OA resolution"]
    O --> E["Easy Scholar unique-venue enrichment"]
    E --> K["Explainable local ranking and packet"]
```

OpenAlex is the cross-disciplinary primary discovery source when its API key is
configured. Crossref is an independent bibliographic companion and DOI verifier.
Europe PMC is preferred for biomedical discovery and JATS. Semantic Scholar is
optional, key-gated, serialized in-process, and paced at no less than 1.2 seconds
between requests. Unpaywall and Easy Scholar never participate in discovery.

Every route attempt records the query variant, selection or skip reason, budget
snapshot, result count, error/degradation, and fallback stage. Records also retain
route provenance through merging and ranking.

The resolver is a depth policy for an already-valid scholarly task, not a general
request classifier. Omitting a level preserves the historical `standard` behavior;
`auto` is explicit opt-in for deterministic local rules. Every batch query receives
its own immutable effective run configuration, while Provider clients and caches may
remain shared. Profile values never authorize MinerU upload or model downloads.

Citation and recommendation expansion still require explicit seeds. They consume
the same routed request budget left after discovery; no Profile reserves or creates
an independent graph budget.

## PDF parser chain

HTML and JATS stay on the local extraction path. Only a PDF location explicitly
marked open access can enter the PDF chain.

```mermaid
flowchart TD
    P["Legally obtained OA PDF"] --> G{"Remote parser explicitly allowed?"}
    G -- "Yes + key configured" --> M["MinerU wrapper<br/>remote upload/API"]
    G -- "No" --> D["Record MinerU skip"]
    M -- "manifest/full.md/content_list available" --> R["ParsedDocument"]
    M -- "Unavailable or failed" --> K["MarkItDown lazy local fallback"]
    D --> K
    K -- "Installed and usable" --> R
    K -- "Unavailable or failed" --> Y["pypdf page-text fallback"]
    Y --> R
```

`ParsedDocument` carries text/Markdown, sections, tables, captions, references,
source hash, parser name/version, local output paths, warnings/errors, and parser
provenance. MarkItDown is treated as a lightweight LLM-oriented conversion, while
`pypdf` is explicitly marked low-structure-fidelity.

A `deep` level raises the candidate limit only after full-text extraction has been
explicitly requested. It does not enable extraction or remote upload by itself.

## Optional Sciverse boundary

The source package defines an `EvidenceProvider`/evidence-record handoff protocol.
It preserves stable identifiers, direct evidence versus inference, offsets, and
partial/truncated warnings. No Sciverse files are imported and no Sciverse runtime
is required by the core pipeline.
