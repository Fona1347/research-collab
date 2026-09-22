"""Create synthetic legacy inputs without reading historical research artifacts."""
from pathlib import Path
import json
import os
import sys


def seed(workspace: Path, mapper: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "AGENTS.md").write_text("# Synthetic test workspace\nNo real research evidence.\n", encoding="utf-8")
    os.environ["ROM_TEST_WORKSPACE"] = str(workspace)
    sys.path[:0] = [str(mapper / "scripts"), str(mapper / "tests")]
    from fixture_factory import make_run
    cases = [
        ("Projects/research_map/validation-runs", "ai-hardware-session-case", "1.0"),
        ("Doc/Typora/note_2025_S2SPR/周工作/W22/sciver mapper", "self-regulating-learning-hardware", "1.2"),
    ]
    for parent, name, version in cases:
        run = make_run(workspace / parent, run_id=name, enhanced_contracts=False)
        original = json.loads((run / "run-manifest.json").read_text(encoding="utf-8"))
        for p in run.glob("*.md"):
            text = p.read_text(encoding="utf-8")
            for old, new in (("C-001", "C-L01"), ("C-002", "C-M01"), ("C-003", "C-H01")):
                text = text.replace(old, new)
            p.write_text(text, encoding="utf-8")
        manifest = {
            "schema_version": version, "skill": "research-opportunity-mapper",
            "run_id": name, "domain": "Synthetic compatibility fixture, not evidence",
            "language": "zh-CN", "created_at": "2026-07-31T00:00:00+00:00",
            "artifact_files": original["artifact_files"],
            "primary_artifact": original["primary_artifact"],
        }
        (run / "run-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
