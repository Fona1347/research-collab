# {{DOMAIN}}：既有报告的审计与修复

报告日期 / 证据截止: {{DATE}} / {{AS_OF_DATE}}

[论证正文](#main-argument) · [审计附录](#audit-appendix) · [参考文献](#references)

<!-- rom-section: decision-summary -->
## 决策摘要

> [!IMPORTANT]
> TBD：紧凑说明当前判定、主要理由、置信度与阻断、当前动作和改变决定的结果。

<!-- rom-section: audit-findings -->
<a id="main-argument"></a>
## 审计判定与修复

### 审计对象、判定依据与影响

TBD：说明不可变快照或原子主张范围、证据与访问边界、最重要的判定和对当前决定的影响。先解释判定和修复，再给核查过程；不制造新路线组合。

### 关键发现与必要解释

TBD：说明实际观察、关键来源及限制、最强反证和置信度上限。解释缺陷为什么影响结论，指出权威修复目标、依赖与尚未解决的科学问题。不能只靠附录中的 ID 和审计字段让读者猜测。

> [!NOTE]
> TBD：关键证据实际建立的事实与不可外推的边界 [1]。

> [!CAUTION]
> TBD：会改变决定的限制或依赖。

> [!WARNING]
> TBD：最高后果发现、保留/降级/修订/终止判定及精确修复。

### 修复验证与下一决定

TBD：说明怎样验证修复，以及通过、失败或仍未决各自意味着什么；区分结构闭合和科学真实性。完整逐项投影在同一报告的审计附录。

<!-- rom-section: audit-appendix -->
<a id="audit-appendix"></a>
## 审计附录

本附录保留权威台账的完整读者投影；正文已解释影响决定的证据和限制。模式 / 发现视角：run-audit / {{DISCOVERY_LENS}}；Run ID：{{RUN_ID}}。父项 / 接口：{{PARENT_RUN}} / {{SELECTED_BRANCH}}。领域与尺度边界应在正文说明。

[返回论证](#main-argument)

<!-- rom-projection: integrity -->
### 完整性判定

| Finding | Evidence | Severity | Verdict | Repair | Decision ID |
|---|---|---|---|---|---|
| manifest, artifact, ID, and citation projections match recomputation | parent-audit deterministic projections | low | Keep | retain the immutable snapshot and rerun after parent change | D-001 |

<!-- rom-projection: scientific-red-team -->
### 科学判定

| Finding ID | Claim | Parent confidence | Active cap codes | Justified confidence | Verdict | Decision ID |
|---|---|---|---|---|---|---|
| F-002 | B-001 | High | context-unverified | Insufficient | Downgrade | D-001 |

<!-- rom-projection: route-verdicts -->
### 最终处置

| Route/claim | Parent status | Strongest objection | Verdict | Allowed conclusion | Required repair | Stop/re-entry condition | Decision ID |
|---|---|---|---|---|---|---|---|
| C-001 | recommended | TBD | Revise | TBD | TBD | TBD | D-001 |

<!-- rom-projection: bio-inspired-audit -->
### 特定前提的审计

| Target | Biological observation | Abstract principle | Mathematical operator/state-update rule | Algorithm | Hardware primitive | De-biologized scientific question | Non-biological baseline | Principle-specific ablation | Intrinsic gain/boundary | Verdict | Decision ID |
|---|---|---|---|---|---|---|---|---|---|---|---|
| not applicable — TBD reason | not applicable | not applicable | not applicable | not applicable | not applicable | 去除生物标签后重述科学问题 | not applicable | not applicable | not applicable | Keep | D-001 |

<!-- rom-projection: red-team-impact -->
### 逐项反驳与修复

| Attack ID | Target ID | Attack surface | Strongest objection | Severity | Verdict | Status | Exact repair | Decision ID |
|---|---|---|---|---|---|---|---|---|
| A-001 | C-001 | cross-scale | TBD | blocking | Revise | open | TBD | D-001 |

<!-- rom-section: references -->
<a id="references"></a>
## 参考文献

1. TBD. [DOI](https://doi.org/TBD)

[返回论证](#main-argument)
