from __future__ import annotations
import re,sys,unittest
from pathlib import Path

SKILL_DIR=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(SKILL_DIR/"scripts"),str(SKILL_DIR/"tests")]
from fixture_factory import make_run,load_manifest,reset_work,cleanup_work,workspace_root
from test_repair_v21 import edit_table,filter_routes,filter_focus_routes
from test_validator_v2 import set_table_cell
from validate_run import V2Document,validate,NARRATIVE_PROJECTION_NAMES

def table_text(table):
    return "\n".join(["| "+" | ".join(table.headers)+" |",
                      "|"+"---|"*len(table.headers),
                      *["| "+" | ".join(row)+" |" for row in table.rows]])

def narrative_reader(run):
    """Transform only the fixture reader; canonical facts and decisions stay intact."""
    mode=load_manifest(run)["run_type"]
    path=run/load_manifest(run)["primary_artifact"]
    old=V2Document.parse(path,path.read_text(encoding="utf-8"))
    summary="\n".join(line.text for line in old.blocks["decision-summary"].lines)
    references="\n".join(line.text for line in old.blocks["references"].lines)
    citations=" ".join("["+n+"]" for n in re.findall(r"^(\d+)\.",references,re.M))
    argument="scientific-argument" if mode in {"landscape","focus"} else "audit-findings"
    text=f"# Controlled reader fixture\n\n<!-- rom-section: decision-summary -->\n{summary}\n\n"
    text+=f"<!-- rom-section: {argument} -->\n## Argument\n\nThe decision concerns a bounded causal state under matched controls. The sources {citations} delimit the evidenced regime; they do not establish system benefit.\n\n"
    # This deliberate first table must never shadow an appendix projection.
    text+="| Comparison | Meaning |\n|---|---|\n| Same-budget control | Explains the comparison only |\n\n"
    text+="> [!IMPORTANT]\n> Retain the authoritative disposition.\n\n> [!NOTE]\n> Source support remains bounded.\n\n> [!CAUTION]\n> Missing bridges remain missing.\n\n> [!WARNING]\n> Apply exact repairs before advancing.\n\n"
    if mode in {"landscape","focus"}:
        cards=old.table("recommended-routes")
        route_col=cards.headers.index("Route") if "Route" in cards.headers else cards.headers.index("路线")
        for row in cards.rows:
            route_id=re.search(r"C-\d{3}",row[route_col]).group()
            text+=f"<!-- rom-route: {route_id} -->\n### Bounded route\n\nCompare the controlled state against the strongest matched baseline. A positive discriminating result supports only the stated regime; a negative result revises the mechanism, while confounded outcomes require the smallest extra control. Retain the calibrated dataset when stopping.\n\n"
    text+="<!-- rom-section: audit-appendix -->\n## Audit appendix\n\nExact projections preserve the authoritative facts and decisions.\n\n"
    for name in NARRATIVE_PROJECTION_NAMES[mode]:
        text+=f"<!-- rom-projection: {name} -->\n### {name}\n\n{table_text(old.table(name))}\n\n"
    text+=f"<!-- rom-section: references -->\n{references}\n"
    path.write_text(text,encoding="utf-8",newline="\n")
    return path

class ReaderNarrativeTests(unittest.TestCase):
    work_name="reader-narrative"
    def setUp(self):
        self.work=reset_work(self.work_name)
        self.workspace=workspace_root()
    def tearDown(self):cleanup_work(self.work_name)
    def errors(self,run):return validate(run,workspace_root=self.workspace).errors
    def assertValid(self,run):self.assertEqual(self.errors(run),[])
    def assertInvalid(self,run,fragment):
        errors=self.errors(run)
        self.assertTrue(any(fragment.casefold() in e.casefold() for e in errors),"\n".join(errors))
    def make(self,mode="landscape"):
        parent=make_run(self.work,run_id="parent") if mode!="landscape" else None
        return make_run(self.work,run_id="subject",mode=mode,parent=parent)

    def test_all_modes_keep_complete_decision_and_audit_projections(self):
        for mode in ("landscape","focus","evidence-audit","run-audit"):
            with self.subTest(mode=mode):
                parent=make_run(self.work,run_id=f"parent-{mode}")
                run=make_run(self.work,run_id=f"child-{mode}",mode=mode,parent=parent if mode!="landscape" else None)
                self.assertValid(run)
                before={p.name:p.read_bytes() for p in run.glob("*.md") if p.name!=load_manifest(run)["primary_artifact"]}
                path=narrative_reader(run)
                self.assertValid(run)
                self.assertEqual(before,{run_name:(run/run_name).read_bytes() for run_name in before})
                doc=V2Document.parse(path,path.read_text(encoding="utf-8"))
                self.assertNotEqual(doc.table("red-team-impact").headers,["Comparison","Meaning"])

    def test_run_audit_recomputes_parent_with_narrative_reader(self):
        parent=make_run(self.work,run_id="narrative-parent")
        narrative_reader(parent);self.assertValid(parent)
        run=make_run(self.work,run_id="narrative-parent-audit",mode="run-audit",parent=parent)
        narrative_reader(run);self.assertValid(run)

    def test_zero_candidates_landscape_and_focus_remain_claim_decisions(self):
        for mode in ("landscape","focus"):
            with self.subTest(mode=mode):
                parent=make_run(self.work,run_id=f"parent-{mode}")
                run=make_run(self.work,run_id=f"zero-{mode}",mode=mode,parent=parent if mode=="focus" else None)
                (filter_routes if mode=="landscape" else filter_focus_routes)(run,set())
                narrative_reader(run);self.assertValid(run)

    def test_single_focus_route_keeps_comparison_and_fallback_as_design(self):
        run=self.make("focus");filter_focus_routes(run,{"C-001"})
        path=narrative_reader(run);self.assertValid(run)
        self.assertEqual(set(V2Document.parse(path,path.read_text(encoding="utf-8")).route_blocks),{"C-001"})
        set_table_cell(run/"05_route-protocol.md","route-boundaries","C-001","Comparator/fallback activation rule","none")
        self.assertInvalid(run,"activation card")

    def test_zero_eligible_pilots_keeps_candidates_and_information_checks(self):
        run=self.make()
        portfolio=run/"05_candidate-portfolio.md"
        for candidate in ("C-001","C-002","C-003"):
            for header in ("Openness gate: pass/conditional/fail/unknown","Contribution gate: pass/conditional/fail/unknown","Feasibility gate: pass/conditional/fail/unknown"):
                set_table_cell(portfolio,"opportunity-gates",candidate,header,"unknown")
            set_table_cell(portfolio,"opportunity-gates",candidate,"Overall: go/conditional-go/defer/no-go","defer")
        edit_table(portfolio,"route-fast-pilots",lambda h,rows:(h,[]))
        edit_table(run/"07_decision-log.md","next-actions",lambda h,rows:(h,[
            ["audit equipment records","search","inventory and acceptance sheets","capability matrix with missing access marked",f"{c} feasibility: documented access reopens review; absent access retains defer"]
            for c in ("C-001","C-002","C-003")]))
        narrative_reader(run);self.assertValid(run)
        set_table_cell(portfolio,"opportunity-gates","C-001","Overall: go/conditional-go/defer/no-go","go")
        self.assertInvalid(run,"Overall")

    def test_existing_wide_and_compact_readers_still_validate(self):
        for mode in ("landscape","focus"):
            parent=make_run(self.work,run_id=f"p-{mode}")
            run=make_run(self.work,run_id=f"r-{mode}",mode=mode,parent=parent if mode=="focus" else None)
            self.assertValid(run)
            path=run/load_manifest(run)["primary_artifact"]
            def compact(h,rows):
                if mode=="landscape":
                    decisions={"C-001":("Revise","D-002"),"C-002":("Keep","D-005"),"C-003":("Keep","D-006")}
                    return ["Route","Summary","Disposition","Decision ID"],[[row[0],"Bounded route explanation.",*decisions[row[0]]] for row in rows]
                return ["Role","Route","Summary","Disposition","Decision ID"],[[row[0],row[1],"Bounded route explanation.",row[-2],row[-1]] for row in rows]
            edit_table(path,"recommended-routes",compact);self.assertValid(run)

    def test_summary_only_or_table_only_cannot_stand_in_for_route_prose(self):
        run=self.make();path=narrative_reader(run)
        text=path.read_text(encoding="utf-8")
        text=re.sub(r"(<!-- rom-route: C-001 -->).*?(?=<!-- rom-route:)",r"\1\n### Route heading\n<!-- Explain later -->\n| What | Why |\n|---|---|\n| A state | A possible effect |\n\n",text,count=1,flags=re.S)
        path.write_text(text,encoding="utf-8")
        self.assertInvalid(run,"C-001 needs visible explanation")

    def test_missing_or_extra_narrative_route_is_rejected(self):
        run=self.make();path=narrative_reader(run)
        path.write_text(path.read_text(encoding="utf-8").replace("<!-- rom-route: C-001 -->","<!-- rom-route: C-999 -->"),encoding="utf-8")
        self.assertInvalid(run,"narrative route ownership")

    def test_fenced_duplicate_and_outside_appendix_projections_fail(self):
        for variant in ("fenced","duplicate","outside"):
            run=make_run(self.work,run_id=variant);path=narrative_reader(run)
            text=path.read_text(encoding="utf-8")
            marker="<!-- rom-projection: red-team-impact -->"
            if variant=="fenced":text=text.replace(marker,"~~~\n"+marker+"\n~~~")
            elif variant=="duplicate":text=text.replace(marker,marker+"\n"+marker)
            else:text=text.replace("<!-- rom-section: audit-appendix -->","<!-- rom-section: audit-appendix -->\n<!-- rom-section: misplaced -->")
            path.write_text(text,encoding="utf-8");self.assertTrue(self.errors(run))

    def test_missing_red_team_projection_cannot_hide_nonkeep_attack(self):
        run=self.make();path=narrative_reader(run)
        text=re.sub(r"<!-- rom-projection: red-team-impact -->.*?(?=<!-- rom-section: references -->)","",path.read_text(encoding="utf-8"),flags=re.S)
        path.write_text(text,encoding="utf-8");self.assertInvalid(run,"projection set mismatch")

    def test_two_tables_in_projection_are_ambiguous_and_rejected(self):
        run=self.make();path=narrative_reader(run)
        marker="<!-- rom-projection: execution -->"
        path.write_text(path.read_text(encoding="utf-8").replace(marker,marker+"\n| Wrong | Table |\n|---|---|\n| X | Y |\n\nExplanation\n"),encoding="utf-8")
        self.assertInvalid(run,"exactly one table")

    def test_appendix_cannot_change_binding_decision_or_sources(self):
        for variant in ("decision","source"):
            run=make_run(self.work,run_id=variant);path=narrative_reader(run)
            text=path.read_text(encoding="utf-8")
            if variant=="decision":
                # Alter the exact audit row while leaving the authoritative working attack unchanged.
                text=text.replace("| A-002 |","| A-099 |")
            else:
                text=text.replace("10.1234/example1","10.1234/forged")
                if text==path.read_text(encoding="utf-8"):
                    text=re.sub(r"https://doi.org/[^\s)]+","https://doi.org/10.1234/forged",text,count=1)
            path.write_text(text,encoding="utf-8");self.assertTrue(self.errors(run))

    def test_moving_bio_premise_to_new_body_still_activates_gate(self):
        run=self.make();path=narrative_reader(run)
        path.write_text(path.read_text(encoding="utf-8").replace("## Argument","## Argument\n\nArtificial neuronal computation is the claimed mechanism."),encoding="utf-8")
        self.assertTrue(any("bio" in e.casefold() for e in self.errors(run)))

if __name__=="__main__":unittest.main()
