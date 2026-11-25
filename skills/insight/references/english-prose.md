# English Academic Prose

Load this file whenever any part of the deliverable is in English (polishing, Chinese-to-English translation, composing, or the English half of a bilingual draft). `expression.md` decides *what* may change and what must be preserved; this file governs *how* English sentences carry that locked content. If the two conflict, fidelity wins.

The target is prose a native-speaking PI would sign without edits: plain, exact, and invisible. Native-level does not mean ornate. A sentence that is already clear, accurate, and idiomatic stays as it is.

## 1. Edit depth

Match the depth to the request. Never escalate silently.

- **Copyedit**: grammar, usage, articles, consistency, typos. Keep the sentence structure.
- **Line edit** (default for "polish"): reorder within sentences for information flow, replace empty verbs, split run-ons. Keep the paragraph structure and every claim.
- **Compose** (default for translation and for the writer in the full route): rebuild each paragraph in English from the locked claims. Do not translate sentence by sentence.

In every mode, keep the author's technical terms, defined abbreviations, spelling variety (US/UK), and reasonable stylistic choices. Do not "upgrade" vocabulary. Add no claims, hedges, or caveats that the source lacks.

## 2. Information flow

- Open each sentence with information the reader already has: a term just introduced, or the previous sentence's endpoint. End it with the new or important element, which is the stress position.
- Put the actor in the subject and the action in the verb. Keep the subject short and the verb close to it. If the reader must hold a long subject before reaching the verb, restructure.
- One paragraph, one claim. State the claim in the first sentence. Keep a consistent topic string, so that successive sentences share a subject or pick up the previous stress.
- Use one term for one concept. Do not vary *device / cell / element / memristor* for elegance, because readers will assume four different things.
- Let content carry the transitions: repeat the key noun, or write *This trade-off* or *The redesign*. Use a connective only when it encodes a relation (contrast, cause, concession, condition) that the order of sentences does not already make obvious. A bare *This* always takes a noun.

> Before: *The sense amplifier was redesigned. Lower readout power, by 20%, and higher latency, by 8%, were the result of this redesign.*
> After: *We redesigned the sense amplifier. The redesign cut readout power by 20% but raised latency by 8%.*

## 3. Verbs, voice, tense

- Turn a nominalization back into a verb when it hides who did what: *An investigation of the temperature dependence of retention was performed* becomes *We measured how retention depends on temperature.* Keep a nominalization when it is the established term, or when it refers back as given information (*This reduction…*).
- Do not let empty carrier verbs hold the action: *perform, conduct, carry out, realize, achieve, exhibit, possess, make use of, play a role in*.
- Use the active voice with *we* for decisions, claims, and contributions (*we propose, we find, we argue*). Use the passive when the agent is irrelevant (*Samples were annealed at 400 °C*) or when it keeps given information in the subject position. Never use the passive to blur who is claiming what.
- Use the present tense for established knowledge, for what a figure or the paper shows, and for claims the authors stand behind. Use the past tense for what was done or observed in a specific study. Use the present perfect for a body of work that still bears on the question. Do not switch tense within a single claim.

## 4. Claim verbs must match evidence status

| Evidence status | Verbs that fit | Not with this evidence |
|---|---|---|
| Direct, controlled measurement | *show, demonstrate*, or report the result: *X increased by 12%* | — |
| Inference from consistent evidence | *indicate*; weaker: *suggest* | *prove, establish* |
| Compatible but not discriminating | *is consistent with, is compatible with* | *confirm, support strongly* |
| Simulation or calculation | *predict, estimate, yield* | *prove, verify, confirm* (for physical claims) |
| Correlation or observation | *is associated with, correlates with* | *leads to, drives, improves, causes* |
| Proposal or hypothesis | *we propose, we hypothesize, may* | *has been realized, enables* |
| Formal proof | *we prove, it follows that, implies* | *suggests* (for proved results) |

When translating from Chinese, map each word to the evidence, not to the dictionary. *表明* becomes *shows*, *indicates*, or *suggests*, depending on the evidence. *证实* becomes *confirms* only when a stated hypothesis was tested. *验证* becomes *tested against X*: always name X. *显著* becomes *significantly* only when a statistical test is reported; otherwise write *substantially* or give the number. *首次* or *novel* stays only if the supplied material establishes priority; otherwise drop it. For *实现* or *有效*, state the result and its metric.

Hedge once per claim, at the verb or at the scope, never both (*may possibly suggest*). Native researchers hedge precisely, not rarely.

## 5. Stock phrases and AI patterns: judge by function, not by word list

There is no global blacklist. For each flagged phrase, ask three questions: (a) Does it carry content, such as a logical relation, a scope, or an evidence status? (b) Could a specific word or number replace it? (c) Would a referee in the field write it? If it fails, cut it or replace it with the specific content.

Patterns to audit:

- **Inflated importance**: *pivotal, crucial, paramount, groundbreaking, unprecedented, remarkable, plays a vital role, holds great promise, paves the way*. Replace with the actual consequence and its size.
- **Empty significance verbs**: *highlight, underscore, shed light on, offer insights into, delve into*. Say what was found. (*Highlighted in red* in a caption is literal and fine.)
- **Scaffolding**: *It is worth noting that, It should be emphasized that, In this section we will, Taken together, Overall/In summary* used to restate the paragraph. Delete it and start with the content.
- **Stacked additive connectives**: *Moreover, Furthermore, Additionally* at sentence starts when the sentence is simply the next item.
- **Rhetorical templates**: *not only… but also* for unsurprising pairs; adjective triads (*robust, scalable, and efficient*) whose members are not each shown; *This is not X but Y* when nobody claimed X; dramatic colons and em-dashes.
- **Unearned evaluatives**: *robust, efficient, effective, comprehensive, seamless, state-of-the-art*. Keep them only next to the test, metric, or comparison that earns them.
- **Meta-labels on evidence status**: *It should be noted that this is a simulation result rather than an experimental measurement.* Fold the status into the subject or the verb instead: *Simulations predict…*

Keep: hedges that calibrate evidence, *However* where a result really cuts against expectation, and field formulas readers expect (*Here we show* in a Nature summary paragraph; *Let… Then…* in mathematics).

## 6. Translationese and Chinglish structures

- **Compose from the claim inventory.** Reorder Chinese background-first paragraphs so that they lead with the claim.
- **Topic-comment calques**: *For this method, its accuracy is high* becomes *The method is accurate to within 2%* (give the number if the source has one).
- **Comma chains (一逗到底)**: one main clause per claim. Split at each new claim and remove comma splices. Break up chains of *which…, thus…, thereby…*.
- **Formulaic openers**: *With the rapid development of X; In recent years X has attracted increasing attention; Aiming at the problem of X, this paper proposes*. Open with the concrete problem or gap: *To address X, we…*
- **Four-character parallelism**: do not render it as noun triads (*high efficiency, low cost and strong stability*). State the measured properties.
- **Articles and number**: check every countable noun. Use *the* for something already mentioned or uniquely identifiable.
- **Terminology**: use the field's standard English term (存算一体 is *compute-in-memory*, not *storage-computing integration*). If unsure, flag the term in internal drafts rather than coin a literal one.
- **Agent**: prefer *we* or *here* to repeated *this paper*.

## 7. Register and venue

Follow the venue and register in `T` or in the user's request. Do not invent journal rules. If word limits or section formats matter and are not supplied, ask or follow the provided guidelines.

| Venue or field | Calibration |
|---|---|
| Nature / Science main text | Readable by non-specialists; define jargon and abbreviations; short sentences; active *we*. The summary paragraph runs from context to gap to *Here we show* to key results with numbers to implication. |
| Engineering / IEEE | Specifications with units and baselines; passive acceptable in Methods; comparisons stated against a named baseline. |
| Clinical (CONSORT / STROBE) | *associated with* for observational data; prespecified endpoints; absolute and relative effects with CIs; no *trend toward significance*; report serious adverse events plainly. |
| Economics / quantitative social science | *we find, we estimate*; causal verbs only with an identification strategy, named as such. |
| Mathematics | *We prove, Let… Then…, It follows that*; define before use; no hedging on proved results; *conjecture* for unproved ones; never request experiments. |
| Humanities / law | *I argue* is acceptable; longer periodic sentences are fine; name the interlocutor and meet the strongest objection; law uses *hold, reason, distinguish*. Never *mechanistic inference, working hypothesis, simulated*. |

Mechanics: one spelling variety throughout. SI units with a space (*400 °C*) and percentages per the venue. Define abbreviations at first use and use them consistently. No contractions. Italicize variables, genes, and species. For internal drafts only, the audit block header reads `> **Audit note | non-blocking**` or `> **Edit note | factual correction**`.

## 8. Pre-delivery check (English)

1. **Strength**: every claim verb matches the evidence status in the locked inventory (or in `B*`/`E*`). No unsupported *significantly, demonstrates, confirms, novel, for the first time*.
2. **Fidelity**: numbers, directions, baselines, conditions, and trade-offs are intact. No new caveats.
3. **Flow**: each sentence opens with given information and ends on the new point; subjects are short and close to their verbs; one term per concept.
4. **Audit hits** from §5 and §6: each one remaining earns its place by function.
5. **Scope**: in polish mode, sentences that were already sound are unchanged; register matches `T`.

## 9. Worked examples

**Example 1: translationese + AI patterns (line edit, adds nothing)**

> Original: *With the rapid development of artificial intelligence, compute-in-memory has attracted more and more attention in recent years. It is worth noting that memristor-based architectures play a pivotal role in this field, which can not only significantly reduce energy consumption but also realize high-efficiency computing, thus paving the way for next-generation edge devices.*
>
> Line edit: *Memristor-based compute-in-memory architectures can substantially reduce the energy cost of computation, which makes them candidates for next-generation edge devices.*
>
> What changed: the formulaic opener and *it is worth noting* carried no claim. *Pivotal role* and *paving the way* were inflated restatements of the energy claim. *Significantly* became *substantially* because no statistical test is reported. *Realize high-efficiency computing* duplicated *reduce energy*. If the source supplies the mechanism (weights are used in place, so data movement is avoided), a composed version states it; a line edit does not invent it.

**Example 2: meta-labels + overhedging (keep the baseline and the cost)**

> Original: *The simulation results verify that scheme A can significantly reduce the readout power by 20% compared with scheme B, but it should be noted that the readout latency is increased by 8%. It should be noted that this is only a simulation result rather than an experimental measurement, and it may not be applicable to all chips. Further studies are needed.*
>
> Rewrite: *In circuit simulations, scheme A reduced readout power by 20% relative to scheme B, at the cost of an 8% increase in readout latency.*
>
> What changed: the evidence status moved into the opening phrase, so the meta-label sentence goes. *Verify* is wrong for a simulation. The baseline (*relative to scheme B*) and the latency cost stay, because they are part of the claim. The generic caveat and the future-work line had no specific content. Do not write *outperforms B*.

**Example 3: correlation stated as causation (fix the overclaim and flag it; do not silently keep it)**

> Original: *The implementation of mindfulness training led to a significant improvement of patients' sleep quality (r = 0.32), which demonstrates the effectiveness of the intervention.*
>
> Rewrite: *Patients who completed more mindfulness sessions reported better sleep quality (r = 0.32), consistent with a benefit of the training.*
>
> Note to author (outside the manuscript text): *Changed "led to" and "demonstrates the effectiveness" because a correlation without a control group does not establish an effect. Restore "significant" only if a test and P value are reported.*
>
> What changed: the nominalization (*The implementation of… led to*) hid a causal claim the design cannot carry. The correlation stays a correlation, and the minimal correction is reported in line with expression.md's rule against preserving errors.
