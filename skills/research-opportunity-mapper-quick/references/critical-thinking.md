# Critical-Thinking Protocol

## Epistemic Labels

Use these labels consistently:

- `Evidence`: directly supported by a cited source or observed laboratory fact.
- `Inference`: derived from multiple evidence items or a model; state the reasoning and uncertainty.
- `Recommendation`: a choice under stated objectives and constraints.
- `Speculation`: plausible but weakly supported; useful for search or experiment generation only.

Do not let recommendation language masquerade as evidence.

## Candidate Audit

### 1. Persistent bottleneck

- Does the bottleneck survive plausible improvements in conventional technology?
- Is it a first-order system limit or a benchmark-specific inconvenience?
- Which system budget does it dominate, and under what operating regime?

### 2. Causal mechanism

- What is the physical state variable?
- What control changes it?
- What is read out?
- Which governing equation or kinetic model describes the state transition?
- Can the proposed experiment distinguish the mechanism from charge trapping, heating, ionic drift, contact effects, leakage, or measurement artifact?

### 3. Independent control

- Are multiple claimed state variables independently controllable or merely correlated?
- Does adding a terminal, material, or stimulus create a new degree of freedom or just a new way to access the same state?
- What experiment demonstrates orthogonality?

### 4. System value

- What is the strongest digital, CMOS, or conventional sensor baseline?
- Are ADC/DAC, drivers, refresh, calibration, redundancy, communication, and control included?
- Does a device-level improvement survive array and workload scaling?
- Is accuracy or robustness maintained at the claimed energy and latency?

### 5. Evidence validity

- Is the result primary, replicated, and measured under comparable conditions?
- Are sample size, device-to-device variation, cycle variation, and statistical uncertainty reported?
- Is the benchmark selected after seeing the result?
- Does simulation assume ideal precision, zero parasitics, or unavailable fabrication?

### 6. Crowding and novelty

- Are there direct neighbors with the same mechanism and target operation?
- Is the difference causal and experimentally consequential, or merely a material substitution?
- Have patents, recent conferences, preprints, and adjacent terminology been searched?
- Would the novelty statement remain meaningful without "first," "novel," or an application label?

### 7. Laboratory fit

- Which process and measurement modules transfer unchanged?
- What new module is on the critical path?
- Can the three-month experiment avoid the hardest dependency?
- Is the proposed feature size compatible with the scientific question?

## Alternative-Explanation Table

For every decisive observable, create:

| Observable | Preferred mechanism | Alternative explanation | Discriminating control | Expected signatures | Decision rule |
|---|---|---|---|---|---|

An experiment that produces an attractive curve but cannot discriminate explanations is not decisive.

## Baseline Ladder

Compare in increasing scope:

1. Material or device baseline.
2. Same device with the proposed control disabled.
3. Best known alternative device mechanism.
4. Circuit-level CMOS or digital implementation.
5. End-to-end workload baseline including peripherals.

State which level is feasible in three months and which requires the one-year platform.

## Kill Criteria

Kill criteria should be quantitative where possible and tied to the causal claim. Examples:

- Control axis is not independent within measurement uncertainty.
- State kernel cannot be tuned across the task-relevant time range.
- Apparent memory is dominated by uncontrolled drift or heating.
- Variability or calibration overhead removes the predicted system gain.
- A direct neighbor already demonstrates the same causal interface with a stronger platform.
- The minimal experiment requires an unavailable dependency with no fallback.

Do not define a kill criterion as "the device performs poorly" without a threshold and consequence.

## Red-Team Questions

1. What result would make this only another device demonstration?
2. What assumption is carrying most of the proposed system advantage?
3. Which neighboring community might already have solved the same problem under different terminology?
4. What is the cheapest conventional solution?
5. Can a simpler mechanism explain the expected data?
6. What happens when variability, parasitics, and peripherals are included?
7. Which result would falsify the hypothesis in three months?
8. If the flagship idea fails, what reusable platform or publishable mechanism result remains?

## Recommendation Rule

Recommend a candidate only when:

- The bottleneck is evidenced and plausibly persistent.
- The mechanism exposes a real, falsifiable unknown.
- The laboratory can run a discriminating experiment within the stated horizon.
- Close neighbors leave a bounded unresolved interface.
- The system-value hypothesis survives a baseline and overhead audit.
- Failure still yields interpretable knowledge or reusable infrastructure.
