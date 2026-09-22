# Prompt Library

Replace bracketed fields and keep stable IDs across artifacts. Use [run-modes.md](run-modes.md) to select mode/lens, [schemas.md](schemas.md) for artifact contracts, and [evidence-confidence.md](evidence-confidence.md) for confidence language. These prompts guide reasoning; they do not waive evidence or validation gates.

## Contents

- [Configuration-preflight prompt](#configuration-preflight-prompt)
- [Auto-routing prompt](#auto-routing-prompt)
- [Landscape prompt](#landscape-prompt)
- [Focus prompt](#focus-prompt)
- [Evidence-audit prompt](#evidence-audit-prompt)
- [Run-audit prompt](#run-audit-prompt)
- [Discovery-lens add-ons](#discovery-lens-add-ons)
- [Shared phase prompts](#shared-phase-prompts)
- [Parent-child prompts](#parent-child-prompts)
- [Evidence-chain completion examples](#evidence-chain-completion-examples)
- [Existing-run audit examples](#existing-run-audit-examples)
- [Bio-inspired guardrail example](#bio-inspired-guardrail-example)
- [Natural-language invocation examples](#natural-language-invocation-examples)
- [Recovery and final-audit prompts](#recovery-and-final-audit-prompts)

## Configuration-preflight prompt

Use this before substantive research whenever one or more configuration axes are
inferred from context rather than already confirmed by the user.

```text
Use the current request, conversation context, known needs, constraints,
boundaries, capability state, decision horizon, and approximate direction to
recommend the research-opportunity-mapper configuration before searching,
initializing, creating files, or synthesizing results.

Recommend one formal task_mode, one discovery_lens, and one primary_domain_lens;
add secondary_domain_lens values only for real interfaces. Give one sentence of
reasoning per axis and a routing confidence. If automatic routing is appropriate,
show requested_mode=auto plus the expected formal task_mode. Never write
task_mode=auto.

Render a compact configuration card in the user's language. In Chinese, finish
with exactly:

【是否采用以上配置？】
请回复：

Then show the expected affirmative reply in a separate text block containing:

是

Wait for confirmation. Treat 是 or an equivalent affirmative reply as acceptance.
Apply explicit overrides and restate only changed settings. Skip this pause only
when all applicable axes were already explicitly confirmed or the user requested
direct execution without confirmation. Do not interpret configuration acceptance
as authorization for undeclared context sources, external systems, or an
unspecified persisted output path.
```

## Auto-routing prompt

Use this when the user describes a task without selecting a formal mode.

```text
Use $research-opportunity-mapper to route and execute this request:

[NATURAL-LANGUAGE REQUEST]

First decide whether the formal task mode is landscape, focus, evidence-audit,
or run-audit. Treat auto only as the requested router; never persist auto as the
run mode. Select frontier-led, gray-space-led, or balanced independently.
Select and persist one registered primary domain lens plus only interface-needed
secondary lenses. Use generic-physical-engineering outside the specialized
lenses; use custom only with all ten Common Lens Interface fields supplied.

State the selected mode, discovery lens, domain lens selection, routing reasons,
routing confidence, decision boundary, and missing context before initializing
the run. First present them through the configuration preflight, ask whether the
user adopts them, and wait for confirmation. If the primary
deliverable is instead a systematic review, full-paper deep reading, detailed
experimental design, or statistical-power calculation, route it according to
orchestration.md and preserve the handoff.

After routing, follow the selected mode contract and produce its human-facing
report plus auditable working artifacts. Do not force landscape gates onto focus
or audit modes.
```

## Landscape prompt

```text
Use $research-opportunity-mapper in landscape mode with the [LENS] discovery
lens and [PRIMARY DOMAIN LENS] to map [DOMAIN] for [DECISION]. Persist any
interface-only secondary domain lenses.

Confirmed capabilities: [OBSERVED/REPORTED CAPABILITIES].
Unknown or assumed capabilities: [UNKNOWNS/ASSUMPTIONS].
Constraints and budgets: [TIME, MATERIALS, TOOLS, COST, COLLABORATORS].
Evidence window and cutoff: [WINDOW / AS-OF DATE].

Keep the invariant intersection:
durable bottleneck x falsifiable causal/physical mechanism x transferable
capability x bounded open position.

Build independent bottleneck, state-operation, mechanism, implementation, and
application branches before ranking. Pass the global breadth gate. Search
canonical anchors, recent frontier evidence, direct neighbors, strongest
baselines, limitations, contradictions, and translation evidence. Never infer
novelty from zero hits.

Produce zero, one, or several substantive routes within the requested scope;
label their risk without filling risk quotas. Reuse a shared platform where it
actually helps. Each finalist
must have a decisive first-data experiment, quantitative or operational success
threshold, kill criterion, dependencies, one-year platform path, strongest
baseline, competing explanation, retained value after failure, and route-owned
positive/negative/ambiguous interpretations. Give every route its own execution
and three outcome rows in the reader report. Let red-team
findings revise or kill routes. Write the mode-appropriate human report in
[LANGUAGE].
```

## Focus prompt

```text
Use $research-opportunity-mapper in focus mode with the [LENS] discovery lens
and [PRIMARY DOMAIN LENS] to turn [SELECTED BRANCH OR CAUSAL INTERFACE] into one
executable research route.

Parent run if present: [PARENT RUN].
Selected branch and inherited facts: [BRANCH / CLAIM / EVIDENCE IDS].
Decision and first-data deadline: [DECISION / DEADLINE].
Confirmed capabilities and dependencies: [CAPABILITY PASSPORT].

Do a local alternative search, not a new field-wide landscape. Compare the
proposed mechanism, strongest credible alternative mechanism, and strongest
practical conventional route. State why the question is sufficient, necessary,
timely, and consequential.

Express the route as control X -> state operation Y -> observable A under
constraints Z, compared with baseline B. Produce one primary route, one strongest
comparison design, and a fallback; do not require separate candidates for those
roles. Allow zero, one or several substantive candidates and do not invent a risk portfolio.

Specify baseline, controls, parameter/regime boundaries, phase gates, success
threshold, kill criterion, and dependencies. Give each actual candidate an
owned staged-execution row and separate
positive/negative/ambiguous rows in both the route protocol and reader report.
Keep comparison and fallback controls inside those stages unless they are
separate research candidates. If none survives, keep route-owned tables empty
and close the claim-owned rejection with a useful evidence check or bounded stop.
Explain in plain language: existing basis -> what changes now -> method ->
measurement -> conclusion. Preserve parent lineage and never silently rewrite
parent decisions.
```

## Evidence-audit prompt

```text
Use $research-opportunity-mapper in evidence-audit mode with the [LENS]
discovery lens and [PRIMARY DOMAIN LENS] to complete and challenge the evidence
chain for:

[ATOMIC CLAIMS OR SOURCE SET]

Parent run or context sources: [PARENT / SOURCES].
Decision affected: [ADVANCE / REVISE / STOP DECISION].
Evidence cutoff: [AS-OF DATE].

Split broad propositions into atomic claims with explicit scope, regime, metric,
and claim type. For every decision-critical claim, define required evidence roles
and search direct support, limitations, contradictions, independent replication,
direct neighbors, strongest baselines, and applicability to the target regime.
Every evidence row must list defined Claim IDs and one exact stance: supports,
limits, contradicts, mixed, or context. Split a source into separate rows when
its stance differs by claim; context rows cannot satisfy confidence evidence.
Supporting and limiting evidence lists must link back to the same claim with a
compatible stance.

Separate frontier_salience from claim_confidence. Apply all full-context,
directness, conflict, dependence, proxy, and cross-layer hard caps. Return High,
Moderate, Low, or Insufficient; explain each cap or downgrade; give the strongest
allowed wording; and name the cheapest evidence that would upgrade or overturn
the claim.

Default to a child supplement. Do not mutate a parent run or preserve its
recommendation by fiat. For each decision-critical claim and the affected route,
record Keep, Downgrade, Revise, or Kill.
```

## Run-audit prompt

```text
Use $research-opportunity-mapper in run-audit mode to adversarially audit the
existing run at [PARENT RUN]. Persist [PRIMARY DOMAIN LENS]. Use the [LENS]
discovery lens only for targeted evidence checks; do not rerun the whole field
unless the audit proves premature collapse.

Treat the parent as immutable. Check lineage, artifact integrity, cross-file
claim/evidence/reference closure, confidence caps, reader-report consistency, and
mode completion gates. For schema 2, reject pseudo-definitions in prose,
comments, fenced examples, reference columns, reader reports, or the correct
marker placed in the wrong manifest artifact role. Then attack bottleneck persistence, question necessity and
timeliness, causal identification, alternative mechanisms, open-position search,
capability inflation, proxy-to-system jumps, baseline fairness, and hidden
peripheral/fabrication/measurement costs.

Cover all eight registered red-team surfaces, including an explicit bounded
bio-inspired-translation row even when non-biological. Every finding must
produce Keep, Downgrade, Revise, or Kill,
with evidence, reasoning, affected claim/route, required repair, owner/next action,
and reversal condition. Copy every attack into the reader impact table. Every
non-Keep attack must change the affected main route/claim verdict,
confidence/wording, or parent impact; the strongest target-level verdict binds.
A decorative risk list is a failure.

Write a child audit report that clearly states which parent conclusions survive,
which wording must narrow, which route must change, and whether any route should
stop. Do not edit the parent in place.
```

## Discovery-lens add-ons

Append exactly one lens block to a mode prompt.

### `frontier-led`

```text
Use a frontier-led discovery lens. Start with recent authoritative reviews,
roadmaps, representative primary studies, and important field venues within the
evidence window. Use field/year-normalized citation signals only when provider,
query date, and method are available; otherwise record unavailable. Recover older
canonical work that defines mechanisms and benchmarks. Search limitations,
negative evidence, direct neighbors, and strongest baselines before recommending.
Treat recency, venue, and citation attention as salience, never credibility.
```

### `gray-space-led`

```text
Use a gray-space-led discovery lens. Build a mismatch ledger across mature need x
missing primitive, known mechanism x untested state operation, material physics x
missing control/readout, device effect x missing system metric, studied platform x
untested regime, and adjacent terminology x evaluation mismatch.

Require positive evidence on both sides of every proposed mismatch, a bounded
direct-neighbor search, nearest matches, and an exact unresolved causal interface.
Zero hits mean only that this search did not find a match. Never convert them into
global absence, novelty, or priority.
```

### `balanced`

```text
Use a balanced discovery lens. Build the recent frontier radar and gray-space
mismatch ledger independently, then compare their overlap, conflict, and neglected
interfaces. Keep at least one serious route not selected only by the fashionable
material, device, or architecture. Allocate search effort to confirmation and
disconfirmation, and keep frontier_salience separate from claim_confidence.
```

## Shared phase prompts

### Decision and capability intake

```text
Convert the user context into a decision brief and capability passport. Tag every
fact Observed, Reported, Assumed, or Unknown. State the controllable action,
required guarantee, first-data decision, platform horizon, budgets, dependencies,
and evidence cutoff. Turn every feasibility-controlling Assumed or Unknown item
into a verification action or readiness penalty. Do not recommend a topic yet.
```

### State/mechanism framing

```text
Describe the problem without assuming a favored material. Define workload or
target operation, physical/information state, write/hold/read behavior, persistent
bottleneck, metric, regime, system budget, causal control, observable, null, and
strongest alternative explanation. Mark the last evidenced layer and every later
bridge as validated, modeled, assumed, or missing.
```

### Search design

```text
Create a reproducible query plan appropriate to [MODE] and [LENS]. Include
canonical, frontier, representative-primary, direct-neighbor, strongest-baseline,
alternative-mechanism, limitation/negative, replication, and translation lanes as
needed. Record inclusion/exclusion logic and a decision-based stop rule. Do not
invent citations or treat a query miss as an absence claim.
```

### Claim extraction and confidence

```text
Convert retrieved sources into atomic claim/evidence records. For each
decision-critical claim, assess exact scope, directness, full-context status,
method validity, independence/replication, consistency, applicability, and
contradictions. Apply the strictest confidence cap. State confidence, cap reason,
allowed wording, upgrade action, and overturn condition. Do not grade a paper as a
whole and do not let frontier salience raise confidence. Require every evidence
row to name authoritative Claim IDs and one stance. A supporting confidence edge
requires supports or mixed; a limiting edge requires limits, contradicts, or
mixed. Mixed evidence is not unqualified support and its limiting component must
still constrain caps and wording; context is neither. Split rows when one source
has different stances by claim.
```

### SOTA family synthesis

```text
Group current approaches by causal approach family, not by an arbitrary paper
list. For each family state: core idea, best demonstrated regime, enabling
assumption, strongest evidence, unresolved failure mode, strongest baseline, and
why the persistent bottleneck remains. Separate what is established from what the
run infers about the open interface.
```

### Causal red team

```text
Act as a hostile but evidence-bound reviewer. Challenge whether the question is
real, necessary, and timely; whether the bottleneck persists; whether the proposed
observable uniquely identifies the mechanism; whether search vocabulary hides
close neighbors; whether capability is inflated; whether proxy evidence jumps
layers; and whether baseline budgets omit peripherals, calibration, fabrication,
variation, reliability, or measurement costs.

Create at least one structured row for every exact attack surface:
problem-adequacy, mechanism, evidence, open-position, capability, cross-scale,
baseline-system-cost, and bio-inspired-translation. For every attack, name
evidence, the discriminating search/experiment, and a
Keep/Downgrade/Revise/Kill action. Copy all attacks to the reader impact table.
Every non-Keep attack must alter the affected authoritative decision surface,
and the strongest verdict for one target binds. Do not accept a risk paragraph
or side table that leaves the main recommendation stale.
```

### Human-facing route card

```text
For every recommended route, write the route so a domain researcher can act without reconstructing internal
tables. Answer: What? Why? Need to know? How? What will be learned? Also include
the strongest baseline, competing hypotheses, positive/negative/ambiguous outcome
interpretations, kill criterion, retained value after failure, confidence caps,
and reversal conditions. Give each route an owned execution row and three owned
outcome rows. Use ordinary citations and explain each key source's
contribution, supported viewpoint, and boundary.
```

## Parent-child prompts

### Landscape branch to focus child

```text
Create a focus child from [PARENT LANDSCAPE RUN] using selected branch [BRANCH ID].
Inherit only the declared claim, evidence, and capability facts. Verify parent
lineage before reuse. Reassess freshness and scope; mark inherited, reverified,
revised, and rejected facts separately. Keep the parent read-only.
```

### Evidence supplement to a parent

```text
Create an evidence-audit child for [PARENT RUN] covering [CLAIM IDS]. Treat this as
a supplement. If new evidence changes confidence or the recommendation, record a
proposed disposition and integration action in the child decision log. Do not edit
or silently reinterpret the parent.
```

## Evidence-chain completion examples

### Natural-language Chinese example

```text
使用 $research-opportunity-mapper 补全这个已有方向的关键证据链：
【父 run 或报告路径】。

重点审查以下主张：【逐条列出主张或 B-### / M-### / S-### / CL-###】。请把任务路由为
evidence-audit，默认 balanced；围绕每个主张补检直接支持、限制/反例、
独立复现、最强基线和相邻工作。不要给论文整体打分，要给每个主张标注
High / Moderate / Low / Insufficient、硬上限原因、当前允许的表述，以及
什么证据会升级或推翻它。父 run 只读；如结论变化，在子 run 中给出
Keep / Downgrade / Revise / Kill，不要静默改写原结论。
```

### Key-paper audit example

```text
Audit whether papers [DOI/URL LIST] are sufficient to support claim [CLAIM] under
regime [REGIME]. Expand decision-critical evidence to full context, separate
existence, mechanism, persistence, generalization, and system-value claims, search
independent limitations and contradictions, then return allowed wording and the
cheapest decisive next evidence. Use evidence-audit + frontier-led.
```

## Existing-run audit examples

```text
使用 $research-opportunity-mapper 审计已有 run：【RUN PATH】。

这是 run-audit，不是重新做一遍综述。父 run 必须只读。重点检查：引用与
claim/evidence ID 是否闭环；关键主张是否受全文、直接性、冲突或单团队证据
上限约束；报告是否夸大开放位置；课题组能力是否从 Learning/Unknown 被写成
Observed；材料/器件 proxy 是否越级外推到阵列、IC 或 workload；红队是否真的
改变决策。每个关键问题必须给 Keep / Downgrade / Revise / Kill，并说明修复、
下一动作和反转条件。
```

## Bio-inspired guardrail example

```text
Use $research-opportunity-mapper in focus mode to evaluate [BIO-INSPIRED IDEA].
Do not assume that biological performance makes literal hardware imitation useful.

Build and test this chain:
biological observation -> abstract functional principle -> mathematical operator
or state update -> algorithm -> hardware primitive -> strong non-biomimetic
baseline -> principle-specific ablation -> measurable intrinsic gain and boundary.

Rewrite the research question so it remains meaningful after removing “brain”,
“neuron”, and “synapse” language. Match parameter count, state dimension, training
or tuning budget, memory, peripherals, and hardware complexity. Distinguish pure
algorithm, ideal-device simulation, device-aware simulation, hardware-in-loop,
single-device, array, and chip evidence. Kill or revise the biomimetic claim if the
gain disappears under ablation or a same-budget conventional baseline reproduces
it cheaply.

If any biological observation, analogy, label, or superiority premise affects
the route, the gate is triggered and the translation chain cannot be wholly not
applicable. Fill every link or issue Revise/Kill with an exact repair. Use an
all-N/A row only when biology is genuinely irrelevant, and state the reason plus
the ordinary-baseline boundary.
```

Chinese invocation:

```text
聚焦评估“仿生【功能】用于【硬件/算法】”这个方向。不要采用“大脑更好，
所以复刻大脑一定更好”的前提。先抽象出不依赖生物叙事的计算原则，再依次
写出删除“大脑/神经元/突触”标签后仍成立的科学问题，并分别落到数学状态
操作、算法、硬件原语、非仿生强基线和原理消融。只有在匹配
参数量、训练预算、状态维度、外围与硬件复杂度后仍有可测增益，才能保留
“bio-inspired 带来本质提升”的结论；否则降级为一般动力学或工程实现。
只要生物前提已经影响问题，就不得把整条 translation 写成 not applicable。
```

## Natural-language invocation examples

### Broad map, balanced

```text
帮我对“可重构铁电计算硬件”做一次广域机会地图，目标是选择博士课题和
一年平台路线。自动判断模式和 lens；如果没有更强理由，使用 landscape +
balanced。不要先锁定材料，必须比较瓶颈、状态操作和机制家族，最后给共享
平台的实质路线组合，允许零、一或若干条，不为风险配额凑数。
```

### Broad map, frontier-led

```text
以 2023 年至今的近期权威综述、顶级期刊/会议和代表性原始论文为态势入口，
调研可调超表面的研究机会。使用 landscape + frontier-led。顶刊和引用只用于
确定前沿关注度，不直接提高关键主张可信度；补做直接近邻、负结果和成熟
基线审查。
```

### Focus, gray-space-led

```text
把“PTO/STO 相边界状态到 FTJ 电学读出”作为一个选定 branch 深挖，使用
focus + gray-space-led。围绕“已知可控状态 × 缺失因果唯一读出”建立两侧
正证据和有边界的相邻缺口。允许零、一或若干条实质候选，有候选时保留一条主路线，
并保留最强比较设计和fallback；不为补角色或风险档位制造独立C-ID。
```

### Evidence audit, frontier-led

```text
审查“某器件动力学在同预算下能改善持续学习”这个主张。使用
evidence-audit + frontier-led，把材料/器件现象、计算原则、算法结果和硬件
系统优势拆成不同 claim，逐项给可信度、允许表述和推翻条件。
```

### Existing-run audit

```text
对【已有 run 路径】做 run-audit + balanced。不要修改原 run；创建带血缘的
审计子 run，检查红队、证据上限、跨层推断和报告一致性，并给出真实的
Keep / Downgrade / Revise / Kill 裁决。
```

## Recovery and final-audit prompts

### Anti-anchoring recovery

```text
The run may have converged prematurely on [CURRENT IDEA]. Freeze ranking. Identify
which terminology, assumptions, and evidence chains dominate it. If this is a
landscape, rebuild independent bottleneck and mechanism branches; if this is a
focus run, rebuild only the local mechanism and practical alternatives. Search
counterexamples and strongest baselines, then retain, revise, downgrade, or kill
the idea without converting search misses into novelty.
```

### Final mode-aware audit

```text
Audit the complete run against its persisted formal mode and discovery lens. Read
the mode contract, schema contract, confidence hard caps, selected domain lenses,
and reader-report contract. Check cross-artifact integrity, evidence/inference/
recommendation separation, bounded search language, baseline fairness, causal
discrimination, capability status, route-owned outcome branches, evidence
Claim-ID/stance compatibility, authoritative definition roles, all eight
red-team surfaces, and non-Keep propagation into the main decision.

Apply only the selected mode's completion gate: scope-appropriate landscape breadth and substantive-route
portfolio; focus local alternatives and primary/comparator/fallback; evidence-audit
claim confidence and allowed wording; run-audit immutable-parent integrity and
Keep/Downgrade/Revise/Kill. State exact repairs for every blocker. Validation is a
structural audit, not a declaration that the scientific conclusion is true.
```
