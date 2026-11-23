from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable

from .errors import SafetyError


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def require_output_authorization(
    output_base: Path,
    *,
    allowed_root: Path,
    allow_external: bool,
) -> None:
    target = output_base.parent.resolve()
    if not is_within(target, allowed_root) and not allow_external:
        raise SafetyError(
            f"Output is outside the allowed root {allowed_root.resolve()}: {target}. "
            "Pass --allow-external-output only after explicit confirmation."
        )


def require_distinct_from_inputs(
    outputs: Iterable[Path],
    inputs: Iterable[Path],
) -> None:
    input_set = {path.resolve() for path in inputs}
    for output in outputs:
        if output.resolve() in input_set:
            raise SafetyError(f"Output would overwrite an input file: {output}")


def file_fingerprint(path: Path) -> dict[str, int | str]:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    stat = path.stat()
    return {
        "sha256": digest.hexdigest(),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def verify_fingerprints(before: dict[Path, dict[str, int | str]]) -> None:
    for path, expected in before.items():
        current = file_fingerprint(path)
        if current != expected:
            raise SafetyError(f"Input changed during rendering: {path}")


def redact_cli_args(args: Iterable[str]) -> list[str]:
    redacted: list[str] = []
    hide_next = False
    sensitive_markers = ("token", "password", "secret", "api-key", "apikey")
    for raw in args:
        value = str(raw)
        lowered = value.lower()
        if hide_next:
            redacted.append("[REDACTED]")
            hide_next = False
        elif any(marker in lowered for marker in sensitive_markers):
            if "=" in value:
                redacted.append(value.split("=", 1)[0] + "=[REDACTED]")
            else:
                redacted.append(value)
                hide_next = True
        else:
            redacted.append(value)
    return redacted
