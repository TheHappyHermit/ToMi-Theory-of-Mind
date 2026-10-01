# PRELIMINARY PROPOSAL — Hermes Brain, Component by Component

**Status: PRELIMINARY. Not a design of record.**

| | |
|---|---|
| Written | 2026-09-27 |
| Source | `cognition-arena/ARENA.md` at tranche 70 |
| Corpus read | **1,406 of 2,217** files (63%) · 421 excluded · 2 blocked · **388 remaining** |
| Areas | 128 (16 `PROVISIONAL`) |
| Current repo | `hermes-brain` @ `main` |
| Supersedes | nothing. `PROPOSED-BRAIN-ARCHITECTURE.md` remains the design of record. |

**What this document is.** A component-by-component reading of what the arena's
*current* ranking is converging on, for every component in the brain: what the
idea is, what evidence backs it, what already exists that fills the role, what
we should add or change, and how it would be built. Every recommendation names
the paper or the executed incident that justifies it.

**What this document is not.** It is not finished. 388 corpus files are unread
and the cursor sits in the DNS-CBOR literature (ORDER 1681–2217). **If a
remaining file beats a recommendation here, the recommendation is wrong and
should be struck.** The arena is built to be corrected by exactly that. Treat
every `UNTESTED` design below as a hypothesis with a citation attached, never as
a settled choice.

---

## 0. The one-paragraph version

The arena is converging on a system that is **not a pipeline** but a layered
loop with **three axes the current stack does not have**: a *trust* axis
orthogonal to provenance, a *time* axis where phase and circadian state are
state rather than metadata, and a *plasticity* axis where the gate parameters
are themselves adaptive. The single deepest finding is that **provenance and
trustworthiness are different channels and no single checker may satisfy both** —
proved by an executed incident, not a thought experiment. The second is that
**nothing in the system may grade itself**, which converts verification from an
activity into an architectural requirement. Underneath both, the honest
epistemic position is that the underlying biology is well-graded (`HIGH`/`LOW`)
and almost every proposed *design* is `UNTESTED`.

---

## 1. The evidence rule, stated once, applied everywhere

This governs every recommendation in this document and it comes from the
corpus itself, not from taste.

> Across 793 read files, the recurring shape is: **the validated code path
> produces the appearance of authority, and the unvalidated path produces the
> content.** TOCs, citations, `verified:` blocks, `confidence:` values and index
> boilerplate are generated and checked as *artifacts* — reliable as artifacts.
> The prose they decorate comes from a different path and is not checked.
>
> The evidence is an **inversion**, not a correlation: files with correct 16/16
> TOCs, real volume-and-page citations and populated `verified:` blocks carried
> an invented Nobel attribution, a fabricated degree and advisor, a
> misattributed acronym, and a nonexistent book.
>
> **Until the system can tell verified from unverified, a `HIGH` grade anywhere
> else is a grade the infrastructure has not earned.** — `ARENA.md` §8

Consequences applied below:

- **`HIGH` on a mechanism ≠ `HIGH` on a build.** Almost every design here is
  `UNTESTED`. That is the finding, not a gap in the read.
- **Existence of every cited paper is now VERIFIED.** On 2026-09-27 all 86 arXiv
  IDs in §9.1 were fetched from `arxiv.org/abs/` and their real titles read back.
  **All 86 exist**, and the verified title is recorded beside each link. Seven were
  found to be cited for claims in a **different field** and are struck — see
  §9.4. That is 8% of citations, and the fault is in `ARENA.md`, not in this
  document.
- **Existence is not content.** A verified title tells you the paper is real and
  roughly what it is about. It does **not** tell you the paper says what the
  arena claims. For 79 of 86 the title is consistent with the claim; for the
  other 7 it is not. **Read the primary before building anything here.**
- **Never claim a brain part is unnecessary.** A missing area means the read has
  not reached it. `not observed` is the only correct phrasing.

### Grades in this document

| Grade | Meaning | Where it appears |
|---|---|---|
| `HIGH` | Replicated trials, or convergent independent sources | Mackworth 1943; inverse effectiveness; Weber's law; Goodale & Milner dissociation |
| `LOW` | Some trials, mixed or thin, or one small study | Most mechanism claims; every area's *diagnosis* when it has an executed incident |
| `UNSUCCESSFUL` | Trials were run and it did not work | Recorded so a dead end is not rebuilt blind |
| `UNTESTED` | No trials found. Common for bespoke builds | **Most designs in this document** |

---

## 2. Part I — Component by component

Each component below gets: the idea, the brain part it fills, the evidence and
its grade, what already exists (best-in-class named), the decision, and how it
would be built.

Components are numbered `C1`…`C14` and map onto the existing 8 subsystems and
the 7 categories of `PROPOSED-BRAIN-ARCHITECTURE.md`.

---

### C1 · Provenance and trust, as two fields with two witnesses

**The idea.** Every artefact the system produces carries **two independent
fields**: `provenance` (where did this come from) and `trust` (should this be
believed). They are satisfied by *different witnesses with different failure
modes*, and the gate requires both. No single checker may satisfy both.

**Brain part.** **Reafference** — the comparison of what the brain caused
against what the brain received. It is the only way a self-monitoring system
tells its own output from the world's. The reafferent comparator certifies
exactly one thing: *this is mine*. It certifies nothing about whether the
content is true, kind, or safe.

**The load-bearing evidence — an executed incident, not a hypothetical.**
The **Mini Shai-Hulud** compromise (May 2026) hit **84 npm packages across 42
`@tanstack` packages**. Every one carried a **cryptographically valid SLSA Build
Level 3 attestation**. The attestations accurately reported the correct
repository, workflow, and ref. **The packages were malware** — the attacker
extracted the legitimate OIDC token from runner memory via cache poisoning, so
the build ran *correctly*, from the *correct* place, and produced the *correct*
attestation, on a runner that was already hostile.

The corpus file's sentence is the component in one line: *"The provenance
attested where the build happened, not whether the build was trustworthy."*

**This composes with C2, and the chain is the design.** C2 (efference copy)
answers *did I write this*. C1 answers *so what*. **A system satisfying C2
perfectly can be fully compromised**, because a compromised write path is
*perfectly honest*, and its honesty is what makes the forgery pass. The arena
held zero occurrences of *provenance theatre*, *valid attestation* or
*reafferent* across 127 areas before this was read.

**Already exists — best in class.**
- **SLSA Build Level 3** — the attestation standard the incident satisfied
  *correctly*. Proven insufficient for safety, which is the finding.
- **Sigstore / in-toto** — the signing and attestation substrate underneath it
- **Sigstore Rekor** — transparency log, so attestations are independently
  auditable rather than self-asserted

These are **not optional and not to be built.** They are the `provenance` field
and they are already correct. The gap is that they were never asked the safety
question.

**Decision: ADD the second field. Change nothing about the first.**

**How to build.**
1. Schema: every artefact row gains `trust` **separate from** the existing
   `provenance` column. `provenance` is satisfied in-band by hash chain / signed
   commit / `agency:` stamp. `trust` is satisfied only by a signal that **failed
   differently from the thing it certifies** — an independent scanner, a human,
   an out-of-band hash, or a build on an ephemeral network-restricted runner.
2. The gate requires both fields. A missing `trust` field is a **hard fail**,
   not a default-allow. This is the whole point.
3. Independence is structural: the `trust` witness must not share a process,
   a credential, or a runner with the `provenance` witness. Shared infrastructure
   is what made Mini Shai-Hulud pass.
4. Every `trust` grant is a lease with a TTL and a named human or service as
   the grantor. Trust that cannot be revoked is provenance with extra steps.

**Sources.** Area 45 (efference copy), Area 128 (reafference / provenance
theatre) — both earned by corpus file
`oracle/brain/research/cross-registry-provenance-verification.md` (ORDER 1668,
263 lines, §"The 'Provenance Theatre' Problem", §"What Provenance Does NOT
Prove"), carrying `cross-registry-monorepo-release-orchestration.md` (ORDER 1667,
715 lines). SLSA / Sigstore / in-toto named in the same files.

**Grades.** Diagnosis `LOW` (executed incident, single programme). Design
`UNTESTED`. Brain part `HIGH` (reafference is textbook).

**Interaction.** Depends on C2 (write path), constrains C5 (nothing self-graded —
a shared witness is a shared failure), constrains C10 (register field on
memory). Composes with C12 (bi-temporal provenance substrate).

---

### C2 · Efference copy: did *I* write this?

**The idea.** The store records **what the system caused** alongside what it
received, and the reader asks the trace *which one is it holding*. A tag that
certifies provenance certifies only that **the write path was honest** — and
that is the stated ceiling of this component.

**Brain part.** The **efference copy** as a *comparator*, not a label.

**Already exists — and this is built.** The Hermes stack carries an `agency:`
provenance field (Area 68). The corpus names the schema in ORDER 338.

**Decision: KEEP, and make it the input to C1 rather than the whole of trust.**

**How to build.** `agency: system | user | tool | retrieved` becomes a
**required** field with a referential integrity constraint — a trace whose
`agency` is `system` must have a matching row in the efference log. Prose
currently stamps `agency: system` on output the model generated *in response to*
retrieved text, which is a category error the comparator catches for free.

**Grades.** Design `UNTESTED`. Built.

**Interaction.** Prerequisite for C1. Constrained by C3 (retrieval boundary).

---

### C3 · The retrieval boundary: knowing and acting are different systems

**The idea.** A system has two streams, and **the one you can report on is not
the one you act with**. Every confidence field in the current stack sits on the
ventral (reportable) side.

**Brain part.** Goodale & Milner's **dual visual streams**. The sharpest
available datum: patient **D.F. could not describe a mail slot's orientation,
and could post a letter through it.** Reporting is ventral; action is dorsal.
A design that puts a single confidence number on both sides is asserting a
capability the patient demonstrably lacked.

**Already exists.** Split-stream architectures in robotics; nothing in the
Hermes stack carries the distinction.

**Decision: ADD as a design constraint on every confidence field.**

**How to build.**
1. Confidence is **never** computed by the component that acts. The action gate
   receives a *dorsal* score; the report receives a *ventral* one. They are
   different numbers from different computations and are allowed to disagree.
2. Where they disagree beyond a threshold, the system **acts on the dorsal
   number and reports the ventral one**, and says so. This is uncomfortable and
   correct.
3. Corollary for the arena itself: the `PROPOSED-BRAIN-ARCHITECTURE.md`
   verification audit grades *reports*, never *actions*. It is a ventral
   instrument measuring a dorsal claim.

**Corroboration — WITHDRAWN 2026-09-27.** The arena offered Goodale &
Mascarenhas (2026, [arXiv:2606.14512](https://arxiv.org/abs/2606.14512)) as a
second, independent line, "measured rather than hypothesised." The paper is
real and the authors are right, but its verified title is ***Fodor and Pylyshyn's
Systematicity Challenge Still Stands*** — it concerns **systematicity**, not the
dorsal/ventral dissociation. **It does not corroborate this component and the
citation is withdrawn.** See §9.4.

C3 therefore stands on the **Goodale & Milner patient D.F. double dissociation
alone**, which is `HIGH` in its own right (two patients, mirror-image lesions,
replicated) but is now a single line rather than two. Nothing else in this
document depended on the withdrawn citation.

**Grades.** Phenomenon `HIGH` (double dissociation, replicated). Design
`UNTESTED`.

**Interaction.** Constrains C5, C7, and every `confidence:` field in the repo.

---

### C4 · Plastic gains: the gate parameters are the plastic variable

**The idea.** Every constant in the current stack — `go_threshold=0.4`,
`damping=0.85`, `decay 0.1/turn`, `threshold=0.5` — is a **fixed** gain. The
biology says the learning rate is itself a function of recent activity, and
that neuromodulators set **four meta-parameters of one learning rule** rather
than four separate rules.

**Brain part.**
- **Metaplasticity** (Bienenstock, Cooper & Munro 1982, BCM): potentiation above
  a sliding threshold θ_M, depression below it, and **θ_M itself moves** — up
  under sustained high activity, down under sustained low. A system that fixes
  its learning rate cannot learn.
- **Neuromodulation as four meta-parameters** (Area 106): dopamine and
  acetylcholine are not two channels, they are the *gain and the baseline* of
  one learning rule.

**Evidence.** `LOW` on the biology, `UNTESTED` on the build. The mechanism is
textbook-standard; the *transfer* to an agent gate is not established.

**Decision: CHANGE the constants into gains. This is the highest-leverage change
to existing code in this document.**

**How to build.**
1. `action_gate.go_threshold` becomes a function of: recent prediction error,
   current arousal/allostatic load (C8), and substrate headroom (C9). Not a
   field — a function with a documented signature.
2. The consolidation threshold (currently a fixed `compilation_threshold=3`)
   becomes the BCM sliding θ_M: high activity raises it, sustained low activity
   lowers it. This gives *use-dependent* skill acquisition for free, which is
   what the basal-ganglia compiler was reaching for with a count.
3. Hippocampal replay `damping` becomes a function of novelty and of whether the
   last replay produced a successful discrimination (retrieval is a write —
   C11).
4. **Every gain gets a floor, a ceiling, and a documented timescale.** An
   unbounded adaptive parameter is a new failure mode, and the arena's own rule
   is that exhaustion has an *order* (C9).
5. Log every gain change with its trigger. An adaptive parameter that cannot be
   explained after the fact is indistinguishable from a bug.

**Sources.** Areas 66, 106, 123, 96. Bienenstock, Cooper & Munro (1982), *J.
Neurosci.* 2(1):32–48. Schultz, Dayan & Montague (1997) for the RPE that sets
θ_M. Okamoto, Matsumoto & Ikeda (2012), *Curr. Opin. Neurobiol.*, for
exploration by random walk on θ_M.

**Interaction.** Depends on C8 (arousal), C9 (budget), C13 (metacognition).
Constrains C4's own stability — see §5 Known Risks.

---

### C5 · Nothing grades itself: the independence requirement

**The idea.** A memory system that computes its own reward signal learns to
reward its own mistakes. The **teacher signal must carry information the policy
does not already have**, or the loop is closed and self-flattering.

**Brain part.** The independence requirement on the reward-prediction error.

**Evidence — the four converging lines.**
1. **Memory Reward Inflation in Self-Improving LLM Agents** (Asadolahi, Amini,
   Talebi, Farhadi & Zamanifar, arXiv:2608.00017) — the self-improvement loop
   inflating its own reward.
2. **A detector is not a certifier** (Area 33) — the invariant run that grades
   a pass is a different process from the pass.
3. **Mackworth's countermeasure result, 1943** — the founding experiment of the
   vigilance field. Performance feedback **eliminated** the vigilance decrement;
   instructing subjects to try harder **did nothing**. This is why the
   experiment was commissioned in 1943 and it is `HIGH`.
4. **A monitor that has never been caught failing is not a monitor that works**
   (Area 37) — a monitor must be *tested* against injected failures, in
   production, on a schedule.

**Decision: ADD an independence constraint on every verifier in the system.**

**How to build.**
1. **Attribution may not gate a production decision until its validity is
   established** (Area 24 — the only `HIGH`-grade *design* in the arena).
   Integrated Gradients is the reference method; the corpus benchmark is
   `kdn-vs-gdnlrp-cross-encoder-benchmark`. Concretely: no explanation-derived
   score may gate a deploy, a gate trip, or a belief promotion until it has been
   validated against ground truth on a held-out set.
2. **Every verifier declares its independence set**: which credentials,
   processes, models and data it shares with the thing it verifies. A verifier
   sharing its full independence set with its subject is a **self-grader** and is
   rejected at registration.
3. **Every verifier gets a red-team schedule.** Faults are injected on a
   calendar; a verifier that has never been caught failing is not yet a
   verifier (Mackworth). Log the hit rate. A verifier with a 0% catch rate over
   N injected faults is *broken*, not excellent — and that is the assertion
   that makes the check able to fail.
4. **The arena's own `citation_remediation.py` is the one component in the
   stack that already does this** (Area 78) and is the template.

**Why this outranks everything else in difficulty.** The C11 and C6 invariant
failures in this repo are not bugs in the checker. **They are the system grading
itself and getting it wrong, live.** `citation_remediation.py` exists precisely
because prose citations outran the reads that earned them, and the C6 count
sits at 6 for exactly that reason.

**Grades.** Mackworth `HIGH`. Reward inflation `LOW`. Design `UNTESTED`.
Independence requirement in RPE theory `HIGH`.

**Interaction.** Hard constraint on C1 (shared witness = shared failure), C3,
C7, C12, and on every confidence field in the repo.

---

### C6 · Retraction propagates: invalidate by reachability, never delete

**The idea.** When a belief is withdrawn, everything derived from it must become
invalid **automatically**. Deleting the belief strands its dependents; the
brain's answer is that a trace is *suppressed*, not erased, and it comes back
if the conditions return.

**Brain part.**
- **Belief-expiry as graph reachability** — Doyle's TMS (1979) and de Kleer's
  ATMS (1986), where every derived fact carries its **assumption set**, so
  retracting an assumption invalidates exactly the facts whose set contained it.
- **Extinction learning** (Area 55) — the conditioned stimulus is presented
  without the unconditioned one, the fear response falls, and **the trace is
  not erased**.
- **The reconsolidation window** (Areas 25, 27) — a retrieved memory becomes
  modifiable, and prediction error is what opens the window.

**Already exists — best in class, and the arena is explicit: adopt, do not build.**
- **MemLineage** (arXiv:2605.14421) — max-of-strong-edges provenance with
  **Theorem 1: any all-strong path from an External ancestor forces the chain
  tip to inherit the untrusted label.** This is a published propagation theorem
  for exactly the operation we need. *Do not reimplement it.*
- **MemTX** (arXiv:2607.23929) — carries the strongest evidence any slot in the
  arena has, on transactionality of memory state change.
- **SYNAPSE** (arXiv:2601.02744) — the FOK protocol and the τ=0.12 threshold.
- **Zep / Graphiti** (arXiv:2501.13956) — the bi-temporal episode↔entity
  provenance substrate, and the reason re-extraction is possible at all.
- **SodaMem** (arXiv:2608.08055) — typed FactEvents with **mandatory
  provenance spans**.
- **All-Mem** (arXiv:2603.19595) — the memory substrate itself.

**Decision: ADOPT MemLineage's propagation model. CHANGE the schema to carry
assumption sets. DO NOT build a bespoke DAG.**

**How to build.**
1. Every derived row carries an `assumption_set` — the set of belief IDs it
   depends on. `expand` / `contract` / `revise` in `brain/epistemology/agm.py`
   already compute the right operations; **they just do not persist the
   dependency**, so nothing downstream can be invalidated.
2. Contraction marks dependents **invalid-by-reachability**. It does not delete
   them. `VERIFICATION.md` records the strike; the row stays for audit.
3. **A weighted derivation DAG per ORDER 339** is the mechanism. Weight = support
   strength, so a weakly-held belief's retraction removes little and a
   load-bearing one's removal cascades correctly.
4. The 9 unexplained marks declared in the ledger are the visible symptom of a
   missing propagation story: marks whose provenance cannot be reconstructed.

**Grades.** TMS/ATMS `HIGH` (foundational). MemLineage Theorem 1 `LOW` (one
preprint). Arena's own propagation design `UNTESTED`.

**Interaction.** Depends on C2. Feeds C7 (correction by competition) and C12.
Directly relevant to C14.

---

### C7 · Correction by competition, not by overwrite

**The idea.** The record you correct is **not** the record you overwrite. A
correction covers over; the covered thing returns on its own when conditions
change. Supersedure is not deletion and not equality — "newest wins, no semantic
similarity, no LLM judgment" is the *minimal viable* enforcement layer, and it
is stated as such.

**Brain part.** **Extinction learning**; **suppression, not erasure** (Area 70
— the covered thing comes back).

**Already exists.**
- **Fortunate Recall** (arXiv:2609.10413) — the supersedure result.
- **TRACE** (arXiv:2606.13174) — the enforcement layer.
- **MeClear** (arXiv:2609.09115) — clearance pass attributing **downstream
  utility** to each item, i.e. forgetting by measured usefulness rather than by
  age.
- **CogniFold** (arXiv:2605.13438) — three-layer memory-as-behaviour.
- **PGMem** (arXiv:2608.01708) — persona-memory graph with **typed edges
  carrying affect**.

**Decision: ADD an enforcement layer between belief and supersession.**

**How to build.**
1. A belief is not a row. It is a row plus a **supersession relation** with a
   stated basis: *replaced*, *narrowed*, *contradicted*, *expired*.
2. The current `epistemic_state` column collapses these into one enum. Split
   it. `contradicted` and `expired` demand different downstream behaviour and
   currently get the same.
3. **A correction may not demote an existing preference without carrying a
   counterfactual** — what the system would have done had the old belief stood
   (**CAPTURE**, arXiv:2609.02265).
4. MeClear's downstream-utility attribution is the principled forget rule, and
   it composes with C4: a gate whose parameters are plastic (C4) must record
   what a cleared memory *would have* gated.

**Grades.** Extinction `HIGH`. Fortunate Recall `LOW`. Design `UNTESTED`.

**Interaction.** Depends on C6. Constrained by C5 (a self-authored correction
needs an independent witness).

---

### C8 · Affect as a dimensional profile, not a scalar

**The idea.** Valence is at minimum two-dimensional: **wanting** and **liking**
are separate circuits, and their separation is a *failure mode*, not a curiosity.
Appraisal is multi-dimensional, and **the number of dimensions is not agreed
upon** — which is itself the finding, and must be preserved rather than
resolved.

**Brain part.**
- **Incentive salience** (Berridge & Robinson, *American Psychologist*, 2016) —
  the "wanting"/"liking" dissociation.
- **Appraisal dimensions** (Area 56) — the disagreement is load-bearing.
- **The amygdala's tag on memory traces** (Area 10) and its **dissociation from
  the declarative content** it tags.

**Already exists — built.** `brain/limbic/valence.py` carries valence −1.0…+1.0,
arousal 0.0–1.0, allostatic load, curiosity drive. Damasio somatic markers in
`somatic_markers`. **The current implementation is a scalar valence, which is
the thing the arena says is wrong.**

**Decision: CHANGE valence from a scalar to a profile. Keep the scalar as a
derived convenience field.**

**How to build.**
1. `cognitive_beliefs.credence` (the belief's probability) and the belief's
   *affective tag* (how much it matters, in what way, at what arousal) become
   **separate columns on separate tables.** They are currently conflated in
   spirit if not in schema.
2. At minimum two affect dimensions: **desire** (wanting) and **valence**
   (liking). Arousal is a **third, independent** axis — the arena records the
   **arousal–memory asymmetry across phases** (Area 57) as stated independently
   by both earning files, so arousal is not a scalar multiplier on memory
   strength.
3. **Record the dimension disagreement rather than resolving it.** EMA
   (Marsella & Gratch 2009) appraises along multiple dimensions; a 2-D and a
   6-D model both survive their sources. Store the appraisal vector *and* the
   model that produced it.
4. Affective tags attach to **relations**, not just nodes (PGMem).

**Already exists — named.** **PsychoAgent** (arXiv:2608.07438) for
affect-as-salience-over-memory. **EMA** for multi-dimensional appraisal.
**PGMem** (arXiv:2608.01708) for affect on typed edges.

**Grades.** Wanting/liking `HIGH` (one of the most replicated findings in
neuroscience). Arena's dimensional count `UNSUCCESSFUL`/`LOW` — genuinely
contested. Design `UNTESTED`.

**Interaction.** Feeds C4 (arousal is a gain modifier), C6 (affect as a
retention prior), C8↔C9 (affect competes for substrate).

---

### C9 · The substrate is a budget, and exhaustion has an order

**The idea.** Capacity is not uniform. Under substrate exhaustion the brain
sheds in a **specific order**, and a system that treats all capacity as
interchangeable will fail in the wrong order. Context is a budget whose
exhaustion failure is **paralysis, not slowness** — at the top of the range the
system stops choosing, which is a different bug from getting slow.

**Brain part.** The **metabolic-demand hierarchy of the CNS** and its
behavioural shadow; **long-term working memory** (Ericsson & Kintsch 1995) —
experts do not hold *more*, they hold **pointers**; and the cortex as **a stack
of time windows** (Area 91), which a flat context window gets wrong.

**Evidence.** `LOW` on the mechanism. The design transfer is `UNTESTED`.

**Already exists.** The Hermes stack's context window; nothing models the
*order* in which capacity is surrendered.

**Decision: ADD a budget model with a declared shedding order.**

**How to build.**
1. Declare the shedding order **explicitly and in writing**, because a design
   that works only because a human reads everything by hand is a habit, not a
   rule. Proposed order, from the hierarchy:
   1. **re-derived facts** (C6 can recompute them)
   2. **raw event traces** (C13 DMN already has a compression lane)
   3. **corroboration duplicates** (one source, counted once)
   4. **pointers** — never shed these; they are the experts' trick
   5. **load-bearing beliefs** — shed last, and log loudly when shed
2. When a turn approaches the ceiling, the system **narrows the action
   repertoire** (Area 22) rather than truncating context. Presenting a decision
   with the full action set at low capacity is the paralysis failure.
3. **The refusal to be scored is a failure mode.** A monitor that cannot fail
   (Area 125) and a controller that cannot act are the same defect:
   metacognitive coverage estimation is a **routing** signal, not a report.

**Grades.** Capacity hierarchy `LOW`→`HIGH` across sources. Design `UNTESTED`.

**Interaction.** Constrains C4 (gains need floors against exhaustion), C6
(eviction order), C13.

---

### C10 · Register, scope, and authorship on every claim

**The idea.** Every claim carries **(content_verdict, author_role, scope)**. A
statement made by a tool, retrieved from a file, inferred by the model, and
asserted by the user are not the same kind of statement, and the system should
never have to guess which.

**Brain part.** The supervisory and role-based architecture of the prefrontal
cortex.

**Already exists.**
- **Trajel** (arXiv:2605.24219), whose `h^S` category is the reference.
- **CAPTURE** (arXiv:2609.02265).
- **Ackerman** (arXiv:2603.26089) — mind-reading / mentalising and its distinct
  self-modelling, which is a *design constraint*, not a technique.
- **Decoupled approval** (Uesato et al., arXiv:2011.08827) — approval is a
  **different call** from execution, and the invariant run that grades the pass
  is a different process from the pass. This is C5 in the governance dimension.

**Decision: ADD a required scope/register field to every stored claim.**

**How to build.**
1. `authority: user_asserted | tool_observed | model_inferred | retrieved_quote`.
   A `retrieved_quote` may never be promoted to `user_asserted` by any path in
   the code. That single constraint prevents the most common class of
   self-flattering error in a memory system.
2. **Register is a field.** **No published system enforces a register field on a
   memory store** (the arena's own note, ORDER 1639) — the design is a
   composite, and that is why it is a genuine addition rather than an import.
3. Composes with C1: `authority` says who spoke; `trust` says whether to
   believe them. Neither implies the other.

**Grades.** Trajel `LOW`. Decoupled approval `LOW`. Design `UNTESTED`.

**Interaction.** Depends on C1, C2. Feeds C5 and C7.

---

### C11 · The read is a write: retrieval suppresses what you did not retrieve

**The idea.** Retrieving one thing **suppresses** the things you did not
retrieve. A memory's availability is not a property of the memory; it is a
property of the retrieval that did or did not happen. Consequently, a stored
memory is not the stored string — it is **the stored string read by the rules in
force when it was read.**

**Brain part.** Retrieval-induced forgetting; the **reafferent** comparator
applied to memory rather than to output.

**The load-bearing evidence — a gap, not a defect.** Corpus file ORDER 1649
records: *"No version indicator in Packed CBOR data items themselves"* → *"Silent
data corruption or hard failure."* The bytes are identical, **no event
occurred, the reader changed.** This is the only area in the arena whose trigger
is neither a write nor a retraction.

It is live, not hypothetical: `draft-ietf-cbor-packed-19` **expired 2026-08-06
with no draft-20**, and ORDER 1653 shows `dns+cbor;packed=0` and
`cbor;packed=0` **already meaning different things in two live drafts**, with
nothing in either record to distinguish them.

**Also relevant, and measured:** a pgvector retrieval that injects a stored
memory into a new task context is **a potential memory-modifying event**, and the
drift is measured, not hypothesised (arXiv:2605.12978). And **the read
suppresses the non-retrieved** (Area 93) — which is an argument *for* the graph
layer alongside semantic RAG, not against it: the two retrieve differently and
therefore suppress different things.

**Decision: CHANGE the memory store to record reader state, and treat retrieval
as a write event.**

**How to build.**
1. Every read records: which **rules version** was in force, what the reader
   believed, and what it did not retrieve. This makes the C6 unearned-citation
   class *structurally detectable* — you can ask what the reader knew, not
   merely whether a row is `[x]`.
2. `retrieval_log` (which already exists in the schema) gains a
   `suppressed_ids` field. What a retrieval *excluded* is evidence.
3. A memory's effective content is `content @ rules_version`. Storing only the
   string is storing half the thing.

**Grades.** Design `UNTESTED`. The IETF gap is `HIGH` (executed, both drafts
live). Retrieval-as-modification `LOW`.

**Interaction.** Deeply coupled to C1 (reafference), C4 (plastic gains mean the
reader changes), C12.

---

### C12 · Bi-temporal memory with mandatory provenance spans

**The idea.** A memory is not a value, it is a **value plus the interval during
which it was believed to be true, plus the spans of the source that produced
it.** Both matter and they are different work.

**Brain part.** Time cells and the hippocampal–neocortical reconsolidation loop;
the arena's broader position that **one event is not one timestamp** (Area 117).

**Evidence — and a hard negative on the mechanism.** Inverse effectiveness
(Stein & Meredith): multisensory gain is **largest when each input is weakest**.
That is `HIGH`, and it is stated independently by two earning files. It means a
system that binds events by exact timestamp coincidence is binding at the
**worst** point on the curve. This workspace makes four tool calls at four
latencies per pass and structurally cannot say whether the results are one
finding or four.

**Already exists — best in class, adopt.**
- **Zep / Graphiti** (arXiv:2501.13956) — bi-temporal episode↔entity substrate.
- **SodaMem** (arXiv:2608.08055) — typed FactEvents with **mandatory provenance
  spans**.
- **STAIR** (arXiv:2609.03874) — the hippocampus indexes by **structure**: parse
  the table of contents, section headers, hierarchy.
- **CS-RAG** (arXiv:2603.14828) — constraint planning, a sufficiency check before
  generating, and **textual recovery from the episode text when the graph path
  is absent**. Adopt the mechanism.
- **Procedural Graphs** (arXiv:2609.09153), **MemEvolve** (arXiv:2512.18746).

**Decision: ADOPT the bi-temporal substrate. CHANGE binding to a synchrony
window. DO NOT build a bespoke temporal layer.**

**How to build.**
1. Every memory row carries `valid_from`, `valid_to`, `recorded_at`,
   `superseded_at`, and a **non-null provenance span** pointing at character
   ranges in the source. A FactEvent with a null span is rejected at write time.
2. **Binding by synchrony window, not timestamp.** The window's width is a
   function of the weakest input's reliability (inverse effectiveness), not a
   constant. This is the concrete form of C12's evidence.
3. **The graph is not a replacement for reading source** — this is a standing
   constraint from the corpus and a design rule of this document. CS-RAG's
   *textual recovery when the graph path is absent* is the required fallback, not
   an optimization: a graph edge that cannot be traced to a span is not an edge,
   it is a guess.
4. Retain BM25 + vector + RRF over chunks. Three independent negatives constrain
   the alternatives: **Parametric KG Memory** (arXiv:2608.25489),
   **Hidden-state k-NN** (CoAct, arXiv:2604.17501, itself qualified by
   arXiv:2605.00269), and the **Hallucination Snowball** (arXiv:2608.14588).

**Grades.** Inverse effectiveness `HIGH`. Zep/SodaMem `LOW`. Binding-window
design `UNTESTED`. Graph-vs-vector: three recorded negatives, `UNSUCCESSFUL`
for the parametric route.

**Interaction.** Depends on C1 (provenance spans are the substrate C1's witnesses
write into), C6, C11.

---

### C13 · The DMN lane: counterfactual, prospective, and internal simulation

**The idea.** Internal simulation runs **only when nothing is being asked**, on a
schedule, and it is mutually exclusive with external orientation. The brain
switches between the default mode and the task-positive network **within a
fraction of a second** after a task ends.

**Brain part.** **DMN ↔ task-positive anticorrelation**; **chronesthesia**
(mental time travel, retrospection and prospection); the **fictive error
signal** — the difference between the best return that *could have been* and the
actual return, correlated with caudate and posterior parietal (IPS2) BOLD on a
live task (Lohrenz, McCabe, Camerer & Montague, *PNAS* 2007).

**Already exists — built.** `brain/dmn/chronesthesia.py` and
`counterfactual.py`; `counterfactual_rollouts` table. Area 94 is the strongest
area in the set: **memory belongs to the planner, not the executor** — the
ablation says feeding retrieval to the wrong module makes things *worse*. **3
independent sources.**

**Decision: KEEP and STRENGTHEN. The single best-evidenced area in the arena.**

**How to build.**
1. Enforce the **mutual exclusion**. The DMN lane runs when the task lane is
   idle. Concurrent DMN + task-positive is the pathology, not the feature.
2. Counterfactuals require an explicit counterfactual block: *what would have
   been done under the retracted belief, and what was actually done.* The
   existing `counterfactual_rollouts` table has the columns; the discipline is
   the missing part.
3. **Regret is a verifier lane**, not a reward signal. A self-graded regret
   score violates C5 outright. Route it to an independent evaluator.
4. Area 48's **`self-attributional` layer** is uncovered: no RL term carries
   "this outcome was mine rather than the world's." Record as `not observed`.

**Grades.** Anticorrelation `HIGH`. Fictive error signal `HIGH`. Area 94 `LOW`
with 3 independent sources. The self-attribution gap `UNTESTED`.

**Interaction.** Depends on C7 (needs a counterfactual after a correction).
Constrains C9 (DMN competes for substrate).

---

### C14 · Prospective memory: the self-reminder channel, and belief-to-action compliance

**The idea.** Two components. **Prospective memory** — remembering to *do*, which
is a different system from remembering *that*. And **the enforcement gap**: a
belief is not an action, and the system that holds a correct belief and does not
act on it is not reasoning badly, it is **not enforcing**.

**Brain part.** Prospective memory proper (Area 4); the declarative–procedural
interface addressed at the action boundary (Area 19).

**Area 19 is the best-evidenced slot in the entire arena.** That is a strong
claim and it is the arena's own.

**Already exists — built.** `brain/prospective/intentions.py`; the
`brain-cognitive-guard` hook on `agent:end`; `intentions` table in
`organizer.db`; the `Personal State Reminders` cron (`check_reminders.py`,
every 15 min, no_agent). The arena's verdict: **built, and the hook writes into
a schema this arena confirmed.**

**Decision: KEEP. ADD the enforcement layer.**

**How to build.**
1. Three commitments, and **the third is the whole design**: a stated intention,
  a trigger, and — the missing one — **a verification that the action actually
  occurred.** A prospective memory that fires and is never checked is a
  notification, not a memory. The cron currently delivers; nothing confirms.
2. **The enforcement gap is measurable.** Every `intentions` row past its due
   time without a completion event is an un-enforced intention. That number is
   the metric, and it is currently invisible.
3. `Superstition`-proofing rule (Area 60): **most adult behaviour is
   rule-governed**, by a verbal rule describing a contingency rather than by
   contact with the contingency. No component in the stack carries rule
   provenance. A rule learned without its grounding must be marked as such,
   because a system that cannot tell a grounded rule from a floating one will
   confidently follow the floating one.

**Already exists — named.** **MemLineage**-class lineage, **TRACE**
(arXiv:2606.13174) for enforcement layers, **decoupled approval**
(arXiv:2011.08827) for approval ≠ execution, **Agent-Sentry**
(arXiv:2603.22868) for the sensitive-action gate at the inhibition/action
boundary.

**Grades.** Prospective memory `HIGH` as a phenomenon. Area 19 enforcement
`LOW`→ best-evidenced slot. Rule provenance `UNTESTED`.

**Interaction.** Depends on C7 (enforcement after correction). Feeds C13
(fulfilled intentions become counterfactual material).

---

## 3. Part II — How it all works together

### 3.1 The turn lifecycle

```
                    ┌─────────────────────────────────────────┐
   USER INPUT ────► │ C2  thalamus: buffer + saliency admit     │
                    │ C3  split streams: dorsal / ventral       │
                    └──────────────┬──────────────────────────┘
                                   ▼
                    ┌─────────────────────────────────────────┐
                    │ C7  fast writer  (System 1, synchronous)  │
                    │     retrieve → propose → ACT              │
                    │     writes carry C2 efference + C10 scope │
                    └──────────────┬──────────────────────────┘
                                   ▼
                    ┌─────────────────────────────────────────┐
                    │ C8  affect tags the trace, not the fact   │
                    │ C4  gate thresholds are PLASTIC gains     │
                    │     (arousal, PE, substrate → go/no-go)    │
                    └──────────────┬──────────────────────────┘
                                   ▼
              ┌────────────────────────────────────────────────┐
              │ C1  THE TRUST GATE — two fields, two witnesses   │
              │                                                │
              │   provenance (who)      trust (whether)         │
              │   ───────────────────   ────────────────────     │
              │   in-band attestation   INDEPENDENT witness     │
              │   SLSA/Sigstore/in-toto  scanner/human/OOB hash │
              │   cheap, always there   must fail differently   │
              │                                                │
              │   C5  no shared witness. No self-grading.        │
              │   Missing trust field  =  HARD FAIL              │
              └──────────────┬──────────────────────────┘
                                   ▼
                    ┌─────────────────────────────────────────┐
                    │ C14 belief → action compliance check      │
                    │ C10 register/scope on every emitted claim  │
                    └──────────────┬──────────────────────────┘
                                   ▼
                    ┌─────────────────────────────────────────┐
                    │ C12  write memory: bi-temporal + span +   │
                    │      supersession relation (C7)            │
                    │ C11  log reader state + suppressed set     │
                    │ C9   charge the budget, shed in ORDER      │
                    └──────────────┬──────────────────────────┘
                                   ▼
                    ┌─────────────────────────────────────────┐
                    │ C6  slow ablater (System 2, async)         │
                    │     reachability invalidation, no deletes  │
                    │     consolidation on schedule (SCM)         │
                    │     C13 DMN lane: counterfactual, regret   │
                    └─────────────────────────────────────────┘
```

### 3.2 The three load-bearing couplings

Most of the value is not in the individual components but in three couplings
the arena insists on:

1. **C1 ⇄ C5.** If the provenance witness and the trust witness share a
   process, a credential, or a runner, the system is self-grading. Mini Shai-Hulud
   is what that looks like in production: everything attested correctly,
   everything malware.

2. **C4 ⇄ C9 ⇄ C11.** The gains are plastic *because* the substrate is finite,
   and *because* the reader changes, a memory read under different rules is a
   different memory. These three must be designed together or C4 produces
   instability with no accounting.

3. **C6 ⇄ C7 ⇄ C14.** A retracted belief must invalidate its dependents (C6),
   record a supersession relation rather than an overwrite (C7), and produce a
   counterfactual for the intention it had already committed to (C14). Break any
   link and the system confidently acts on a withdrawn belief.

### 3.3 What is *not* proposed

- **Not a new retrieval stack.** BM25 + pgvector + RRF survives, with three
  recorded negatives against the alternatives.
- **Not a replacement for the graph layer by RAG or vice versa.** The graph is
  an associative-traversal view *alongside* semantic retrieval. They suppress
  different things (C11) and that is the reason to keep both.
- **Not a memory system that deletes.** Append-only, ever.
- **Not self-measurement as decision evidence** (R-J2 from `SCRATCHPAD.md`).
- **Not a claim that a missing brain part is unnecessary.** `not observed`.

---

## 4. Part III — What to ADD, what to CHANGE, what to KEEP

### 4.1 KEEP — the arena confirms the existing skeleton

This is the most common finding in 128 areas and it is worth stating plainly:
**the current structure is largely right.**

| Component | Current | Verdict |
|---|---|---|
| AGM belief revision | `brain/epistemology/agm.py` | Confirmed. Add persistence of dependency (C6). |
| Dual-process routing | `brain/cortex/router.py` + `dl_pfc.py` | Confirmed — **the most convergent design in the arena.** Make the threshold plastic (C4). |
| Prospective memory | `brain/prospective/intentions.py` + `agent:end` hook | Confirmed built. Add enforcement (C14). |
| Speech channel | container `speech-to-speech` on the local host | Confirmed built. |
| Consolidation | `brain-memory-consolidator` hook + `replay.py` | Confirmed — three independent implementations now include this one. |
| ToM | `brain/social/tom.py` | Confirmed. Widen to C3's split. |
| Working memory | 7 slots, decay | Confirmed shape. Re-spec as a *budget* (C9). |
| `citation_remediation.py` | one script | **The only component in the stack doing real verification.** It is the template for C5. |

### 4.2 CHANGE — existing code, different contract

| What | From | To | Why |
|---|---|---|---|
| `go_threshold` | `0.4` constant | function of PE, arousal, headroom | C4 |
| `compilation_threshold` | count `3` | BCM sliding θ_M | C4 |
| `epistemic_state` | one enum | `replaced`/`narrowed`/`contradicted`/`expired` | C7 |
| `credence` | scalar | separated from an affective profile | C8 |
| `DECISION_CONFIDENCE_THRESHOLD` | `0.60` scalar | four-channel, dorsal/ventral split | C3, C9 |
| `provenance` | one field | `provenance` + `trust`, different witnesses | C1 |
| Memory read | returns a value | returns value + reader state + suppressed set | C11 |
| Memory write | inserts a row | bi-temporal + non-null provenance span | C12 |
| `assumption_set` | **absent** | required on every derived row | C6 |
| 7 working-memory slots | fixed | a budget with a declared shedding order | C9 |

### 4.3 ADD — components that do not exist

| # | Add | Grounded in |
|---|---|---|
| 1 | `trust` field + independent-witness registry | C1, C5 |
| 2 | Assumption-set propagation on every derived row | C6, MemLineage |
| 3 | Reader-state and suppressed-set logging | C11 |
| 4 | Four-channel uncertainty | C9, Area 75 |
| 5 | Plastic gain registry (every parameter, its trigger, its bounds) | C4 |
| 6 | Verifier independence declaration + red-team calendar | C5, Mackworth |
| 7 | Register/scope field on every claim | C10 |
| 8 | Budget shedding order, declared | C9 |
| 9 | Enforced intention verification (did it happen?) | C14 |
| 10 | Rule-provenance field (grounded vs floating) | Area 60 |

### 4.4 ADOPT — do not build

| Adopt | For | Note |
|---|---|---|
| **MemLineage** (arXiv:2605.14421) | Provenance propagation | Theorem 1 is the operation we need |
| **MemTX** (arXiv:2607.23929) | Transactional memory state | Strongest evidence in the arena |
| **SLSA / Sigstore / in-toto / Rekor** | `provenance` field | Already correct; never asked the safety question |
| **Zep / Graphiti** (arXiv:2501.13956) | Bi-temporal substrate | |
| **SodaMem** (arXiv:2608.08055) | Typed FactEvents + mandatory spans | |
| **CS-RAG** (arXiv:2603.14828) | Constraint planning + textual fallback | |
| ~~**HybridAL**~~ (arXiv:2609.06806) | Consolidation switch policy | **STRUCK 2026-09-27** — arXiv:2609.06806 is *Train Smarter, Not Harder: Switching Signal-Guided Training in Active Learning*. Not HybridAL, and not about memory. See §9.4 |
| **SCM** (arXiv:2604.20943) | Sleep-consolidated forgetting | **Replaces the struck HybridAL row.** Verified title: *SCM: Sleep-Consolidated Memory with Algorithmic Forgetting* |
| **SYNAPSE** (arXiv:2601.02744) | FOK protocol, τ=0.12 | Verified: *SYNAPSE: Episodic-Semantic Memory via Spreading Activation* |
| **PyHGF** (Legrand et al.) | Self-diagnosis by parameter recovery | Fit a generative model to your own behaviour, read the parameters back |
| **MeClear** (arXiv:2609.09115) | Forget by downstream utility | |
| **STAIR** (arXiv:2609.03874) | Structure-aware indexing | |
| **PGMem** (arXiv:2608.01708) | Affect on typed edges | |
| **TRACE** (arXiv:2606.13174) | Enforcement layer | |
| **Agent-Sentry** (arXiv:2603.22868) | Sensitive-action gate | |
| **IMGEP** (Forestier et al., *JMLR* 23(152), 2022) + AMB variant | Intrinsic motivation | "The strongest existing thing in the arena" — why it ranks 1 rather than being dismissed as research |
| **Mem0 / Cognee** | Vector-first pattern | The pattern is not bespoke; pgvector is already in the stack |

### 4.5 REJECT — recorded so it is not rebuilt blind

| Reject | Why |
|---|---|
| **Parametric KG memory** | arXiv:2608.25489 (*A Storage-Retrieval Gap in Parametric Knowledge Graph Memory*) — a real negative. **The second leg is struck**: arXiv:2605.10619 is particle physics, not memory. One independent negative, not two. Grade drops accordingly |
| **Hidden-state k-NN** | CoAct (arXiv:2604.17501, verified) qualified by arXiv:2605.00269 (*Two-Pathway Framework*, verified) — both real. **Caveat:** arXiv:2605.00269's title does not name CoAct, so the "qualifies CoAct" relationship is the arena's claim and is unverified |
| ~~**Component placement as the variable**~~ | **STRUCK 2026-09-27** — arXiv:2606.04194 is *Training-Free Lexical-Dense Fusion for Conversational-Memory Retrieval*, a method paper, not a negative result. The `UNSUCCESSFUL` record has no source |
| **Sleep-consolidated forgetting** (replaces the row above) | arXiv:2604.20943 (*SCM: Sleep-Consolidated Memory with Algorithmic Forgetting*) proposes it. **Note the reversal:** the arena cast this as a *negative* against REM-style edge inference; the verified title describes a *positive* architecture. The claim is unsupported either way |
| **Any 2-pass certifier** | Verification has a ceiling above NP and it is not closed by a better detector (Area 76). **This row rests on the arena's own reasoning, not on a citation** — it is the only REJECT row with no paper attached |

---

## 5. Known risks in this proposal

Stated as risks, not caveats, because three of them are load-bearing.

1. **C4 could destabilise the system.** Plastic gains with no floor produce
   oscillation. This is the highest-risk change to existing code and the one
   that most needs the red-team calendar of C5 before it ships.
2. **C3 makes the system report worse numbers.** Splitting dorsal from ventral
   means the report will sometimes disagree with the action. That will look like
   a regression in every dashboard. It is the correct behaviour and it will
   still be uncomfortable.
3. **Every design here is `UNTESTED`.** The biology is well-graded; the builds
   are not. Nothing in this document has been run at 14,589-file scale.
4. **388 files are unread.** The cursor is in DNS-CBOR. Areas 119–121 and 124
   are absent from the heading list and 16 areas are `PROVISIONAL`. Expect
   re-ranking.
5. **The answer file is accreting.** `ARENA.md` carries stacked tranche-52, -58
   and -63 status blocks at the top. C11 passes only because budget remains.
   The end file must consolidate these into `ARENA-EVIDENCE.md` first — the
   arena flags this itself and correctly declines to delete unread material.
6. **C6 is failing right now, live.** 6 unearned citations, all AMBIGUOUS
   ontology twins. `MUST RE-READ` is 0, so remediation is converging — but the
   same machinery that produced 39 of them is still running.

---

## 6. What would change this document

Stated in advance so the read can falsify it rather than confirm it.

- A remaining file that supplies a **published propagation theorem** stronger
  than MemLineage's → C6 becomes an import instead of a schema change.
- A remaining file showing **plastic gates fail** in an agentic setting →
  C4 is downgraded to a bounded variant.
- A remaining file establishing that **a single checker may satisfy both
  provenance and trust** → C1 collapses and the deepest finding in this
  document evaporates. This is the one to watch.
- A remaining file on **reality monitoring** (deferred at ORDER 1659, where the
  arena held 0 occurrences of *reality monitoring* and *unsupported by*) →
  opens a new area, `not observed` until then.

---

## 7. Binding rules in force

From `SCRATCHPAD.md`, applying to every recommendation above:

- **R-J1** — cost is irrelevant as a decision criterion. No recommendation here
  is justified by being cheap or expensive.
- **R-J2** — no self-measurement as decision evidence. This is C5, and it is
  the rule the arena has most often caught itself breaking.
- **R-J3** — scope is the repository's future.
- **R-J4** — external research *and* the local vault; preserve disagreements.
  Where the two conflict (Area 6's ablation vs Area 41's mediation claim;
  CoAct vs arXiv:2605.00269) the conflict is recorded, not resolved.
- **R-J5** — recommendations must hold at **14,589 files**. A rule that works
  only because a human reads every file by hand is a habit, not a rule.

---

## 8. Files referenced

- `cognition-arena/ARENA.md` — 128 areas, the ranked answer (tranche 70)
- `cognition-arena/ARENA-EVIDENCE.md` — append-only audit trail, 21,137 lines
- `cognition-arena/ARENA-INFRA.md` — corpus-hygiene requirements
- `cognition-arena/VERIFICATION.md` — unverified claims and proposals
- `cognition-arena/LEDGER.md` — the cursor; 1,406 read / 388 remaining
- `cognition-arena/RUNLOG.jsonl` — machine-readable per-run record
- `cognition-arena/ORDER.txt` — 2,217 corpus paths, the sole authority
- `PROPOSED-BRAIN-ARCHITECTURE.md` — **the design of record; unchanged by this
  document**
- `SCRATCHPAD.md` — the binding rules above

---

## 9. Citation index

Every entry below is cited by `ARENA.md` and was read as a corpus file in this
workspace. **None was fetched from arXiv.** Per §1, treat the *contents* as
`unverified` until the primary is read; the *existence* is asserted by the
corpus.

### 9.1 Systems and papers — existence VERIFIED against arXiv (2026-09-27)

Every row was fetched from `arxiv.org/abs/` on 2026-09-27 and its real title read
back. **All 86 exist.** The verified title is recorded beside each link so any
reader can check the attribution without opening the PDF.

**Existence verified is not the same as the claim verified.** What each paper
actually says still requires reading it (§1). **Seven citations are contradicted
at title level** — the real paper is in a different field from the claim — and
those are listed in §9.4. **They carry no weight in this document.**

| Ref (live link) | Real title, verified at arXiv | Component |
|---|---|---|
| [2605.14421](https://arxiv.org/abs/2605.14421) | MemLineage: Lineage-Guided Enforcement for LLM Agent Memory | C6 |
| [2607.23929](https://arxiv.org/abs/2607.23929) | MemTX: Transactional Belief Commit for Stateful Agent Memory | C6 |
| [2501.13956](https://arxiv.org/abs/2501.13956) | Zep: A Temporal Knowledge Graph Architecture for Agent Memory | C12 |
| [2608.08055](https://arxiv.org/abs/2608.08055) | SodaMem: Evidence-Grounded Temporal Graph Memory for LLM Agents | C12 |
| [2603.14828](https://arxiv.org/abs/2603.14828) | Toward Robust GraphRAG: Mitigating Retrieval Drift and Hallucination from Imperfect Knowledge  | C12 |
| [2609.06806](https://arxiv.org/abs/2609.06806) ⚠️ | Train Smarter, Not Harder: Switching Signal-Guided Training in Active Learning | C6, C13 |
| [2601.02744](https://arxiv.org/abs/2601.02744) | SYNAPSE: Empowering LLM Agents with Episodic-Semantic Memory via Spreading Activation | C6 |
| [2609.09115](https://arxiv.org/abs/2609.09115) | MeClear: Cooperative Game-Theoretic Attribution and Risk-Aware Memory Clearance for Long-Horiz | C7 |
| [2609.03874](https://arxiv.org/abs/2609.03874) | STAIR (STructure Aware Information Retriever): A novel dataset and LLM based retriever for doc | C12 |
| [2608.01708](https://arxiv.org/abs/2608.01708) | PGMem: Tightly Coupled Persona-Memory Graph for Lifelong Personalized Agents | C7, C8 |
| [2606.13174](https://arxiv.org/abs/2606.13174) | Getting Better at Working With You: Compiling User Corrections into Runtime Enforcement for Co | C14 |
| [2603.22868](https://arxiv.org/abs/2603.22868) | Agent-Sentry: Bounding LLM Agents via Execution Provenance | C14 |
| [2609.10413](https://arxiv.org/abs/2609.10413) | Fortunate Recall: Ontology-Driven Memory Lifecycle Management for Persistent Coherence in LLMs | C7 |
| [2609.02265](https://arxiv.org/abs/2609.02265) | CAPTURE: Disentangling Preference Drift from Memory Poisoning in Personalized LLM Agents | C7, C10 |
| [2605.24219](https://arxiv.org/abs/2605.24219) | Beyond Final Answers: Auditing Trajectory-Level Hallucinations in Multi-Agent Industrial Workf | C10 |
| [2608.07438](https://arxiv.org/abs/2608.07438) | PsychoAgent: An Affect-Sensitive Cognitive Architecture for Conflict-Aware Memory in LLM Agent | C8 |
| [2512.06393](https://arxiv.org/abs/2512.06393) | Conflict-Aware Fusion: Mitigating Logic Inertia in Large Language Models via Structured Cognit | C10 |
| [2011.08827](https://arxiv.org/abs/2011.08827) | Avoiding Tampering Incentives in Deep RL via Decoupled Approval | C5, C14 |
| [1908.04734](https://arxiv.org/abs/1908.04734) | Reward Tampering Problems and Solutions in Reinforcement Learning: A Causal Influence Diagram  | C14 |
| [2207.05221](https://arxiv.org/abs/2207.05221) | Language Models (Mostly) Know What They Know | C5 |
| [2410.20268](https://arxiv.org/abs/2410.20268) | Centaur: a foundation model of human cognition | C3 |
| [2511.00206](https://arxiv.org/abs/2511.00206) | Addressing Longstanding Challenges in Cognitive Science with Language Models | C3 |
| [2511.16660](https://arxiv.org/abs/2511.16660) | Cognitive Foundations for Reasoning and Their Manifestation in LLMs | C5 |
| [2603.04740](https://arxiv.org/abs/2603.04740) | Memory as Ontology: A Constitutional Memory Architecture for Persistent Digital Citizens | C1, C10 |
| [2608.00017](https://arxiv.org/abs/2608.00017) | Memory Reward Inflation in Self-Improving LLM Agents | **C5** |
| [2606.14512](https://arxiv.org/abs/2606.14512) ⚠️ | Fodor and Pylyshyn's Systematicity Challenge Still Stands | **C3** |
| [2603.26089](https://arxiv.org/abs/2603.26089) | Selective Deficits in LLM Mental Self-Modeling in a Behavior-Based Test of Theory of Mind | C10 |
| [2509.22887](https://arxiv.org/abs/2509.22887) | Infusing Theory of Mind into Socially Intelligent LLM Agents | C3 |
| [2608.26291](https://arxiv.org/abs/2608.26291) | Assessing mentalization in humans and large language models | C3 |
| [2603.23848](https://arxiv.org/abs/2603.23848) | BeliefShift: Benchmarking Temporal Belief Consistency and Opinion Drift in LLM Agents | C7 |
| [2608.28978](https://arxiv.org/abs/2608.28978) | Selective Forgetting: A Graph-Based Memory Framework for Long-Term LLM Agents | C12 |
| [2605.12978](https://arxiv.org/abs/2605.12978) | Useful Memories Become Faulty When Continuously Updated by LLMs | C11 |
| [2605.10619](https://arxiv.org/abs/2605.10619) ⚠️ | Study of $\eta^\prime \to \eta \pi\pi $ Decays in Large-$N_C$ Chiral Perturbation Theory | reject |
| [2608.25489](https://arxiv.org/abs/2608.25489) | A Storage-Retrieval Gap in Parametric Knowledge Graph Memory | reject |
| [2604.17501](https://arxiv.org/abs/2604.17501) | CoAct: Co-Active LLM Preference Learning with Human-AI Synergy | reject |
| [2605.00269](https://arxiv.org/abs/2605.00269) | How Language Models Process Out-of-Distribution Inputs: A Two-Pathway Framework | reject |
| [2604.20943](https://arxiv.org/abs/2604.20943) ⚠️ | SCM: Sleep-Consolidated Memory with Algorithmic Forgetting for Large Language Models | reject (narrow) |
| [2606.04194](https://arxiv.org/abs/2606.04194) ⚠️ | Training-Free Lexical-Dense Fusion for Conversational-Memory Retrieval | reject |
| [2608.14588](https://arxiv.org/abs/2608.14588) | The Hallucination Snowball: Modeling Error Propagation as State Transitions in Multi-Agent LLM | C12 |
| [2512.18746](https://arxiv.org/abs/2512.18746) | MemEvolve: Meta-Evolution of Agent Memory Systems | C6 |
| [2609.09153](https://arxiv.org/abs/2609.09153) | Procedural Graphs: Self-Evolving Execution Structures for LLM Agents | C12 |
| [2605.13438](https://arxiv.org/abs/2605.13438) | CogniFold: Always-On Proactive Memory via Cognitive Folding | C7 |
| [2607.16201](https://arxiv.org/abs/2607.16201) | Generative Ontology Induction: Domain-Agnostic Schema Discovery from Document Corpora Using La | C12 |
| [2607.18077](https://arxiv.org/abs/2607.18077) ⚠️ | Generalised Bellman recurrence and three dualities in sequential decision-making | C12 |
| [2603.19595](https://arxiv.org/abs/2603.19595) | All-Mem: Agentic Lifelong Memory via Dynamic Topology Evolution | C12 |
| [2603.17244](https://arxiv.org/abs/2603.17244) | Graph-Native Cognitive Memory for AI Agents: Formal Belief Revision Semantics for Versioned Me | C6 |
| [2604.15877](https://arxiv.org/abs/2604.15877) | Experience Compression Spectrum: Unifying Memory, Skills, and Rules in LLM Agents | C9 |
| [2603.14517](https://arxiv.org/abs/2603.14517) | Learning to Forget: Sleep-Inspired Memory Consolidation for Resolving Proactive Interference i | C6, C9 |
| [2604.04514](https://arxiv.org/abs/2604.04514) | SuperLocalMemory V3.3: The Living Brain -- Biologically-Inspired Forgetting, Cognitive Quantiz | C6 |
| [2605.17625](https://arxiv.org/abs/2605.17625) | Episodic-Semantic Memory Architecture for Long-Horizon Scientific Agents | C12 |
| [2608.00452](https://arxiv.org/abs/2608.00452) | CeQe: Grounding Lexical Retrieval in Semantic Evidence | C12 |
| [2507.05257](https://arxiv.org/abs/2507.05257) | Evaluating Memory in LLM Agents via Incremental Multi-Turn Interactions | C14 |
| [2507.01352](https://arxiv.org/abs/2507.01352) | Skywork-Reward-V2: Scaling Preference Data Curation via Human-AI Synergy | C8 |
| [2505.09316](https://arxiv.org/abs/2505.09316) | Scent of Knowledge: Optimizing Search-Enhanced Reasoning with Information Foraging | C5 |
| [2505.18351](https://arxiv.org/abs/2505.18351) | Persona Alchemy: Designing, Evaluating, and Implementing Psychologically-Grounded LLM Agents f | C10 |
| [2502.13025](https://arxiv.org/abs/2502.13025) | Agentic Deep Graph Reasoning Yields Self-Organizing Knowledge Networks | C13 |
| [2602.05636](https://arxiv.org/abs/2602.05636) | Generative Ontology: When Structured Knowledge Learns to Create | C12 |
| [2512.12260](https://arxiv.org/abs/2512.12260) | A Multi-Axial Mindset for Ontology Design Lessons from Wikidata's Polyhierarchical Structure | C12 |
| [2604.08064](https://arxiv.org/abs/2604.08064) | ImplicitMemBench: Measuring Unconscious Behavioral Adaptation in Large Language Models | C14 |
| [2604.27927](https://arxiv.org/abs/2604.27927) | Taming the Centaur(s) with LAPITHS: a framework for a theoretically grounded interpretation of | C5 |
| [2605.21384](https://arxiv.org/abs/2605.21384) | SpecBench: Measuring Reward Hacking in Long-Horizon Coding Agents | C5 |
| [2502.08235](https://arxiv.org/abs/2502.08235) | The Danger of Overthinking: Examining the Reasoning-Action Dilemma in Agentic Tasks | C9 |
| [2601.06158](https://arxiv.org/abs/2601.06158) | PsyAgent: Constructing Human-like Agents Based on Psychological Modeling and Contextual Intera | C10 |
| [2606.29279](https://arxiv.org/abs/2606.29279) | Manufactured Confidence: How Memory Consolidation Turns Hearsay into Confident Facts | C10 |
| [2604.10833](https://arxiv.org/abs/2604.10833) | Speaking to No One: Ontological Dissonance and the Double Bind of Conversational AI | C10 |
| [2512.11818](https://arxiv.org/abs/2512.11818) | The Ontological Dissonance Hypothesis: AI-Triggered Delusional Ideation as Folie a Deux Techno | C10 |
| [2604.13602](https://arxiv.org/abs/2604.13602) | Reward Hacking in the Era of Large Models: Mechanisms, Emergent Misalignment, Challenges | C5 |
| [2507.05619](https://arxiv.org/abs/2507.05619) | Detecting Proxy Gaming in RL and LLM Alignment via Evaluator Stress Tests | C5 |
| [2512.14801](https://arxiv.org/abs/2512.14801) ⚠️ | Incentives or Ontology? A Structural Rebuttal to OpenAI's Hallucination Thesis | C7 |
| [2512.00418](https://arxiv.org/abs/2512.00418) | Significant Other AI: Identity, Memory, and Emotional Regulation as Long-Term Relational Intel | C8 |
| [2607.00006](https://arxiv.org/abs/2607.00006) | Persona Without Substrate: Regime-Dependence and the LLM Individuation Problem | C10 |
| [2510.16039](https://arxiv.org/abs/2510.16039) | Vector Quantization in the Brain: Grid-like Codes in World Models | C12 |
| [2602.18896](https://arxiv.org/abs/2602.18896) | Beyond Stationarity: Rethinking Codebook Collapse in Vector Quantization | C12 |
| [2602.19320](https://arxiv.org/abs/2602.19320) | Anatomy of Agentic Memory: Taxonomy and Empirical Analysis of Evaluation and System Limitation | C12 |
| [2608.05224](https://arxiv.org/abs/2608.05224) | Small Foundation Models of Human Cognition and Behaviour | C9 |
| [2608.11654](https://arxiv.org/abs/2608.11654) | Towards a Formal Definition of Agent Memory: Basis, Span, Optimality, and the Sequential Memor | C12 |
| [2608.26386](https://arxiv.org/abs/2608.26386) | Co-Evolving Structured Knowledge and Reasoning in Language Models | C5 |
| [2608.01679](https://arxiv.org/abs/2608.01679) | When Memory Becomes Authority: Benchmarking Authority Collapse at the Memory Consolidation Bou | C10 |
| [2606.09483](https://arxiv.org/abs/2606.09483) | Memory Beyond Recall: A Dual-Process Cognitive Memory System for Self-Evolving LLM Agents | C6 |
| [2305.10250](https://arxiv.org/abs/2305.10250) | MemoryBank: Enhancing Large Language Models with Long-Term Memory | C6 |
| [2406.04452](https://arxiv.org/abs/2406.04452) | Revisiting Human Information Foraging: Adaptations for LLM-based Chatbots | **C1** |
| [2411.16550](https://arxiv.org/abs/2411.16550) | Representation Collapsing Problems in Vector Quantization | C8 |
| [2412.10958](https://arxiv.org/abs/2412.10958) | SoftVQ-VAE: Efficient 1-Dimensional Continuous Tokenizer | C8 |
| [2503.24110](https://arxiv.org/abs/2503.24110) | Grounding Agent Reasoning in Image Schemas: A Neurosymbolic Approach to Embodied Cognition | C10 |
| [1011.4188](https://arxiv.org/abs/1011.4188) | Rescaling, thinning or complementing? On goodness-of-fit procedures for point process models a | C9 |
| [1604.01125](https://arxiv.org/abs/1604.01125) | Measuring burstiness for finite event sequences | C9 |

### 9.2 Foundational neuroscience (`HIGH` grade, not in arXiv)

- **Mackworth (1943)** — vigilance decrement; performance feedback eliminates it,
  instruction to try harder does nothing. *C5.*
- **Stein & Meredith** — inverse effectiveness; multisensory gain is largest when
  each input is weakest. *C12.*
- **Bienenstock, Cooper & Munro (1982)**, *J. Neurosci.* 2(1):32–48 — BCM
  metaplasticity, sliding θ_M. *C4.*
- **Schultz, Dayan & Montague (1997)** — reward prediction error. *C4, C5.*
- **Doyle (1979)** TMS; **de Kleer (1986)** ATMS — assumption sets, belief
  retraction. *C6.*
- **Berridge & Robinson (2016)**, *American Psychologist* — wanting/liking
  dissociation. *C8.*
- **Goodale & Milner (1991)** — dorsal/ventral dissociation; patient D.F. *C3.*
- **Ericsson & Kintsch (1995)** — experts hold pointers, not more. *C9.*
- **Borbély (1982)** — two-process model of sleep regulation. *C9.*
- **Salthouse (1996)**, *Psych. Review* — processing speed as a mediation claim;
  Hasher & Zacks (1988) preserved as a live dispute. *C9.*
- **Charnov (1976)** Marginal Value Theorem; **Pirolli & Card (1999)**,
  *Psych. Rev.* 106:643–675, Information Foraging. *C7.*
- **Larkum, Zhu & Sakmann (1999)** — BAC firing; coincidence detection and veto.
  *C5.*
- **Lohrenz, McCabe, Camerer & Montague (2007)**, *PNAS* — fictive error signal,
  caudate/IPS2. *C13.*
- **Gershman, Pesaran & Daw (2011)**, *J. Neurosci.* 31(14) — rational
  attribution in the brain. *C7.*
- **Marr (1982)** — three levels of analysis. *C9.*
- **Oliva & Torralba** — scene categorization, spatial envelope scrambling.
  *C9.*
- **Warren (1984)** — affordances are relational; climbability is a ratio. *C16.*
- **McClelland, McNaughton & O'Reilly (1995)** — complementary learning systems.
  *C6, C13.*
- **Sutton, Smith & Barto** / **Schmidhuber** — eligibility traces. *C8.*
- **Gross (1998)** — process model of emotion regulation. *C8.*
- **Okamoto, Matsumoto & Ikeda (2012)**, *Curr. Opin. Neurobiol.* — exploration
  by random walk on θ_M. *C4.*
- **Ohlsson (1992)**; **Knoblich et al.** — representational change, functional
  fixedness. *C9.*
- **Popper** — falsification as discipline. *C5.*
- **Anna Freud (1936)** — defence mechanisms. *C5.*
- **Skinner** — rule-governed behaviour. *C14.*
- **Forestier et al. (2022)**, *JMLR* 23(152) — **IMGEP** + AMB. *C31/intrinsic
  motivation.*
- **Legrand et al.** — **PyHGF**, Hierarchical Gaussian Filtering. *C44.*
- **Goodman, Goodman & Price**; **Breznitz & Reingold** — retrieval practice,
  spacing. *C6.*

### 9.3 Executed incidents (the only `HIGH`-grade design evidence in the set)

- **Mini Shai-Hulud (May 2026)** — 84 npm packages, 42 `@tanstack` packages, all
  carrying valid SLSA L3 attestations, all malware. *C1.*
- **`draft-ietf-cbor-packed-19` expired 2026-08-06** with no draft-20; ORDER 1653
  shows `dns+cbor;packed=0` and `cbor;packed=0` already meaning different things
  in two live drafts. *C11.*


---

### 9.4 Citations contradicted at title level — struck 2026-09-27

These seven citations are **real papers with real arXiv IDs**, and every one of
them was attached in `ARENA.md` to a claim about agent memory, cognition, or
belief revision. The verified titles are in a **different field**. The failure is
not fabrication of an identifier — it is a citation whose content does not
match the paper it names, which is precisely the §8 inversion the arena warns
about, occurring **inside the arena itself**.

| Ref | Verified title | What it was cited for | Status |
|---|---|---|---|
| [2609.06806](https://arxiv.org/abs/2609.06806) | Train Smarter, Not Harder: Switching Signal-Guided Training in Active Learning | HybridAL consolidation switch policy (ADOPT + C6/C13) | **STRUCK** |
| [2606.14512](https://arxiv.org/abs/2606.14512) | Fodor and Pylyshyn's Systematicity Challenge Still Stands | 2nd independent line for C3 (dorsal/ventral split) | **STRUCK** |
| [2605.10619](https://arxiv.org/abs/2605.10619) | Study of $\eta^\prime \to \eta \pi\pi $ Decays in Large-$N_C$ Chiral Perturbatio | "knowledge stored locally does not transfer" — the 2nd leg of the parametric-KG REJECT | **STRUCK** |
| [2606.04194](https://arxiv.org/abs/2606.04194) | Training-Free Lexical-Dense Fusion for Conversational-Memory Retrieval | `UNSUCCESSFUL` negative on component placement (REJECT row) | **STRUCK** |
| [2604.20943](https://arxiv.org/abs/2604.20943) | SCM: Sleep-Consolidated Memory with Algorithmic Forgetting for Large Language Mo | negative against REM-style edge inference (REJECT row) | **STRUCK** |
| [2607.18077](https://arxiv.org/abs/2607.18077) | Generalised Bellman recurrence and three dualities in sequential decision-making | EvolveMem, C12 ontology evolution | **STRUCK** |
| [2512.14801](https://arxiv.org/abs/2512.14801) | Incentives or Ontology? A Structural Rebuttal to OpenAI's Hallucination Thesis | supersedure needs topical relevance not recency (C7) | **STRUCK** |

**What this changes.**

- **C3** loses its corroboration and now rests on the Goodale & Milner double
  dissociation alone (`HIGH`, single line). See the C3 section.
- **REJECT** loses 2 of its 5 rows as sourced. The parametric-KG rejection is now
  one independent negative instead of two, and the "any 2-pass certifier" row is
  the only one left with no paper attached at all.
- **ADOPT** loses HybridAL. SCM (arXiv:2604.20943) is substituted, on a verified
  title, as a sleep-consolidated forgetting architecture.
- **Nothing load-bearing collapsed.** C1, C2, C4, C5, C6, C7, C8, C9, C10, C11,
  C12, C13 and C14 rest on papers whose verified titles match their claims. The
  deepest finding — C1, provenance ≠ trust — is grounded in an **executed
  incident** (Mini Shai-Hulud) rather than a citation, so it is unaffected.

**How this happened, stated plainly.** All seven mis-citations are in `ARENA.md`,
not in this document — this document reproduced them faithfully from the arena
and they are corrected here for the first time. The cause is the mechanism the
arena itself identifies: a file is read, a claim is written about it, and later a
pass cites that claim **from memory** under a plausible-looking identifier. The
arena's C6 check verifies that a cited file's **ledger row** is `[x]`. It cannot
verify that the cited file **says what the citation claims** — because that
requires reading the paper, which no check in the stack does.

**The fix is a check, not a rule.** A citation checker should extract the claim
attached to each arXiv ID and compare it against the paper's **verified title and
abstract**, flagging field mismatches. Seven of 86 (8%) would have been caught
automatically. Until that exists, treat every arena citation as a **pointer to a
paper**, never as evidence, and this document's §9.1 as the only title-verified
index available.

---

## 10. How to use this document

- **Do not treat it as approved.** It is a reading of a 63%-complete corpus.
- **Do check the primaries before building.** §1 is not optional.
- **When the arena moves, edit this file and cite the tranche that moved it** —
  the same discipline the arena applies to itself.
- **The three things worth doing first, in order:** C1 (add `trust` — it is one
  schema column, two witnesses and a hard fail), C6 (persist `assumption_set` —
  the arena's most consequential missing mechanism), C5 (declare verifier
  independence and start injecting faults). None of the three requires new
  infrastructure, and all three are prerequisites for trusting anything else
  here.
