"""Local extraction for public web pages, JATS XML, and OA PDF files."""

from __future__ import annotations

import hashlib
from importlib import metadata
import ipaddress
import json
import os
import sys
import re
import subprocess
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree

from .http_client import HttpClient, HttpRequestError
from .models import EvidenceChunk, FullTextLocation, PaperRecord, Provenance, utc_now
from .providers import unique_locations


@dataclass(slots=True)
class ParsedDocument:
    """Unified parser output for HTML, JATS, MinerU, MarkItDown, and pypdf."""

    url: str
    title: str = ""
    authors: list[str] = field(default_factory=list)
    publication_date: str = ""
    text: str = ""
    source_type: str = "webpage"
    extraction_method: str = ""
    sections: list[dict[str, str]] = field(default_factory=list)
    tables: list[dict[str, str]] = field(default_factory=list)
    captions: list[dict[str, str]] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    content_hash: str = ""
    local_path: str = ""
    retrieved_at: str = field(default_factory=utc_now)
    warnings: list[str] = field(default_factory=list)
    markdown: str = ""
    source_file_hash: str = ""
    parser_name: str = ""
    parser_version: str = ""
    local_output_paths: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    parser_provenance: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.source_file_hash:
            self.source_file_hash = self.content_hash
        if not self.content_hash:
            self.content_hash = self.source_file_hash
        if not self.parser_name:
            self.parser_name = self.extraction_method
        if not self.extraction_method:
            self.extraction_method = self.parser_name
        if self.local_path and "source" not in self.local_output_paths:
            self.local_output_paths["source"] = self.local_path

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def evidence_chunks(self, *, max_chunks: int = 40) -> list[EvidenceChunk]:
        chunks: list[EvidenceChunk] = []
        seen: set[tuple[str, str, str]] = set()

        def append(text: str, source_type: str, locator: str) -> None:
            value = re.sub(r"\s+", " ", str(text or "")).strip()
            key = (value, source_type, locator)
            if not value or key in seen:
                return
            seen.add(key)
            chunks.append(
                EvidenceChunk(
                    text=value,
                    source_type=source_type,
                    locator=locator,
                    url=self.url,
                    extraction_method=self.extraction_method,
                    content_hash=hashlib.sha256(value.encode("utf-8")).hexdigest(),
                )
            )

        for section in self.sections:
            append(
                str(section.get("text") or ""),
                self.source_type,
                str(section.get("title") or "section"),
            )
        for index, table in enumerate(self.tables, start=1):
            label = str(table.get("label") or f"table-{index}")
            text = " ".join(
                value
                for value in (
                    str(table.get("caption") or ""),
                    str(table.get("text") or ""),
                )
                if value
            )
            append(text, "table", label)
        for index, caption in enumerate(self.captions, start=1):
            append(
                str(caption.get("text") or ""),
                "figure-caption" if caption.get("type") == "fig" else "table-caption",
                str(caption.get("label") or f"caption-{index}"),
            )
        for index, reference in enumerate(self.references[:20], start=1):
            append(reference, "reference-list", f"reference-{index}")
        if not chunks and self.text:
            paragraphs = split_text(self.text)
            for index, text in enumerate(paragraphs, start=1):
                append(text, self.source_type, f"chunk-{index}")
        return chunks[:max_chunks]


ExtractedDocument = ParsedDocument


class Extractor(Protocol):
    def extract_url(
        self,
        url: str,
        *,
        expected_kind: str = "",
        download_dir: str | Path | None = None,
        is_open_access: bool = False,
    ) -> ParsedDocument: ...


class ParserUnavailable(RuntimeError):
    """Raised when an optional parser cannot run in the current environment."""


class DocumentParser(Protocol):
    name: str

    def parse(
        self,
        path: str | Path,
        *,
        output_dir: str | Path,
        max_chars: int = 500_000,
    ) -> ParsedDocument: ...


def split_text(text: str, *, target_chars: int = 1800) -> list[str]:
    paragraphs = [
        re.sub(r"\s+", " ", value).strip()
        for value in re.split(r"\n\s*\n|(?<=[.!?])\s+(?=[A-Z0-9])", text or "")
    ]
    paragraphs = [value for value in paragraphs if len(value) >= 40]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if current and len(current) + len(paragraph) + 1 > target_chars:
            chunks.append(current)
            current = paragraph
        else:
            current = f"{current} {paragraph}".strip()
    if current:
        chunks.append(current)
    return chunks


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _redact_configured_secrets(text: str) -> str:
    """Keep subprocess diagnostics useful without persisting configured secrets."""
    redacted = str(text or "")
    for variable in (
        "MINERU_API_KEY",
        "OPENALEX_API_KEY",
        "SEMANTIC_SCHOLAR_API_KEY",
        "EASYSCHOLAR_SECRET_KEY",
        "SCIVERSE_API_TOKEN",
    ):
        value = os.environ.get(variable, "")
        if value:
            redacted = redacted.replace(value, "***")
    return redacted


def _markdown_sections(markdown: str) -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    heading = "document"
    content: list[str] = []

    def flush() -> None:
        value = "\n".join(content).strip()
        if value:
            sections.append({"title": heading, "text": value})

    for line in markdown.splitlines():
        match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*$", line)
        if match:
            flush()
            heading = match.group(1).strip()
            content = []
        else:
            content.append(line)
    flush()
    if not sections and markdown.strip():
        sections = [{"title": "document", "text": markdown.strip()}]
    return sections


def _markdown_tables(markdown: str) -> list[dict[str, str]]:
    lines = markdown.splitlines()
    tables: list[dict[str, str]] = []
    index = 0
    while index + 1 < len(lines):
        if (
            "|" in lines[index]
            and re.match(
                r"^\s*\|?\s*:?-{3,}",
                lines[index + 1],
            )
        ):
            table_lines = [lines[index], lines[index + 1]]
            index += 2
            while index < len(lines) and "|" in lines[index] and lines[index].strip():
                table_lines.append(lines[index])
                index += 1
            tables.append(
                {
                    "label": f"table-{len(tables) + 1}",
                    "caption": "",
                    "text": "\n".join(table_lines),
                }
            )
            continue
        index += 1
    return tables


def _caption_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return " ".join(
            str(part).strip() for part in value if str(part).strip()
        )
    return ""


class MinerUParser:
    """Remote MinerU wrapper adapter; execution requires explicit caller consent."""

    name = "mineru"

    def __init__(
        self,
        *,
        allow_remote: bool,
        is_open_access: bool,
        python_executable: str | None = None,
        wrapper_path: str | None = None,
        model: str = "vlm",
        language: str = "ch",
        timeout_seconds: int = 1800,
    ) -> None:
        self.allow_remote = bool(allow_remote)
        self.is_open_access = bool(is_open_access)
        settings_path = Path(__file__).resolve().parents[2] / "config" / "local.json"
        settings = json.loads(settings_path.read_text(encoding="utf-8")) if settings_path.is_file() else {}
        self.python_executable = Path(python_executable or os.environ.get("MINERU_PYTHON") or settings.get("mineru_python") or sys.executable)
        wrapper = wrapper_path or os.environ.get("MINERU_WRAPPER") or settings.get("mineru_wrapper")
        self.wrapper_path = Path(wrapper) if wrapper else None
        self.model = model
        self.language = language
        self.timeout_seconds = max(60, int(timeout_seconds))

    def _read_outputs(
        self,
        source: Path,
        output: Path,
        *,
        max_chars: int,
        reused: bool,
    ) -> ParsedDocument:
        manifest_path = output / "manifest.json"
        markdown_path = output / "full.md"
        content_path = output / "content_list.json"
        if not manifest_path.exists() or not markdown_path.exists():
            raise RuntimeError(
                "MinerU output is incomplete; manifest.json and full.md are required."
            )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        markdown = markdown_path.read_text(encoding="utf-8", errors="replace")
        content_items: list[dict[str, Any]] = []
        warnings = [str(value) for value in manifest.get("notes") or []]
        if content_path.exists():
            try:
                raw_content = json.loads(content_path.read_text(encoding="utf-8"))
                if isinstance(raw_content, list):
                    content_items = [
                        item for item in raw_content if isinstance(item, dict)
                    ]
                else:
                    warnings.append("MinerU content_list.json is not a JSON array.")
            except json.JSONDecodeError as exc:
                warnings.append(f"MinerU content_list.json is invalid JSON: {exc}")
        else:
            warnings.append("MinerU content_list.json is unavailable.")

        tables: list[dict[str, str]] = []
        captions: list[dict[str, str]] = []
        references: list[str] = []
        for index, item in enumerate(content_items, start=1):
            item_type = str(item.get("type") or "").casefold()
            page = item.get("page_idx")
            page_label = (
                f"page-{page + 1}" if isinstance(page, int) else f"block-{index}"
            )
            if item_type == "table":
                caption = _caption_text(
                    item.get("table_caption") or item.get("caption")
                )
                table_text = str(
                    item.get("table_body")
                    or item.get("html")
                    or item.get("text")
                    or ""
                ).strip()
                tables.append(
                    {
                        "label": page_label,
                        "caption": caption,
                        "text": table_text,
                    }
                )
                if caption:
                    captions.append(
                        {"label": page_label, "text": caption, "type": "table-wrap"}
                    )
            elif item_type in {"image", "chart"}:
                caption = _caption_text(
                    item.get("image_caption") or item.get("caption")
                )
                if caption:
                    captions.append(
                        {"label": page_label, "text": caption, "type": "fig"}
                    )
            elif item_type in {"reference", "ref"}:
                value = str(item.get("text") or "").strip()
                if value:
                    references.append(value)

        source_hash = str(
            (manifest.get("source") or {}).get("input_sha256")
            or _file_hash(source)
        )
        mineru = manifest.get("mineru") or {}
        local_paths = {
            "manifest": str(manifest_path),
            "markdown": str(markdown_path),
            "output_directory": str(output),
        }
        if content_path.exists():
            local_paths["content_list"] = str(content_path)
        images = output / "images"
        if images.exists():
            local_paths["images"] = str(images)
        return ParsedDocument(
            url="",
            text=markdown[:max_chars],
            markdown=markdown[:max_chars],
            source_type="pdf",
            extraction_method="mineru-remote-api-wrapper",
            sections=_markdown_sections(markdown[:max_chars]),
            tables=tables,
            captions=captions,
            references=references,
            content_hash=source_hash,
            source_file_hash=source_hash,
            local_path=str(source),
            parser_name=self.name,
            parser_version=f"manifest-v{manifest.get('schema_version', 'unknown')}",
            local_output_paths=local_paths,
            warnings=warnings,
            parser_provenance=[
                {
                    "parser": self.name,
                    "status": "reused" if reused else "ok",
                    "remote": True,
                    "model": mineru.get("model") or self.model,
                    "manifest_schema": manifest.get("schema_version"),
                    "output": str(output),
                }
            ],
        )

    def parse(
        self,
        path: str | Path,
        *,
        output_dir: str | Path,
        max_chars: int = 500_000,
    ) -> ParsedDocument:
        source = Path(path).resolve()
        output = Path(output_dir).resolve()
        if not self.allow_remote:
            raise ParserUnavailable(
                "MinerU remote parsing was not authorized by --allow-remote-parser."
            )
        if not self.is_open_access:
            raise ParserUnavailable(
                "MinerU remote parsing requires a PDF explicitly marked open access."
            )
        if not self.python_executable.exists():
            raise ParserUnavailable(
                f"MinerU Python executable is unavailable: {self.python_executable}"
            )
        if self.wrapper_path is None or not self.wrapper_path.is_file():
            raise ParserUnavailable(
                f"MinerU wrapper is unavailable: {self.wrapper_path}"
            )
        if not os.environ.get("MINERU_API_KEY"):
            raise ParserUnavailable("MINERU_API_KEY is not configured.")
        if output.exists() and any(output.iterdir()):
            return self._read_outputs(
                source,
                output,
                max_chars=max_chars,
                reused=True,
            )
        output.parent.mkdir(parents=True, exist_ok=True)
        command = [
            str(self.python_executable),
            str(self.wrapper_path),
            "--input",
            str(source),
            "--output",
            str(output),
            "--model",
            self.model,
            "--language",
            self.language,
            "--timeout-seconds",
            str(self.timeout_seconds),
        ]
        try:
            process = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds + 60,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise RuntimeError(f"MinerU wrapper execution failed: {exc}") from exc
        if process.returncode != 0:
            detail = _redact_configured_secrets(
                (process.stderr or process.stdout or "").strip()[-2000:]
            )
            raise RuntimeError(
                "MinerU wrapper returned "
                f"exit code {process.returncode}: {detail or 'no error detail'}"
            )
        return self._read_outputs(
            source,
            output,
            max_chars=max_chars,
            reused=False,
        )


class MarkItDownParser:
    """Lazy Microsoft MarkItDown PDF conversion fallback."""

    name = "markitdown"

    def parse(
        self,
        path: str | Path,
        *,
        output_dir: str | Path,
        max_chars: int = 500_000,
    ) -> ParsedDocument:
        try:
            from markitdown import MarkItDown  # type: ignore
        except ImportError as exc:
            raise ParserUnavailable(
                "MarkItDown is not installed; install the optional markitdown group."
            ) from exc

        source = Path(path).resolve()
        output = Path(output_dir).resolve()
        output.mkdir(parents=True, exist_ok=True)
        try:
            converter = MarkItDown(enable_plugins=False)
        except TypeError:
            converter = MarkItDown()
        try:
            result = converter.convert(str(source))
            markdown = str(getattr(result, "text_content", "") or "")
        except Exception as exc:
            raise RuntimeError(f"MarkItDown PDF conversion failed: {exc}") from exc
        if not markdown.strip():
            raise RuntimeError("MarkItDown returned no text.")
        markdown = markdown[:max_chars]
        markdown_path = output / "document.md"
        markdown_path.write_text(markdown, encoding="utf-8")
        try:
            version = metadata.version("markitdown")
        except metadata.PackageNotFoundError:
            version = "unknown"
        digest = _file_hash(source)
        return ParsedDocument(
            url="",
            text=markdown,
            markdown=markdown,
            source_type="pdf",
            extraction_method="markitdown-pdf",
            sections=_markdown_sections(markdown),
            tables=_markdown_tables(markdown),
            content_hash=digest,
            source_file_hash=digest,
            local_path=str(source),
            parser_name=self.name,
            parser_version=version,
            local_output_paths={
                "source": str(source),
                "markdown": str(markdown_path),
                "output_directory": str(output),
            },
            warnings=[
                "MarkItDown is a lightweight LLM-oriented structure conversion; "
                "it is not equivalent to MinerU layout, formula, or table parsing."
            ],
            parser_provenance=[
                {
                    "parser": self.name,
                    "status": "ok",
                    "remote": False,
                    "version": version,
                    "output": str(markdown_path),
                }
            ],
        )


class PypdfParser:
    """Lightweight page-text final fallback with low structure fidelity."""

    name = "pypdf"

    def parse(
        self,
        path: str | Path,
        *,
        output_dir: str | Path,
        max_chars: int = 500_000,
    ) -> ParsedDocument:
        try:
            import pypdf  # type: ignore
            from pypdf import PdfReader  # type: ignore
        except ImportError as exc:
            raise ParserUnavailable("pypdf is not installed.") from exc
        source = Path(path).resolve()
        output = Path(output_dir).resolve()
        output.mkdir(parents=True, exist_ok=True)
        try:
            reader = PdfReader(str(source))
            sections: list[dict[str, str]] = []
            markdown_parts: list[str] = []
            char_count = 0
            for page_number, page in enumerate(reader.pages, start=1):
                value = str(page.extract_text() or "").strip()
                if not value:
                    continue
                remaining = max_chars - char_count
                if remaining <= 0:
                    break
                value = value[:remaining]
                sections.append(
                    {"title": f"Page {page_number}", "text": value}
                )
                markdown_parts.extend([f"## Page {page_number}", "", value, ""])
                char_count += len(value)
        except Exception as exc:
            raise RuntimeError(f"pypdf text extraction failed: {exc}") from exc
        markdown = "\n".join(markdown_parts).strip()
        if not markdown:
            raise RuntimeError("pypdf extracted no usable page text.")
        markdown_path = output / "document.md"
        markdown_path.write_text(
            markdown + ("\n" if markdown else ""),
            encoding="utf-8",
        )
        digest = _file_hash(source)
        return ParsedDocument(
            url="",
            text="\n\n".join(section["text"] for section in sections),
            markdown=markdown,
            source_type="pdf",
            extraction_method="pypdf-page-text",
            sections=sections,
            content_hash=digest,
            source_file_hash=digest,
            local_path=str(source),
            parser_name=self.name,
            parser_version=str(getattr(pypdf, "__version__", "unknown")),
            local_output_paths={
                "source": str(source),
                "markdown": str(markdown_path),
                "output_directory": str(output),
            },
            warnings=[
                "pypdf extracted basic page text with low structure fidelity; "
                "tables, formulas, reading order, and layout may be incomplete."
            ],
            parser_provenance=[
                {
                    "parser": self.name,
                    "status": "ok",
                    "remote": False,
                    "version": str(getattr(pypdf, "__version__", "unknown")),
                    "output": str(markdown_path),
                    "structure_fidelity": "low",
                }
            ],
        )


class PdfParserChain:
    """MinerU -> MarkItDown -> pypdf with explicit remote-upload gating."""

    def __init__(
        self,
        *,
        allow_remote_parser: bool = False,
        is_open_access: bool = False,
        mineru_parser: DocumentParser | None = None,
        markitdown_parser: DocumentParser | None = None,
        pypdf_parser: DocumentParser | None = None,
    ) -> None:
        self.allow_remote_parser = bool(allow_remote_parser)
        self.is_open_access = bool(is_open_access)
        self.mineru_parser = mineru_parser or MinerUParser(
            allow_remote=self.allow_remote_parser,
            is_open_access=self.is_open_access,
        )
        self.markitdown_parser = markitdown_parser or MarkItDownParser()
        self.pypdf_parser = pypdf_parser or PypdfParser()

    def parse(
        self,
        path: str | Path,
        *,
        output_dir: str | Path,
        max_chars: int = 500_000,
    ) -> ParsedDocument:
        source = Path(path).resolve()
        output = Path(output_dir).resolve()
        output.mkdir(parents=True, exist_ok=True)
        attempts: list[dict[str, Any]] = []
        errors: list[str] = []
        warnings: list[str] = []

        def save_parser_ledger(selected_parser: str) -> str:
            ledger_path = output / "parser-ledger.json"
            ledger_path.write_text(
                json.dumps(
                    {
                        "source": str(source),
                        "source_file_hash": _file_hash(source),
                        "selected_parser": selected_parser,
                        "allow_remote_parser": self.allow_remote_parser,
                        "explicitly_open_access": self.is_open_access,
                        "attempts": attempts,
                        "warnings": _deduplicate_strings(warnings),
                        "errors": _deduplicate_strings(errors),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            return str(ledger_path)

        parsers: list[tuple[str, DocumentParser, Path, bool]] = [
            ("mineru", self.mineru_parser, output / "mineru", True),
            ("markitdown", self.markitdown_parser, output / "markitdown", False),
            ("pypdf", self.pypdf_parser, output / "pypdf", False),
        ]
        for name, parser, parser_output, remote in parsers:
            if name == "mineru" and not self.allow_remote_parser:
                reason = (
                    "MinerU skipped because remote PDF upload was not explicitly allowed."
                )
                attempts.append(
                    {
                        "parser": name,
                        "status": "skipped",
                        "remote": True,
                        "reason": reason,
                    }
                )
                warnings.append(reason)
                continue
            if name == "mineru" and not self.is_open_access:
                reason = (
                    "MinerU skipped because the PDF was not explicitly marked open access."
                )
                attempts.append(
                    {
                        "parser": name,
                        "status": "skipped",
                        "remote": True,
                        "reason": reason,
                    }
                )
                warnings.append(reason)
                continue
            try:
                document = parser.parse(
                    source,
                    output_dir=parser_output,
                    max_chars=max_chars,
                )
            except ParserUnavailable as exc:
                message = str(exc)
                attempts.append(
                    {
                        "parser": name,
                        "status": "unavailable",
                        "remote": remote,
                        "error": message,
                    }
                )
                warnings.append(message)
                continue
            except Exception as exc:
                message = str(exc)
                attempts.append(
                    {
                        "parser": name,
                        "status": "error",
                        "remote": remote,
                        "error": message,
                    }
                )
                errors.append(f"{name}: {message}")
                continue

            attempts.append(
                {
                    "parser": name,
                    "status": "ok",
                    "remote": remote,
                    "output_directory": str(parser_output),
                }
            )
            document.warnings = _deduplicate_strings(
                [*warnings, *document.warnings]
            )
            document.errors = _deduplicate_strings(
                [*errors, *document.errors]
            )
            document.parser_provenance = [
                *attempts,
                *document.parser_provenance,
            ]
            document.local_output_paths["parser_ledger"] = save_parser_ledger(
                document.parser_name or name
            )
            return document

        digest = _file_hash(source)
        document = ParsedDocument(
            url="",
            source_type="pdf",
            extraction_method="pdf-unparsed",
            content_hash=digest,
            source_file_hash=digest,
            local_path=str(source),
            parser_name="unparsed",
            parser_version="",
            local_output_paths={
                "source": str(source),
                "output_directory": str(output),
            },
            warnings=_deduplicate_strings(warnings),
            errors=_deduplicate_strings(
                [*errors, "No PDF parser produced a usable document."]
            ),
            parser_provenance=attempts,
        )
        document.local_output_paths["parser_ledger"] = save_parser_ledger(
            "unparsed"
        )
        return document


def _deduplicate_strings(values: list[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in output:
            output.append(text)
    return output


class _CleanHtmlParser(HTMLParser):
    block_tags = {
        "p",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "li",
        "blockquote",
        "pre",
        "article",
        "section",
    }
    skipped_tags = {
        "script",
        "style",
        "nav",
        "footer",
        "header",
        "aside",
        "form",
        "svg",
        "noscript",
    }
    boilerplate_tokens = {
        "advert",
        "advertisement",
        "ads",
        "banner",
        "breadcrumb",
        "cookie",
        "footer",
        "header",
        "menu",
        "nav",
        "navigation",
        "newsletter",
        "promo",
        "related",
        "share",
        "sidebar",
        "social",
    }
    author_meta = {
        "author",
        "article:author",
        "citation_author",
        "dc.creator",
        "parsely-author",
    }
    date_meta = {
        "article:published_time",
        "citation_date",
        "citation_publication_date",
        "date",
        "datepublished",
        "dc.date",
        "dc.date.issued",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip_tags: list[str] = []
        self.title_depth = 0
        self.title_parts: list[str] = []
        self.current: list[str] = []
        self.blocks: list[str] = []
        self.seen_blocks: set[str] = set()
        self.meta_authors: list[str] = []
        self.meta_dates: list[str] = []
        self.table_depth = 0
        self.table_parts: list[str] = []
        self.tables: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attributes = {str(key).lower(): str(value or "") for key, value in attrs}
        if tag == "meta":
            meta_key = (
                attributes.get("name")
                or attributes.get("property")
                or attributes.get("itemprop")
                or ""
            ).casefold()
            content = attributes.get("content", "").strip()
            if content and meta_key in self.author_meta and content not in self.meta_authors:
                self.meta_authors.append(content)
            if content and meta_key in self.date_meta and content not in self.meta_dates:
                self.meta_dates.append(content)

        marker_text = " ".join(
            (attributes.get("id", ""), attributes.get("class", ""), attributes.get("role", ""))
        ).casefold()
        marker_tokens = set(re.findall(r"[a-z0-9]+", marker_text))
        should_skip = tag in self.skipped_tags or bool(
            marker_tokens.intersection(self.boilerplate_tokens)
        )
        if should_skip:
            self.skip_tags.append(tag)
            return
        if self.skip_tags:
            return
        if tag == "title":
            self.title_depth += 1
        if tag == "table":
            self.table_depth += 1
        if tag in self.block_tags and self.current:
            self._flush()

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self.skip_tags:
            if tag == self.skip_tags[-1]:
                self.skip_tags.pop()
            return
        if tag == "title" and self.title_depth:
            self.title_depth -= 1
        if tag in self.block_tags:
            self._flush()
        if tag == "table" and self.table_depth:
            self.table_depth -= 1
            if not self.table_depth:
                text = re.sub(r"\s+", " ", " ".join(self.table_parts)).strip()
                if text:
                    self.tables.append(
                        {"label": f"table-{len(self.tables) + 1}", "caption": "", "text": text}
                    )
                self.table_parts = []

    def handle_data(self, data: str) -> None:
        if self.skip_tags:
            return
        value = re.sub(r"\s+", " ", data).strip()
        if not value:
            return
        if self.title_depth:
            self.title_parts.append(value)
        if self.table_depth:
            self.table_parts.append(value)
        self.current.append(value)

    def _flush(self) -> None:
        value = re.sub(r"\s+", " ", " ".join(self.current)).strip()
        key = value.casefold()
        if len(value) >= 30 and key not in self.seen_blocks:
            self.blocks.append(value)
            self.seen_blocks.add(key)
        self.current = []

    def finish(self) -> tuple[str, str, list[str], str, list[dict[str, str]]]:
        self._flush()
        title = re.sub(r"\s+", " ", " ".join(self.title_parts)).strip()
        return (
            title,
            "\n\n".join(self.blocks),
            list(self.meta_authors),
            self.meta_dates[0] if self.meta_dates else "",
            list(self.tables),
        )


def _stdlib_html(
    html_text: str,
) -> tuple[str, str, list[str], str, list[dict[str, str]]]:
    parser = _CleanHtmlParser()
    parser.feed(html_text)
    return parser.finish()


def extract_html(html_text: str, *, url: str = "", max_chars: int = 250_000) -> ParsedDocument:
    title = ""
    text = ""
    method = "stdlib-html-parser"
    warnings: list[str] = []

    try:
        import trafilatura  # type: ignore

        text = str(
            trafilatura.extract(
                html_text,
                url=url or None,
                include_comments=False,
                include_tables=True,
                favor_precision=True,
                output_format="txt",
            )
            or ""
        )
        method = "trafilatura"
    except ImportError:
        pass
    except Exception as exc:  # optional extractor failure should degrade locally
        warnings.append(f"trafilatura failed: {exc}")

    stdlib_title, stdlib_text, authors, publication_date, tables = _stdlib_html(html_text)
    title = stdlib_title
    if not text:
        try:
            from readability import Document  # type: ignore

            summary = str(Document(html_text).summary())
            readable_title, readable_text, _, _, _ = _stdlib_html(summary)
            title = readable_title or title
            text = readable_text
            method = "readability-lxml"
        except ImportError:
            pass
        except Exception as exc:
            warnings.append(f"readability-lxml failed: {exc}")

    if not text:
        try:
            from bs4 import BeautifulSoup  # type: ignore

            soup = BeautifulSoup(html_text, "html.parser")
            for node in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
                node.decompose()
            title = str(soup.title.string).strip() if soup.title and soup.title.string else title
            text = "\n\n".join(
                value.get_text(" ", strip=True)
                for value in soup.find_all(["h1", "h2", "h3", "p", "li", "blockquote"])
                if len(value.get_text(" ", strip=True)) >= 30
            )
            method = "beautifulsoup"
        except ImportError:
            pass
        except Exception as exc:
            warnings.append(f"BeautifulSoup failed: {exc}")

    if not text:
        text = stdlib_text
        method = "stdlib-html-parser"
    text = text[:max_chars].strip()
    digest = hashlib.sha256(html_text.encode("utf-8", errors="replace")).hexdigest()
    package_name = {
        "trafilatura": "trafilatura",
        "readability-lxml": "readability-lxml",
        "beautifulsoup": "beautifulsoup4",
    }.get(method)
    if package_name:
        try:
            parser_version = metadata.version(package_name)
        except metadata.PackageNotFoundError:
            parser_version = "unknown"
    else:
        parser_version = "python-stdlib"
    return ExtractedDocument(
        url=url,
        title=title,
        authors=authors,
        publication_date=publication_date,
        text=text,
        source_type="html",
        extraction_method=method,
        sections=[{"title": "document", "text": value} for value in split_text(text)],
        tables=tables,
        content_hash=digest,
        warnings=warnings,
        parser_name=method,
        parser_version=parser_version,
        parser_provenance=[
            {
                "parser": method,
                "version": parser_version,
                "status": "ok",
                "remote": False,
            }
        ],
    )


def _local_name(element: ElementTree.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _node_text(element: ElementTree.Element | None) -> str:
    if element is None:
        return ""
    return re.sub(r"\s+", " ", " ".join(element.itertext())).strip()


def _find_first(root: ElementTree.Element, name: str) -> ElementTree.Element | None:
    return next((node for node in root.iter() if _local_name(node) == name), None)


def extract_jats(xml_text: str, *, url: str = "", max_chars: int = 500_000) -> ParsedDocument:
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        raise ValueError(f"Invalid JATS/XML document: {exc}") from exc

    title = _node_text(_find_first(root, "article-title"))
    authors: list[str] = []
    for contributor in root.iter():
        if _local_name(contributor) != "contrib":
            continue
        if contributor.attrib.get("contrib-type", "author") != "author":
            continue
        name = _find_first(contributor, "name")
        if name is None:
            name = _find_first(contributor, "collab")
        value = _node_text(name)
        if value and value not in authors:
            authors.append(value)
    publication_date = ""
    for date_node in root.iter():
        if _local_name(date_node) != "pub-date":
            continue
        parts: list[str] = []
        for field_name in ("year", "month", "day"):
            value = _node_text(_find_first(date_node, field_name))
            if value:
                parts.append(value.zfill(2) if field_name != "year" else value)
        if parts:
            publication_date = "-".join(parts)
            break
    sections: list[dict[str, str]] = []
    abstract = _find_first(root, "abstract")
    abstract_text = _node_text(abstract)
    if abstract_text:
        sections.append({"title": "Abstract", "text": abstract_text})

    body = _find_first(root, "body")
    if body is not None:
        section_nodes = [node for node in body.iter() if _local_name(node) == "sec"]
        if section_nodes:
            for index, section in enumerate(section_nodes, start=1):
                heading = _node_text(_find_first(section, "title")) or f"Section {index}"
                paragraphs = [
                    _node_text(node)
                    for node in section
                    if _local_name(node) == "p" and _node_text(node)
                ]
                if paragraphs:
                    sections.append({"title": heading, "text": "\n\n".join(paragraphs)})
        else:
            paragraphs = [
                _node_text(node)
                for node in body.iter()
                if _local_name(node) == "p" and _node_text(node)
            ]
            if paragraphs:
                sections.append({"title": "Body", "text": "\n\n".join(paragraphs)})

    captions: list[dict[str, str]] = []
    tables: list[dict[str, str]] = []
    for node in root.iter():
        kind = _local_name(node)
        if kind not in {"fig", "table-wrap"}:
            continue
        label = _node_text(_find_first(node, "label")) or kind
        caption = _node_text(_find_first(node, "caption"))
        if caption:
            captions.append({"label": label, "text": caption, "type": kind})
        if kind == "table-wrap":
            table_node = _find_first(node, "table")
            table_text = _node_text(table_node)
            if table_text or caption:
                tables.append(
                    {"label": label, "caption": caption, "text": table_text}
                )

    references: list[str] = []
    for node in root.iter():
        if _local_name(node) == "ref":
            text = _node_text(node)
            if text:
                references.append(text)

    combined = "\n\n".join(section["text"] for section in sections)[:max_chars]
    return ExtractedDocument(
        url=url,
        title=title,
        authors=authors,
        publication_date=publication_date,
        text=combined,
        source_type="jats",
        extraction_method="stdlib-elementtree-jats",
        sections=sections,
        tables=tables,
        captions=captions,
        references=references,
        content_hash=hashlib.sha256(xml_text.encode("utf-8", errors="replace")).hexdigest(),
        parser_name="stdlib-elementtree-jats",
        parser_version="python-stdlib",
        parser_provenance=[
            {
                "parser": "stdlib-elementtree-jats",
                "version": "python-stdlib",
                "status": "ok",
                "remote": False,
            }
        ],
    )


def extract_pdf(
    path: str | Path,
    *,
    url: str = "",
    max_chars: int = 500_000,
    allow_remote_parser: bool = False,
    is_open_access: bool = False,
    parser_output_dir: str | Path | None = None,
) -> ParsedDocument:
    source = Path(path).resolve()
    output = (
        Path(parser_output_dir).resolve()
        if parser_output_dir
        else source.parent / "parsed" / source.stem
    )
    chain = PdfParserChain(
        allow_remote_parser=allow_remote_parser,
        is_open_access=is_open_access,
    )
    document = chain.parse(source, output_dir=output, max_chars=max_chars)
    document.url = url
    return document


def _safe_remote_url(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("Only absolute HTTP(S) URLs are supported.")
    hostname = parts.hostname.casefold()
    if hostname in {"localhost", "localhost.localdomain"}:
        raise ValueError("Localhost URLs are disabled.")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return
    if address.is_private or address.is_loopback or address.is_link_local:
        raise ValueError("Private and link-local IP URLs are disabled.")


class WebExtractor:
    def __init__(
        self,
        *,
        cache_dir: str | Path,
        client: HttpClient | None = None,
        check_robots: bool = True,
        max_bytes: int = 50 * 1024 * 1024,
        allow_remote_parser: bool = False,
    ) -> None:
        self.client = client or HttpClient(
            "web_extract",
            cache_dir=cache_dir,
            min_interval=0.2,
            user_agent="research-lookup-enhanced/0.1",
        )
        self.check_robots = check_robots
        self.max_bytes = max_bytes
        self.allow_remote_parser = bool(allow_remote_parser)

    def _robots_allowed(self, url: str) -> bool:
        if not self.check_robots:
            return True
        parts = urlsplit(url)
        robots_url = urljoin(f"{parts.scheme}://{parts.netloc}", "/robots.txt")
        try:
            text, _ = self.client.get_text(robots_url)
        except HttpRequestError:
            return True
        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(text.splitlines())
        return parser.can_fetch("research-lookup-enhanced/0.1", url)

    def extract_url(
        self,
        url: str,
        *,
        expected_kind: str = "",
        download_dir: str | Path | None = None,
        is_open_access: bool = False,
    ) -> ParsedDocument:
        _safe_remote_url(url)
        if not self._robots_allowed(url):
            raise PermissionError(f"robots.txt disallows automated retrieval: {url}")
        result = self.client.request("GET", url)
        _safe_remote_url(result.url)
        if len(result.body) > self.max_bytes:
            raise ValueError(f"Response exceeds the {self.max_bytes}-byte safety limit.")
        content_type = result.content_type
        kind = expected_kind.lower()
        if "pdf" in content_type or kind == "pdf" or result.body.startswith(b"%PDF"):
            destination = Path(download_dir or ".")
            destination.mkdir(parents=True, exist_ok=True)
            name = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20] + ".pdf"
            path = destination / name
            path.write_bytes(result.body)
            return extract_pdf(
                path,
                url=result.url,
                allow_remote_parser=self.allow_remote_parser,
                is_open_access=is_open_access,
                parser_output_dir=destination / "parsed" / path.stem,
            )
        text = result.text()
        if (
            kind in {"jats", "xml"}
            or "xml" in content_type
            or text.lstrip().startswith("<?xml")
        ):
            document = extract_jats(text, url=result.url)
        else:
            document = extract_html(text, url=result.url)
        if download_dir:
            destination = Path(download_dir)
            destination.mkdir(parents=True, exist_ok=True)
            suffix = ".xml" if document.source_type == "jats" else ".html"
            path = destination / (
                hashlib.sha256(url.encode("utf-8")).hexdigest()[:20] + suffix
            )
            path.write_bytes(result.body)
            document.local_path = str(path)
            document.local_output_paths["source"] = str(path)
        return document


class FullTextManager:
    def __init__(
        self,
        *,
        cache_dir: str | Path,
        extractor: Extractor | None = None,
        allow_remote_parser: bool = False,
    ) -> None:
        self.extractor = extractor or WebExtractor(
            cache_dir=cache_dir,
            allow_remote_parser=allow_remote_parser,
        )

    @staticmethod
    def ranked_locations(record: PaperRecord) -> list[FullTextLocation]:
        priority = {"jats": 0, "xml": 0, "html": 1, "pdf": 2, "landing": 3}
        locations = [
            item for item in unique_locations(record.fulltext_locations) if item.is_oa is True
        ]
        return sorted(locations, key=lambda item: priority.get(item.kind, 4))

    def download_and_extract(
        self,
        record: PaperRecord,
        *,
        directory: str | Path,
        max_locations: int = 3,
    ) -> tuple[PaperRecord, list[dict[str, Any]]]:
        attempts: list[dict[str, Any]] = []
        for location in self.ranked_locations(record)[:max_locations]:
            try:
                document = self.extractor.extract_url(
                    location.url,
                    expected_kind=location.kind,
                    download_dir=directory,
                    is_open_access=location.is_oa is True,
                )
            except Exception as exc:
                attempts.append(
                    {"url": location.url, "status": "error", "error": str(exc)}
                )
                continue
            record.evidence_chunks.extend(document.evidence_chunks())
            if document.title and not record.title:
                record.title = document.title
                record.mark_fields("local_extraction", ("title",))
            if document.authors and not record.authors:
                record.authors = list(document.authors)
                record.mark_fields("local_extraction", ("authors",))
            if document.publication_date and not record.publication_date:
                record.publication_date = document.publication_date
                record.mark_fields("local_extraction", ("publication_date",))
            if document.publication_date and not record.year:
                year_match = re.search(r"\b(19\d{2}|20\d{2})\b", document.publication_date)
                if year_match:
                    record.year = int(year_match.group(1))
                    record.mark_fields("local_extraction", ("year",))
            record.provenance.append(
                Provenance(
                    provider="local_extraction",
                    request_url=location.url,
                    provider_record_id=record.doi or record.pmid or record.title,
                    operation="extract",
                    notes=[
                        f"source_type={document.source_type}",
                        f"method={document.extraction_method}",
                        f"local_path={document.local_path}",
                        f"content_hash={document.content_hash}",
                        f"parser_name={document.parser_name}",
                        f"parser_version={document.parser_version}",
                        "parser_outputs="
                        + json.dumps(
                            document.local_output_paths,
                            ensure_ascii=False,
                            sort_keys=True,
                        ),
                    ],
                )
            )
            attempts.append(
                {
                    "url": location.url,
                    "status": "ok",
                    "source_type": document.source_type,
                    "method": document.extraction_method,
                    "local_path": document.local_path,
                    "content_hash": document.content_hash,
                    "warnings": document.warnings,
                    "errors": document.errors,
                    "parser_name": document.parser_name,
                    "parser_version": document.parser_version,
                    "local_output_paths": document.local_output_paths,
                    "parser_provenance": document.parser_provenance,
                }
            )
            if document.text:
                break
        return record, attempts


def save_extraction(document: ExtractedDocument, path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(document.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
