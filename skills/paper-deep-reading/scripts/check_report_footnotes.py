#!/usr/bin/env python3
"""Check reader footnotes, keeping main-source attribution separate from verification."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


FOOTNOTE_REF_RE = re.compile(r"(?<![!\\])\[\^([^\]\r\n]+)\]")
FOOTNOTE_DEF_RE = re.compile(r"^[ \t]*\[\^([^\]\r\n]+)\]:[ \t]*(.*)$")
ANCHOR_RE = re.compile(r"<a\b[^>]*\bid=[\"']([^\"']+)[\"'][^>]*>\s*</a>", re.I)
BACKLINK_RE = re.compile(r"\[回到正文\]\(#([^\)]+)\)")
HEADING_RE = re.compile(r"^#{1,6}\s+外部核验文献\s*$")
MAIN_HEADING_RE = re.compile(r"^#{1,6}\s+主文与转引注释\s*$")
MAIN_LOC_KEY_RE = re.compile(r"^main-loc-[a-z0-9]+(?:-[a-z0-9]+)*$")
MAIN_REF_KEY_RE = re.compile(r"^main-ref-([1-9]\d*)$")
INLINE_CODE_RE = re.compile(r"(`+).*?\1")
LINK_RE = re.compile(r"\[((?:\\.|[^\]\\])*)\]\(([^)\r\n]+)\)")
SEMANTIC_YEAR_RE = re.compile(r"^\d{4}$")
COLLISION_SUFFIX_RE = re.compile(r"^[a-z]$")
ITALIC_RE = re.compile(r"(?<!\*)\*([^*\r\n]+)\*(?!\*)")
CONTROLLED_FOOTNOTE_VALUES = {"none", "not-cited", "not-applicable", "pending"}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def is_fence_line(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("```") or stripped.startswith("~~~")


def fenced_lines(lines: list[str]) -> set[int]:
    """Return line indexes inside Markdown fenced code blocks, including fences."""

    ignored: set[int] = set()
    inside = False
    fence_char = ""
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if not is_fence_line(line):
            if inside:
                ignored.add(index)
            continue
        marker = stripped[0]
        if not inside:
            inside = True
            fence_char = marker
            ignored.add(index)
        elif marker == fence_char:
            ignored.add(index)
            inside = False
            fence_char = ""
        else:
            ignored.add(index)
    return ignored


def parse_document(text: str) -> dict:
    lines = text.splitlines()
    ignored = fenced_lines(lines)
    definition_starts: list[tuple[int, str, str]] = []
    for index, line in enumerate(lines):
        if index in ignored:
            continue
        match = FOOTNOTE_DEF_RE.match(line)
        if match:
            definition_starts.append((index, match.group(1), match.group(2)))

    definitions: dict[str, str] = {}
    definition_key_sequence: list[str] = []
    definition_ranges: list[tuple[int, int, str]] = []
    for start, key, first_line in definition_starts:
        end = start + 1
        # Markdown continuation paragraphs are indented. A later heading or body
        # paragraph must not be swallowed by the preceding footnote definition.
        while end < len(lines):
            line = lines[end]
            if line.strip() and not line.startswith(("    ", "\t")):
                break
            end += 1
        block = "\n".join([first_line, *lines[start + 1 : end]])
        definitions[key] = block
        definition_key_sequence.append(key)
        definition_ranges.append((start, end, key))

    definition_indexes: set[int] = set()
    for start, end, _ in definition_ranges:
        definition_indexes.update(range(start, end))

    references: list[tuple[str, int]] = []
    anchors: dict[str, list[int]] = defaultdict(list)
    body_lines: list[str] = []
    for index, line in enumerate(lines):
        if index in ignored or index in definition_indexes:
            body_lines.append("")
            continue
        line = INLINE_CODE_RE.sub("", line)
        body_lines.append(line)
        references.extend((match.group(1), index) for match in FOOTNOTE_REF_RE.finditer(line))
        for match in ANCHOR_RE.finditer(line):
            anchors[match.group(1)].append(index)

    headings = [index for index, line in enumerate(lines) if index not in ignored and HEADING_RE.match(line)]
    return {
        "lines": lines,
        "definitions": definitions,
        "definition_key_sequence": definition_key_sequence,
        "definition_ranges": definition_ranges,
        "references": references,
        "anchors": anchors,
        "headings": headings,
        "main_headings": [index for index, line in enumerate(lines) if index not in ignored and MAIN_HEADING_RE.match(line)],
        "body_lines": body_lines,
    }


def citation_kind(key: str) -> str:
    if MAIN_LOC_KEY_RE.fullmatch(key):
        return "main-paper"
    if MAIN_REF_KEY_RE.fullmatch(key):
        return "secondary"
    return "external"


def citation_syntax_errors(document: dict) -> list[str]:
    errors: list[str] = []
    for index, line in enumerate(document["body_lines"], start=1):
        if re.search(r"\[\s*\^", FOOTNOTE_REF_RE.sub("", line)):
            errors.append(f"broken footnote marker at line {index}; keep [^key] on one line")
        if re.match(r"^\s*\[[^\]^]+\]:\s*$", line):
            errors.append(f"empty reference-link definition at line {index}")
    body = "\n".join(document["body_lines"])
    for match in LINK_RE.finditer(body):
        label, target = match.groups()
        compact = re.sub(r"[\\\[\]\s]", "", label)
        numbered = re.fullmatch(r"\d+(?:[-–,;、]\d+)*", compact)
        citation_target = re.match(r"#(?:review-ref|main-ref|ref|reference|source|原文)[-_]", target, re.I)
        page_label = re.search(r"(?:综述|主文|原文|review|main paper)\s*(?:pp?\.|第\s*\d)", label, re.I)
        page_target = re.search(r"\.pdf#page=\d+", target, re.I)
        if (numbered and citation_target) or (page_label and page_target):
            line = body.count("\n", 0, match.start()) + 1
            errors.append(f"ordinary citation link at line {line}; use a superscript footnote and move the locator into its definition")
    return errors


def is_key_character(character: str) -> bool:
    category = unicodedata.category(character)
    return category[0] in {"L", "M", "N"} or character in " -'’"


def validate_key(key: str) -> tuple[str | None, list[str]]:
    errors: list[str] = []
    if key != key.strip() or "  " in key or "\t" in key:
        errors.append("must use trimmed single spaces")

    parts = key.split("_")
    suffix: str | None = None
    if len(parts) == 4 and COLLISION_SUFFIX_RE.fullmatch(parts[-1]):
        suffix = parts.pop()
    if len(parts) != 3:
        errors.append("must have author, journal abbreviation, and year separated by structural underscores")
        return None, errors

    author, journal, year = parts
    if not author or not journal:
        errors.append("author and journal abbreviation must be non-empty")
    if " " not in author.strip():
        errors.append("first-author key must contain given name and family name")
    if any(len(token) == 1 and token.isascii() and token.isalpha() for token in author.split()):
        errors.append("first-author key must not use an ASCII initial")
    if not SEMANTIC_YEAR_RE.fullmatch(year):
        errors.append("publication year must be exactly four digits")
    for component_name, component in (("author", author), ("journal abbreviation", journal)):
        if any(not is_key_character(character) for character in component):
            errors.append(f"{component_name} contains punctuation that must be normalized")
    base = "_".join([author, journal, year])
    if suffix:
        base = f"{base}_{suffix}"
    return base, errors


def key_slug(key: str) -> str:
    folded = key.casefold()
    output: list[str] = []
    pending_hyphen = False
    for character in folded:
        category = unicodedata.category(character)
        if category[0] in {"L", "M", "N"}:
            if pending_hyphen and output:
                output.append("-")
            output.append(character)
            pending_hyphen = False
        else:
            pending_hyphen = True
    return "".join(output).strip("-")


def split_collision_key(key: str) -> tuple[str, str | None]:
    parts = key.split("_")
    if len(parts) == 4 and COLLISION_SUFFIX_RE.fullmatch(parts[-1]):
        return "_".join(parts[:3]), parts[-1]
    return key, None


def split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def is_table_separator(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def parse_markdown_table(
    text: str,
    required_headers: tuple[str, ...],
    label: str,
) -> tuple[list[dict[str, str]], list[str]]:
    lines = text.splitlines()
    header_index: int | None = None
    headers: list[str] = []
    for index, line in enumerate(lines):
        if not line.strip().startswith("|"):
            continue
        candidate = split_table_row(line)
        if all(header in candidate for header in required_headers):
            header_index = index
            headers = candidate
            break

    if header_index is None:
        joined = ", ".join(required_headers)
        return [], [f"{label} lacks a Markdown table with columns: {joined}"]

    rows: list[dict[str, str]] = []
    started = False
    for line in lines[header_index + 1 :]:
        if not line.strip():
            if started:
                break
            continue
        if not line.strip().startswith("|"):
            if started:
                break
            continue
        cells = split_table_row(line)
        if is_table_separator(cells):
            continue
        if len(cells) != len(headers):
            return rows, [f"{label} contains a row with {len(cells)} cells; expected {len(headers)}"]
        rows.append(dict(zip(headers, cells)))
        started = True
    return rows, []


def parse_anchor_ids(cell: str) -> list[str]:
    return [anchor.strip() for anchor in cell.split(",") if anchor.strip()]


def is_controlled_footnote_value(value: str) -> bool:
    return value in CONTROLLED_FOOTNOTE_VALUES or value.startswith("blocked:")


def read_registry(path: Path) -> tuple[dict[str, dict[str, object]], list[str]]:
    errors: list[str] = []
    try:
        text = read_text(path)
    except OSError as exc:
        return {}, [f"cannot read Source Registry: {exc}"]

    rows, table_errors = parse_markdown_table(
        text,
        (
            "Source ID",
            "Citation status",
            "Reader-facing footnote key",
            "Backlink anchor IDs",
        ),
        "Source Registry",
    )
    errors.extend(table_errors)
    records: dict[str, dict[str, object]] = {}
    source_ids: set[str] = set()
    for row in rows:
        source_id = row["Source ID"].strip()
        citation_status = row["Citation status"].strip()
        key = row["Reader-facing footnote key"].strip()
        anchor_cell = row["Backlink anchor IDs"].strip()

        if not key or is_controlled_footnote_value(key):
            if citation_status == "cited":
                errors.append(f"Source Registry cited row `{source_id or '<missing>'}` lacks a semantic key")
            continue

        if citation_status != "cited":
            errors.append(f"Source Registry key `{key}` requires Citation status `cited`")
        if not source_id:
            errors.append(f"Source Registry key `{key}` lacks a Source ID")
        elif source_id in source_ids:
            errors.append(f"Source Registry contains duplicate Source ID: {source_id}")
        source_ids.add(source_id)

        if key in records:
            errors.append(f"Source Registry contains duplicate reader-facing key: {key}")
        anchors = parse_anchor_ids(anchor_cell)
        if not anchors or is_controlled_footnote_value(anchor_cell):
            errors.append(f"Source Registry key `{key}` lacks backlink anchor IDs")
        records[key] = {"source_id": source_id, "anchors": anchors}
    return records, errors


def read_audit_footnote_map(text: str) -> tuple[dict[str, dict[str, object]], list[str]]:
    rows, errors = parse_markdown_table(
        text,
        ("Reader-facing footnote key", "Source ID", "Backlink anchor IDs"),
        "G5 audit Footnote Map",
    )
    records: dict[str, dict[str, object]] = {}
    for row in rows:
        key = row["Reader-facing footnote key"].strip()
        source_id = row["Source ID"].strip()
        anchors = parse_anchor_ids(row["Backlink anchor IDs"].strip())
        if not key:
            errors.append("G5 audit Footnote Map contains an empty reader-facing key")
            continue
        if key in records:
            errors.append(f"G5 audit Footnote Map contains duplicate key: {key}")
        if not source_id:
            errors.append(f"G5 audit Footnote Map key `{key}` lacks a Source ID")
        if not anchors:
            errors.append(f"G5 audit Footnote Map key `{key}` lacks backlink anchor IDs")
        records[key] = {"source_id": source_id, "anchors": anchors}
    return records, errors


def validate_g5_gate_table(text: str) -> list[str]:
    rows, errors = parse_markdown_table(
        text,
        ("Gate", "Status"),
        "G5 Gate table",
    )
    if errors:
        return errors
    g5_rows = [row for row in rows if re.match(r"^G5(?:\s|$)", row["Gate"].strip(), re.I)]
    if len(g5_rows) != 1:
        return ["G5 Gate table must contain exactly one G5 row"]
    if g5_rows[0]["Status"].strip() != "pass":
        return ["G5 Gate table status must be `pass` for delivery"]
    return []


def definition_metadata_errors(key: str, definition: str) -> list[str]:
    base, _ = split_collision_key(key)
    key_parts = base.split("_")
    if len(key_parts) != 3:
        return []
    key_author, key_journal, key_year = key_parts

    italics = list(ITALIC_RE.finditer(definition))
    if len(italics) < 2:
        return [f"footnote definition lacks author, article title, and journal metadata: {key}"]

    author_text = definition[: italics[0].start()].strip(" ,.;:")
    title = italics[0].group(1).strip()
    journal = italics[1].group(1).strip()
    journal_tail = definition[italics[1].end() :]
    bibliographic_tail = re.split(
        r"(?:DOI\s*:|https?://|Evidence role\s*:|证据作用\s*:|Locator\s*:|定位\s*:)",
        journal_tail,
        maxsplit=1,
        flags=re.I,
    )[0]
    abbreviation_match = re.search(r"\[([^\]\r\n]+)\]", bibliographic_tail)

    if not author_text or not re.search(r"[^\W\d_]", author_text, re.UNICODE) or not title or not journal:
        return [f"footnote definition lacks author, article title, and journal metadata: {key}"]

    metadata_errors: list[str] = []
    normalized_author_text = " ".join(author_text.split()).casefold()
    normalized_key_author = " ".join(key_author.split()).casefold()
    author_remainder = normalized_author_text[len(normalized_key_author) :]
    if not normalized_author_text.startswith(normalized_key_author) or (
        author_remainder and author_remainder[0] not in " ,.;"
    ):
        metadata_errors.append(f"footnote definition first-author name does not match key: {key}")
    if abbreviation_match is None:
        metadata_errors.append(f"footnote definition lacks a standard journal abbreviation: {key}")
    elif abbreviation_match.group(1).strip() != key_journal:
        metadata_errors.append(f"footnote definition journal abbreviation does not match key: {key}")
    if not re.search(rf"(?<!\d){re.escape(key_year)}(?!\d)", bibliographic_tail):
        metadata_errors.append(f"footnote definition publication year does not match key: {key}")
    return metadata_errors


def main_definition_errors(key: str, definition: str) -> list[str]:
    errors: list[str] = []
    if citation_kind(key) == "main-paper":
        if not re.search(r"(?:主文|Main paper)\s*[:：]\s*\S", definition, re.I):
            errors.append(f"main-paper footnote lacks main-paper attribution: {key}")
    else:
        number = MAIN_REF_KEY_RE.fullmatch(key).group(1)
        if not re.search(r"(?:转引自|Cited via)\s*[:：]\s*\S", definition, re.I):
            errors.append(f"secondary footnote lacks cited-via attribution: {key}")
        if not re.search(r"未独立核验原始文献|original (?:source|study) not independently verified", definition, re.I):
            errors.append(f"secondary footnote must disclose that the original source was not independently verified: {key}")
        if not re.search(rf"(?:原文文献|Original ref\.)\s*\[{number}\]", definition, re.I):
            errors.append(f"secondary footnote must preserve original reference [{number}]: {key}")
        if not ITALIC_RE.search(definition) or not re.search(r"\b(?:19|20)\d{2}\b", definition):
            errors.append(f"secondary footnote lacks original bibliography title/year: {key}")
    return errors


def check_report(
    report_path: Path,
    registry_path: Path | None,
    audit_path: Path | None,
    require_citations: bool = False,
) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        document = parse_document(read_text(report_path))
    except OSError as exc:
        return {"status": "BLOCKED", "errors": [f"cannot read report: {exc}"], "warnings": []}

    definitions: dict[str, str] = document["definitions"]
    references: list[tuple[str, int]] = document["references"]
    anchors: dict[str, list[int]] = document["anchors"]
    reference_counts = Counter(key for key, _ in references)
    external_counts = Counter({key: count for key, count in reference_counts.items() if citation_kind(key) == "external"})
    audit_text: str | None = None
    if audit_path is not None:
        try:
            audit_text = read_text(audit_path)
        except OSError as exc:
            errors.append(f"cannot read G5 audit: {exc}")
    modes = re.findall(r"(?m)^\s*reader_backlinks\s*:\s*(\S+)\s*$", audit_text or "")
    if len(modes) > 1 or any(mode not in {"native", "explicit"} for mode in modes):
        errors.append("G5 audit reader_backlinks must be a single `native` or `explicit` value")
    backlink_mode = modes[0] if modes else "explicit"  # Preserve legacy reports.
    errors.extend(citation_syntax_errors(document))
    if require_citations and not references:
        errors.append("a full reader report requires citations even when external validation is out of scope")

    all_keys = set(reference_counts) | set(definitions)
    sections = sorted([(i, "external") for i in document["headings"]] + [(i, "main") for i in document["main_headings"]])
    for indexes, title, external in ((document["headings"], "外部核验文献", True), (document["main_headings"], "主文与转引注释", False)):
        keys = {key for key in all_keys if (citation_kind(key) == "external") == external}
        if keys and not indexes:
            errors.append(f"footnote definitions require an exact `{title}` heading")
        if len(indexes) > 1:
            errors.append(f"report must contain exactly one `{title}` heading")
        if indexes and not keys:
            errors.append(f"the `{title}` section must not be empty")
    for start, _, key in document["definition_ranges"]:
        preceding = [kind for line, kind in sections if line < start]
        expected_section = "external" if citation_kind(key) == "external" else "main"
        if not preceding or preceding[-1] != expected_section:
            errors.append(f"footnote definition is in the wrong citation section: {key}")

    for key, _ in references:
        if key not in definitions:
            errors.append(f"body footnote has no definition: {key}")
    for key in definitions:
        if key not in reference_counts:
            errors.append(f"footnote definition is not used in the body: {key}")

    parsed_keys: dict[str, str] = {}
    for key, count in Counter(document["definition_key_sequence"]).items():
        if count > 1:
            errors.append(f"footnote definition is duplicated: {key}")

    for key in sorted(set(reference_counts) | set(definitions)):
        if citation_kind(key) != "external":
            parsed_keys[key] = key
            continue
        normalized, key_errors = validate_key(key)
        if normalized is not None:
            parsed_keys[key] = normalized
        for message in key_errors:
            errors.append(f"invalid footnote key `{key}`: {message}")

    grouped: dict[str, list[str]] = defaultdict(list)
    for key, normalized in parsed_keys.items():
        if citation_kind(key) != "external":
            continue
        base, suffix = split_collision_key(normalized)
        grouped[base].append(suffix or "")
    for base, suffixes in grouped.items():
        if any(suffixes):
            if len(suffixes) < 2:
                errors.append(f"collision suffixes for `{base}` require at least `_a` and `_b`")
                continue
            if len(suffixes) > 26:
                errors.append(f"collision suffixes for `{base}` support at most `_a` through `_z`")
                continue
            expected = [chr(ord("a") + index) for index in range(len(suffixes))]
            if sorted(suffixes) != expected:
                errors.append(f"collision suffixes for `{base}` must be deterministic `_a`, `_b`, ...")

    anchor_ids = set(anchors)
    if backlink_mode == "native" and any(anchor.startswith("ref-") for anchor in anchor_ids):
        errors.append("native footnotes must not contain manual citation HTML anchors")
    for key, count in reference_counts.items():
        if key not in parsed_keys:
            continue
        if backlink_mode == "native":
            if BACKLINK_RE.search(definitions.get(key, "")):
                errors.append(f"native footnotes must use renderer-generated return links, not manual backlinks: {key}")
            continue
        slug = key_slug(key)
        expected_ids = [f"ref-{slug}-{index}" for index in range(1, count + 1)]
        missing = [anchor_id for anchor_id in expected_ids if anchor_id not in anchor_ids]
        if missing:
            errors.append(f"missing body backlink anchor(s) for `{key}`: {', '.join(missing)}")

        backlinks = BACKLINK_RE.findall(definitions.get(key, ""))
        if backlinks != expected_ids:
            errors.append(
                f"backlinks for `{key}` must be exactly {', '.join(expected_ids)} in first-appearance order"
            )

    for anchor_id, locations in anchors.items():
        if len(locations) > 1:
            errors.append(f"HTML anchor ID is duplicated: {anchor_id}")

    for key, definition in definitions.items():
        if not definition.strip():
            errors.append(f"footnote definition is empty: {key}")
            continue
        if not re.search(r"(?:Locator|定位)\s*[:：]\s*\S", definition, re.I):
            errors.append(f"footnote definition lacks Locator: {key}")
        if citation_kind(key) != "external":
            errors.extend(main_definition_errors(key, definition))
            continue
        if not re.search(r"\b(?:19|20)\d{2}\b", definition):
            errors.append(f"footnote definition lacks a four-digit publication year: {key}")
        if not re.search(r"(?:Evidence role|证据作用)\s*[:：]", definition, re.I):
            errors.append(f"footnote definition lacks Evidence role: {key}")
        if not re.search(r"(?:DOI\s*:|https?://)", definition, re.I):
            errors.append(f"footnote definition lacks a DOI or stable URL: {key}")
        errors.extend(definition_metadata_errors(key, definition))

    registry_records: dict[str, dict[str, object]] = {}
    if external_counts and registry_path is None:
        errors.append("--registry is required when external footnotes are present")
    if registry_path is not None:
        registry_records, registry_errors = read_registry(registry_path)
        errors.extend(registry_errors)
        for key in sorted(external_counts):
            if key not in registry_records:
                errors.append(f"Source Registry does not contain reader-facing key: {key}")
                continue
            expected_ids = ["native"] if backlink_mode == "native" else [f"ref-{key_slug(key)}-{index}" for index in range(1, reference_counts[key] + 1)]
            actual_ids = registry_records[key]["anchors"]
            if actual_ids != expected_ids:
                errors.append(
                    f"Source Registry backlink IDs for `{key}` must be exactly "
                    f"{', '.join(expected_ids)} in first-appearance order"
                )
        for key in sorted(set(registry_records) - set(external_counts)):
            errors.append(f"Source Registry marks a key as cited but the report does not use it: {key}")

    if references:
        if audit_path is None:
            errors.append("--audit is required when reader footnotes are present")
        elif audit_text is not None:
            audit = audit_text
            if not re.search(
                r"(?m)^\s*reader_citation_contract\s*:\s*semantic-footnote-v1\s*$",
                audit,
            ):
                errors.append("G5 audit does not record reader_citation_contract: semantic-footnote-v1")
            errors.extend(validate_g5_gate_table(audit))
            audit_records, audit_errors = read_audit_footnote_map(audit)
            errors.extend(audit_errors)
            for key in sorted(set(reference_counts) - set(audit_records)):
                errors.append(f"G5 audit Footnote Map does not record reader-facing key: {key}")
            for key in sorted(set(audit_records) - set(reference_counts)):
                errors.append(f"G5 audit Footnote Map contains a key not used by the report: {key}")
            for key in sorted(set(reference_counts) & set(audit_records)):
                expected_ids = ["native"] if backlink_mode == "native" else [
                    f"ref-{key_slug(key)}-{index}"
                    for index in range(1, reference_counts[key] + 1)
                ]
                actual_ids = audit_records[key]["anchors"]
                if actual_ids != expected_ids:
                    errors.append(
                        f"G5 audit Footnote Map backlink IDs for `{key}` must be exactly "
                        f"{', '.join(expected_ids)} in first-appearance order"
                    )
                registry_record = registry_records.get(key)
                kind = citation_kind(key)
                if kind != "external":
                    expected_source = "main" if kind == "main-paper" else key
                    if audit_records[key]["source_id"] != expected_source:
                        errors.append(f"G5 audit Footnote Map Source ID must be `{expected_source}` for main-source key: {key}")
                elif registry_record is not None:
                    if audit_records[key]["source_id"] != registry_record["source_id"]:
                        errors.append(f"G5 audit Footnote Map Source ID does not match the registry: {key}")

    return {
        "status": "BLOCKED" if errors else "PASS" if references else "NOT-APPLICABLE",
        "errors": errors,
        "warnings": warnings,
        "counts": {
            "body_references": len(references),
            "distinct_keys": len(reference_counts),
            "definitions": len(definitions),
            "anchors": len(anchors),
            "external_keys": len(external_counts),
            "main_source_keys": len(reference_counts) - len(external_counts),
        },
        "rendering_checked": False,
        "backlink_mode": backlink_mode,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path, help="reader-facing view-report.md")
    parser.add_argument("--registry", type=Path, help="auxiliary-literature-table.md Source Registry")
    parser.add_argument("--audit", type=Path, help="view-report-audit.md G5 audit")
    parser.add_argument("--require-citations", action="store_true", help="require reader citations for a full report, including main-paper-only/fully-local runs")
    parser.add_argument("--json", action="store_true", help="emit a machine-readable result")
    args = parser.parse_args()

    result = check_report(args.report, args.registry, args.audit, args.require_citations)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["status"])
        for error in result["errors"]:
            print(f"ERROR: {error}")
        for warning in result["warnings"]:
            print(f"WARNING: {warning}")
        if not result["errors"]:
            print(
                "Checked "
                f"{result['counts']['distinct_keys']} semantic key(s), "
                f"{result['counts']['body_references']} body reference(s), "
                f"{result['counts']['anchors']} anchor(s)."
            )
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
