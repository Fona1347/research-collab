from pathlib import Path
import json

root = Path(__file__).resolve().parents[2]
skill = root / "skills/sciverse-research"
for path in (
    root / "contracts/sciverse-research/evidence-record.schema.json",
    root / "tests/sciverse-research/routing-cases.json",
    root / "docs/components/sciverse-research/sciverse-skill.json",
):
    json.loads(path.read_text(encoding="utf-8"))
entry = (skill / "SKILL.md").read_text(encoding="utf-8")
assert "Selection boundary" in entry
assert "research-lookup-enhanced" in entry
assert "does not start a Mapper task" in entry
routing_text = entry + "\n" + (skill / "references/sciverse-api.md").read_text(encoding="utf-8")
cases = json.loads((root / "tests/sciverse-research/routing-cases.json").read_text(encoding="utf-8"))["cases"]
for case in cases:
    relative = case.get("expected_reference_route")
    if relative:
        target = (skill / relative).resolve()
        assert target.is_relative_to(skill.resolve()), case["id"]
        assert target.is_file(), case["id"]
    route = case.get("expected_primary_route")
    if route and route != "paper_schema":
        assert route in routing_text, case["id"]
print("SCIVERSE_CONTRACTS_OK")
