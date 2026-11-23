"""Core package for the research-lookup-enhanced skill."""

from .evidence_provider import EvidenceHandoff, EvidenceProvider, EvidenceRecord
from .models import EvidenceChunk, FullTextLocation, PaperRecord, Provenance
from .query_plan import QueryPlan, QueryVariant
from .research_profile import (
    EffectiveRunConfig,
    ResearchLevelDecision,
    ResearchLevelResolver,
    ResearchProfile,
)

__all__ = [
    "EvidenceChunk",
    "EvidenceHandoff",
    "EvidenceProvider",
    "EvidenceRecord",
    "EffectiveRunConfig",
    "FullTextLocation",
    "PaperRecord",
    "Provenance",
    "QueryPlan",
    "QueryVariant",
    "ResearchLevelDecision",
    "ResearchLevelResolver",
    "ResearchProfile",
]
