#!/usr/bin/env python3
"""Extract a public URL locally without Parallel Extract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rle.extraction import WebExtractor, save_extraction


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract HTML, JATS XML, or PDF content")
    parser.add_argument("url")
    parser.add_argument("--kind", choices=["html", "jats", "xml", "pdf"], default="")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--cache-dir", default=".cache/research-lookup-enhanced")
    parser.add_argument(
        "--allow-remote-parser",
        action="store_true",
        help="Allow an explicitly OA PDF to be uploaded through the MinerU wrapper",
    )
    parser.add_argument(
        "--confirm-oa",
        action="store_true",
        help="Confirm that the target PDF is legally obtained and explicitly open access",
    )
    args = parser.parse_args()
    if args.allow_remote_parser and not args.confirm_oa:
        parser.error("--allow-remote-parser requires --confirm-oa")

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    extractor = WebExtractor(
        cache_dir=args.cache_dir,
        check_robots=True,
        allow_remote_parser=args.allow_remote_parser,
    )
    document = extractor.extract_url(
        args.url,
        expected_kind=args.kind,
        download_dir=output / "source",
        is_open_access=args.confirm_oa,
    )
    artifact = output / "extraction.json"
    save_extraction(document, artifact)
    print(json.dumps({"artifact": str(artifact), **document.to_dict()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
