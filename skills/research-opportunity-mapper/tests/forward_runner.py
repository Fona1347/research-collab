from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fixture_factory import load_manifest, make_run, sha256
from validate_run import validate


SUPPORTED_MODES = {"landscape", "focus", "evidence-audit", "run-audit"}
SUPPORTED_LENSES = {"frontier-led", "gray-space-led", "balanced"}
NON_KEEP = re.compile(r"\b(?:Downgrade|Revise|Kill)\b", re.IGNORECASE)


def tree_snapshot(root: Path) -> tuple[str, int, int]:
    rows: list[str] = []
    total = 0
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        size = path.stat().st_size
        total += size
        rows.append(f"{path.relative_to(root).as_posix()}\t{sha256(path)}\t{size}\n")
    return hashlib.sha256("".join(rows).encode("utf-8")).hexdigest(), len(rows), total


def load_cases(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases")
    if not isinstance(cases, list):
        raise AssertionError("forward-cases.json must contain a cases list")
    return cases


def assert_catalog_contract(cases: list[dict[str, Any]]) -> None:
    if len(cases) != 8:
        raise AssertionError(f"expected exactly eight forward cases, found {len(cases)}")
    ids = [case.get("id") for case in cases]
    if len(set(ids)) != len(ids) or not all(isinstance(item, str) and item for item in ids):
        raise AssertionError("forward case IDs must be unique non-empty strings")
    if {case.get("task_mode") for case in cases} != SUPPORTED_MODES:
        raise AssertionError("forward catalog must cover all four formal modes")
    if {case.get("discovery_lens") for case in cases} != SUPPORTED_LENSES:
        raise AssertionError("forward catalog must cover all three discovery lenses")
    for case in cases:
        for key in (
            "request",
            "domain",
            "primary_domain_lens",
            "secondary_domain_lenses",
            "capability_state",
            "scenario_summary",
        ):
            if key not in case:
                raise AssertionError(f"{case['id']} is missing {key}")
        behaviors = case.get("required_behavior")
        if not isinstance(behaviors, list) or not behaviors:
            raise AssertionError(f"{case['id']} requires a non-empty required_behavior list")
        audit_target = case.get("audit_target")
        if audit_target is not None and (
            case.get("task_mode") != "run-audit"
            or re.fullmatch(
                r"(?:(?:B|M|S|CL)-\d{3}|C-(?:\d{3}|[LMH]\d{2}))",
                str(audit_target),
            ) is None
        ):
            raise AssertionError(f"{case['id']} has an invalid run-audit target")
        behavior_ids = [behavior.get("id") for behavior in behaviors]
        if len(set(behavior_ids)) != len(behavior_ids):
            raise AssertionError(f"{case['id']} has duplicate required_behavior IDs")
        for behavior in behaviors:
            if not isinstance(behavior.get("checks"), list) or not behavior["checks"]:
                raise AssertionError(
                    f"{case['id']} behavior {behavior.get('id')!r} has no executable checks"
                )


def _manifest_value(manifest: dict[str, Any], dotted_path: str) -> Any:
    value: Any = manifest
    for part in dotted_path.split("."):
        if not isinstance(value, dict) or part not in value:
            raise AssertionError(f"manifest path {dotted_path!r} does not exist")
        value = value[part]
    return value


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text).casefold()


@dataclass(frozen=True)
class ForwardCaseResult:
    case_id: str
    run_dir: Path
    parent_dir: Path | None
    checked_behaviors: tuple[str, ...]
    manifest: dict[str, Any]


class ForwardCaseRunner:
    def __init__(self, *, work: Path, workspace: Path) -> None:
        self.work = work
        self.workspace = workspace.resolve()
        self._generated_parents: dict[str, Path] = {}

    def _generated_landscape(self, run_id: str) -> Path:
        existing = self._generated_parents.get(run_id)
        if existing is not None:
            return existing
        parent = make_run(
            self.work,
            mode="landscape",
            lens="balanced",
            run_id=run_id,
            domain="broad AI-hardware mother landscape",
            primary_domain_lens="neuromorphic-system",
            secondary_domain_lenses=["semiconductor-device", "integrated-circuit"],
            routing_request="Build an immutable mother landscape for child-run forward tests.",
            scenario_summary=(
                "Define BR-001 and authoritative B/M/S/CL, E, and CAP identifiers for "
                "lineage-aware focus and evidence-audit children."
            ),
            capability_state="Reported",
        )
        self._generated_parents[run_id] = parent
        return parent

    def resolve_parent(self, case: dict[str, Any]) -> Path | None:
        spec = case.get("parent")
        if spec is None:
            return None
        kind = spec.get("kind")
        if kind == "generated-landscape":
            return self._generated_landscape(str(spec["run_id"]))
        if kind == "workspace-legacy":
            parent = (self.workspace / Path(str(spec["workspace_relpath"]))).resolve()
            try:
                parent.relative_to(self.workspace)
            except ValueError as exc:
                raise AssertionError("legacy forward parent escapes the workspace") from exc
            if not (parent / "run-manifest.json").is_file():
                raise AssertionError(f"legacy forward parent does not exist: {parent}")
            return parent
        raise AssertionError(f"unsupported forward parent kind: {kind!r}")

    def run(self, case: dict[str, Any]) -> ForwardCaseResult:
        parent = self.resolve_parent(case)
        parent_before = tree_snapshot(parent) if parent is not None else None
        run_dir = make_run(
            self.work,
            mode=str(case["task_mode"]),
            lens=str(case["discovery_lens"]),
            parent=parent,
            bio=bool(case.get("bio", False)),
            run_id=str(case["id"]),
            domain=str(case["domain"]),
            primary_domain_lens=str(case["primary_domain_lens"]),
            secondary_domain_lenses=list(case["secondary_domain_lenses"]),
            routing_request=str(case["request"]),
            scenario_summary=str(case["scenario_summary"]),
            capability_state=str(case["capability_state"]),
            audit_target=(
                str(case["audit_target"]) if "audit_target" in case else None
            ),
        )
        manifest = load_manifest(run_dir)

        validation = validate(run_dir, workspace_root=self.workspace)
        if validation.errors:
            raise AssertionError("\n".join(validation.errors))
        if validation.warnings:
            raise AssertionError("\n".join(validation.warnings))

        self._assert_base_contract(case, manifest)
        role_text = "\n".join(
            (run_dir / relpath).read_text(encoding="utf-8")
            for relpath in manifest["artifact_roles"].values()
        )
        checked: list[str] = []
        for behavior in case["required_behavior"]:
            behavior_id = str(behavior["id"])
            for check in behavior["checks"]:
                self._execute_check(
                    case=case,
                    check=check,
                    manifest=manifest,
                    role_text=role_text,
                    parent=parent,
                    parent_before=parent_before,
                )
            checked.append(behavior_id)

        declared = tuple(str(item["id"]) for item in case["required_behavior"])
        if tuple(checked) != declared:
            raise AssertionError(f"{case['id']} did not consume every required_behavior")
        if parent is not None and tree_snapshot(parent) != parent_before:
            raise AssertionError(f"{case['id']} mutated its parent run")
        return ForwardCaseResult(
            case_id=str(case["id"]),
            run_dir=run_dir,
            parent_dir=parent,
            checked_behaviors=tuple(checked),
            manifest=manifest,
        )

    @staticmethod
    def _assert_base_contract(case: dict[str, Any], manifest: dict[str, Any]) -> None:
        expected = {
            "task_mode": case["task_mode"],
            "run_type": case["task_mode"],
            "discovery_lens": case["discovery_lens"],
            "domain": case["domain"],
            "primary_domain_lens": case["primary_domain_lens"],
            "secondary_domain_lenses": case["secondary_domain_lenses"],
            "completion_status": "complete",
        }
        for key, value in expected.items():
            if manifest.get(key) != value:
                raise AssertionError(
                    f"{case['id']} manifest {key}={manifest.get(key)!r}; expected {value!r}"
                )
        routing = manifest.get("routing", {})
        if routing.get("request") != case["request"] or routing.get("selected") != case["task_mode"]:
            raise AssertionError(f"{case['id']} did not persist its exact routing request/selection")

    def _execute_check(
        self,
        *,
        case: dict[str, Any],
        check: dict[str, Any],
        manifest: dict[str, Any],
        role_text: str,
        parent: Path | None,
        parent_before: tuple[str, int, int] | None,
    ) -> None:
        kind = check.get("kind")
        normalized = _normalized(role_text)
        if kind == "markers":
            for marker in check.get("value", []):
                if marker not in role_text:
                    raise AssertionError(f"{case['id']} lacks required marker {marker!r}")
            return
        if kind == "text-all":
            for phrase in check.get("value", []):
                if _normalized(str(phrase)) not in normalized:
                    raise AssertionError(f"{case['id']} lacks scenario evidence {phrase!r}")
            return
        if kind == "text-none":
            for phrase in check.get("value", []):
                if _normalized(str(phrase)) in normalized:
                    raise AssertionError(f"{case['id']} contains forbidden claim {phrase!r}")
            return
        if kind == "manifest-equals":
            actual = _manifest_value(manifest, str(check["path"]))
            if actual != check.get("value"):
                raise AssertionError(
                    f"{case['id']} manifest {check['path']}={actual!r}; "
                    f"expected {check.get('value')!r}"
                )
            return
        if kind == "parent-immutable":
            if parent is None or parent_before is None:
                raise AssertionError(f"{case['id']} requires a parent immutability check")
            if tree_snapshot(parent) != parent_before:
                raise AssertionError(f"{case['id']} mutated its parent")
            return
        if kind == "lineage":
            self._assert_lineage(case, check, manifest, parent)
            return
        if kind == "real-legacy-parent":
            self._assert_real_legacy_parent(case, check, manifest, parent)
            return
        if kind == "non-keep-decision":
            if "rom-table: decisions" not in role_text or NON_KEEP.search(role_text) is None:
                raise AssertionError(f"{case['id']} lacks a propagated non-Keep decision")
            return
        raise AssertionError(f"{case['id']} uses unsupported forward check kind {kind!r}")

    def _assert_lineage(
        self,
        case: dict[str, Any],
        check: dict[str, Any],
        manifest: dict[str, Any],
        parent: Path | None,
    ) -> None:
        if parent is None:
            raise AssertionError(f"{case['id']} requires a lineage parent")
        parents = manifest.get("lineage", {}).get("parents", [])
        if len(parents) != 1:
            raise AssertionError(f"{case['id']} must persist exactly one lineage parent")
        row = parents[0]
        parent_manifest_path = parent / "run-manifest.json"
        parent_manifest = json.loads(parent_manifest_path.read_text(encoding="utf-8"))
        expected_relpath = parent.resolve().relative_to(self.workspace).as_posix()
        if row.get("run_id") != parent_manifest.get("run_id"):
            raise AssertionError(f"{case['id']} lineage run_id does not match its parent")
        if check.get("workspace_relative") and row.get("workspace_relpath") != expected_relpath:
            raise AssertionError(f"{case['id']} lacks an exact workspace-relative parent path")
        if (
            check.get("manifest_sha256")
            and row.get("source_manifest_sha256") != sha256(parent_manifest_path)
        ):
            raise AssertionError(f"{case['id']} lacks the exact parent manifest SHA-256")
        if check.get("selected_branch"):
            selected = manifest.get("selected_branch")
            if (
                not isinstance(selected, dict)
                or selected.get("source") != "parent"
                or not selected.get("id")
            ):
                raise AssertionError(f"{case['id']} lacks a parent-backed selected branch")
        if check.get("inherited_ids"):
            inherited = manifest.get("inherited_ids", {})
            if not all(inherited.get(key) for key in ("claims", "evidence", "capabilities")):
                raise AssertionError(f"{case['id']} lacks declared inherited typed IDs")

    @staticmethod
    def _assert_real_legacy_parent(
        case: dict[str, Any],
        check: dict[str, Any],
        manifest: dict[str, Any],
        parent: Path | None,
    ) -> None:
        if parent is None:
            raise AssertionError(f"{case['id']} requires the real legacy parent")
        parent_manifest = json.loads((parent / "run-manifest.json").read_text(encoding="utf-8"))
        if parent_manifest.get("run_id") != check.get("run_id"):
            raise AssertionError(f"{case['id']} resolved the wrong legacy run")
        if parent_manifest.get("schema_version") != check.get("schema_version"):
            raise AssertionError(f"{case['id']} resolved the wrong legacy schema")
        parents = manifest.get("lineage", {}).get("parents", [])
        if len(parents) != 1 or parents[0].get("run_id") != check.get("run_id"):
            raise AssertionError(
                f"{case['id']} audit manifest does not point to the real legacy run"
            )
