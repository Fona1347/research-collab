"""Build manuscript-ready, provenance-preserving evidence packets."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from rle.models import (
    EvidenceChunk,
    PaperRecord,
    Provenance,
    merge_records,
    normalize_doi,
    record_score,
    source_text,
    utc_now,
)


SAMPLE_SIZE_RE = re.compile(
    r"\b(?:n\s*=\s*|sample(?:\s+size)?\s+(?:of\s+)?)([\d,]+)\b", re.I
)
EFFECT_RE = re.compile(
    r"(?:\b\d+(?:\.\d+)?\s*%|\bp\s*[<=>]\s*0?\.\d+|"
    r"\b(?:OR|RR|HR|MD|SMD)\s*[=:]\s*-?\d+(?:\.\d+)?|\b95\s*%\s*CI\b)",
    re.I,
)
CONFLICT_TERMS = (
    "conflict",
    "contradict",
    "no significant",
    "null result",
    "did not",
    "failed to",
    "inconsistent",
)
PUBLICATION_TYPES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("systematic review", ("systematic review",)),
    ("meta-analysis", ("meta-analysis", "meta analysis")),
    ("randomized controlled trial", ("randomized controlled trial", "randomised controlled trial", " rct ")),
    ("clinical trial", ("clinical trial",)),
    ("cohort study", ("cohort",)),
    ("case-control study", ("case-control", "case control")),
    ("cross-sectional study", ("cross-sectional", "cross sectional")),
    ("methods/protocol", ("protocol", "benchmark", "methodology", "methods paper")),
    ("case report/series", ("case report", "case series")),
    ("review", ("review",)),
)
EVIDENCE_WEIGHTS = {
    "systematic review": 5,
    "meta-analysis": 5,
    "randomized controlled trial": 4,
    "clinical trial": 4,
    "cohort study": 3,
    "case-control study": 3,
    "cross-sectional study": 2,
    "methods/protocol": 2,
    "review": 2,
    "case report/series": 1,
    "primary/other": 2,
}


def split_sentences(text: str) -> list[str]:
    compact = re.sub(r"\s+", " ", text or "").strip()
    if not compact:
        return []
    values = re.split(r"(?<=[.!?。！？])\s+(?=[A-Z0-9\u4e00-\u9fff])", compact)
    return [value.strip() for value in values if 30 <= len(value.strip()) <= 1200]


def classify_publication(record: PaperRecord, text: str) -> str:
    # Crossref's peer-review type describes a review/decision document, not a
    # literature review. Do not infer this type from prose saying "peer reviewed".
    if any(value.strip().lower().replace("_", "-") == "peer-review"
           for value in record.publication_types):
        return "peer-review-document"
    explicit = " ".join(record.publication_types).lower()
    combined = f" {explicit} {text.lower()} "
    for publication_type, terms in PUBLICATION_TYPES:
        if any(term in combined for term in terms):
            return publication_type
    return record.publication_types[0] if record.publication_types else "primary/other"


def evidence_quality(publication_type: str, *, preprint: bool, retracted: bool) -> tuple[str, str]:
    if retracted:
        return "exclude", "Source is marked as retracted or withdrawn."
    weight = EVIDENCE_WEIGHTS.get(publication_type, 2)
    if preprint:
        weight = max(1, weight - 1)
    label = {5: "high", 4: "high", 3: "moderate", 2: "contextual"}.get(weight, "low")
    rationale = f"Classified as {publication_type}"
    if preprint:
        rationale += "; preprint status lowers confidence pending peer review"
    return label, rationale + "."


def _verification_status(record: PaperRecord) -> str:
    fulltext_types = {
        "html",
        "jats",
        "pdf",
        "table",
        "figure-caption",
        "table-caption",
        "reference-list",
    }
    if any(chunk.source_type in fulltext_types for chunk in record.evidence_chunks):
        return "full-text-extracted"
    if any(chunk.source_type == "webpage" for chunk in record.evidence_chunks):
        return "page-extracted"
    if record.abstract:
        return "abstract-verified"
    if any((record.doi, record.pmid, record.pmcid, record.openalex_id, record.semantic_scholar_id)):
        return "identifier-verified"
    return "search-only"


def _supporting_excerpts(record: PaperRecord) -> list[dict[str, str]]:
    excerpts = [
        {
            "text": chunk.text,
            "source_type": chunk.source_type,
            "locator": chunk.locator,
            "url": chunk.url,
            "extraction_method": chunk.extraction_method,
            "content_hash": chunk.content_hash,
        }
        for chunk in record.evidence_chunks
        if chunk.text.strip()
    ]
    if not excerpts and record.abstract:
        excerpts.append(
            {
                "text": record.abstract,
                "source_type": "abstract",
                "locator": "abstract",
                "url": record.url,
                "extraction_method": "provider-metadata",
                "content_hash": "",
            }
        )
    return excerpts[:10]


def _candidate_findings(record: PaperRecord, text: str) -> list[str]:
    del text
    evidence_text = " ".join(
        chunk.text
        for chunk in record.evidence_chunks
        if chunk.source_type
        not in {"citation-context", "reference-list", "search-excerpt"}
    ) or record.abstract
    sentences = split_sentences(evidence_text)
    markers = (
        "found",
        "showed",
        "demonstrated",
        "associated",
        "increased",
        "decreased",
        "effect",
        "result",
        "concluded",
        "发现",
        "结果",
        "表明",
        "显示",
    )
    findings = [sentence for sentence in sentences if any(term in sentence.lower() for term in markers)]
    return (findings or sentences)[:3]


def _section_tags(text: str, publication_type: str) -> list[str]:
    tags = {"introduction", "discussion"}
    lowered = text.lower()
    if publication_type == "methods/protocol" or any(
        term in lowered
        for term in ("method", "protocol", "assay", "measure", "instrument", "benchmark")
    ):
        tags.add("methods-rationale")
    return sorted(tags)


def normalize_reference(record: PaperRecord, index: int) -> dict[str, Any]:
    text = source_text(record)
    publication_type = classify_publication(record, text)
    preprint = (
        bool(record.arxiv_id)
        or any("preprint" in value.casefold() for value in record.publication_types)
        or any(
            value in record.url.lower()
            for value in ("arxiv.org", "biorxiv.org", "medrxiv.org")
        )
    )
    quality, rationale = evidence_quality(
        publication_type, preprint=preprint, retracted=record.is_retracted
    )
    findings = _candidate_findings(record, text)
    sentences = split_sentences(text)
    sample = SAMPLE_SIZE_RE.search(text)
    return {
        "reference_id": f"ref-{index:03d}",
        "title": record.title or "Untitled source",
        "authors": record.authors,
        "authors_text": "; ".join(record.authors),
        "publication_date": record.publication_date,
        "year": record.year,
        "venue": record.venue,
        "url": record.url,
        "doi": record.doi,
        "pmid": record.pmid,
        "pmcid": record.pmcid,
        "openalex_id": record.openalex_id,
        "semantic_scholar_id": record.semantic_scholar_id,
        "arxiv_id": record.arxiv_id,
        "publication_type": publication_type,
        "source_publication_types": list(record.publication_types),
        "study_design": publication_type,
        "fields_of_study": record.fields_of_study,
        "keywords": record.keywords,
        "sample_size": sample.group(1).replace(",", "") if sample else "",
        "abstract": record.abstract,
        "key_findings": findings,
        "quantitative_findings": [value for value in sentences if EFFECT_RE.search(value)][:5],
        "limitations": [
            value
            for value in sentences
            if any(term in value.lower() for term in ("limitation", "limited by", "bias", "uncertain", "caution"))
        ][:3],
        "evidence_quality": quality,
        "quality_rationale": rationale,
        "preprint": preprint,
        "retracted": record.is_retracted,
        "verification_status": _verification_status(record),
        "manuscript_sections": _section_tags(text, publication_type),
        "supporting_excerpts": _supporting_excerpts(record),
        "facets": record.facets,
        "providers": record.providers,
        "field_sources": record.field_sources,
        "field_conflicts": record.conflicts,
        "metrics_by_provider": record.metrics_by_provider,
        "journal_metrics": record.journal_metrics,
        "ranking": record.ranking,
        "retrieval_routes": record.retrieval_routes,
        "is_open_access": record.is_open_access,
        "fulltext_locations": [
            {
                "url": item.url,
                "kind": item.kind,
                "source": item.source,
                "license": item.license,
                "host_type": item.host_type,
                "version": item.version,
                "is_oa": item.is_oa,
            }
            for item in record.fulltext_locations
        ],
        "provenance": [
            {
                "provider": item.provider,
                "retrieved_at": item.retrieved_at,
                "request_url": item.request_url,
                "provider_record_id": item.provider_record_id,
                "cache_path": item.cache_path,
                "operation": item.operation,
                "notes": item.notes,
            }
            for item in record.provenance
        ],
    }


def _claim_map(references: list[dict[str, Any]]) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for reference in references:
        if reference["retracted"]:
            continue
        excerpts = reference.get("supporting_excerpts") or []
        for finding in reference.get("key_findings") or []:
            claims.append(
                {
                    "claim": finding,
                    "reference_ids": [reference["reference_id"]],
                    "evidence": excerpts[:2],
                    "status": "single-source",
                    "review_required": True,
                }
            )
    return claims


def _synthesis(references: list[dict[str, Any]]) -> dict[str, Any]:
    consensus: list[dict[str, str]] = []
    conflicts: list[dict[str, str]] = []
    for reference in references:
        if reference.get("retracted"):
            continue
        for finding in reference.get("key_findings") or []:
            item = {"reference_id": reference["reference_id"], "finding": finding}
            if any(term in finding.lower() for term in CONFLICT_TERMS):
                conflicts.append(item)
            elif len(consensus) < 30:
                consensus.append(item)
    designs = Counter(str(item.get("publication_type") or "unknown") for item in references)
    gaps: list[str] = []
    if not any(item.get("evidence_quality") == "high" for item in references):
        gaps.append("No high-tier synthesis or trial evidence was identified by the heuristic classifier.")
    if not conflicts:
        gaps.append("No explicit contradictory or null wording was detected; targeted negative-results searching remains necessary.")
    if not any(item.get("verification_status") == "full-text-extracted" for item in references):
        gaps.append("No source reached full-text-extracted status.")
    return {
        "consensus_candidates": consensus,
        "conflicting_evidence": conflicts,
        "methodological_patterns": dict(designs),
        "research_gaps": gaps,
        "boundary_note": "These are deterministic candidates, not model-authored conclusions.",
    }


def _section_briefs(references: list[dict[str, Any]]) -> dict[str, Any]:
    purposes = {
        "introduction": "Background, significance, and unresolved gap.",
        "methods-rationale": "Published precedent for methods, measures, models, and analyses.",
        "discussion": "Supporting and conflicting evidence, mechanisms, limitations, and implications.",
    }
    briefs = {
        key: {"purpose": purpose, "reference_ids": [], "candidate_evidence": []}
        for key, purpose in purposes.items()
    }
    for reference in references:
        for section in reference.get("manuscript_sections") or []:
            if section not in briefs:
                continue
            briefs[section]["reference_ids"].append(reference["reference_id"])
            if reference.get("key_findings"):
                briefs[section]["candidate_evidence"].append(
                    {
                        "reference_id": reference["reference_id"],
                        "finding": reference["key_findings"][0],
                    }
                )
    return briefs


def _coverage(references: list[dict[str, Any]], target: int) -> dict[str, Any]:
    verified = [
        item
        for item in references
        if item.get("verification_status") != "search-only" and not item.get("retracted")
    ]
    return {
        "requested_references": target,
        "total_unique_references": len(references),
        "verified_references": len(verified),
        "shortfall": max(0, target - len(verified)),
        "verification_mix": dict(Counter(item["verification_status"] for item in references)),
        "evidence_quality_mix": dict(Counter(item["evidence_quality"] for item in references)),
        "provider_mix": dict(Counter(provider for item in references for provider in item.get("providers") or [])),
        "facet_mix": dict(Counter(facet for item in references for facet in item.get("facets") or [])),
        "open_access_records": sum(item.get("is_open_access") is True for item in references),
        "full_text_extracted": sum(item.get("verification_status") == "full-text-extracted" for item in references),
        "preprints": sum(bool(item.get("preprint")) for item in references),
        "retracted_or_withdrawn": sum(bool(item.get("retracted")) for item in references),
        "records_with_field_conflicts": sum(bool(item.get("field_conflicts")) for item in references),
        "missing_doi_or_pmid": sum(not item.get("doi") and not item.get("pmid") for item in references),
    }


def _legacy_source_record(source: dict[str, Any]) -> PaperRecord:
    """Map the original research-lookup source envelope into schema 2 records."""
    raw_authors = source.get("authors") or source.get("author") or []
    if isinstance(raw_authors, str):
        authors = [
            value.strip()
            for value in re.split(r"\s*(?:;|\band\b)\s*", raw_authors)
            if value.strip()
        ]
    else:
        authors = [str(value) for value in raw_authors or []]
    publication_date = str(
        source.get("publication_date") or source.get("publish_date") or ""
    )
    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", publication_date)
    excerpts = source.get("excerpts") or []
    if isinstance(excerpts, str):
        excerpts = [excerpts]
    source_type = "webpage" if source.get("extracted") else "search-excerpt"
    chunks = [
        EvidenceChunk(
            text=str(value),
            source_type=source_type,
            locator=f"legacy-excerpt-{index}",
            url=str(source.get("url") or ""),
            extraction_method=(
                str(source.get("extraction_method") or "legacy-extracted-source")
                if source.get("extracted")
                else "legacy-search-result"
            ),
        )
        for index, value in enumerate(excerpts, start=1)
        if str(value).strip()
    ]
    searchable = "\n".join(
        [
            str(source.get("doi") or ""),
            str(source.get("url") or ""),
            str(source.get("title") or ""),
            *(str(value) for value in excerpts),
        ]
    )
    pmid = str(source.get("pmid") or "")
    if not pmid:
        pmid_match = re.search(r"(?:pubmed\.ncbi\.nlm\.nih\.gov/|PMID[:\s]+)(\d+)", searchable, re.I)
        pmid = pmid_match.group(1) if pmid_match else ""
    provider = str(source.get("provider") or source.get("backend") or "legacy_source")
    record = PaperRecord(
        title=str(source.get("title") or ""),
        authors=authors,
        publication_date=publication_date,
        year=int(year_match.group(1)) if year_match else None,
        venue=str(source.get("venue") or source.get("journal") or ""),
        doi=normalize_doi(searchable),
        pmid=pmid,
        url=str(source.get("url") or ""),
        abstract=str(source.get("abstract") or source.get("snippet") or ""),
        is_retracted=bool(source.get("retracted")),
        evidence_chunks=chunks,
        facets=(
            [str(source.get("facets"))]
            if isinstance(source.get("facets"), str)
            else [str(value) for value in source.get("facets") or []]
        ),
        provenance=[
            Provenance(
                provider=provider,
                request_url=str(source.get("url") or ""),
                provider_record_id=str(source.get("id") or ""),
                operation="legacy-source-import",
                notes=["Mapped from the original research-lookup source envelope."],
            )
        ],
    )
    fields = [
        "title",
        "authors",
        "publication_date",
        "year",
        "venue",
        "doi",
        "pmid",
        "url",
        "abstract",
    ]
    if "retracted" in source:
        fields.append("is_retracted")
    record.mark_fields(
        provider,
        fields,
    )
    return record


def build_manuscript_packet(
    *,
    query: str,
    records: Iterable[PaperRecord | dict[str, Any]] | None = None,
    sources: list[dict[str, Any]] | None = None,
    search_ledger: list[dict[str, Any]],
    target_references: int = 60,
    manuscript_context: dict[str, Any] | None = None,
    extraction_ledger: list[dict[str, Any]] | None = None,
    query_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if records is None and sources is None:
        raise ValueError("Either records or legacy sources must be supplied.")
    inputs: list[PaperRecord | dict[str, Any]] = list(records or [])
    inputs.extend(_legacy_source_record(source) for source in sources or [])
    merged = merge_records(inputs)
    merged.sort(
        key=lambda record: (
            0 if record.is_retracted else 1,
            1 if record.ranking else 0,
            float(record.ranking.get("total_score") or 0.0),
            record_score(record),
        ),
        reverse=True,
    )
    references = [normalize_reference(record, index) for index, record in enumerate(merged, 1)]
    coverage = _coverage(references, target_references)
    batches = [
        {"provider": item.get("provider"), "query_variant_id": item.get("query_variant_id"),
         **item["search_batch"]}
        for item in search_ledger if item.get("search_batch")
    ]
    failures = [item for item in search_ledger if item.get("status") == "error"]
    budget_stops = [item for item in search_ledger
                    if item.get("status") == "skipped" and "budget" in str(item.get("reason", ""))]
    coverage["retrieval_completeness"] = {
        "status": "partial" if failures or budget_stops or any(
            item.get("discarded_count") or item.get("has_more") is True for item in batches
        ) else "bounded" if batches else "unknown",
        "provider_batches": batches,
        "failed_requests": len(failures), "budget_stops": len(budget_stops),
        "normalization_discarded": sum(item.get("discarded_count") or 0 for item in batches),
        "normalization_diagnostics_complete": bool(batches) and all(item.get("diagnostics_available") for item in batches),
        "note": "Completeness describes executed requests, not field-wide recall; provider totals overlap and must not be summed.",
    }
    coverage["relevance_assessment"] = {"status": "not-assessed", "reason": "Ranking and stable identifiers do not establish topical sufficiency; host review is required."}
    coverage["target_count_met"] = coverage["shortfall"] == 0
    warnings: list[str] = []
    if coverage["shortfall"]:
        warnings.append(
            f"Verified {coverage['verified_references']} of {target_references} requested references; the list was not padded."
        )
    if coverage["retracted_or_withdrawn"]:
        warnings.append("Retracted or withdrawn records are excluded from claim support.")
    if any(item["publication_type"] == "peer-review-document" for item in references):
        warnings.append(
            "The raw packet includes peer-review/decision documents, not literature reviews "
            "or independent research papers; screen them out of ordinary paper shortlists."
        )
    if not manuscript_context:
        warnings.append("No structured manuscript context was supplied; section briefs remain broad.")
    synthesis = _synthesis(references)
    synthesis["consensus_evidence"] = list(synthesis["consensus_candidates"])
    return {
        "schema_version": "2.0",
        "created_at": utc_now(),
        "query": query,
        "query_plan": query_plan or {},
        "manuscript_context": manuscript_context or {},
        "target_references": target_references,
        "references": references,
        "evidence_matrix": references,
        "claim_source_map": _claim_map(references),
        "synthesis": synthesis,
        "section_briefs": _section_briefs(references),
        "coverage": coverage,
        "search_ledger": search_ledger,
        "extraction_ledger": extraction_ledger or [],
        "warnings": warnings,
        "interpretation_boundaries": {
            "retrieval": "Provider metadata and locally extracted public/OA content.",
            "evidence": "Quoted or normalized source content with locators and provenance.",
            "inference": "Any cross-source interpretation requires explicit review.",
            "recommendation": "Recommendations are not generated automatically from metadata alone.",
        },
    }


def citation_text(reference: dict[str, Any]) -> str:
    authors = reference.get("authors_text") or ""
    year = reference.get("year") or "n.d."
    venue = reference.get("venue") or ""
    identifier = f"https://doi.org/{reference['doi']}" if reference.get("doi") else reference.get("url") or ""
    lead = f"{authors} ({year}). " if authors else f"({year}). "
    return f"{lead}{reference['title']}.{' ' + venue + '.' if venue else ''} {identifier}".strip()


def packet_markdown(packet: dict[str, Any]) -> str:
    coverage = packet["coverage"]
    lines = [
        "# Manuscript Research Packet",
        "",
        f"**Query:** {packet['query']}",
        f"**Verified references:** {coverage['verified_references']} / {coverage['requested_references']}",
        f"**Full text extracted:** {coverage['full_text_extracted']}",
        "",
    ]
    if packet.get("warnings"):
        lines.extend(["## Warnings", ""])
        lines.extend(f"- {value}" for value in packet["warnings"])
        lines.append("")
    lines.extend(["## References", ""])
    for reference in packet["references"]:
        lines.append(
            f"- **{reference['reference_id']}** {citation_text(reference)} "
            f"_[{reference['verification_status']}; {reference['evidence_quality']}; "
            f"providers={','.join(reference['providers']) or 'unknown'}]_"
        )
    lines.extend(["", "## Evidence Synthesis", "", "### Consensus candidates", ""])
    consensus = packet["synthesis"]["consensus_candidates"]
    lines.extend(f"- [{item['reference_id']}] {item['finding']}" for item in consensus)
    if not consensus:
        lines.append("- No candidate statements were extracted.")
    lines.extend(["", "### Conflicting or null evidence", ""])
    conflicts = packet["synthesis"]["conflicting_evidence"]
    lines.extend(f"- [{item['reference_id']}] {item['finding']}" for item in conflicts)
    if not conflicts:
        lines.append("- No explicit conflict wording was detected.")
    lines.extend(["", "### Research gaps", ""])
    lines.extend(f"- {value}" for value in packet["synthesis"]["research_gaps"])
    lines.extend(["", "## Section Briefs", ""])
    for section, brief in packet["section_briefs"].items():
        lines.extend([f"### {section.replace('-', ' ').title()}", "", brief["purpose"], ""])
        for item in brief["candidate_evidence"][:20]:
            lines.append(f"- [{item['reference_id']}] {item['finding']}")
        if not brief["candidate_evidence"]:
            lines.append("- No section-specific evidence was extracted.")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _bibtex_escape(value: Any) -> str:
    return str(value).replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def bibtex_text(references: list[dict[str, Any]]) -> str:
    records: list[str] = []
    for reference in references:
        if reference.get("retracted"):
            continue
        lead_author = (reference.get("authors") or ["source"])[0]
        key = re.sub(r"[^A-Za-z0-9]+", "", f"{lead_author}{reference.get('year') or 'nd'}{reference['reference_id']}")
        fields = {
            "title": reference.get("title"),
            "author": " and ".join(reference.get("authors") or []),
            "year": reference.get("year"),
            "journal": reference.get("venue"),
            "doi": reference.get("doi"),
            "url": reference.get("url"),
        }
        lines = [f"@article{{{key},"]
        lines.extend(
            f"  {name} = {{{_bibtex_escape(value)}}},"
            for name, value in fields.items()
            if value not in (None, "", [])
        )
        lines.append("}")
        records.append("\n".join(lines))
    return "\n\n".join(records) + ("\n" if records else "")


def save_packet(packet: dict[str, Any], directory: str | Path) -> dict[str, str]:
    destination = Path(directory)
    destination.mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, Path] = {
        "packet_json": destination / "packet.json",
        "packet_markdown": destination / "packet.md",
        "references_json": destination / "references.json",
        "references_bib": destination / "references.bib",
        "evidence_matrix": destination / "evidence-matrix.json",
        "claim_source_map": destination / "claim-source-map.json",
        "synthesis": destination / "synthesis.json",
        "section_briefs": destination / "section-briefs.json",
        "coverage": destination / "coverage.json",
        "search_ledger": destination / "search-ledger.json",
        "extraction_ledger": destination / "extraction-ledger.json",
        "provenance": destination / "provenance.json",
    }
    payloads: dict[str, Any] = {
        "packet_json": packet,
        "references_json": packet["references"],
        "evidence_matrix": packet["evidence_matrix"],
        "claim_source_map": packet["claim_source_map"],
        "synthesis": packet["synthesis"],
        "section_briefs": packet["section_briefs"],
        "coverage": packet["coverage"],
        "search_ledger": packet["search_ledger"],
        "extraction_ledger": packet["extraction_ledger"],
        "provenance": [
            {"reference_id": item["reference_id"], "provenance": item["provenance"]}
            for item in packet["references"]
        ],
    }
    for name, payload in payloads.items():
        artifacts[name].write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    artifacts["packet_markdown"].write_text(packet_markdown(packet), encoding="utf-8")
    artifacts["references_bib"].write_text(bibtex_text(packet["references"]), encoding="utf-8")
    return {name: str(path) for name, path in artifacts.items()}
