# Document parser chain

## Contents

- [ParsedDocument contract](#parseddocument-contract)
- [Parser order](#parser-order)
- [MinerU gate and normalization](#mineru-gate-and-normalization)
- [Local fallbacks](#local-fallbacks)
- [Failure provenance](#failure-provenance)

## ParsedDocument contract

Every parser returns `ParsedDocument` with:

- `text` and optional `markdown`;
- `sections`, `tables`, figure/table `captions`, and `references`;
- `source_file_hash`;
- `parser_name` and `parser_version`;
- `local_output_paths`;
- `warnings` and `errors`;
- ordered `parser_provenance`.

Compatibility fields retain `content_hash`, `local_path`, `source_type`, and
`extraction_method` for existing evidence-chunk and packet consumers.

## Parser order

Keep public HTML and JATS on their local parsers. For an OA PDF, use:

1. MinerU remote API wrapper, but only with explicit permission;
2. Microsoft MarkItDown, lazily imported;
3. `pypdf` page text.

Each parser has an isolated output directory. Save `parser-ledger.json` with the
selected parser, all attempts, remote/OA gates, warnings, errors, and source hash.

## MinerU gate and normalization

Call:

```powershell
<python-executable> <mineru-wrapper-script> `
  --input "<oa-pdf>" `
  --output "<empty-parser-output>" `
  --model vlm `
  --language ch
```

Do not pass `MINERU_API_KEY` on the command line. The wrapper reads it from the
environment. It uploads the selected PDF to the MinerU remote API, polls the task,
and downloads the result.

Require both:

- the full-text location is explicitly marked OA; and
- the caller supplies `--allow-remote-parser`.

Normalize `manifest.json`, `full.md`, `content_list.json`, and available `images/`.
Use `full.md` for Markdown and sections. Use content-list blocks for tables,
captions, page locators, and reference blocks. Preserve manifest model/schema and
local output paths. Reuse an existing complete output directory only after its
source.input_sha256 matches the current input file. Reject missing, malformed or
stale hashes and incomplete non-empty directories; preserve their contents and
record the error before trying a local fallback. Do not automatically re-upload
or label a manifest hash as verified without comparing it to the source bytes.

## Local fallbacks

Import MarkItDown only inside its parser. Use the narrow `markitdown[pdf]` optional
dependency. Save the converted Markdown and identify it as a lightweight
LLM-oriented conversion; do not claim MinerU-grade formula, table, or layout
fidelity.

Use `pypdf` as the final local fallback. Emit page-labelled Markdown and sections.
Always warn that reading order, tables, formulas, and layout have low structure
fidelity. Never label this output as MinerU parsing.

## Failure provenance

Treat missing packages, missing keys, an unavailable wrapper, non-OA input, and
missing remote permission as explicit skips or unavailable states. Treat wrapper or
parser exceptions as errors. Preserve the message in `ParsedDocument` and
`parser-ledger.json`, then continue automatically.

Do not claim MinerU evidence unless the wrapper completed (or a complete prior
MinerU output was reused) and the normalized output files were actually read.

## Portable runtime configuration

Set MINERU_WRAPPER and optionally MINERU_PYTHON, or use the matching mineru_wrapper
and mineru_python fields in config/local.json beside this Skill. Explicit adapter
arguments take precedence, then environment values, then the local file. The
interpreter defaults to the current Python. Missing wrapper configuration preserves
the existing local-parser fallback. API keys remain environment-only. This does not
grant remote-upload permission; OA and explicit remote-parser gates still apply.

## Public HTTP boundary

HTTP(S) retrieval checks every redirect and all resolved destination addresses
before opening a connection. Direct connections use the checked DNS results;
configured urllib proxies receive a checked destination IP with the original Host
and TLS server name. Existing proxy/no_proxy configuration is trusted transport,
not permission for a source URL to select an internal destination. Cross-origin
redirects do not forward credentials or request bodies. Policy blocks also apply
to robots.txt and fail explicitly; they are not treated as missing robots files.
Injected test transports are trusted code and must preserve this boundary if they
perform real I/O. No certificate verification or global network settings are changed.

The input SHA-256 check binds reuse to the selected source bytes. It is not an output signature: it does not authenticate locally edited parser outputs or establish the scientific correctness of parsed text. Keep the cache in a trusted local directory and inspect important claims against the source.
