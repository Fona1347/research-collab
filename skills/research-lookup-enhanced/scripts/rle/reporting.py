"""Deterministic, citation-linked long report generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol


class Synthesizer(Protocol):
    def synthesize(self, packet: dict[str, Any]) -> str: ...


class EvidenceReportSynthesizer:
    """Render a long report without generating facts beyond the packet."""

    def synthesize(self, packet: dict[str, Any]) -> str:
        coverage = packet["coverage"]
        lines = [
            "# Traceable Research Report",
            "",
            "## Executive summary",
            "",
            f"This packet contains {coverage['total_unique_references']} unique records, "
            f"of which {coverage['verified_references']} have identifier, abstract, public-page, "
            f"or full-text verification. {coverage['full_text_extracted']} records include "
            "locally extracted public/OA text.",
            "",
            "This report is a deterministic evidence index. Candidate statements below "
            "remain source-attributed and require subject-matter review; they are not an "
            "LLM-authored scientific conclusion.",
            "",
            "## Research question and scope",
            "",
            f"**Query:** {packet['query']}",
            f"**Packet created (UTC):** {packet.get('created_at', 'not recorded')}",
            "",
        ]
        query_plan = packet.get("query_plan") or {}
        if query_plan:
            lines.extend(
                [
                    f"**Query language:** {query_plan.get('query_language', 'unknown')}",
                    f"**Fallback triggered:** {bool(query_plan.get('fallback_triggered'))}",
                    "",
                ]
            )
        context = packet.get("manuscript_context") or {}
        if context:
            lines.extend(f"- **{key.replace('_', ' ').title()}:** {value}" for key, value in context.items())
        else:
            lines.append("- No structured manuscript context was supplied.")

        lines.extend(["", "## Retrieval and verification method", ""])
        lines.append(
            "The workflow searched independent scholarly metadata providers by bounded "
            "facets, merged records by stable identifiers and normalized titles, preserved "
            "field conflicts, resolved explicitly open-access locations, and recorded local "
            "extraction methods and locators."
        )
        lines.extend(["", "### Provider coverage", ""])
        for provider, count in sorted(coverage.get("provider_mix", {}).items()):
            lines.append(f"- {provider}: {count} merged records")
        if not coverage.get("provider_mix"):
            lines.append("- No provider coverage was recorded.")

        lines.extend(["", "### Search facet coverage", ""])
        for facet, count in sorted(coverage.get("facet_mix", {}).items()):
            lines.append(f"- {facet}: {count} records")
        if not coverage.get("facet_mix"):
            lines.append("- No facet coverage was recorded.")

        lines.extend(["", "### Verification coverage", ""])
        for status, count in sorted(coverage.get("verification_mix", {}).items()):
            lines.append(f"- {status}: {count} records")

        lines.extend(["", "## Evidence-supported candidate findings", ""])
        candidates = packet["synthesis"].get("consensus_candidates") or []
        for item in candidates:
            lines.append(f"- [{item['reference_id']}] {item['finding']}")
        if not candidates:
            lines.append("- No candidate findings were extracted from available abstracts/full text.")

        lines.extend(["", "## Conflicting, null, or limitation evidence", ""])
        conflicts = packet["synthesis"].get("conflicting_evidence") or []
        for item in conflicts:
            lines.append(f"- [{item['reference_id']}] {item['finding']}")
        if not conflicts:
            lines.append(
                "- No explicit conflict wording was detected. This is an absence-of-detection "
                "signal, not evidence of consensus."
            )

        lines.extend(["", "## Methodological patterns", ""])
        for design, count in sorted(packet["synthesis"].get("methodological_patterns", {}).items()):
            lines.append(f"- {design}: {count}")

        lines.extend(["", "## Open-access and extraction status", ""])
        lines.extend(
            [
                f"- Records marked open access: {coverage['open_access_records']}",
                f"- Records with locally extracted full text: {coverage['full_text_extracted']}",
                f"- Records with metadata conflicts preserved: {coverage['records_with_field_conflicts']}",
            ]
        )

        lines.extend(["", "## Provider metadata conflicts", ""])
        metadata_conflicts = [
            reference
            for reference in packet["references"]
            if reference.get("field_conflicts")
        ]
        for reference in metadata_conflicts:
            fields = ", ".join(sorted(reference["field_conflicts"]))
            lines.append(f"- [{reference['reference_id']}] conflicting fields: {fields}")
        if not metadata_conflicts:
            lines.append("- No cross-provider metadata conflicts were recorded.")

        lines.extend(["", "## Research gaps and limitations", ""])
        for gap in packet["synthesis"].get("research_gaps") or []:
            lines.append(f"- {gap}")
        for warning in packet.get("warnings") or []:
            lines.append(f"- {warning}")
        failed = [item for item in packet.get("search_ledger") or [] if item.get("status") == "error"]
        for item in failed:
            lines.append(
                f"- Provider pass failed: {item.get('provider', 'unknown')} / "
                f"{item.get('facet', 'unknown')}: {item.get('error', 'unknown error')}"
            )

        lines.extend(["", "## Reference index", ""])
        for reference in packet["references"]:
            identifier = reference.get("doi") or reference.get("pmid") or reference.get("url") or "no stable identifier"
            provenance = reference.get("provenance") or []
            providers = ", ".join(reference.get("providers") or []) or "unknown provider"
            retrieved = provenance[0].get("retrieved_at") if provenance else "not recorded"
            lines.append(
                f"- **[{reference['reference_id']}] {reference['title']}** "
                f"({reference.get('year') or 'n.d.'}; {reference['verification_status']}; "
                f"{identifier}; providers: {providers}; first retrieved: {retrieved})"
            )

        lines.extend(
            [
                "",
                "## Interpretation boundaries",
                "",
                "- **Retrieved metadata:** provider-supplied bibliographic fields and metrics.",
                "- **Evidence:** source text with a source type, extraction method, locator, and provenance; page extraction is not automatically full-text review.",
                "- **Inference:** any comparison or causal interpretation requires explicit expert review.",
                "- **Recommendation:** no clinical, policy, or experimental recommendation is inferred automatically.",
                "",
            ]
        )
        return "\n".join(lines)


def save_report(
    packet: dict[str, Any],
    directory: str | Path,
    *,
    synthesizer: Synthesizer | None = None,
) -> dict[str, str]:
    destination = Path(directory)
    destination.mkdir(parents=True, exist_ok=True)
    renderer = synthesizer or EvidenceReportSynthesizer()
    report = renderer.synthesize(packet)
    report_path = destination / "research-report.md"
    outline_path = destination / "research-report-data.json"
    report_path.write_text(report, encoding="utf-8")
    outline_path.write_text(
        json.dumps(
            {
                "created_at": packet.get("created_at"),
                "query": packet["query"],
                "query_plan": packet.get("query_plan") or {},
                "manuscript_context": packet.get("manuscript_context") or {},
                "coverage": packet["coverage"],
                "references": packet["references"],
                "claim_source_map": packet["claim_source_map"],
                "synthesis": packet["synthesis"],
                "search_ledger": packet.get("search_ledger") or [],
                "extraction_ledger": packet.get("extraction_ledger") or [],
                "warnings": packet.get("warnings") or [],
                "interpretation_boundaries": packet["interpretation_boundaries"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {"research_report": str(report_path), "research_report_data": str(outline_path)}
