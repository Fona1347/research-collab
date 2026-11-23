"""Stable optional evidence handoff contracts without importing another Skill."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Protocol


@dataclass(slots=True)
class EvidenceRecord:
    """Provider-neutral direct-evidence handoff with tolerant optional identifiers."""

    text: str
    source_id: str
    source_type: str = "evidence"
    doi: str = ""
    pmid: str = ""
    pmcid: str = ""
    doc_id: str = ""
    chunk_id: str = ""
    offset: int | None = None
    page_number: int | None = None
    locator: str = ""
    direct_evidence: bool = True
    inference: str = ""
    partial: bool = False
    truncated: bool = False
    warnings: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EvidenceProvider(Protocol):
    """Optional evidence source boundary, including a future Sciverse adapter."""

    name: str

    def configured(self) -> bool: ...

    def retrieve_evidence(
        self,
        question: str,
        *,
        constraints: Mapping[str, Any] | None = None,
        request_budget: int = 1,
    ) -> list[EvidenceRecord]: ...


@dataclass(slots=True)
class EvidenceHandoff:
    """Serializable handoff accepted from an independently maintained provider."""

    provider: str
    question: str
    records: list[EvidenceRecord] = field(default_factory=list)
    partial: bool = False
    truncated: bool = False
    warnings: list[str] = field(default_factory=list)
    provider_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "question": self.question,
            "records": [record.to_dict() for record in self.records],
            "partial": self.partial,
            "truncated": self.truncated,
            "warnings": list(self.warnings),
            "provider_metadata": dict(self.provider_metadata),
        }
