#!/usr/bin/env python3
"""Small offline checks for query planning, routing, pacing, and PDF fallback."""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILL_SCRIPTS = PROJECT_ROOT / "skills" / "research-lookup-enhanced" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

from rle.extraction import (  # noqa: E402
    ParsedDocument,
    ParserUnavailable,
    PdfParserChain,
)
from rle.http_client import HttpClient, TransportResponse  # noqa: E402
from rle.models import PaperRecord, Provenance  # noqa: E402
from rle.providers import ProviderStatus, SearchFilters, SemanticScholarProvider  # noqa: E402
from rle.query_plan import build_query_plan  # noqa: E402
from rle.source_router import SourceRouter  # noqa: E402


class FakeProvider:
    def __init__(
        self,
        name: str,
        records: list[PaperRecord] | None = None,
        *,
        fail: bool = False,
        configured: bool = True,
    ) -> None:
        self.name = name
        self.records = records or []
        self.fail = fail
        self.configured_value = configured
        self.capabilities = ("search", "get_paper", "provenance")

    def status(self) -> ProviderStatus:
        return ProviderStatus(
            self.name,
            self.configured_value,
            "" if self.configured_value else "not configured",
            self.capabilities,
        )

    def search(self, query: str, **_: Any) -> list[PaperRecord]:
        if self.fail:
            raise RuntimeError(f"{self.name} synthetic failure")
        output: list[PaperRecord] = []
        for record in self.records:
            copy = PaperRecord.from_dict(record.to_dict())
            copy.provenance.append(
                Provenance(provider=self.name, operation="search")
            )
            output.append(copy)
        return output

    def get_paper(self, identifier: str) -> PaperRecord | None:
        values = self.search(identifier)
        return values[0] if values else None


class NeverCalledParser:
    name = "mineru"

    def __init__(self) -> None:
        self.called = False

    def parse(self, *_: Any, **__: Any) -> ParsedDocument:
        self.called = True
        raise AssertionError("Unauthorized MinerU parser must not be called.")


class FailingRemoteParser:
    name = "mineru"

    def parse(self, *_: Any, **__: Any) -> ParsedDocument:
        raise RuntimeError("synthetic MinerU outage")


class UnavailableParser:
    name = "markitdown"

    def parse(self, *_: Any, **__: Any) -> ParsedDocument:
        raise ParserUnavailable("synthetic MarkItDown absence")


class SuccessfulParser:
    def __init__(self, name: str) -> None:
        self.name = name

    def parse(
        self,
        path: str | Path,
        *,
        output_dir: str | Path,
        max_chars: int = 500_000,
    ) -> ParsedDocument:
        del max_chars
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        markdown = output / "document.md"
        markdown.write_text("# Parsed\n\nOffline parser result.\n", encoding="utf-8")
        return ParsedDocument(
            url="",
            text="Offline parser result.",
            markdown="# Parsed\n\nOffline parser result.",
            source_type="pdf",
            extraction_method=f"{self.name}-synthetic",
            sections=[{"title": "Parsed", "text": "Offline parser result."}],
            local_path=str(path),
            parser_name=self.name,
            parser_version="synthetic",
            local_output_paths={"markdown": str(markdown)},
        )


def check_query_plans() -> None:
    configuration = {
        "openalex": True,
        "semantic_scholar": True,
        "crossref": True,
        "europe_pmc": True,
    }
    chinese = build_query_plan(
        "柔性石墨烯传感器如何用于帕金森病步态监测？",
        provider_configuration=configuration,
    )
    assert chinese.original_query.endswith("？")
    assert chinese.query_language == "zh"
    assert chinese.variant("original") is not None
    assert chinese.variant("english-term-expansion") is not None
    assert len(chinese.query_variants) <= 6
    assert chinese.to_dict() == build_query_plan(
        "柔性石墨烯传感器如何用于帕金森病步态监测？",
        provider_configuration=configuration,
    ).to_dict()

    weak_engineering = build_query_plan(
        "铁电材料用于时序计算的研究空白",
        provider_configuration=configuration,
    )
    assert weak_engineering.variant("english-term-expansion") is None
    assert weak_engineering.router_confidence == 0.58

    translated_engineering = build_query_plan(
        "铁电器件用于时序计算的研究空白与潜在方向",
        english_query=(
            "ferroelectric devices temporal computing "
            "time-series information processing"
        ),
        provider_configuration=configuration,
    )
    assert translated_engineering.original_query.startswith("铁电器件")
    assert translated_engineering.ranking_query_variant_id == (
        "english-term-expansion"
    )
    assert translated_engineering.ranking_query().startswith(
        "ferroelectric devices"
    )
    assert translated_engineering.router_confidence == 0.84

    biomedical = build_query_plan(
        "Clinical outcomes of CRISPR base editing for sickle cell disease",
        provider_configuration=configuration,
    )
    assert biomedical.recommended_provider_route[0]["provider"] == "europe_pmc"
    assert "clinical" in {
        value.casefold() for value in biomedical.materials_or_objects
    } or biomedical.router_confidence >= 0.9

    identifier = build_query_plan(
        "DOI:10.1038/s41586-020-2649-2",
        provider_configuration=configuration,
    )
    assert identifier.identifiers["doi"] == "10.1038/s41586-020-2649-2"
    assert identifier.variant("stable-identifier") is not None
    assert identifier.router_confidence >= 0.95


def check_router_fallback() -> None:
    query = "cross-disciplinary adaptive sensor validation"
    plan = build_query_plan(
        query,
        global_request_budget=8,
        provider_budgets={
            "openalex": 2,
            "crossref": 2,
            "semantic_scholar": 1,
            "europe_pmc": 2,
        },
        provider_configuration={
            "openalex": True,
            "crossref": True,
            "semantic_scholar": False,
            "europe_pmc": True,
        },
    )
    providers = [
        FakeProvider("openalex", fail=True),
        FakeProvider(
            "crossref",
            [
                PaperRecord(
                    title="Adaptive sensor validation",
                    doi="10.1000/crossref-record",
                )
            ],
        ),
        FakeProvider(
            "europe_pmc",
            [
                PaperRecord(
                    title="Biomedical adaptive sensor",
                    pmid="1001",
                ),
                PaperRecord(
                    title="Clinical sensor validation",
                    pmid="1002",
                ),
            ],
        ),
    ]
    ledger: list[dict[str, Any]] = []
    result = SourceRouter(
        providers,
        query_plan=plan,
        filters=SearchFilters(),
        max_results_per_request=5,
        fallback_threshold=3,
        stable_identifier_threshold=0.5,
    ).run(ledger)
    assert plan.fallback_triggered
    assert "openalex" in result.failed_providers
    assert result.records
    assert any(item.get("route_stage") == "coverage-fallback" for item in ledger)
    assert any(record.retrieval_routes for record in result.records)
    assert result.budget["global"]["used"] <= result.budget["global"]["limit"]


def check_semantic_scholar_serialization() -> None:
    assert SemanticScholarProvider.min_interval >= 1.1
    assert SemanticScholarProvider.serialize_requests is True

    state = {"active": 0, "max_active": 0}
    state_lock = threading.Lock()

    def transport(
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
        timeout: float,
    ) -> TransportResponse:
        del method, headers, body, timeout
        with state_lock:
            state["active"] += 1
            state["max_active"] = max(state["max_active"], state["active"])
        time.sleep(0.02)
        with state_lock:
            state["active"] -= 1
        return TransportResponse(
            status=200,
            url=url,
            headers={"content-type": "application/json"},
            body=b"{}",
        )

    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="rle-http-smoke-") as temporary:
        clients = [
            HttpClient(
                "semantic_scholar",
                cache_dir=temporary,
                min_interval=0.0,
                serialize_requests=True,
                serialization_key="semantic_scholar",
                transport=transport,
            )
            for _ in range(2)
        ]

        def worker(index: int) -> None:
            try:
                clients[index % len(clients)].get_json(
                    "https://example.invalid/search",
                    params={"index": index},
                    use_cache=False,
                )
            except Exception as exc:  # pragma: no cover - diagnostic capture
                errors.append(str(exc))

        threads = [
            threading.Thread(target=worker, args=(index,))
            for index in range(5)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    assert not errors, errors
    assert state["max_active"] == 1


def check_pdf_fallback() -> None:
    with tempfile.TemporaryDirectory(prefix="rle-pdf-smoke-") as temporary:
        root = Path(temporary)
        source = root / "fake.pdf"
        source.write_bytes(b"%PDF-1.4\n% offline smoke artifact\n")

        remote = NeverCalledParser()
        unauthorized_chain = PdfParserChain(
            allow_remote_parser=False,
            is_open_access=True,
            mineru_parser=remote,
            markitdown_parser=UnavailableParser(),
            pypdf_parser=SuccessfulParser("pypdf"),
        )
        unauthorized = unauthorized_chain.parse(
            source,
            output_dir=root / "unauthorized",
        )
        assert not remote.called
        assert unauthorized.parser_name == "pypdf"
        assert any(
            item.get("parser") == "mineru" and item.get("status") == "skipped"
            for item in unauthorized.parser_provenance
        )

        unavailable_chain = PdfParserChain(
            allow_remote_parser=True,
            is_open_access=True,
            mineru_parser=FailingRemoteParser(),
            markitdown_parser=SuccessfulParser("markitdown"),
            pypdf_parser=SuccessfulParser("pypdf"),
        )
        unavailable = unavailable_chain.parse(
            source,
            output_dir=root / "unavailable",
        )
        assert unavailable.parser_name == "markitdown"
        assert any("synthetic MinerU outage" in value for value in unavailable.errors)
        assert Path(unavailable.local_output_paths["parser_ledger"]).exists()


def main() -> int:
    checks = {
        "query_plans": check_query_plans,
        "router_fallback": check_router_fallback,
        "semantic_scholar_serialization": check_semantic_scholar_serialization,
        "pdf_fallback": check_pdf_fallback,
    }
    completed: list[str] = []
    for name, check in checks.items():
        check()
        completed.append(name)
    print(json.dumps({"offline_smoke": "ok", "checks": completed}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
