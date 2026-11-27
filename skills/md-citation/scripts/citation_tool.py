#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deterministic Academic Markdown & Typora Citation Engine (`citation_tool.py`).

Pure Python 3.10+ standard-library CLI tool supporting:
  1. `config`  : View, set, or reset persistent user/workspace defaults (default
                 bibliography style, inline scheme, clickable link mode & label).
  2. `resolve` : Parse `.bib` / `.json` / raw DOIs into normalized metadata records,
                 with optional Crossref REST API enrichment (`--online`, zero Zotero MCP)
                 and multi-style formatting (IEEE, GB/T 7714, Nature, APA, Vancouver,
                 ACS, Chicago) + resolved source URLs.
  3. `render`  : Render drafts with `[^R001]` / `[@CiteKey]` placeholders into strict
                 order-of-first-appearance numbered citations across Schemes A–F with
                 verified clickable trailing hyperlinks (`[DOI](...)`, `[arXiv](...)`,
                 `[Website](...)`, or custom label).
  4. `convert` : Re-index edited Markdown files in `1..N` first-appearance order and
                 losslessly switch between Schemes A–F and all 7 bibliography styles.
  5. `verify`  : Deterministic QA audit (1..N bijection, monotonic first-appearance,
                 blank-line footnote separation, trailing link integrity, punctuation/
                 math/table/Mermaid hygiene, and DOI-suffix-as-article-number check).
"""

from __future__ import annotations

import argparse
import dataclasses
import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants, Supported Styles & Configurable Defaults
# ---------------------------------------------------------------------------
SUPPORTED_SCHEMES: tuple[str, ...] = ("A", "B", "C", "D", "E", "F")
SUPPORTED_BIB_STYLES: tuple[str, ...] = (
    "ieee",
    "gbt7714",
    "nature",
    "apa",
    "vancouver",
    "acs",
    "chicago",
)
SUPPORTED_LINK_MODES: tuple[str, ...] = ("auto", "off")

PRESETS: dict[str, dict[str, Any]] = {
    "md-ieee": {"scheme": "A", "bib_style": "ieee", "link_mode": "auto"},
    "md-nature": {"scheme": "A", "bib_style": "nature", "link_mode": "auto"},
    "md-apa": {"scheme": "A", "bib_style": "apa", "link_mode": "auto"},
    "md-vancouver": {"scheme": "A", "bib_style": "vancouver", "link_mode": "auto"},
    "md-acs": {"scheme": "A", "bib_style": "acs", "link_mode": "auto"},
    "md-chicago": {"scheme": "A", "bib_style": "chicago", "link_mode": "auto"},
    "cn-proposal": {"scheme": "E", "bib_style": "gbt7714", "link_mode": "off", "heading": "## 参考文献"},
}

BUILTIN_DEFAULTS: dict[str, Any] = {
    "default_scheme": "A",
    "default_bib_style": "ieee",
    "link_mode": "auto",
    "link_label": "auto",
    "heading": None,
}

SKILL_ROOT = Path(__file__).resolve().parents[1]
SKILL_CONFIG_PATH = SKILL_ROOT / "config" / "local.json"
WORKSPACE_CONFIG_NAME = ".md-citation.json"
LEGACY_WORKSPACE_CONFIG_NAME = ".typora-citation.json"

# ---------------------------------------------------------------------------
# Standard IEEE Journal Abbreviation Lookup (Physics, Materials, ECE, CS/AI, Bio)
# ---------------------------------------------------------------------------
IEEE_JOURNAL_ABBREVS: dict[str, str] = {
    "nature": "Nature",
    "science": "Science",
    "cell": "Cell",
    "nature communications": "Nat. Commun.",
    "nature materials": "Nat. Mater.",
    "nature nanotechnology": "Nat. Nanotechnol.",
    "nature electronics": "Nat. Electron.",
    "nature physics": "Nat. Phys.",
    "nature photonics": "Nat. Photonics",
    "nature machine intelligence": "Nat. Mach. Intell.",
    "nature computational science": "Nat. Comput. Sci.",
    "nature biomedical engineering": "Nat. Biomed. Eng.",
    "nature chemistry": "Nat. Chem.",
    "nature energy": "Nat. Energy",
    "nature methods": "Nat. Methods",
    "nature reviews physics": "Nat. Rev. Phys.",
    "nature reviews materials": "Nat. Rev. Mater.",
    "nature reviews electrical engineering": "Nat. Rev. Electr. Eng.",
    "science advances": "Sci. Adv.",
    "science robotics": "Sci. Robot.",
    "scientific reports": "Sci. Rep.",
    "npj computational materials": "npj Comput. Mater.",
    "npj quantum materials": "npj Quantum Mater.",
    "npj spintronics": "npj Spintronics",
    "npj 2d materials and applications": "npj 2D Mater. Appl.",
    "npj unconventional computing": "npj Unconv. Comput.",
    "communications physics": "Commun. Phys.",
    "communications materials": "Commun. Mater.",
    "proceedings of the national academy of sciences": "Proc. Nat. Acad. Sci. USA",
    "proceedings of the national academy of sciences of the united states of america": "Proc. Nat. Acad. Sci. USA",
    "pnas": "Proc. Nat. Acad. Sci. USA",
    "physical review letters": "Phys. Rev. Lett.",
    "physical review x": "Phys. Rev. X",
    "prx energy": "PRX Energy",
    "physical review b": "Phys. Rev. B",
    "physical review a": "Phys. Rev. A",
    "physical review e": "Phys. Rev. E",
    "physical review applied": "Phys. Rev. Appl.",
    "physical review materials": "Phys. Rev. Mater.",
    "physical review research": "Phys. Rev. Res.",
    "reviews of modern physics": "Rev. Mod. Phys.",
    "reports on progress in physics": "Rep. Prog. Phys.",
    "applied physics letters": "Appl. Phys. Lett.",
    "journal of applied physics": "J. Appl. Phys.",
    "applied physics reviews": "Appl. Phys. Rev.",
    "advanced materials": "Adv. Mater.",
    "advanced functional materials": "Adv. Funct. Mater.",
    "advanced electronic materials": "Adv. Electron. Mater.",
    "advanced intelligent systems": "Adv. Intell. Syst.",
    "advanced science": "Adv. Sci.",
    "advanced optical materials": "Adv. Opt. Mater.",
    "small": "Small",
    "acs nano": "ACS Nano",
    "nano letters": "Nano Lett.",
    "acs applied materials & interfaces": "ACS Appl. Mater. Interfaces",
    "acs applied electronic materials": "ACS Appl. Electron. Mater.",
    "chemical reviews": "Chem. Rev.",
    "chemical society reviews": "Chem. Soc. Rev.",
    "journal of the american chemical society": "J. Amer. Chem. Soc.",
    "journal of the american ceramic society": "J. Amer. Ceram. Soc.",
    "acta materialia": "Acta Mater.",
    "matter": "Matter",
    "joule": "Joule",
    "device": "Device",
    "national science review": "Natl. Sci. Rev.",
    "science bulletin": "Sci. Bull.",
    "chinese physics letters": "Chin. Phys. Lett.",
    "acta physica sinica": "Acta Phys. Sin.",
    "ieee transactions on electron devices": "IEEE Trans. Electron Devices",
    "ieee electron device letters": "IEEE Electron Device Lett.",
    "ieee journal of solid-state circuits": "IEEE J. Solid-State Circuits",
    "ieee transactions on circuits and systems i: regular papers": "IEEE Trans. Circuits Syst. I, Reg. Papers",
    "ieee transactions on circuits and systems": "IEEE Trans. Circuits Syst.",
    "ieee transactions on neural networks and learning systems": "IEEE Trans. Neural Netw. Learn. Syst.",
    "ieee transactions on pattern analysis and machine intelligence": "IEEE Trans. Pattern Anal. Mach. Intell.",
    "ieee transactions on computers": "IEEE Trans. Comput.",
    "ieee transactions on electronic computers": "IEEE Trans. Electron. Comput.",
    "ieee transactions on magnetics": "IEEE Trans. Magn.",
    "ieee transactions on nanotechnology": "IEEE Trans. Nanotechnol.",
    "proceedings of the ieee": "Proc. IEEE",
    "journal of machine learning research": "J. Mach. Learn. Res.",
    "neural computation": "Neural Comput.",
    "neural networks": "Neural Netw.",
    "neuromorphic computing and engineering": "Neuromorph. Comput. Eng.",
    "nanotechnology": "Nanotechnology",
    "journal of physics: condensed matter": "J. Phys.: Condens. Matter",
    "journal of physics d: applied physics": "J. Phys. D, Appl. Phys.",
    "physica d: nonlinear phenomena": "Physica D",
    "physica d": "Physica D",
    "proceedings of the royal society a": "Proc. R. Soc. A",
    "proceedings of the royal society a: mathematical, physical and engineering sciences": "Proc. R. Soc. A",
    "computational materials science": "Comput. Mater. Sci.",
    "computer physics communications": "Comput. Phys. Commun.",
    "computer methods in applied mechanics and engineering": "Comput. Methods Appl. Mech. Eng.",
    "journal of computational physics": "J. Comput. Phys.",
    "journal of the mechanics and physics of solids": "J. Mech. Phys. Solids",
    "progress in materials science": "Prog. Mater. Sci.",
    "annual review of materials research": "Annu. Rev. Mater. Res.",
    "japanese journal of applied physics": "Jpn. J. Appl. Phys.",
    "fundamental research": "Fundam. Res.",
    "current applied physics": "Curr. Appl. Phys.",
    "frontiers in physics": "Front. Phys.",
    "frontiers in neuroscience": "Front. Neurosci.",
    "the lancet": "Lancet",
    "new england journal of medicine": "N. Engl. J. Med.",
    "jama": "JAMA",
}

def _smart_title_journal(raw: str) -> str:
    minor = {"of", "on", "the", "and", "in", "for", "a", "an", "to"}
    special = {"ieee": "IEEE", "acs": "ACS", "pnas": "PNAS", "npj": "npj", "2d": "2D", "usa": "USA", "jama": "JAMA", "prx": "PRX"}
    words = raw.split()
    out: list[str] = []
    for i, w in enumerate(words):
        lw = w.lower().rstrip(":")
        colon = ":" if w.endswith(":") else ""
        if lw in special:
            out.append(special[lw] + colon)
        elif i > 0 and lw in minor and not (out and out[-1].endswith(":")):
            out.append(lw + colon)
        else:
            out.append(w[:1].upper() + w[1:] + ("" if colon else ""))
    return " ".join(out)


ABBREV_TO_FULL_JOURNAL: dict[str, str] = {
    v.lower(): _smart_title_journal(k)
    for k, v in IEEE_JOURNAL_ABBREVS.items()
    if k not in ("pnas", "physica d", "proceedings of the royal society a: mathematical, physical and engineering sciences")
}

LATEX_ACCENTS: list[tuple[str, str]] = [
    (r'{\"a}', "ä"), (r'{\"o}', "ö"), (r'{\"u}', "ü"),
    (r'{\"A}', "Ä"), (r'{\"O}', "Ö"), (r'{\"U}', "Ü"),
    (r'\"a', "ä"), (r'\"o', "ö"), (r'\"u', "ü"),
    (r"{\'e}", "é"), (r"{\'a}", "á"), (r"{\'o}", "ó"), (r"{\'c}", "ć"),
    (r"\'e", "é"), (r"\'a", "á"), (r"\'o", "ó"),
    (r"{\`e}", "è"), (r"{\`a}", "à"),
    (r"{\^o}", "ô"), (r"{\^e}", "ê"),
    (r"{\~n}", "ñ"), (r"{\~a}", "ã"),
    (r"{\c{c}}", "ç"), (r"{\v{s}}", "š"), (r"{\v{c}}", "č"), (r"{\v{z}}", "ž"),
    (r"{\i}", "ı"), (r"{\l}", "ł"), (r"{\ss}", "ß"), (r"{\o}", "ø"),
    (r"{\.I}", "İ"),
]


@dataclasses.dataclass
class RefRecord:
    key: str
    entry_type: str = "article"  # article | inproceedings | book | preprint | misc
    authors: list[tuple[str, str]] = dataclasses.field(default_factory=list)  # (given, family)
    has_et_al: bool = False
    title: str = ""
    venue: str = ""
    venue_abbrev: str = ""
    year: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""
    art_no: str = ""
    publisher: str = ""
    address: str = ""
    doi: str = ""
    arxiv_id: str = ""
    url: str = ""
    raw_ieee: str = ""
    raw_gbt: str = ""
    raw_source: str = ""
    source_style: str = ""
    warnings: list[str] = dataclasses.field(default_factory=list)


# ---------------------------------------------------------------------------
# Persistent Configuration Discovery & Validation
# ---------------------------------------------------------------------------
def _validate_config_payload(data: dict[str, Any], origin: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError(f"Config at {origin} must be a JSON object.")
    cleaned: dict[str, Any] = {}
    if "default_scheme" in data and data["default_scheme"] is not None:
        sch = str(data["default_scheme"]).strip().upper()
        if sch not in SUPPORTED_SCHEMES:
            raise ValueError(f"Invalid default_scheme '{sch}' in {origin}; expected one of {SUPPORTED_SCHEMES}.")
        cleaned["default_scheme"] = sch
    if "default_bib_style" in data and data["default_bib_style"] is not None:
        st = str(data["default_bib_style"]).strip().lower()
        if st not in SUPPORTED_BIB_STYLES:
            raise ValueError(f"Invalid default_bib_style '{st}' in {origin}; expected one of {SUPPORTED_BIB_STYLES}.")
        cleaned["default_bib_style"] = st
    if "link_mode" in data and data["link_mode"] is not None:
        lm = str(data["link_mode"]).strip().lower()
        if lm not in SUPPORTED_LINK_MODES:
            raise ValueError(f"Invalid link_mode '{lm}' in {origin}; expected one of {SUPPORTED_LINK_MODES}.")
        cleaned["link_mode"] = lm
    if "link_label" in data and data["link_label"] is not None:
        lbl = str(data["link_label"]).strip()
        if not lbl:
            raise ValueError(f"Invalid empty link_label in {origin}.")
        cleaned["link_label"] = lbl
    if "heading" in data:
        cleaned["heading"] = str(data["heading"]).strip() if data["heading"] else None
    return cleaned


def find_workspace_config(start_dir: Path) -> Path | None:
    cur = start_dir.resolve()
    while True:
        for fname in (WORKSPACE_CONFIG_NAME, LEGACY_WORKSPACE_CONFIG_NAME):
            candidate = cur / fname
            if candidate.is_file():
                return candidate
        if (cur / ".git").exists() or cur.parent == cur:
            return None
        cur = cur.parent


def load_effective_config(
    start_dir: Path | None = None,
    explicit_config: Path | None = None,
    skill_config_path: Path | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Load merged defaults with provenance: builtin -> skill local.json -> workspace -> explicit."""
    cfg = dict(BUILTIN_DEFAULTS)
    sources: list[str] = ["builtin"]

    sk_path = skill_config_path if skill_config_path is not None else SKILL_CONFIG_PATH
    if sk_path.is_file():
        raw = json.loads(sk_path.read_text(encoding="utf-8-sig"))
        cfg.update(_validate_config_payload(raw, str(sk_path)))
        sources.append(str(sk_path))

    ws_path = find_workspace_config(start_dir or Path.cwd())
    if ws_path and ws_path.resolve() != sk_path.resolve():
        raw = json.loads(ws_path.read_text(encoding="utf-8-sig"))
        cfg.update(_validate_config_payload(raw, str(ws_path)))
        sources.append(str(ws_path))

    if explicit_config is not None:
        if not explicit_config.is_file():
            raise FileNotFoundError(f"Config file not found: {explicit_config}")
        raw = json.loads(explicit_config.read_text(encoding="utf-8-sig"))
        cfg.update(_validate_config_payload(raw, str(explicit_config)))
        sources.append(str(explicit_config))

    return cfg, sources


# ---------------------------------------------------------------------------
# LaTeX / String Cleaning, Link Resolution & Author Formatting Helpers
# ---------------------------------------------------------------------------
def clean_bibtex_str(val: str) -> str:
    s = val.strip()
    for pat, rep in LATEX_ACCENTS:
        s = s.replace(pat, rep)
    s = re.sub(r"\\&", "&", s)
    s = re.sub(r"\s+", " ", s)
    out: list[str] = []
    in_math = False
    for ch in s:
        if ch == "$":
            in_math = not in_math
            out.append(ch)
        elif ch in "{}" and not in_math:
            continue
        else:
            out.append(ch)
    res = "".join(out).strip()
    res = res.replace("---", "—").replace("--", "–")
    return res


def normalize_doi(doi: str) -> str:
    d = doi.strip()
    d = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", d, flags=re.IGNORECASE)
    d = re.sub(r"^doi:\s*", "", d, flags=re.IGNORECASE)
    return d.rstrip(".,;) ")


def clean_arxiv_id(arxiv_id: str) -> str:
    a = arxiv_id.strip()
    a = re.sub(r"^https?://arxiv\.org/(?:abs|pdf)/", "", a, flags=re.IGNORECASE)
    a = re.sub(r"^arxiv:\s*", "", a, flags=re.IGNORECASE)
    a = re.sub(r"\.pdf$", "", a, flags=re.IGNORECASE)
    return a.rstrip(".,;) ")


def normalize_url(url: str) -> str:
    u = url.strip().rstrip(".,;)")
    if re.match(r"^https?://\S+$", u, flags=re.IGNORECASE):
        return u
    return ""


def resolve_reference_link(rec: RefRecord) -> tuple[str, str]:
    """Return (url, kind) where kind in {'doi', 'arxiv', 'website', ''} from verified metadata only."""
    doi_norm = normalize_doi(rec.doi)
    if doi_norm:
        return f"https://doi.org/{doi_norm}", "doi"
    arx = clean_arxiv_id(rec.arxiv_id)
    if arx:
        return f"https://arxiv.org/abs/{arx}", "arxiv"
    u = normalize_url(rec.url)
    if u:
        return u, "website"
    return "", ""


def format_trailing_link(rec: RefRecord, link_mode: str = "auto", link_label: str = "auto") -> str:
    """Emit trailing clickable Markdown hyperlink ` [Label](https://...)` if enabled and verified."""
    if link_mode.lower() == "off":
        return ""
    url, kind = resolve_reference_link(rec)
    if not url:
        return ""
    lbl_raw = (link_label or "auto").strip()
    if lbl_raw.lower() == "auto":
        label = {"doi": "DOI", "arxiv": "arXiv", "website": "Website"}[kind]
    else:
        label = lbl_raw.replace("[", "(").replace("]", ")")
    return f" [{label}]({url})"


TRAILING_LINK_RE = re.compile(r"\s*\[([^\]]+)\]\((https?://[^\s)]+)\)\s*$")


def strip_trailing_markdown_link(text: str) -> tuple[str, str]:
    """Strip a single trailing Markdown hyperlink ` [Label](https://...)` and return (clean_body, url)."""
    m = TRAILING_LINK_RE.search(text)
    if not m:
        return text.strip(), ""
    return text[: m.start()].strip(), m.group(2).strip()


def is_cjk(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def given_to_ieee_initials(given: str) -> str:
    g = given.strip()
    if not g:
        return ""
    if is_cjk(g):
        return g
    tokens = re.split(r"\s+", g)
    formatted_tokens: list[str] = []
    for tok in tokens:
        if "-" in tok:
            hy_parts = [p for p in tok.split("-") if p]
            hy_init = "-".join(
                (p if p.endswith(".") and len(p) <= 3 else f"{p[0]}.")
                for p in hy_parts
            )
            formatted_tokens.append(hy_init)
        else:
            clean_t = tok.rstrip(".")
            if clean_t:
                formatted_tokens.append(f"{clean_t[0]}.")
    return " ".join(formatted_tokens)


def given_to_gbt_initials(given: str) -> str:
    g = given.strip()
    if not g:
        return ""
    if is_cjk(g):
        return g
    tokens = re.split(r"[\s\-]+", g)
    inits = [t.rstrip(".")[0].upper() for t in tokens if t.rstrip(".")]
    return " ".join(inits)


def given_to_vancouver_initials(given: str) -> str:
    g = given.strip()
    if not g:
        return ""
    if is_cjk(g):
        return g
    tokens = re.split(r"[\s\-]+", g)
    return "".join(t.rstrip(".")[0].upper() for t in tokens if t.rstrip("."))


def format_authors_ieee(authors: list[tuple[str, str]], has_et_al: bool = False) -> str:
    if not authors:
        return "[待核实],"
    if len(authors) == 1 and is_cjk(authors[0][1]):
        base = f"{authors[0][1]}{authors[0][0]}"
        return f"{base}等," if has_et_al else f"{base},"

    def fmt_one(given: str, family: str) -> str:
        if is_cjk(family):
            return f"{family}{given}"
        inits = given_to_ieee_initials(given)
        return f"{inits} {family}".strip()

    if len(authors) >= 7 or (has_et_al and len(authors) >= 1):
        first = fmt_one(*authors[0])
        return f"{first} *et al.*,"
    if len(authors) == 1:
        return f"{fmt_one(*authors[0])},"
    if len(authors) == 2:
        return f"{fmt_one(*authors[0])} and {fmt_one(*authors[1])},"
    leading = ", ".join(fmt_one(*a) for a in authors[:-1])
    return f"{leading}, and {fmt_one(*authors[-1])},"


def format_authors_gbt(authors: list[tuple[str, str]], has_et_al: bool = False) -> str:
    if not authors:
        return "[待核实]."

    def fmt_one(given: str, family: str) -> str:
        if is_cjk(family):
            return f"{family}{given}"
        inits = given_to_gbt_initials(given)
        return f"{family} {inits}".strip()

    cjk_mode = is_cjk(authors[0][1])
    if len(authors) > 3 or has_et_al:
        shown = ", ".join(fmt_one(*a) for a in authors[:3])
        suffix = ", 等." if cjk_mode else ", et al."
        return f"{shown}{suffix}"
    return ", ".join(fmt_one(*a) for a in authors) + "."


def format_authors_nature(authors: list[tuple[str, str]], has_et_al: bool = False) -> str:
    if not authors:
        return "[待核实]."

    def fmt_one(given: str, family: str) -> str:
        if is_cjk(family):
            return f"{family}{given}"
        inits = given_to_ieee_initials(given)
        return f"{family}, {inits}" if inits else family

    if len(authors) > 5 or has_et_al:
        return f"{fmt_one(*authors[0])} *et al.*"
    if len(authors) == 1:
        one = fmt_one(*authors[0])
        return one if one.endswith(".") else f"{one}."
    if len(authors) == 2:
        pair = f"{fmt_one(*authors[0])} & {fmt_one(*authors[1])}"
        return pair if pair.endswith(".") else f"{pair}."
    joined = ", ".join(fmt_one(*a) for a in authors[:-1]) + f" & {fmt_one(*authors[-1])}"
    return joined if joined.endswith(".") else f"{joined}."


def format_authors_apa(authors: list[tuple[str, str]], has_et_al: bool = False) -> str:
    if not authors:
        return "[待核实]"

    def fmt_one(given: str, family: str) -> str:
        if is_cjk(family):
            return f"{family}{given}"
        inits = given_to_ieee_initials(given)
        return f"{family}, {inits}" if inits else family

    if has_et_al and len(authors) == 1:
        return f"{fmt_one(*authors[0])}, et al."
    if len(authors) > 20:
        first19 = ", ".join(fmt_one(*a) for a in authors[:19])
        return f"{first19}, ... {fmt_one(*authors[-1])}"
    if len(authors) == 1:
        return fmt_one(*authors[0])
    if len(authors) == 2:
        return f"{fmt_one(*authors[0])}, & {fmt_one(*authors[1])}"
    return ", ".join(fmt_one(*a) for a in authors[:-1]) + f", & {fmt_one(*authors[-1])}"


def format_authors_vancouver(authors: list[tuple[str, str]], has_et_al: bool = False) -> str:
    if not authors:
        return "[待核实]."

    def fmt_one(given: str, family: str) -> str:
        if is_cjk(family):
            return f"{family}{given}"
        inits = given_to_vancouver_initials(given)
        return f"{family} {inits}".strip()

    if len(authors) > 6 or has_et_al:
        shown = ", ".join(fmt_one(*a) for a in authors[:6])
        return f"{shown}, et al."
    return ", ".join(fmt_one(*a) for a in authors) + "."


def format_authors_acs(authors: list[tuple[str, str]], has_et_al: bool = False) -> str:
    if not authors:
        return "[待核实]."

    def fmt_one(given: str, family: str) -> str:
        if is_cjk(family):
            return f"{family}{given}"
        inits = given_to_ieee_initials(given)
        return f"{family}, {inits}" if inits else family

    if has_et_al and len(authors) == 1:
        return f"{fmt_one(*authors[0])}; et al."
    if len(authors) > 10:
        return "; ".join(fmt_one(*a) for a in authors[:10]) + "; et al."
    res = "; ".join(fmt_one(*a) for a in authors)
    return res if res.endswith(".") else f"{res}."


def format_authors_chicago(authors: list[tuple[str, str]], has_et_al: bool = False) -> str:
    if not authors:
        return "[待核实]."

    def fmt_first(given: str, family: str) -> str:
        if is_cjk(family):
            return f"{family}{given}"
        return f"{family}, {given}".strip(", ") if given else family

    def fmt_other(given: str, family: str) -> str:
        if is_cjk(family):
            return f"{family}{given}"
        return f"{given} {family}".strip()

    if has_et_al and len(authors) == 1:
        return f"{fmt_first(*authors[0])}, et al."
    if len(authors) > 10:
        parts = [fmt_first(*authors[0])] + [fmt_other(*a) for a in authors[1:7]]
        return ", ".join(parts) + ", et al."
    if len(authors) == 1:
        s = fmt_first(*authors[0])
        return s if s.endswith(".") else f"{s}."
    if len(authors) == 2:
        s = f"{fmt_first(*authors[0])}, and {fmt_other(*authors[1])}"
        return s if s.endswith(".") else f"{s}."
    parts = [fmt_first(*authors[0])] + [fmt_other(*a) for a in authors[1:-1]]
    s = ", ".join(parts) + f", and {fmt_other(*authors[-1])}"
    return s if s.endswith(".") else f"{s}."


def abbreviate_journal_ieee(venue: str, short_hint: str = "") -> str:
    v = venue.strip()
    if v and v.lower() in IEEE_JOURNAL_ABBREVS:
        return IEEE_JOURNAL_ABBREVS[v.lower()]
    if short_hint and "." in short_hint:
        return short_hint.strip()
    if not v:
        return short_hint.strip()
    return v


def expand_journal_full(venue: str, venue_abbrev: str) -> str:
    if venue and "." not in venue:
        return venue
    cand = (venue or venue_abbrev).strip()
    low = cand.lower()
    if low in ABBREV_TO_FULL_JOURNAL:
        return ABBREV_TO_FULL_JOURNAL[low]
    return cand


def _norm_pages_en_dash(pages: str) -> str:
    p = pages.strip().replace("--", "–")
    return re.sub(r"(?<=\w)-(?=\w)", "–", p)


def _extract_arxiv_str(rec: RefRecord, doi_norm: str) -> str:
    arx = clean_arxiv_id(rec.arxiv_id)
    if not arx and "arxiv." in doi_norm.lower():
        arx = re.sub(r"^.*arxiv\.", "", doi_norm, flags=re.IGNORECASE)
    return f"arXiv:{arx}" if arx else "arXiv:[待核实]"


def _is_preprint(rec: RefRecord, doi_norm: str) -> bool:
    return rec.entry_type == "preprint" or bool(rec.arxiv_id) or "10.48550/arxiv." in doi_norm.lower()


def check_doi_suffix_page_collision(doi: str, locator: str) -> bool:
    """Detect high-risk LLM hallucination where a 5+ digit DOI submission ID is copied as page/article number."""
    if not doi or not locator:
        return False
    loc_clean = locator.strip()
    if not re.fullmatch(r"\d{5,7}", loc_clean):
        return False
    low_doi = doi.lower()
    # Nature (e.g. 10.1038/s41467-025-12345-6) or Wiley (10.1002/adma.202512345) manuscript-ID collision
    m_nat = re.search(r"10\.1038/s\d+-\d{3}-(\d{5})-\w", low_doi)
    if m_nat and m_nat.group(1) == loc_clean:
        return True
    m_wiley = re.search(r"10\.1002/[a-z]+\.\d{4}(\d{5})", low_doi)
    if m_wiley and m_wiley.group(1) == loc_clean:
        return True
    return False


# ---------------------------------------------------------------------------
# 7 Academic Bibliography Style Formatters
# ---------------------------------------------------------------------------
def format_record_ieee(rec: RefRecord) -> str:
    if rec.raw_ieee and not rec.title:
        return rec.raw_ieee.strip()

    auth_str = format_authors_ieee(rec.authors, rec.has_et_al)
    year_str = rec.year.strip() or "[待核实]"
    doi_norm = normalize_doi(rec.doi)
    doi_tail = f", doi: {doi_norm}." if doi_norm else "."

    if rec.entry_type == "book":
        title_clean = rec.title.rstrip(".,")
        if rec.address and rec.publisher:
            pub_part = f" {rec.address}: {rec.publisher}, {year_str}"
        elif rec.publisher:
            pub_part = f" {rec.publisher}, {year_str}"
        else:
            pub_part = f" {year_str}"
        return f"{auth_str} *{title_clean}*.{pub_part}{doi_tail}"

    title_clean = rec.title.strip().rstrip(".")
    title_clean_quotes = title_clean.replace('"', "'")
    if title_clean_quotes.endswith(("?", "!")):
        quoted_title = f'"{title_clean_quotes}"'
    else:
        quoted_title = f'"{title_clean_quotes.rstrip(",")},"'

    if _is_preprint(rec, doi_norm):
        arx_str = _extract_arxiv_str(rec, doi_norm)
        return f"{auth_str} {quoted_title} *arXiv preprint* {arx_str}, {year_str}{doi_tail}"

    if rec.entry_type == "inproceedings":
        conf = rec.venue_abbrev or rec.venue or "[待核实]"
        parts = [f"{auth_str} {quoted_title} in *{conf}*"]
        if rec.volume:
            parts.append(f"vol. {rec.volume}")
        parts.append(year_str)
        if rec.pages:
            parts.append(f"pp. {_norm_pages_en_dash(rec.pages)}")
        elif rec.art_no:
            parts.append(f"Art. no. {rec.art_no}")
        return f"{', '.join(parts)}{doi_tail}"

    j_name = abbreviate_journal_ieee(rec.venue, rec.venue_abbrev) or "[待核实]"
    parts = [f"{auth_str} {quoted_title} *{j_name}*"]
    if rec.volume:
        parts.append(f"vol. {rec.volume}")
    elif not rec.doi:
        parts.append("vol. [待核实]")
    if rec.issue:
        parts.append(f"no. {rec.issue}")
    if rec.art_no:
        parts.append(f"Art. no. {rec.art_no}")
    elif rec.pages:
        p_norm = _norm_pages_en_dash(rec.pages)
        if "–" in p_norm:
            parts.append(f"pp. {p_norm}")
        elif re.fullmatch(r"[eE]?\d{4,8}[a-zA-Z]?", p_norm):
            parts.append(f"Art. no. {p_norm}")
        else:
            parts.append(f"p. {p_norm}")
    elif not rec.doi:
        parts.append("pp. [待核实]")
    parts.append(year_str)
    return f"{', '.join(parts)}{doi_tail}"


def format_record_gbt(rec: RefRecord) -> str:
    if rec.raw_gbt and not rec.title:
        return rec.raw_gbt.strip()

    auth_str = format_authors_gbt(rec.authors, rec.has_et_al)
    title_clean = rec.title.strip().rstrip(".,").replace("*", "")
    year_str = rec.year.strip() or "[待核实]"
    doi_norm = normalize_doi(rec.doi)
    doi_tail = f" DOI: {doi_norm}." if doi_norm else ""

    if rec.entry_type == "book":
        pub = f"{rec.address}: {rec.publisher}" if (rec.address and rec.publisher) else (rec.publisher or "[出版者待核实]")
        return f"{auth_str} {title_clean}[M]. {pub}, {year_str}.{doi_tail}"

    if _is_preprint(rec, doi_norm):
        arx_str = _extract_arxiv_str(rec, doi_norm)
        return f"{auth_str} {title_clean}[EB/OL]. {arx_str}, {year_str}.{doi_tail}"

    if rec.entry_type == "inproceedings":
        conf = rec.venue or rec.venue_abbrev or "[会议名待核实]"
        loc = _norm_pages_en_dash(rec.pages) if rec.pages else (rec.art_no or "[页码待核实]")
        return f"{auth_str} {title_clean}[C]//{conf}. {year_str}: {loc}.{doi_tail}"

    j_full = expand_journal_full(rec.venue, rec.venue_abbrev) or "[刊名待核实]"
    if not rec.volume and not rec.pages and not rec.art_no and doi_norm:
        return f"{auth_str} {title_clean}[J]. {j_full}, {year_str}.{doi_tail}"
    vol_no = rec.volume or "[卷待核实]"
    if rec.issue:
        vol_no = f"{vol_no}({rec.issue})"
    loc = rec.art_no or (_norm_pages_en_dash(rec.pages) if rec.pages else "[页码待核实]")
    return f"{auth_str} {title_clean}[J]. {j_full}, {year_str}, {vol_no}: {loc}.{doi_tail}"


def format_record_nature(rec: RefRecord) -> str:
    auth_str = format_authors_nature(rec.authors, rec.has_et_al)
    title_clean = rec.title.strip().rstrip(".")
    year_str = rec.year.strip() or "[待核实]"
    doi_norm = normalize_doi(rec.doi)
    title_end = title_clean if title_clean.endswith(("?", "!")) else f"{title_clean}."

    if rec.entry_type == "book":
        pub = rec.publisher or "[Publisher]"
        return f"{auth_str} *{title_clean}* ({pub}, {year_str})."

    if _is_preprint(rec, doi_norm):
        arx_str = _extract_arxiv_str(rec, doi_norm)
        return f"{auth_str} {title_end} Preprint at {arx_str} ({year_str})."

    if rec.entry_type == "inproceedings":
        conf = rec.venue_abbrev or rec.venue or "[Conference]"
        loc = _norm_pages_en_dash(rec.pages) if rec.pages else rec.art_no
        loc_part = f" {loc}" if loc else ""
        return f"{auth_str} {title_end} In *{conf}*{loc_part} ({year_str})."

    j_name = abbreviate_journal_ieee(rec.venue, rec.venue_abbrev) or "[Journal]"
    loc = rec.art_no or (_norm_pages_en_dash(rec.pages) if rec.pages else "")
    if rec.volume and loc:
        return f"{auth_str} {title_end} *{j_name}* **{rec.volume}**, {loc} ({year_str})."
    if rec.volume:
        return f"{auth_str} {title_end} *{j_name}* **{rec.volume}** ({year_str})."
    return f"{auth_str} {title_end} *{j_name}* ({year_str})."


def format_record_apa(rec: RefRecord, link_mode: str = "auto") -> str:
    auth_str = format_authors_apa(rec.authors, rec.has_et_al)
    title_clean = rec.title.strip().rstrip(".")
    year_str = rec.year.strip() or "n.d."
    doi_norm = normalize_doi(rec.doi)
    title_end = title_clean if title_clean.endswith(("?", "!")) else f"{title_clean}."
    raw_doi_tail = f" https://doi.org/{doi_norm}" if (doi_norm and link_mode.lower() == "off") else ""

    if rec.entry_type == "book":
        pub = rec.publisher or "[Publisher]"
        return f"{auth_str} ({year_str}). *{title_clean}*. {pub}.{raw_doi_tail}"

    if _is_preprint(rec, doi_norm):
        arx_str = _extract_arxiv_str(rec, doi_norm)
        return f"{auth_str} ({year_str}). {title_end} *arXiv*, {arx_str}.{raw_doi_tail}"

    if rec.entry_type == "inproceedings":
        conf = rec.venue or rec.venue_abbrev or "[Conference]"
        loc = _norm_pages_en_dash(rec.pages) if rec.pages else rec.art_no
        loc_part = f" (pp. {loc})" if loc else ""
        return f"{auth_str} ({year_str}). {title_end} In *{conf}*{loc_part}.{raw_doi_tail}"

    j_full = expand_journal_full(rec.venue, rec.venue_abbrev) or "[Journal]"
    loc = rec.art_no or (_norm_pages_en_dash(rec.pages) if rec.pages else "")
    vol_part = f"*{rec.volume}*({rec.issue})" if (rec.volume and rec.issue) else (f"*{rec.volume}*" if rec.volume else "")
    tail_parts = [p for p in (f"*{j_full}*", vol_part, loc) if p]
    return f"{auth_str} ({year_str}). {title_end} {', '.join(tail_parts)}.{raw_doi_tail}"


def format_record_vancouver(rec: RefRecord) -> str:
    auth_str = format_authors_vancouver(rec.authors, rec.has_et_al)
    title_clean = rec.title.strip().rstrip(".")
    year_str = rec.year.strip() or "[待核实]"
    doi_norm = normalize_doi(rec.doi)
    title_end = title_clean if title_clean.endswith(("?", "!")) else f"{title_clean}."
    doi_tail = f" doi:{doi_norm}." if doi_norm else ""

    if rec.entry_type == "book":
        pub_chunks = []
        if rec.address:
            pub_chunks.append(f"{rec.address}: ")
        pub_chunks.append(rec.publisher or "[Publisher]")
        return f"{auth_str} *{title_clean}*. {''.join(pub_chunks)}; {year_str}.{doi_tail}"

    if _is_preprint(rec, doi_norm):
        arx_str = _extract_arxiv_str(rec, doi_norm)
        return f"{auth_str} {title_end} {arx_str} [Preprint]. {year_str}.{doi_tail}"

    if rec.entry_type == "inproceedings":
        conf = rec.venue_abbrev or rec.venue or "[Conference]"
        loc = _norm_pages_en_dash(rec.pages) if rec.pages else rec.art_no
        loc_part = f" p. {loc}." if loc else ""
        return f"{auth_str} {title_end} In: *{conf}*; {year_str}.{loc_part}{doi_tail}"

    j_name = abbreviate_journal_ieee(rec.venue, rec.venue_abbrev) or "[Journal]"
    loc = rec.art_no or (_norm_pages_en_dash(rec.pages) if rec.pages else "")
    vol_issue = f"{rec.volume}({rec.issue})" if (rec.volume and rec.issue) else rec.volume
    if vol_issue and loc:
        bib_tail = f"{year_str};{vol_issue}:{loc}."
    elif vol_issue:
        bib_tail = f"{year_str};{vol_issue}."
    else:
        bib_tail = f"{year_str}."
    return f"{auth_str} {title_end} *{j_name}* {bib_tail}{doi_tail}"


def format_record_acs(rec: RefRecord, link_mode: str = "auto") -> str:
    auth_str = format_authors_acs(rec.authors, rec.has_et_al)
    title_clean = rec.title.strip().rstrip(".")
    year_str = rec.year.strip() or "[待核实]"
    doi_norm = normalize_doi(rec.doi)
    title_end = title_clean if title_clean.endswith(("?", "!")) else f"{title_clean}."
    doi_tail = f" DOI: {doi_norm}." if (doi_norm and link_mode.lower() == "off") else ""

    if rec.entry_type == "book":
        pub = f"{rec.publisher}: {rec.address}" if (rec.publisher and rec.address) else (rec.publisher or "[Publisher]")
        return f"{auth_str} *{title_clean}*; {pub}, {year_str}.{doi_tail}"

    if _is_preprint(rec, doi_norm):
        arx_str = _extract_arxiv_str(rec, doi_norm)
        return f"{auth_str} {title_end} *arXiv* **{year_str}**, {arx_str}.{doi_tail}"

    if rec.entry_type == "inproceedings":
        conf = rec.venue_abbrev or rec.venue or "[Conference]"
        loc = _norm_pages_en_dash(rec.pages) if rec.pages else rec.art_no
        loc_part = f"; pp {loc}" if loc else ""
        return f"{auth_str} {title_end} In *{conf}*; {year_str}{loc_part}.{doi_tail}"

    j_name = abbreviate_journal_ieee(rec.venue, rec.venue_abbrev) or "[Journal]"
    loc = rec.art_no or (_norm_pages_en_dash(rec.pages) if rec.pages else "")
    parts = [f"*{j_name}* **{year_str}**"]
    if rec.volume and rec.issue:
        parts.append(f"*{rec.volume}* ({rec.issue})")
    elif rec.volume:
        parts.append(f"*{rec.volume}*")
    if loc:
        parts.append(loc)
    return f"{auth_str} {title_end} {', '.join(parts)}.{doi_tail}"


def format_record_chicago(rec: RefRecord, link_mode: str = "auto") -> str:
    auth_str = format_authors_chicago(rec.authors, rec.has_et_al)
    title_clean = rec.title.strip().rstrip(".").replace('"', "'")
    year_str = rec.year.strip() or "n.d."
    doi_norm = normalize_doi(rec.doi)
    quoted_title = f'"{title_clean}"' if title_clean.endswith(("?", "!")) else f'"{title_clean}."'
    doi_tail = f" https://doi.org/{doi_norm}." if (doi_norm and link_mode.lower() == "off") else ""

    if rec.entry_type == "book":
        pub = f"{rec.address}: {rec.publisher}" if (rec.address and rec.publisher) else (rec.publisher or "[Publisher]")
        return f"{auth_str} *{title_clean}*. {pub}, {year_str}.{doi_tail}"

    if _is_preprint(rec, doi_norm):
        arx_str = _extract_arxiv_str(rec, doi_norm)
        return f"{auth_str} {quoted_title} *arXiv preprint* {arx_str} ({year_str}).{doi_tail}"

    if rec.entry_type == "inproceedings":
        conf = rec.venue or rec.venue_abbrev or "[Conference]"
        loc = _norm_pages_en_dash(rec.pages) if rec.pages else rec.art_no
        loc_part = f", {loc}" if loc else ""
        return f"{auth_str} {quoted_title} In *{conf}*{loc_part}. {year_str}.{doi_tail}"

    j_full = expand_journal_full(rec.venue, rec.venue_abbrev) or "[Journal]"
    loc = rec.art_no or (_norm_pages_en_dash(rec.pages) if rec.pages else "")
    vol_part = f" {rec.volume}" if rec.volume else ""
    if rec.issue:
        vol_part += f", no. {rec.issue}"
    loc_part = f": {loc}" if loc else ""
    return f"{auth_str} {quoted_title} *{j_full}*{vol_part} ({year_str}){loc_part}.{doi_tail}"


def format_record(
    rec: RefRecord,
    bib_style: str = "ieee",
    link_mode: str = "auto",
    link_label: str = "auto",
) -> str:
    """Format a RefRecord in the chosen bibliography style and append optional clickable source link."""
    st = bib_style.lower()
    if st not in SUPPORTED_BIB_STYLES:
        raise ValueError(f"Unsupported bib_style '{bib_style}'; expected one of {SUPPORTED_BIB_STYLES}.")

    if rec.source_style == st and rec.raw_source and st in ("ieee", "gbt7714"):
        core = rec.raw_source.strip()
    elif not rec.title and rec.raw_source:
        core = rec.raw_source.strip()
    elif st == "ieee":
        core = format_record_ieee(rec)
    elif st == "gbt7714":
        core = format_record_gbt(rec)
    elif st == "nature":
        core = format_record_nature(rec)
    elif st == "apa":
        core = format_record_apa(rec, link_mode=link_mode)
    elif st == "vancouver":
        core = format_record_vancouver(rec)
    elif st == "acs":
        core = format_record_acs(rec, link_mode=link_mode)
    elif st == "chicago":
        core = format_record_chicago(rec, link_mode=link_mode)
    else:
        core = format_record_ieee(rec)

    tail_link = format_trailing_link(rec, link_mode=link_mode, link_label=link_label)
    return f"{core}{tail_link}"


# ---------------------------------------------------------------------------
# BibTeX, Existing Formatted Entry & Crossref Parsers
# ---------------------------------------------------------------------------
def parse_bibtex_authors(author_field: str) -> tuple[list[tuple[str, str]], bool]:
    cleaned = clean_bibtex_str(author_field)
    parts = [p.strip() for p in re.split(r"\s+and\s+", cleaned, flags=re.IGNORECASE) if p.strip()]
    authors: list[tuple[str, str]] = []
    has_et_al = False
    for p in parts:
        if p.lower() in ("others", "et al.", "et al"):
            has_et_al = True
            continue
        if "," in p:
            fam, giv = [x.strip() for x in p.split(",", 1)]
            authors.append((giv, fam))
        else:
            toks = p.split()
            if len(toks) == 1:
                authors.append(("", toks[0]))
            else:
                authors.append((" ".join(toks[:-1]), toks[-1]))
    return authors, has_et_al


def parse_bibtex(bib_text: str) -> dict[str, RefRecord]:
    records: dict[str, RefRecord] = {}
    idx = 0
    n = len(bib_text)
    while idx < n:
        at_pos = bib_text.find("@", idx)
        if at_pos == -1:
            break
        m_head = re.match(r"@([A-Za-z]+)\s*\{\s*([^,\s]+)\s*,", bib_text[at_pos:])
        if not m_head:
            idx = at_pos + 1
            continue
        raw_type = m_head.group(1).lower()
        cite_key = m_head.group(2).strip()
        body_start = at_pos + m_head.end()
        depth = 1
        pos = body_start
        in_quotes = False
        while pos < n and depth > 0:
            ch = bib_text[pos]
            if ch == '"' and (pos == 0 or bib_text[pos - 1] != "\\"):
                in_quotes = not in_quotes
            elif not in_quotes:
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
            pos += 1
        entry_body = bib_text[body_start : pos - 1]
        idx = pos

        if raw_type in ("comment", "preamble", "string"):
            continue

        fields: dict[str, str] = {}
        f_pos = 0
        fn = len(entry_body)
        while f_pos < fn:
            m_f = re.search(r"([A-Za-z0-9_\-]+)\s*=\s*", entry_body[f_pos:])
            if not m_f:
                break
            fname = m_f.group(1).lower()
            v_start = f_pos + m_f.end()
            while v_start < fn and entry_body[v_start].isspace():
                v_start += 1
            if v_start >= fn:
                break
            if entry_body[v_start] == "{":
                d2 = 1
                vp = v_start + 1
                while vp < fn and d2 > 0:
                    if entry_body[vp] == "{":
                        d2 += 1
                    elif entry_body[vp] == "}":
                        d2 -= 1
                    vp += 1
                fval = entry_body[v_start + 1 : vp - 1]
                f_pos = vp
            elif entry_body[v_start] == '"':
                vp = v_start + 1
                while vp < fn and not (entry_body[vp] == '"' and entry_body[vp - 1] != "\\"):
                    vp += 1
                fval = entry_body[v_start + 1 : vp]
                f_pos = vp + 1
            else:
                vp = v_start
                while vp < fn and entry_body[vp] not in ",\r\n":
                    vp += 1
                fval = entry_body[v_start:vp].strip()
                f_pos = vp
            fields[fname] = fval

        etype = "article"
        if raw_type in ("inproceedings", "conference", "proceedings"):
            etype = "inproceedings"
        elif raw_type in ("book", "inbook"):
            etype = "book"
        elif fields.get("archiveprefix", "").lower() == "arxiv" or "arxiv" in fields.get("journal", "").lower():
            etype = "preprint"

        authors, has_etal = parse_bibtex_authors(fields.get("author", ""))
        pages_raw = clean_bibtex_str(fields.get("pages", ""))
        art_no = clean_bibtex_str(fields.get("eid", "") or fields.get("article-number", "") or fields.get("art_no", ""))
        if not art_no and pages_raw and re.fullmatch(r"[eE]?\d{4,8}[a-zA-Z]?", pages_raw):
            art_no = pages_raw
            pages_raw = ""

        rec = RefRecord(
            key=cite_key,
            entry_type=etype,
            authors=authors,
            has_et_al=has_etal,
            title=clean_bibtex_str(fields.get("title", "")),
            venue=clean_bibtex_str(fields.get("journal", "") or fields.get("booktitle", "")),
            year=clean_bibtex_str(fields.get("year", "") or fields.get("date", "")[:4]),
            volume=clean_bibtex_str(fields.get("volume", "")),
            issue=clean_bibtex_str(fields.get("number", "") or fields.get("issue", "")),
            pages=pages_raw,
            art_no=art_no,
            publisher=clean_bibtex_str(fields.get("publisher", "")),
            address=clean_bibtex_str(fields.get("address", "") or fields.get("location", "")),
            doi=normalize_doi(fields.get("doi", "")),
            arxiv_id=clean_arxiv_id(fields.get("eprint", "")),
            url=normalize_url(clean_bibtex_str(fields.get("url", ""))),
        )
        records[cite_key] = rec
    return records


def _parse_surname_initials_authors(auth_str: str, sep_pattern: str = r"\s*;\s*") -> tuple[list[tuple[str, str]], bool]:
    """Parse `Surname, I. I.` author lists separated by semicolon or ` & ` / `, `."""
    s = auth_str.strip()
    has_et_al = False
    if re.search(r"\*?et al\.?\*?", s, flags=re.IGNORECASE):
        has_et_al = True
        s = re.sub(r"[,;\s]*\*?et al\.?\*?$", "", s, flags=re.IGNORECASE).strip()

    authors: list[tuple[str, str]] = []
    if sep_pattern == "comma_amp":
        # Match pairs `Family, Initials` separated by `, ` or ` & ` (allow optional trailing period on last initial)
        chunks = re.findall(r"([^,&]+?,\s*(?:[A-Z]\.?(?:-[A-Z]\.?)*(?:\s+[A-Z]\.?(?:-[A-Z]\.?)*)*))", s)
        if chunks:
            for ch in chunks:
                fam, giv = [x.strip() for x in ch.split(",", 1)]
                authors.append((giv, fam))
            return authors, has_et_al
        parts = [p.strip() for p in re.split(r"\s*&\s*", s) if p.strip()]
    else:
        parts = [p.strip() for p in re.split(sep_pattern, s) if p.strip()]

    for p in parts:
        p = p.lstrip("& ").strip()
        if not p or p in ("...", "…"):
            continue
        if "," in p:
            fam, giv = [x.strip() for x in p.split(",", 1)]
            authors.append((giv, fam))
        else:
            toks = p.split()
            if len(toks) >= 2:
                authors.append((" ".join(toks[1:]), toks[0]))
            elif toks:
                authors.append(("", toks[0]))
    return authors, has_et_al


def _attach_extracted_url(rec: RefRecord, extracted_url: str) -> RefRecord:
    if not extracted_url:
        return rec
    if re.match(r"^https?://(?:dx\.)?doi\.org/", extracted_url, flags=re.IGNORECASE):
        if not rec.doi:
            rec.doi = normalize_doi(extracted_url)
    elif re.match(r"^https?://arxiv\.org/(?:abs|pdf)/", extracted_url, flags=re.IGNORECASE):
        if not rec.arxiv_id:
            rec.arxiv_id = clean_arxiv_id(extracted_url)
    elif not rec.url:
        rec.url = extracted_url
    return rec


def parse_formatted_ieee_line(key: str, text: str) -> RefRecord:
    """Parse an existing IEEE formatted bibliography string into RefRecord."""
    s = text.strip()
    rec = RefRecord(key=key, raw_ieee=s, raw_source=s, source_style="ieee")

    m_doi = re.search(r",?\s*doi:\s*([^\s]+?)\.?\s*$", s, flags=re.IGNORECASE)
    work = s
    if m_doi:
        rec.doi = normalize_doi(m_doi.group(1))
        work = s[: m_doi.start()].strip()

    m_q = re.match(r'^(.+?),\s*"(.+?)"\s*(.*)$', work)
    if m_q:
        auth_part = m_q.group(1).strip()
        title_part = m_q.group(2).strip().rstrip(",")
        rest = m_q.group(3).lstrip(", ").strip()
        rec.title = title_part

        if "*et al.*" in auth_part or "et al." in auth_part:
            rec.has_et_al = True
            first_a = re.sub(r"\s*\*?et al\.\*?.*$", "", auth_part).strip().rstrip(",")
            toks = first_a.split()
            if len(toks) >= 2:
                rec.authors = [(" ".join(toks[:-1]), toks[-1])]
            elif toks:
                rec.authors = [("", toks[0])]
        else:
            norm_a = re.sub(r",\s+and\s+", ", ", auth_part)
            norm_a = re.sub(r"\s+and\s+", ", ", norm_a)
            for chunk in [c.strip() for c in norm_a.split(",") if c.strip()]:
                toks = chunk.split()
                if len(toks) >= 2:
                    rec.authors.append((" ".join(toks[:-1]), toks[-1]))
                elif toks:
                    rec.authors.append(("", toks[0]))

        if "arxiv" in rest.lower():
            rec.entry_type = "preprint"
            m_arx = re.search(r"(arXiv:\S+)", rest, flags=re.IGNORECASE)
            if m_arx:
                rec.arxiv_id = clean_arxiv_id(m_arx.group(1))
            m_yr = re.search(r"\b(19\d{2}|20\d{2})\b", rest)
            if m_yr:
                rec.year = m_yr.group(1)
            return rec

        if rest.lower().startswith("in *"):
            rec.entry_type = "inproceedings"
            m_v = re.match(r"in\s+\*([^*]+)\*(?:,\s*(.*))?$", rest, flags=re.IGNORECASE)
            if m_v:
                rec.venue_abbrev = m_v.group(1).strip()
                tail = m_v.group(2) or ""
            else:
                tail = rest
        else:
            m_v = re.match(r"\*([^*]+)\*(?:,\s*(.*))?$", rest)
            if m_v:
                rec.venue_abbrev = m_v.group(1).strip()
                tail = m_v.group(2) or ""
            else:
                tail = rest

        m_vol = re.search(r"\bvol\.\s*([^,]+)", tail, flags=re.IGNORECASE)
        if m_vol:
            rec.volume = m_vol.group(1).strip()
        m_no = re.search(r"\bno\.\s*([^,]+)", tail, flags=re.IGNORECASE)
        if m_no:
            rec.issue = m_no.group(1).strip()
        m_art = re.search(r"\bArt\.\s*no\.\s*([^,]+)", tail, flags=re.IGNORECASE)
        if m_art:
            rec.art_no = m_art.group(1).strip().rstrip(".")
        m_pp = re.search(r"\bpp?\.\s*([^,]+)", tail, flags=re.IGNORECASE)
        if m_pp:
            rec.pages = m_pp.group(1).strip().rstrip(".")
        m_yr = re.findall(r"\b(19\d{2}|20\d{2})\b", tail)
        if m_yr:
            rec.year = m_yr[-1]
        return rec

    m_bk = re.match(r"^(.+?),\s*\*([^*]+)\*\.\s*(.+)$", work)
    if m_bk:
        rec.entry_type = "book"
        auth_part = m_bk.group(1).strip()
        rec.title = m_bk.group(2).strip()
        tail = m_bk.group(3).strip().rstrip(".")
        toks = auth_part.split()
        if len(toks) >= 2:
            rec.authors = [(" ".join(toks[:-1]), toks[-1])]
        m_yr = re.search(r"\b(19\d{2}|20\d{2})\b", tail)
        if m_yr:
            rec.year = m_yr.group(1)
            pub_chunk = tail[: m_yr.start()].strip().rstrip(",")
            if ":" in pub_chunk:
                rec.address, rec.publisher = [x.strip() for x in pub_chunk.split(":", 1)]
            else:
                rec.publisher = pub_chunk
    return rec


def parse_formatted_gbt_line(key: str, text: str) -> RefRecord:
    """Parse an existing GB/T 7714 bibliography string."""
    s = text.strip()
    rec = RefRecord(key=key, raw_gbt=s, raw_source=s, source_style="gbt7714")
    m_doi = re.search(r"\s*DOI:\s*([^\s]+?)\.?\s*$", s, flags=re.IGNORECASE)
    work = s[: m_doi.start()].strip() if m_doi else s
    if m_doi:
        rec.doi = normalize_doi(m_doi.group(1))

    m_gbt = re.match(r"^(.+?)\.\s+(.+?)\[(J|C|M|D|EB/OL)\]\.\s*(.+)$", work)
    if not m_gbt:
        return parse_formatted_ieee_line(key, text)

    auth_raw, title_raw, tag, tail = m_gbt.groups()
    rec.title = title_raw.strip()
    if tag == "M":
        rec.entry_type = "book"
    elif tag == "C":
        rec.entry_type = "inproceedings"
    elif tag == "EB/OL":
        rec.entry_type = "preprint"

    for chunk in [c.strip() for c in auth_raw.split(",") if c.strip()]:
        if chunk.lower() in ("et al", "et al.", "等"):
            rec.has_et_al = True
            continue
        toks = chunk.split()
        if len(toks) >= 2 and not is_cjk(chunk):
            init_start = len(toks)
            while init_start > 1 and re.fullmatch(r"[A-Z]\.?", toks[init_start - 1]):
                init_start -= 1
            if init_start < len(toks):
                fam = " ".join(toks[:init_start])
                giv = " ".join(toks[init_start:])
                rec.authors.append((giv, fam))
            else:
                rec.authors.append((" ".join(toks[1:]), toks[0]))
        else:
            rec.authors.append(("", chunk))

    if tag == "J":
        m_j = re.match(r"^(.+?),\s*(19\d{2}|20\d{2}),\s*([^(:]+)(?:\(([^)]+)\))?:\s*(.+?)\.?$", tail)
        if m_j:
            rec.venue = m_j.group(1).strip()
            rec.year = m_j.group(2)
            rec.volume = m_j.group(3).strip()
            rec.issue = (m_j.group(4) or "").strip()
            loc = m_j.group(5).strip().rstrip(".")
            if "–" in loc or "-" in loc:
                rec.pages = loc
            else:
                rec.art_no = loc
        else:
            m_online = re.match(r"^(.+?),\s*(19\d{2}|20\d{2})\.?$", tail)
            if m_online:
                rec.venue = m_online.group(1).strip()
                rec.year = m_online.group(2)
    elif tag == "EB/OL":
        m_arx = re.search(r"(arXiv:\S+)", tail, flags=re.IGNORECASE)
        if m_arx:
            rec.arxiv_id = clean_arxiv_id(m_arx.group(1))
        m_yr = re.search(r"\b(19\d{2}|20\d{2})\b", tail)
        if m_yr:
            rec.year = m_yr.group(1)
    elif tag == "C":
        m_c = re.match(r"^//(.+?)\.\s*(19\d{2}|20\d{2}):\s*(.+?)\.?$", tail)
        if m_c:
            rec.venue = m_c.group(1).strip()
            rec.year = m_c.group(2)
            rec.pages = m_c.group(3).strip().rstrip(".")
    elif tag == "M":
        m_m = re.match(r"^(.+?),\s*(19\d{2}|20\d{2})\.?$", tail)
        if m_m:
            pub_chunk = m_m.group(1).strip()
            rec.year = m_m.group(2)
            if ":" in pub_chunk:
                rec.address, rec.publisher = [x.strip() for x in pub_chunk.split(":", 1)]
            else:
                rec.publisher = pub_chunk
    return rec


def parse_formatted_apa_line(key: str, text: str) -> RefRecord:
    s = text.strip()
    rec = RefRecord(key=key, raw_source=s, source_style="apa")
    m_doi = re.search(r"\s+https?://(?:dx\.)?doi\.org/([^\s]+?)\.?\s*$", s, flags=re.IGNORECASE)
    work = s[: m_doi.start()].strip() if m_doi else s
    if m_doi:
        rec.doi = normalize_doi(m_doi.group(1))

    m = re.match(r"^(.+?)\s*\((\d{4}|n\.d\.)\)\.\s+(.+)$", work)
    if not m:
        return parse_formatted_ieee_line(key, text)
    auth_part, yr, rest = m.groups()
    rec.authors, rec.has_et_al = _parse_surname_initials_authors(auth_part, "comma_amp")
    rec.year = "" if yr == "n.d." else yr

    # Conference: Title. In *Conf* (pp. pages).
    m_c = re.match(r"^(.+?[.?!])\s+In\s+\*([^*]+)\*(?:\s*\(pp?\.\s*([^)]+)\))?\.?$", rest)
    if m_c:
        rec.entry_type = "inproceedings"
        rec.title = m_c.group(1).rstrip(".")
        rec.venue = m_c.group(2).strip()
        rec.pages = (m_c.group(3) or "").strip()
        return rec

    # Journal: Title. *Journal*, *vol*(issue), loc.
    m_j = re.match(r"^(.+?[.?!])\s+\*([^*]+)\*(?:,\s*(.+?))?\.?$", rest)
    if m_j:
        rec.title = m_j.group(1).rstrip(".")
        venue = m_j.group(2).strip()
        tail = (m_j.group(3) or "").strip().rstrip(".")
        if venue.lower() == "arxiv":
            rec.entry_type = "preprint"
            m_arx = re.search(r"arXiv:\S+", tail, flags=re.IGNORECASE)
            if m_arx:
                rec.arxiv_id = clean_arxiv_id(m_arx.group(0))
            return rec
        rec.venue = venue
        m_vi = re.match(r"^\*([^*]+)\*(?:\(([^)]+)\))?(?:,\s*(.+))?$", tail)
        if m_vi:
            rec.volume = m_vi.group(1).strip()
            rec.issue = (m_vi.group(2) or "").strip()
            loc = (m_vi.group(3) or "").strip()
            if loc:
                if "–" in loc or "-" in loc:
                    rec.pages = loc
                else:
                    rec.art_no = loc
        return rec
    return rec


_INITIALS_RE = r"(?:[A-Z]\.(?:-[A-Z]\.)*(?:\s+[A-Z]\.(?:-[A-Z]\.)*)*)"
_ONE_SURNAME_INIT_RE = rf"[^.,;&]+,\s*{_INITIALS_RE}"
_NATURE_AUTH_RE = rf"(?:{_ONE_SURNAME_INIT_RE}(?:\s*(?:,|&)\s*{_ONE_SURNAME_INIT_RE})*(?:\s+\*et al\.\*)?|[^.]+\.)"
_ACS_AUTH_RE = rf"(?:{_ONE_SURNAME_INIT_RE}(?:\s*;\s*{_ONE_SURNAME_INIT_RE})*(?:;\s*et al\.)?|[^.]+\.)"


def parse_formatted_nature_line(key: str, text: str) -> RefRecord:
    s = text.strip()
    rec = RefRecord(key=key, raw_source=s, source_style="nature")
    m_pre = re.match(rf"^({_NATURE_AUTH_RE})\s+(.+?[.?!])\s+Preprint at (arXiv:\S+)\s+\((\d{{4}})\)\.?$", s)
    if m_pre:
        rec.entry_type = "preprint"
        rec.authors, rec.has_et_al = _parse_surname_initials_authors(m_pre.group(1), "comma_amp")
        rec.title = m_pre.group(2).rstrip(".")
        rec.arxiv_id = clean_arxiv_id(m_pre.group(3))
        rec.year = m_pre.group(4)
        return rec

    m_j = re.match(
        rf"^({_NATURE_AUTH_RE})\s+(.+?[.?!])\s+\*([^*]+)\*\s+\*\*([^*]+)\*\*(?:,\s*([^(]+?))?\s*\((\d{{4}})\)\.?$",
        s,
    )
    if m_j:
        rec.authors, rec.has_et_al = _parse_surname_initials_authors(m_j.group(1), "comma_amp")
        rec.title = m_j.group(2).rstrip(".")
        rec.venue_abbrev = m_j.group(3).strip()
        rec.volume = m_j.group(4).strip()
        loc = (m_j.group(5) or "").strip()
        if loc:
            if "–" in loc or "-" in loc:
                rec.pages = loc
            else:
                rec.art_no = loc
        rec.year = m_j.group(6)
        return rec

    m_conf = re.match(rf"^({_NATURE_AUTH_RE})\s+(.+?[.?!])\s+In\s+\*([^*]+)\*(?:\s+([^(]+?))?\s*\((\d{{4}})\)\.?$", s)
    if m_conf:
        rec.entry_type = "inproceedings"
        rec.authors, rec.has_et_al = _parse_surname_initials_authors(m_conf.group(1), "comma_amp")
        rec.title = m_conf.group(2).rstrip(".")
        rec.venue_abbrev = m_conf.group(3).strip()
        loc = (m_conf.group(4) or "").strip()
        if loc:
            rec.pages = loc
        rec.year = m_conf.group(5)
        return rec
    return parse_formatted_ieee_line(key, text)


def parse_formatted_acs_line(key: str, text: str) -> RefRecord:
    s = text.strip()
    m_doi = re.search(r"\s*DOI:\s*([^\s]+?)\.?\s*$", s, flags=re.IGNORECASE)
    work = s[: m_doi.start()].strip() if m_doi else s
    rec = RefRecord(key=key, raw_source=work, source_style="acs")
    if m_doi:
        rec.doi = normalize_doi(m_doi.group(1))

    m = re.match(rf"^({_ACS_AUTH_RE})\s+(.+?[.?!])\s+\*([^*]+)\*\s+\*\*(\d{{4}})\*\*(?:,\s*(.+?))?\.?$", work)
    if not m:
        m_conf = re.match(rf"^({_ACS_AUTH_RE})\s+(.+?[.?!])\s+In\s+\*([^*]+)\*;\s*(\d{{4}})(?:;\s*pp\s+(.+?))?\.?$", work)
        if m_conf:
            rec.entry_type = "inproceedings"
            rec.authors, rec.has_et_al = _parse_surname_initials_authors(m_conf.group(1), r"\s*;\s*")
            rec.title = m_conf.group(2).rstrip(".")
            rec.venue_abbrev = m_conf.group(3).strip()
            rec.year = m_conf.group(4)
            rec.pages = (m_conf.group(5) or "").strip()
            return rec
        return parse_formatted_ieee_line(key, text)
    auth_raw, title_raw, venue, yr, tail = m.groups()
    rec.authors, rec.has_et_al = _parse_surname_initials_authors(auth_raw, r"\s*;\s*")
    rec.title = title_raw.rstrip(".")
    rec.year = yr
    tail = (tail or "").strip().rstrip(".")
    if venue.lower() == "arxiv":
        rec.entry_type = "preprint"
        rec.arxiv_id = clean_arxiv_id(tail)
        return rec
    rec.venue_abbrev = venue.strip()
    m_vi = re.match(r"^\*([^*]+)\*(?:\s*\(([^)]+)\))?(?:,\s*(.+))?$", tail)
    if m_vi:
        rec.volume = m_vi.group(1).strip()
        rec.issue = (m_vi.group(2) or "").strip()
        loc = (m_vi.group(3) or "").strip()
        if loc:
            if "–" in loc or "-" in loc:
                rec.pages = loc
            else:
                rec.art_no = loc
    return rec


def _parse_vancouver_authors(auth_raw: str) -> tuple[list[tuple[str, str]], bool]:
    authors: list[tuple[str, str]] = []
    has_et_al = False
    for chunk in [c.strip() for c in auth_raw.split(",") if c.strip()]:
        if chunk.lower() in ("et al", "et al."):
            has_et_al = True
            continue
        toks = chunk.split()
        if len(toks) >= 2 and re.fullmatch(r"[A-Z]{1,4}", toks[-1]):
            authors.append((" ".join(toks[-1]), " ".join(toks[:-1])))
        elif len(toks) >= 2:
            authors.append((toks[-1], " ".join(toks[:-1])))
        elif toks:
            authors.append(("", toks[0]))
    return authors, has_et_al


def parse_formatted_vancouver_line(key: str, text: str) -> RefRecord:
    s = text.strip()
    m_doi = re.search(r"\s*doi:\s*([^\s]+?)\.?\s*$", s, flags=re.IGNORECASE)
    work = s[: m_doi.start()].strip() if m_doi else s
    rec = RefRecord(key=key, raw_source=work, source_style="vancouver")
    if m_doi:
        rec.doi = normalize_doi(m_doi.group(1))

    m_pre = re.match(r"^([^.]+)\.\s+(.+?[.?!])\s+(arXiv:\S+)\s+\[Preprint\]\.\s*(\d{4})\.?$", work)
    if m_pre:
        rec.entry_type = "preprint"
        rec.authors, rec.has_et_al = _parse_vancouver_authors(m_pre.group(1))
        rec.title = m_pre.group(2).rstrip(".")
        rec.arxiv_id = clean_arxiv_id(m_pre.group(3))
        rec.year = m_pre.group(4)
        return rec

    m_conf = re.match(r"^([^.]+)\.\s+(.+?[.?!])\s+In:\s+\*([^*]+)\*;\s*(\d{4})\.(?:\s*p\.\s*(.+?)\.?)?$", work)
    if m_conf:
        rec.entry_type = "inproceedings"
        rec.authors, rec.has_et_al = _parse_vancouver_authors(m_conf.group(1))
        rec.title = m_conf.group(2).rstrip(".")
        rec.venue_abbrev = m_conf.group(3).strip()
        rec.year = m_conf.group(4)
        rec.pages = (m_conf.group(5) or "").strip().rstrip(".")
        return rec

    m = re.match(r"^([^.]+)\.\s+(.+?[.?!])\s+\*([^*]+)\*\s+(\d{4})(?:;([^(:]+)(?:\(([^)]+)\))?(?::(.+?))?)?\.?$", work)
    if m:
        auth_raw, title_raw, venue, yr, vol, iss, loc = m.groups()
        rec.authors, rec.has_et_al = _parse_vancouver_authors(auth_raw)
        rec.title = title_raw.rstrip(".")
        rec.venue_abbrev = venue.strip()
        rec.year = yr
        rec.volume = (vol or "").strip()
        rec.issue = (iss or "").strip()
        loc_s = (loc or "").strip().rstrip(".")
        if loc_s:
            if "–" in loc_s or "-" in loc_s:
                rec.pages = loc_s
            else:
                rec.art_no = loc_s
        return rec
    return parse_formatted_ieee_line(key, text)


def parse_formatted_chicago_line(key: str, text: str) -> RefRecord:
    s = text.strip()
    m_doi = re.search(r"\s+https?://(?:dx\.)?doi\.org/([^\s]+?)\.?\s*$", s, flags=re.IGNORECASE)
    work = s[: m_doi.start()].strip() if m_doi else s
    rec = RefRecord(key=key, raw_source=work, source_style="chicago")
    if m_doi:
        rec.doi = normalize_doi(m_doi.group(1))

    m = re.match(r'^(.+?)\.\s+"(.+?)"\s+(In\s+)?\*([^*]+)\*(?:,?\s*(.+?))?\.?$', work)
    if not m:
        return parse_formatted_ieee_line(key, text)
    auth_raw, title_raw, in_kw, venue, tail = m.groups()
    rec.title = title_raw.rstrip(".")
    if re.search(r"\bet al\.?$", auth_raw, flags=re.IGNORECASE):
        rec.has_et_al = True
        auth_raw = re.sub(r",?\s*et al\.?$", "", auth_raw, flags=re.IGNORECASE).strip()
    m_first = re.match(r"^([^,]+),\s*([^,]+)(?:,\s*(.*))?$", auth_raw)
    if m_first:
        rec.authors.append((m_first.group(2).strip(), m_first.group(1).strip()))
        rest_a = (m_first.group(3) or "").strip()
        if rest_a:
            rest_a = re.sub(r"^and\s+", "", rest_a)
            rest_a = re.sub(r",\s*and\s+", ", ", rest_a)
            for ch in [c.strip() for c in rest_a.split(",") if c.strip()]:
                toks = ch.split()
                if len(toks) >= 2:
                    rec.authors.append((" ".join(toks[:-1]), toks[-1]))
                elif toks:
                    rec.authors.append(("", toks[0]))
    tail_s = (tail or "").strip()
    if in_kw:
        rec.entry_type = "inproceedings"
        rec.venue = venue.strip()
        m_yr = re.search(r"\b(19\d{2}|20\d{2})\b", tail_s)
        if m_yr:
            rec.year = m_yr.group(1)
            rec.pages = tail_s[: m_yr.start()].strip(" .,")
        return rec
    if "arxiv" in venue.lower():
        rec.entry_type = "preprint"
        m_arx = re.search(r"arXiv:\S+", tail_s, flags=re.IGNORECASE)
        if m_arx:
            rec.arxiv_id = clean_arxiv_id(m_arx.group(0))
        m_yr = re.search(r"\((\d{4})\)", tail_s)
        if m_yr:
            rec.year = m_yr.group(1)
        return rec
    rec.venue = venue.strip()
    m_t = re.match(r"^(?:([^,(]+?)(?:,\s*no\.\s*([^(\s]+))?\s*)?\((\d{4})\)(?::\s*(.+))?$", tail_s)
    if m_t:
        rec.volume = (m_t.group(1) or "").strip()
        rec.issue = (m_t.group(2) or "").strip()
        rec.year = m_t.group(3)
        loc = (m_t.group(4) or "").strip().rstrip(".")
        if loc:
            if "–" in loc or "-" in loc:
                rec.pages = loc
            else:
                rec.art_no = loc
    return rec


def parse_formatted_ref_line(key: str, text: str) -> RefRecord:
    """Detect bibliography style, strip trailing clickable link, and parse into RefRecord."""
    clean_body, extracted_url = strip_trailing_markdown_link(text)
    if re.search(r"\[(J|C|M|D|EB/OL)\]\.", clean_body):
        rec = parse_formatted_gbt_line(key, clean_body)
    elif re.match(r"^.+?\s*\((?:\d{4}|n\.d\.)\)\.\s+", clean_body):
        rec = parse_formatted_apa_line(key, clean_body)
    elif re.search(r"\*[^*]+\*\s+\*\*\d{4}\*\*", clean_body) or re.search(r"\bIn\s+\*[^*]+\*;\s*\d{4}", clean_body):
        rec = parse_formatted_acs_line(key, clean_body)
    elif (
        re.search(r"\*[^*]+\*\s+\*\*[^*]+\*\*.*\(\d{4}\)\.?$", clean_body)
        or "Preprint at arXiv:" in clean_body
        or re.search(r"\bIn\s+\*[^*]+\*(?:\s+[^(]+)?\s*\(\d{4}\)\.?$", clean_body)
    ):
        rec = parse_formatted_nature_line(key, clean_body)
    elif (
        re.search(r"\*[^*]+\*\s+(?:19|20)\d{2};", clean_body)
        or "[Preprint]." in clean_body
        or re.search(r"\bIn:\s+\*[^*]+\*;\s*\d{4}", clean_body)
    ):
        rec = parse_formatted_vancouver_line(key, clean_body)
    elif re.match(r'^.+?\.\s+"[^"]+"\s+(?:In\s+)?\*[^*]+\*', clean_body):
        rec = parse_formatted_chicago_line(key, clean_body)
    else:
        rec = parse_formatted_ieee_line(key, clean_body)
    return _attach_extracted_url(rec, extracted_url)


def fetch_crossref_metadata(doi: str, timeout: float = 8.0) -> dict[str, Any] | None:
    norm = normalize_doi(doi)
    if not norm:
        return None
    url = f"https://api.crossref.org/works/{urllib.parse.quote(norm, safe='')}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "MdCitationSkill/2.0 (Academic Markdown Verification; mailto:research@example.org)",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            return payload.get("message")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


def enrich_record_from_crossref(rec: RefRecord, timeout: float = 8.0) -> bool:
    if not rec.doi:
        return False
    msg = fetch_crossref_metadata(rec.doi, timeout=timeout)
    if not msg:
        return False

    if not rec.authors and msg.get("author"):
        for a in msg["author"]:
            giv = a.get("given", "").strip()
            fam = a.get("family", "") or a.get("name", "")
            if fam:
                rec.authors.append((giv, fam.strip()))

    if not rec.title and msg.get("title"):
        raw_t = msg["title"][0]
        rec.title = re.sub(r"<[^>]+>", "", html.unescape(raw_t)).strip()

    if not rec.venue and msg.get("container-title"):
        rec.venue = html.unescape(msg["container-title"][0]).strip()
    if not rec.venue_abbrev and msg.get("short-container-title"):
        rec.venue_abbrev = html.unescape(msg["short-container-title"][0]).strip()

    if not rec.volume and msg.get("volume"):
        rec.volume = str(msg["volume"]).strip()
    if not rec.issue and msg.get("issue"):
        rec.issue = str(msg["issue"]).strip()

    if not rec.art_no and msg.get("article-number"):
        rec.art_no = str(msg["article-number"]).strip()
    if not rec.pages and not rec.art_no and msg.get("page"):
        p = str(msg["page"]).strip()
        if "-" in p or "–" in p:
            rec.pages = p.replace("-", "–")
        else:
            rec.art_no = p

    if not rec.year:
        for date_field in ("published-print", "published-online", "issued", "created"):
            parts = msg.get(date_field, {}).get("date-parts", [])
            if parts and parts[0] and parts[0][0]:
                rec.year = str(parts[0][0])
                break

    if not rec.url and msg.get("URL"):
        rec.url = normalize_url(str(msg["URL"]))

    ctype = msg.get("type", "")
    if ctype == "proceedings-article":
        rec.entry_type = "inproceedings"
    elif ctype in ("book", "monograph"):
        rec.entry_type = "book"
    elif ctype == "posted-content":
        rec.entry_type = "preprint"
    return True


def make_hover_tooltip(rec: RefRecord, fallback_text: str) -> str:
    if rec.title:
        first_fam = rec.authors[0][1] if rec.authors else ""
        if len(rec.authors) > 2 or rec.has_et_al:
            auth_short = f"{first_fam} et al."
        elif len(rec.authors) == 2:
            auth_short = f"{rec.authors[0][1]} & {rec.authors[1][1]}"
        else:
            auth_short = first_fam
        ven = rec.venue_abbrev or abbreviate_journal_ieee(rec.venue) or "Preprint"
        yr = rec.year or ""
        tip = f"{auth_short} — {rec.title} ({ven}, {yr})".strip(" —,()")
    else:
        clean_fb, _ = strip_trailing_markdown_link(fallback_text)
        tip = re.sub(r"\*", "", clean_fb)
    tip = tip.replace('"', "'").replace("\n", " ")
    return tip[:240]


def make_citekey(rec: RefRecord, index: int) -> str:
    fam = re.sub(r"[^A-Za-z0-9]", "", rec.authors[0][1]) if rec.authors else f"Ref{index}"
    if not fam:
        fam = f"Ref{index}"
    yr = re.sub(r"[^0-9]", "", rec.year) or "nd"
    return f"{fam}{yr}_{index}"


def record_to_bibtex(rec: RefRecord, cite_key: str) -> str:
    btype = "article"
    if rec.entry_type == "inproceedings":
        btype = "inproceedings"
    elif rec.entry_type == "book":
        btype = "book"
    elif rec.entry_type == "preprint":
        btype = "misc"

    lines = [f"@{btype}{{{cite_key},"]
    if rec.authors:
        a_list = [f"{fam}, {giv}".strip(", ") for giv, fam in rec.authors]
        if rec.has_et_al:
            a_list.append("others")
        lines.append(f"  author = {{{' and '.join(a_list)}}},")
    if rec.title:
        lines.append(f"  title = {{{rec.title}}},")
    if btype == "inproceedings" and (rec.venue or rec.venue_abbrev):
        lines.append(f"  booktitle = {{{rec.venue or rec.venue_abbrev}}},")
    elif btype == "article" and (rec.venue or rec.venue_abbrev):
        lines.append(f"  journal = {{{rec.venue or rec.venue_abbrev}}},")
    if rec.year:
        lines.append(f"  year = {{{rec.year}}},")
    if rec.volume:
        lines.append(f"  volume = {{{rec.volume}}},")
    if rec.issue:
        lines.append(f"  number = {{{rec.issue}}},")
    if rec.art_no:
        lines.append(f"  eid = {{{rec.art_no}}},")
    elif rec.pages:
        lines.append(f"  pages = {{{rec.pages.replace('–', '--')}}},")
    if rec.arxiv_id:
        lines.append("  archivePrefix = {arXiv},")
        lines.append(f"  eprint = {{{clean_arxiv_id(rec.arxiv_id)}}},")
    if rec.doi:
        lines.append(f"  doi = {{{normalize_doi(rec.doi)}}},")
    if rec.url:
        lines.append(f"  url = {{{rec.url}}},")
    lines.append("}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Markdown Protected-Span Masking, Parsing & Scheme Rendering
# ---------------------------------------------------------------------------
REF_HEADING_RE = re.compile(
    r"^#{1,3}\s*(?:(?:第?[一二三四五六七八九十\d]+[章节部分、.\s]+)?(?:主要)?(?:参考文献|引用文献)|(?:\d+(?:\.\d+)*\.?\s+)?(?:References|Bibliography))(?:[（(]\s*References\s*[)）])?\s*$",
    flags=re.IGNORECASE,
)


def split_body_and_ref_section(md_text: str) -> tuple[list[str], str, list[str]]:
    """Return (body_lines, ref_heading_line, ref_lines)."""
    lines = md_text.split("\n")
    in_fence = False
    ref_heading_idx = -1
    for i, line in enumerate(lines):
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if not in_fence and REF_HEADING_RE.match(line.strip()):
            ref_heading_idx = i

    if ref_heading_idx != -1:
        body = lines[:ref_heading_idx]
        while body and body[-1].strip() == "":
            body.pop()
        if body and body[-1].strip() == "---":
            body.pop()
            while body and body[-1].strip() == "":
                body.pop()
        return body, lines[ref_heading_idx].strip(), lines[ref_heading_idx + 1 :]

    tail_defs_start = len(lines)
    idx = len(lines) - 1
    while idx >= 0:
        s = lines[idx].strip()
        if s == "" or re.match(r"^\[\^[^\]]+\]:\s+", s) or re.match(r"^\[ref-\d+\]:\s+#ref-\d+", s):
            tail_defs_start = idx
            idx -= 1
        else:
            break
    if tail_defs_start < len(lines) and any(
        re.match(r"^\[\^[^\]]+\]:\s+", l.strip()) for l in lines[tail_defs_start:]
    ):
        body = lines[:tail_defs_start]
        while body and body[-1].strip() == "":
            body.pop()
        if body and body[-1].strip() == "---":
            body.pop()
            while body and body[-1].strip() == "":
                body.pop()
        return body, "## 参考文献（References）", lines[tail_defs_start:]

    return lines, "## 参考文献（References）", []


def parse_existing_ref_section(ref_lines: list[str]) -> dict[str, RefRecord]:
    records: dict[str, RefRecord] = {}
    for raw in ref_lines:
        s = raw.strip()
        if not s or s == "---":
            continue
        if re.match(r"^\[(?:ref-)?\d+\]:\s*#ref-\d+", s):
            continue
        m_a = re.match(r"^\[\^([^\]]+)\]:\s+(.+)$", s)
        if m_a:
            k, body = m_a.group(1).strip(), m_a.group(2).strip()
            records[k] = parse_formatted_ref_line(k, body)
            continue
        m_b = re.match(r'^(?:<a\s+id="ref-\d+"\s*>\s*</a>\s*)?\[(\d+)\]\s+(.+)$', s)
        if m_b:
            k, body = m_b.group(1).strip(), m_b.group(2).strip()
            records[k] = parse_formatted_ref_line(k, body)
            continue
        m_n = re.match(r"^(\d+)\.\s+(.+)$", s)
        if m_n:
            k, body = m_n.group(1).strip(), m_n.group(2).strip()
            records[k] = parse_formatted_ref_line(k, body)
    return records


def mask_line_protected(line: str) -> tuple[str, list[str]]:
    """Mask inline code, inline math, images, and non-#ref Markdown links so citations inside them are never touched."""
    vault: list[str] = []

    def stash(m: re.Match) -> str:
        idx = len(vault)
        vault.append(m.group(0))
        return f"\x00P{idx}\x00"

    s = re.sub(r"``[^`]+``|`[^`]+`", stash, line)
    s = re.sub(r"(?<!\\)\$[^\$\n]+?(?<!\\)\$", stash, s)
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", stash, s)

    def stash_non_ref_link(m: re.Match) -> str:
        full = m.group(0)
        if re.match(r"^\[\[\d+\]\]\(#ref-\d+\)$", full):
            return full
        idx = len(vault)
        vault.append(full)
        return f"\x00P{idx}\x00"

    s = re.sub(r"(?:\[\[\d+\]\]\(#ref-\d+\)|\[[^\]]+\]\([^)]*\))", stash_non_ref_link, s)
    return s, vault


def unmask_line(line: str, vault: list[str]) -> str:
    def restore(m: re.Match) -> str:
        return vault[int(m.group(1))]

    return re.sub(r"\x00P(\d+)\x00", restore, line)


def expand_num_spec(spec: str) -> list[str]:
    """Expand '45–47' or '12, 45-47' into ['12', '45', '46', '47']."""
    out: list[str] = []
    for part in spec.split(","):
        p = part.strip()
        if not p:
            continue
        m_rng = re.match(r"^(\d+)\s*[–\-—]\s*(\d+)$", p)
        if m_rng:
            a, b = int(m_rng.group(1)), int(m_rng.group(2))
            if a <= b and (b - a) <= 200:
                out.extend(str(x) for x in range(a, b + 1))
            else:
                out.extend([str(a), str(b)])
        elif p.isdigit():
            out.append(p)
    return out


CLUSTER_MASTER_RE = re.compile(
    r"""
    (?P<schemeD><sup>\s*\[\[\d+\]\]\(\#ref-\d+\)(?:\s*(?:[–\-—]|,\s*)\[\[\d+\]\]\(\#ref-\d+\))*\s*</sup>)
    | (?P<schemeB>\[\[\d+\]\]\(\#ref-\d+\)(?:\s*(?:[–\-—]|,\s*)\[\[\d+\]\]\(\#ref-\d+\))*)
    | (?P<schemeC>\[\[\d+\]\]\[(?:ref-)?\d+\](?:\s*(?:[–\-—]|,\s*)\[\[\d+\]\]\[(?:ref-)?\d+\])*)
    | (?P<schemeA>(?:\[\^[A-Za-z0-9_.:-]+\])+)
    | (?P<pandoc>\[@[A-Za-z0-9_.:-]+(?:\s*;\s*@[A-Za-z0-9_.:-]+)*\])
    | (?P<schemeE>(?<![!\[\^\\])\[\d+(?:\s*[–\-—]\s*\d+)?(?:\s*,\s*\d+(?:\s*[–\-—]\s*\d+)?)*\](?!\s*[\(\[:]))
    """,
    flags=re.VERBOSE,
)


def parse_cluster_keys(m: re.Match, known_keys: set[str] | None = None) -> list[str] | None:
    if m.group("schemeA"):
        return re.findall(r"\[\^([^\]]+)\]", m.group("schemeA"))
    if m.group("pandoc"):
        return re.findall(r"@([A-Za-z0-9_.:-]+)", m.group("pandoc"))
    if m.group("schemeD") or m.group("schemeB"):
        raw = m.group("schemeD") or m.group("schemeB")
        stripped = re.sub(r"</?sup>", "", raw)
        stripped = re.sub(r"\[\[(\d+)\]\]\(#ref-\d+\)", r"\1", stripped)
        return expand_num_spec(stripped)
    if m.group("schemeC"):
        raw = m.group("schemeC")
        stripped = re.sub(r"\[\[(\d+)\]\]\[(?:ref-)?\d+\]", r"\1", raw)
        return expand_num_spec(stripped)
    if m.group("schemeE"):
        inner = m.group("schemeE")[1:-1]
        nums = expand_num_spec(inner)
        if not nums:
            return None
        if known_keys is not None and not all(k in known_keys for k in nums):
            return None
        return nums
    return None


def group_contiguous_ints(nums: list[int]) -> list[tuple[int, int]]:
    if not nums:
        return []
    runs: list[tuple[int, int]] = []
    start = prev = nums[0]
    for x in nums[1:]:
        if x == prev + 1:
            prev = x
        else:
            runs.append((start, prev))
            start = prev = x
    runs.append((start, prev))
    return runs


def format_inline_cluster(
    nums: list[int],
    scheme: str,
    citekeys: dict[int, str] | None = None,
) -> str:
    scheme = scheme.upper()
    if scheme == "A":
        return "".join(f"[^{n}]" for n in nums)

    if scheme == "F":
        assert citekeys is not None
        inner = "; ".join(f"@{citekeys[n]}" for n in nums)
        return f"[{inner}]"

    runs = group_contiguous_ints(nums)
    if scheme == "B":
        parts = []
        for a, b in runs:
            if a == b:
                parts.append(f"[[{a}]](#ref-{a})")
            elif b == a + 1:
                parts.append(f"[[{a}]](#ref-{a}), [[{b}]](#ref-{b})")
            else:
                parts.append(f"[[{a}]](#ref-{a})–[[{b}]](#ref-{b})")
        return ", ".join(parts)

    if scheme == "C":
        parts = []
        for a, b in runs:
            if a == b:
                parts.append(f"[[{a}]][ref-{a}]")
            elif b == a + 1:
                parts.append(f"[[{a}]][ref-{a}], [[{b}]][ref-{b}]")
            else:
                parts.append(f"[[{a}]][ref-{a}]–[[{b}]][ref-{b}]")
        return ", ".join(parts)

    if scheme == "D":
        parts = []
        for a, b in runs:
            if a == b:
                parts.append(f"[[{a}]](#ref-{a})")
            elif b == a + 1:
                parts.append(f"[[{a}]](#ref-{a}),[[{b}]](#ref-{b})")
            else:
                parts.append(f"[[{a}]](#ref-{a})–[[{b}]](#ref-{b})")
        return f"<sup>{','.join(parts)}</sup>"

    if scheme == "E":
        parts = []
        for a, b in runs:
            if a == b:
                parts.append(f"{a}")
            elif b == a + 1:
                parts.append(f"{a}, {b}")
            else:
                parts.append(f"{a}–{b}")
        return f"[{', '.join(parts)}]"

    raise ValueError(f"Unsupported scheme: {scheme}")


def load_ref_pool(refs_path: Path | None, bib_path: Path | None) -> dict[str, RefRecord]:
    pool: dict[str, RefRecord] = {}
    if bib_path and bib_path.is_file():
        pool.update(parse_bibtex(bib_path.read_text(encoding="utf-8")))
    if refs_path and refs_path.is_file():
        data = json.loads(refs_path.read_text(encoding="utf-8"))
        for k, val in data.items():
            if isinstance(val, str):
                pool[k] = parse_formatted_ref_line(k, val)
            elif isinstance(val, dict):
                authors = [tuple(a) for a in val.get("authors", [])]
                pool[k] = RefRecord(
                    key=k,
                    entry_type=val.get("entry_type", "article"),
                    authors=authors,  # type: ignore[arg-type]
                    has_et_al=bool(val.get("has_et_al", False)),
                    title=val.get("title", ""),
                    venue=val.get("venue", ""),
                    venue_abbrev=val.get("venue_abbrev", ""),
                    year=str(val.get("year", "")),
                    volume=str(val.get("volume", "")),
                    issue=str(val.get("issue", "")),
                    pages=val.get("pages", ""),
                    art_no=val.get("art_no", ""),
                    publisher=val.get("publisher", ""),
                    address=val.get("address", ""),
                    doi=val.get("doi", ""),
                    arxiv_id=val.get("arxiv_id", ""),
                    url=val.get("url", ""),
                    raw_ieee=val.get("raw_ieee", ""),
                    raw_gbt=val.get("raw_gbt", ""),
                    raw_source=val.get("raw_source", ""),
                    source_style=val.get("source_style", ""),
                )
    return pool


def transform_markdown_citations(
    md_text: str,
    external_pool: dict[str, RefRecord],
    scheme: str = "A",
    bib_style: str = "ieee",
    heading: str | None = None,
    fix_punctuation: bool = True,
    link_mode: str = "auto",
    link_label: str = "auto",
) -> tuple[str, dict[int, RefRecord], dict[int, str]]:
    """
    Transform and renumber a Markdown document strictly in 1..N first-appearance order.
    Returns (rendered_markdown, ordered_records_by_new_num, citekeys_for_scheme_F).
    """
    scheme = scheme.upper()
    bib_style = bib_style.lower()
    link_mode = link_mode.lower()
    body_lines, detected_heading, ref_lines = split_body_and_ref_section(md_text)

    pool: dict[str, RefRecord] = {}
    pool.update(parse_existing_ref_section(ref_lines))
    pool.update(external_pool)
    known_keys = set(pool.keys()) if pool else None

    old_to_new: dict[str, int] = {}
    new_to_rec: dict[int, RefRecord] = {}
    citekeys: dict[int, str] = {}

    # Pass 1: Discover strict first-appearance order top-to-bottom, left-to-right
    in_fence = False
    in_math_block = False
    for line in body_lines:
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if not in_fence and stripped.startswith("$$") and stripped.rstrip() == "$$":
            in_math_block = not in_math_block
            continue
        if in_fence or in_math_block or re.match(r"^\s*#{1,6}\s+", line):
            continue

        masked, _ = mask_line_protected(line)
        for m in CLUSTER_MASTER_RE.finditer(masked):
            keys = parse_cluster_keys(m, known_keys)
            if not keys:
                continue
            for k in keys:
                if k not in pool:
                    raise KeyError(f"Undefined citation key '{k}' encountered on line: {line[:100]}")
                if k not in old_to_new:
                    new_idx = len(old_to_new) + 1
                    old_to_new[k] = new_idx
                    rec = pool[k]
                    new_to_rec[new_idx] = rec
                    citekeys[new_idx] = make_citekey(rec, new_idx)

    # Pass 2: Rewrite inline clusters (deduplicated & sorted ascending) + fix post-punctuation
    out_body: list[str] = []
    in_fence = False
    in_math_block = False
    for line in body_lines:
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            out_body.append(line)
            continue
        if not in_fence and stripped.startswith("$$") and stripped.rstrip() == "$$":
            in_math_block = not in_math_block
            out_body.append(line)
            continue
        if in_fence or in_math_block or re.match(r"^\s*#{1,6}\s+", line):
            out_body.append(line)
            continue

        masked, vault = mask_line_protected(line)
        cluster_tokens: list[str] = []

        def replace_cluster(m: re.Match) -> str:
            keys = parse_cluster_keys(m, known_keys)
            if not keys:
                return m.group(0)
            mapped: list[int] = []
            for k in keys:
                nid = old_to_new[k]
                if nid not in mapped:
                    mapped.append(nid)
            mapped.sort()
            rendered = format_inline_cluster(mapped, scheme=scheme, citekeys=citekeys)
            c_idx = len(cluster_tokens)
            cluster_tokens.append(rendered)
            return f"\x01C{c_idx}\x01"

        rewritten = CLUSTER_MASTER_RE.sub(replace_cluster, masked)

        if fix_punctuation:
            rewritten = re.sub(r"([，。；：！？])(\s*)(\x01C\d+\x01)", r"\3\1", rewritten)
            if scheme in ("A", "D"):
                rewritten = re.sub(r"(?<=[\u4e00-\u9fff\)\）\$])\s+(?=\x01C\d+\x01)", "", rewritten)

        def restore_cluster(m: re.Match) -> str:
            return cluster_tokens[int(m.group(1))]

        rewritten = re.sub(r"\x01C(\d+)\x01", restore_cluster, rewritten)
        out_body.append(unmask_line(rewritten, vault))

    final_heading = heading or (
        "## 参考文献" if (scheme == "E" and bib_style == "gbt7714") else (detected_heading or "## 参考文献（References）")
    )

    if scheme == "F" or not new_to_rec:
        final_md = "\n".join(out_body).rstrip() + "\n"
        return final_md, new_to_rec, citekeys

    ref_entries: list[str] = []
    tooltip_defs: list[str] = []

    for idx in range(1, len(new_to_rec) + 1):
        rec = new_to_rec[idx]
        entry_str = format_record(rec, bib_style=bib_style, link_mode=link_mode, link_label=link_label)

        if scheme == "A":
            ref_entries.append(f"[^{idx}]: {entry_str}")
        elif scheme in ("B", "D"):
            ref_entries.append(f'<a id="ref-{idx}"></a>[{idx}] {entry_str}')
        elif scheme == "C":
            ref_entries.append(f'<a id="ref-{idx}"></a>[{idx}] {entry_str}')
            tip = make_hover_tooltip(rec, entry_str)
            tooltip_defs.append(f'[ref-{idx}]: #ref-{idx} "{tip}"')
        elif scheme == "E":
            ref_entries.append(f"[{idx}] {entry_str}")

    ref_section = f"\n\n---\n\n{final_heading}\n\n" + "\n\n".join(ref_entries)
    if scheme == "C" and tooltip_defs:
        ref_section += "\n\n" + "\n".join(tooltip_defs)

    final_md = "\n".join(out_body).rstrip() + ref_section + "\n"
    return final_md, new_to_rec, citekeys


# ---------------------------------------------------------------------------
# Deterministic QA Verification Engine (`verify`)
# ---------------------------------------------------------------------------
def verify_markdown_citations(md_path: Path, scheme: str = "A", allow_crlf: bool = False) -> list[str]:
    errors: list[str] = []
    scheme = scheme.upper()
    raw = md_path.read_bytes()
    if not allow_crlf and b"\r\n" in raw:
        errors.append("CRLF line endings detected; expected UTF-8 LF.")

    text = raw.decode("utf-8")
    body_lines, _, ref_lines = split_body_and_ref_section(text)

    def_nums: list[int] = []
    prev_was_def = False
    for rline in ref_lines:
        s = rline.strip()
        if not s or s == "---":
            prev_was_def = False
            continue
        if re.match(r"^\[(?:ref-)?\d+\]:\s*#ref-\d+", s):
            continue

        m_def = None
        if scheme == "A":
            m_def = re.match(r"^\[\^(\d+)\]:\s+(.+)$", s)
        elif scheme in ("B", "C", "D"):
            m_def = re.match(r'^<a\s+id="ref-(\d+)"\s*>\s*</a>\[(\d+)\]\s+(.+)$', s)
            if m_def and m_def.group(1) != m_def.group(2):
                errors.append(f"Ref line: anchor id ref-{m_def.group(1)} != label [{m_def.group(2)}].")
        elif scheme == "E":
            m_def = re.match(r"^\[(\d+)\]\s+(.+)$", s)

        if m_def:
            if scheme == "A" and prev_was_def:
                errors.append(f"Ref entry [^{m_def.group(1)}]: missing blank line before footnote definition (breaks Typora card isolation).")
            num = int(m_def.group(1))
            entry_body = m_def.group(m_def.lastindex or 2)
            def_nums.append(num)
            prev_was_def = True

            # Check malformed empty trailing link `[Label]()` or non-http(s) link
            if re.search(r"\[[^\]]+\]\(\s*\)\s*$", entry_body):
                errors.append(f"Ref [{num}]: Empty trailing Markdown link target.")

            # Strip trailing clickable link and validate no duplicate trailing links or DOI mismatch
            clean_entry, link_url = strip_trailing_markdown_link(entry_body)
            if link_url and TRAILING_LINK_RE.search(clean_entry):
                errors.append(f"Ref [{num}]: Duplicate trailing Markdown hyperlinks detected.")

            # Extract inline DOI (if present) and link DOI (if doi.org)
            m_doi = re.search(r"(?:doi:|DOI:)\s*(10\.\d{4,9}/\S+?)\.?\s*$", clean_entry)
            inline_doi = normalize_doi(m_doi.group(1)) if m_doi else ""
            link_doi = (
                normalize_doi(link_url)
                if link_url and re.match(r"^https?://(?:dx\.)?doi\.org/", link_url, flags=re.IGNORECASE)
                else ""
            )
            if inline_doi and link_doi and inline_doi.lower() != link_doi.lower():
                errors.append(f"Ref [{num}]: Inline DOI ({inline_doi}) does not match trailing hyperlink ({link_url}).")

            effective_doi = inline_doi or link_doi
            m_art = re.search(r"(?:Art\.\s*no\.\s*|:\s*|\*\*\d+\*\*,\s*)(\d{5,7})\b", clean_entry)
            if effective_doi and m_art and check_doi_suffix_page_collision(effective_doi, m_art.group(1)):
                errors.append(
                    f"Ref [{num}]: Suspected DOI-suffix-as-article-number hallucination ({m_art.group(1)} matches manuscript ID in {effective_doi})."
                )
        else:
            errors.append(f"Unrecognized reference line for Scheme {scheme}: {s[:80]}")

    expected = list(range(1, len(def_nums) + 1))
    if def_nums != expected:
        errors.append(f"Reference definitions are not strictly sequential 1..{len(def_nums)}: got {def_nums[:15]}...")

    known_set = {str(x) for x in def_nums}
    first_seen: list[int] = []
    seen_set: set[int] = set()

    in_fence = False
    fence_lang = ""
    in_math_block = False

    for line_no, line in enumerate(body_lines, start=1):
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            if not in_fence:
                in_fence = True
                fence_lang = stripped.strip("`~ ").lower()
            else:
                in_fence = False
                fence_lang = ""
            continue
        if in_fence:
            if fence_lang == "mermaid" and re.search(r"\[\^[^\]]+\]", line):
                errors.append(f"L{line_no}: Footnote syntax inside Mermaid block.")
            continue

        if stripped.startswith("$$") and stripped.rstrip() == "$$":
            in_math_block = not in_math_block
            continue
        if in_math_block:
            if re.search(r"\[\^[^\]]+\]", line):
                errors.append(f"L{line_no}: Footnote syntax inside $$ display math block.")
            continue

        if re.match(r"^\s*#{1,6}\s+", line):
            if re.search(r"\[\^\d+\]|\[\[\d+\]\]", line):
                errors.append(f"L{line_no}: Citation marker placed inside Markdown heading.")
            continue

        for m_math in re.finditer(r"(?<!\\)\$([^\$\n]+?)(?<!\\)\$", line):
            if re.search(r"\[\^\d+\]", m_math.group(1)):
                errors.append(f"L{line_no}: Footnote marker placed inside inline $math$.")

        masked, _ = mask_line_protected(line)

        if re.search(r"\[\^R\d+\]", masked):
            errors.append(f"L{line_no}: Leftover temporary placeholder [^Rxxx].")
        if scheme == "A" and re.search(r"\[\^\d+\s*[-–—,]\s*\d+\]", masked):
            errors.append(f"L{line_no}: Invalid range/comma footnote syntax in Scheme A (must use separate [^a][^b]).")

        if re.search(r"（\s*）|\(\s*\)|。。|，，|；；", masked):
            errors.append(f"L{line_no}: Empty parentheses or doubled punctuation scar detected.")

        if re.search(
            r"[，。；：！？]\s*(?:\[\^\d+\]|\[\[\d+\]\]|<sup>\[\[\d+\]\]|\[\d+(?:\s*[–\-—,]\s*\d+)*\](?!\s*[\(\[:]))",
            masked,
        ):
            errors.append(f"L{line_no}: Citation placed AFTER Chinese punctuation instead of before.")

        for m in CLUSTER_MASTER_RE.finditer(masked):
            keys = parse_cluster_keys(m, known_keys=known_set if scheme == "E" else None)
            if not keys:
                continue
            nums_in_cluster: list[int] = []
            for k in keys:
                if not k.isdigit():
                    errors.append(f"L{line_no}: Non-numeric citation key '{k}' in numbered Scheme {scheme}.")
                    continue
                val = int(k)
                nums_in_cluster.append(val)
                if val not in seen_set:
                    seen_set.add(val)
                    first_seen.append(val)
            if nums_in_cluster != sorted(set(nums_in_cluster)):
                errors.append(f"L{line_no}: Unsorted or duplicate numbers in citation cluster {nums_in_cluster}.")

    if scheme != "F":
        if not def_nums:
            errors.append("No reference entries found in bibliography section.")
        if sorted(seen_set) != expected:
            missing = sorted(set(expected) - seen_set)
            extra = sorted(seen_set - set(expected))
            errors.append(f"Citation bijection mismatch: unreferenced_defs={missing}, undefined_cites={extra}.")
        if first_seen != expected:
            for pos, (got, exp) in enumerate(zip(first_seen, expected), start=1):
                if got != exp:
                    errors.append(
                        f"First-appearance order violation at #{pos}: saw [{got}] before [{exp}] (expected strict 1..{len(expected)})."
                    )
                    break

    return errors


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------
def cmd_config(args: argparse.Namespace) -> int:
    if args.path:
        target = Path(args.path)
    elif args.scope == "workspace":
        target = Path.cwd() / WORKSPACE_CONFIG_NAME
    else:
        target = SKILL_CONFIG_PATH

    if args.reset:
        if target.is_file():
            target.unlink()
            print(f"[OK] Removed config override -> {target}")
        else:
            print(f"[OK] No config override existed at {target}")
        cfg, sources = load_effective_config(start_dir=Path.cwd(), explicit_config=Path(args.config) if args.config else None)
        print(json.dumps({"effective": cfg, "sources": sources}, ensure_ascii=False, indent=2))
        return 0

    updates: dict[str, Any] = {}
    if args.set_scheme is not None:
        updates["default_scheme"] = args.set_scheme.upper()
    if args.set_bib_style is not None:
        updates["default_bib_style"] = args.set_bib_style.lower()
    if args.set_link_mode is not None:
        updates["link_mode"] = args.set_link_mode.lower()
    if args.set_link_label is not None:
        updates["link_label"] = args.set_link_label.strip()
    if args.set_heading is not None:
        updates["heading"] = args.set_heading.strip() or None

    if updates:
        existing: dict[str, Any] = {}
        if target.is_file():
            existing = json.loads(target.read_text(encoding="utf-8-sig"))
        merged = {**existing, **updates}
        validated = _validate_config_payload(merged, str(target))
        final_payload = {**BUILTIN_DEFAULTS, **validated}
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(final_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(f"[OK] Saved defaults -> {target}")

    cfg, sources = load_effective_config(
        start_dir=Path.cwd(),
        explicit_config=Path(args.config) if args.config else (target if args.path and target.is_file() else None),
    )
    print(json.dumps({"effective": cfg, "sources": sources}, ensure_ascii=False, indent=2))
    return 0


def cmd_resolve(args: argparse.Namespace) -> int:
    records: dict[str, RefRecord] = {}
    if args.bib:
        records.update(parse_bibtex(Path(args.bib).read_text(encoding="utf-8")))
    if args.dois:
        for idx, raw_d in enumerate(args.dois, start=1):
            d = normalize_doi(raw_d)
            k = f"R{idx:03d}"
            records[k] = RefRecord(key=k, doi=d)

    enriched = 0
    if args.online:
        for rec in records.values():
            needs_lookup = not (rec.title and rec.authors and rec.year and (rec.volume or rec.entry_type != "article"))
            if rec.doi and needs_lookup:
                if enrich_record_from_crossref(rec, timeout=args.timeout):
                    enriched += 1

    out_obj: dict[str, Any] = {}
    for k, rec in records.items():
        rec.raw_ieee = format_record_ieee(rec)
        rec.raw_gbt = format_record_gbt(rec)
        if check_doi_suffix_page_collision(rec.doi, rec.art_no or rec.pages):
            rec.warnings.append("Suspected DOI manuscript suffix used as page/article number.")
        entry_dict = dataclasses.asdict(rec)
        resolved_url, link_kind = resolve_reference_link(rec)
        entry_dict["resolved_url"] = resolved_url
        entry_dict["resolved_link_kind"] = link_kind
        entry_dict["formatted"] = {
            st: format_record(rec, bib_style=st, link_mode="auto", link_label="auto")
            for st in SUPPORTED_BIB_STYLES
        }
        out_obj[k] = entry_dict

    out_path = Path(args.out)
    out_path.write_text(json.dumps(out_obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"[OK] Resolved {len(out_obj)} references (Crossref enriched: {enriched}) -> {out_path}")
    return 0


def resolve_effective_options(args: argparse.Namespace, start_dir: Path) -> tuple[str, str, str | None, str, str]:
    """Merge builtin -> skill local.json -> workspace -> --config -> --preset -> explicit CLI flags."""
    cfg, _ = load_effective_config(
        start_dir=start_dir,
        explicit_config=Path(args.config) if getattr(args, "config", None) else None,
    )
    scheme = cfg["default_scheme"]
    bib_style = cfg["default_bib_style"]
    link_mode = cfg["link_mode"]
    link_label = cfg["link_label"]
    heading = cfg["heading"]

    preset_name = getattr(args, "preset", None)
    if preset_name:
        preset = PRESETS[preset_name]
        scheme = preset["scheme"]
        bib_style = preset["bib_style"]
        link_mode = preset["link_mode"]
        if "heading" in preset:
            heading = preset["heading"]

    if getattr(args, "scheme", None) is not None:
        scheme = args.scheme.upper()
    if getattr(args, "bib_style", None) is not None:
        bib_style = args.bib_style.lower()
    if getattr(args, "no_links", False):
        link_mode = "off"
    elif getattr(args, "link_mode", None) is not None:
        link_mode = args.link_mode.lower()
    if getattr(args, "link_label", None) is not None:
        link_label = args.link_label.strip()
    if getattr(args, "heading", None) is not None:
        heading = args.heading

    return scheme, bib_style, heading, link_mode, link_label


def cmd_render_or_convert(args: argparse.Namespace) -> int:
    in_path = Path(args.input)
    out_path = Path(args.output) if args.output else in_path
    scheme, bib_style, heading, link_mode, link_label = resolve_effective_options(args, start_dir=in_path.parent)

    md_text = in_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    ext_pool = load_ref_pool(
        Path(args.refs) if getattr(args, "refs", None) else None,
        Path(args.bib) if getattr(args, "bib", None) else None,
    )

    rendered, new_records, citekeys = transform_markdown_citations(
        md_text=md_text,
        external_pool=ext_pool,
        scheme=scheme,
        bib_style=bib_style,
        heading=heading,
        fix_punctuation=not args.no_fix_punctuation,
        link_mode=link_mode,
        link_label=link_label,
    )

    out_path.write_text(rendered, encoding="utf-8", newline="\n")

    if scheme == "F":
        bib_out = out_path.with_suffix(".bib")
        bib_entries = [record_to_bibtex(new_records[i], citekeys[i]) for i in range(1, len(new_records) + 1)]
        bib_out.write_text("\n\n".join(bib_entries) + "\n", encoding="utf-8", newline="\n")
        print(f"[OK] Exported Scheme F Pandoc Markdown -> {out_path} + companion BibTeX -> {bib_out} ({len(new_records)} refs)")
        return 0

    errs = verify_markdown_citations(out_path, scheme=scheme)
    if errs:
        print(f"[WARN] Rendered {out_path} ({len(new_records)} refs), but QA reported {len(errs)} issue(s):", file=sys.stderr)
        for e in errs[:20]:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(
        f"[OK] Formatted {out_path} | Scheme={scheme} | BibStyle={bib_style} | "
        f"Links={link_mode}({link_label}) | UniqueRefs={len(new_records)} | QA=PASS (0 errors)"
    )
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    md_path = Path(args.input)
    scheme = args.scheme
    if scheme is None:
        cfg, _ = load_effective_config(
            start_dir=md_path.parent,
            explicit_config=Path(args.config) if getattr(args, "config", None) else None,
        )
        scheme = cfg["default_scheme"]
    errs = verify_markdown_citations(md_path, scheme=scheme, allow_crlf=args.allow_crlf)
    if errs:
        print(f"[FAIL] {md_path} ({len(errs)} error(s)):", file=sys.stderr)
        for e in errs:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(f"[PASS] {md_path} verified cleanly for Scheme {scheme.upper()} (0 errors).")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Academic Markdown Citation Engine (md-citation)")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_cfg = sub.add_parser("config", help="View, set, or reset persistent default citation settings")
    p_cfg.add_argument("--show", action="store_true", help="Print active merged defaults and config sources")
    p_cfg.add_argument("--scope", choices=["skill", "workspace"], default="skill", help="Where to save overrides")
    p_cfg.add_argument("--path", help="Explicit config JSON file to write/reset")
    p_cfg.add_argument("--config", help="Explicit config JSON file to inspect")
    p_cfg.add_argument("--set-scheme", choices=["A", "B", "C", "D", "E", "F", "a", "b", "c", "d", "e", "f"])
    p_cfg.add_argument("--set-bib-style", choices=list(SUPPORTED_BIB_STYLES))
    p_cfg.add_argument("--set-link-mode", choices=list(SUPPORTED_LINK_MODES))
    p_cfg.add_argument("--set-link-label", help="Default link label ('auto', 'Website', 'Website Connection', '原文链接', etc.)")
    p_cfg.add_argument("--set-heading", help="Default reference heading (empty string clears override)")
    p_cfg.add_argument("--reset", action="store_true", help="Remove stored config override at target scope/path")
    p_cfg.set_defaults(func=cmd_config)

    p_res = sub.add_parser("resolve", help="Resolve .bib or raw DOIs into normalized multi-style JSON")
    p_res.add_argument("--bib", help="Input BibTeX .bib file")
    p_res.add_argument("--dois", nargs="*", help="Raw DOIs to resolve")
    p_res.add_argument("--out", required=True, help="Output JSON path")
    p_res.add_argument("--online", action="store_true", help="Query public Crossref API for missing fields")
    p_res.add_argument("--timeout", type=float, default=8.0, help="HTTP timeout in seconds")
    p_res.set_defaults(func=cmd_resolve)

    for sub_name in ("render", "convert"):
        sp = sub.add_parser(sub_name, help=f"{sub_name.capitalize()} Markdown citations into target scheme & bibliography style")
        sp.add_argument("input", help="Input Markdown file")
        sp.add_argument("-o", "--output", help="Output Markdown file (defaults to in-place overwrite)")
        sp.add_argument("--refs", help="Optional JSON reference pool (from `resolve` or {key: ref_str})")
        sp.add_argument("--bib", help="Optional BibTeX .bib reference pool")
        sp.add_argument("--config", help="Optional explicit config JSON overriding skill/workspace defaults")
        sp.add_argument("--scheme", default=None, choices=["A", "B", "C", "D", "E", "F", "a", "b", "c", "d", "e", "f"])
        sp.add_argument("--bib-style", default=None, choices=list(SUPPORTED_BIB_STYLES))
        sp.add_argument("--preset", choices=sorted(PRESETS.keys()), help="Convenience preset")
        sp.add_argument("--link-mode", default=None, choices=list(SUPPORTED_LINK_MODES), help="Trailing clickable link mode (auto|off)")
        sp.add_argument("--no-links", action="store_true", help="Shorthand for --link-mode off")
        sp.add_argument("--link-label", default=None, help="Trailing clickable link text ('auto', 'Website', 'Website Connection', etc.)")
        sp.add_argument("--heading", default=None, help="Custom reference section heading")
        sp.add_argument("--no-fix-punctuation", action="store_true", help="Disable moving citations before CJK punctuation")
        sp.set_defaults(func=cmd_render_or_convert)

    p_ver = sub.add_parser("verify", help="Run deterministic QA checks on a formatted Markdown file")
    p_ver.add_argument("input", help="Markdown file to audit")
    p_ver.add_argument("--scheme", default=None, choices=["A", "B", "C", "D", "E", "F", "a", "b", "c", "d", "e", "f"])
    p_ver.add_argument("--config", help="Optional explicit config JSON")
    p_ver.add_argument("--allow-crlf", action="store_true")
    p_ver.set_defaults(func=cmd_verify)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
