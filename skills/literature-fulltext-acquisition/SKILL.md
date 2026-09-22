---
name: literature-fulltext-acquisition
description: Acquire legal scholarly full text after paper discovery by routing open-access requests through paper-search or OpenAlex and user-authorized closed DOI batches through InstSci. Use only when explicitly invoked to download OA PDFs or TEI XML, or to retrieve papers the user is entitled to access through an institution. Do not use for primary literature discovery, general web search, citation review, or bypassing access controls.
---

# Literature Full-Text Acquisition

Experimental: live end-to-end retrieval is not certified by the collection's offline checks.

Use this Skill after discovery has produced a DOI, PMID, PMCID, arXiv ID, or OpenAlex Work ID. Keep SciVerse and the existing research Skills as the primary discovery layer; this Skill owns acquisition and provenance only.

## Safety invariants

- Retrieve only open-access content or content the user is authorized to access through their institution.
- Never use Sci-Hub, LibGen, Tor, proxy rotation, credential sharing, or access-control bypasses.
- Never store passwords in commands, configuration, manifests, or the workspace.
- Require a caller-supplied absolute output directory inside the active research project. Do not put downloaded papers in the configured protected tool workspace.
- Keep SSO, MFA, CAPTCHA, and consent steps visible and under the user's control.
- Rate-limit automated access and honor provider and institution terms.

## Route

1. Normalize identifiers and deduplicate the request. Preserve the original identifier beside the resolved DOI.
2. Try targeted OA retrieval with `paper-search`; prefer `arxiv`, `pmc`, `europepmc`, `semantic`, `core`, and `unpaywall` rather than an unrestricted all-source fan-out.
3. Use OpenAlex Official CLI only for OpenAlex metadata, bulk OA content, or TEI XML. Before requesting `--content`, require an OA or license filter and tell the user that cached content can consume OpenAlex credits.
4. If OA retrieval fails and the user has confirmed institutional entitlement, use InstSci for the failed DOI list. Prefer `instsci papers ... --publisher auto --no-broker`, visible browsing, concurrency 1, and explicit output.
5. For only one or two closed papers, an already authenticated Chrome or in-app browser session may be simpler than InstSci. Do not automate login, MFA, or CAPTCHA.
6. Do not let paper-search and InstSci race the same DOI. Hand only the OA failure manifest to the institutional stage.

## MCP policy

The installed paper-search MCP is optional and is not registered in the default Codex configuration, so its large tool set does not appear in unrelated projects. The repository contains an opt-in configuration template, but no Codex profile or launcher is wired yet. Its upstream `download_scihub` and `download_with_fallback` tools must remain disabled. Even if another client exposes them, do not call them.

InstSci MCP is installed for compatibility but is not registered globally. Use the visible CLI for closed-access evidence and browser interaction.

## Output contract

Write a `retrieval-manifest.jsonl` beside the acquired files. Record at least:

- original identifier, resolved DOI, title, and provider;
- access path (`oa`, `institution`, or `browser`) and reported license when available;
- local path, SHA-256, UTC retrieval time, and status;
- a concise failure reason for every unresolved item.

Never label a cached PDF as OA solely because OpenAlex can supply it; verify the work's OA or license fields.

## Local commands

Read [references/tools.md](references/tools.md) before invoking a local tool. Use the guarded wrapper there instead of relying on `PATH`.
