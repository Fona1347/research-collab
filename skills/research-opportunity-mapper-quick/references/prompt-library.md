# Prompt Library

Replace bracketed fields. Use the same IDs and artifact names across phases.

## Master Prompt

```text
Use $research-opportunity-mapper-quick to turn [DOMAIN] into a decision-ready research map.

Decision: [PHD TOPIC / LAB PLATFORM / GRANT / EXPERIMENT].
Laboratory capabilities: [OBSERVED MODULES].
Constraints: [TIME, FEATURE SIZE, MATERIAL ACCESS, BUDGET, COLLABORATORS].
Horizon: first decisive data in [N] months; reusable platform in [N] year(s).
Preferred evidence window: [YEAR RANGE], with older canonical sources clearly labeled.

Do not begin from a favorite material. First map workloads, information/state types,
persistent bottlenecks, missing primitives, mechanism families, and system metrics.
Meet the breadth gate before ranking. Separate Evidence, Inference, Recommendation,
and Speculation. Preserve claim-level provenance. Treat search misses as bounded
negative evidence, not proof of absence.

Produce the eight auditable working artifacts and one human-facing
map_report_<short_task_name>_<YYYY-MM-DD>.md. Include a low/medium/high-risk
shared-platform portfolio, three-month decisive experiments, one-year platform
paths, baselines, alternative explanations, kill criteria, uncertainty register,
and next searches. Working artifacts use GitHub source annotations with detailed
provenance. The reader report uses numbered citations, DOI or stable links, and
callouts explaining each key source's core contribution, supported viewpoint,
and boundary without exposing internal retrieval identifiers.
```

## Phase 0: Intake

```text
Act as a research-program architect. Convert the supplied context into a decision
brief and capability passport. Tag every item Observed, Reported, Assumed, or
Unknown. Identify the exact decision, controllable actions, required guarantee,
three-month output, one-year platform, hard constraints, and missing information.
Do not propose a research topic yet.
```

## Phase 1: Controlled Divergence

```text
Act as a scientific brainstorming lead. Given the decision brief, generate a
breadth ledger with at least four durable bottleneck families, four physical
mechanism families, two application contexts, and one route outside the lab's
current favorite materials. Organize ideas by workload, state type, system budget,
missing primitive, and physical state operation. Include one reason each branch
might fail. Do not claim novelty and do not rank yet.
```

## Phase 2: Literature Search Design

```text
Act as a scoping-review methodologist. Turn the breadth ledger into a reproducible
query lattice. For every branch, provide discovery queries, exact-neighbor queries,
failure/counterexample queries, baseline queries, source priorities, inclusion and
exclusion rules, and a stop rule. Distinguish landscape search from opportunity
testing. Do not invent citations.
```

## Phase 3: Retrieval

```text
Act as the evidence retrieval layer. Execute the query plan using Sciverse when
available and authoritative primary sources as fallback. Return structured
bibliographic records and claim-level evidence. Preserve DOI or stable URL,
database identifiers, chunk/page/location, evidence depth, and verification state.
Expand decisive claims to surrounding context. Log misses without inferring absence.
```

## Phase 4: Candidate Generation

```text
Act as a mechanism-oriented research designer. Use only the evidence matrix and
capability passport to propose candidate causal interfaces. For each, formulate:
Can control X independently modulate physical state operation Y under constraints Z,
yielding advantage A over baseline B? Provide competing hypotheses, discriminating
observables, process route, dependencies, and why the question is more than a
material-plus-application combination. Label unsupported elements Speculation.
```

## Phase 5: Crowding and Red Team

```text
Act as a skeptical reviewer. For each candidate, search direct neighbors and
adjacent terminology, then challenge causality, orthogonality, scalability,
variability, peripherals, calibration, refresh, benchmark fairness, and strongest
digital/conventional alternatives. Classify crowding as crowded, active but open,
sparse evidence, or unsearched. Write quantitative kill criteria and the smallest
experiment or search that resolves each major objection.
```

## Phase 6: Portfolio and Roadmap

```text
Act as a research mentor making a constrained portfolio decision. Rank candidates
with explicit 1-5 rationales for persistence, mechanism depth, lab transfer,
three-month data, one-year leverage, open-interface evidence, dependencies, and
system value. Select low-, medium-, and high-risk routes that share infrastructure.
Show score sensitivity, rejected routes, reversal conditions, milestones, and the
next decision date. Do not conceal uncertainty.
```

## Phase 7: Human-Facing Reader Report

```text
Act as the final research mentor and technical editor. Use the completed intake,
evidence matrix, research map, candidate portfolio, red-team report, and decision
log to write map_report_<short_task_name>_<YYYY-MM-DD>.md in the user's language.
This is the primary deliverable, not an appendix and not a concatenation of the
working files.

Lead with a one-page decision. Explain the causal progression from workload and
state type through bottleneck, missing primitive, device mechanism, material route,
and decisive experiment. Compare low-, medium-, and high-risk routes on their shared
platform. Include three-month experiments, one-year platform paths, strongest
baselines, kill criteria, uncertainties, and reversal conditions.

Convert internal evidence IDs into ordinary numbered citations with DOI or stable
links. For each decision-critical source block, state its core contribution, the
viewpoint it supports, and its boundary. Use GitHub callouts semantically. Keep
database retrieval identifiers in the evidence matrix, not in the reader report.
Do not claim absence or priority from a failed search.
```

## Anti-Anchoring Recovery Prompt

```text
The map may have converged prematurely on [CURRENT IDEA]. Freeze ranking. Identify
which terminology, assumptions, and source papers dominate the current map. Rebuild
the root taxonomy independently of that idea, add at least three bottleneck families
and three mechanism families that do not depend on it, search for counterexamples
and alternative baselines, then reposition [CURRENT IDEA] as one branch. Preserve
its useful causal insight but remove any unsupported exclusivity or priority claim.
```

## Final Audit Prompt

```text
Audit the complete run against $research-opportunity-mapper-quick completion gates. List
blocking errors first. Check breadth, provenance, evidence/inference separation,
negative-search language, direct neighbors, system overhead, decisive experiments,
kill criteria, risk balance, shared platform, rejected alternatives, and unresolved
uncertainty. Also verify that the dynamic map_report exists, is readable without
the internal artifacts, uses ordinary citations and semantic callouts, explains
source contributions and boundaries, covers all three risk levels and both time
horizons, and matches the evidence and decision logs. Do not rewrite conclusions
unless a gate fails; state the exact repair required.
```
