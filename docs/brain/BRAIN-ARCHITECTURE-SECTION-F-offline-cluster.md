# BRAIN ARCHITECTURE — SECTION F: THE OFFLINE CLUSTER
C-4 incubation · C-5 curiosity · C-9 world models · C-11 circadian · C-12 sleep/replay.
Read after Section A. One section, five gaps, because they share one missing
thing: **nothing in this repo runs on a schedule derived from evidence.**

## THE MISSING THING, STATED

The repo has a cron system, a `hippocampus/replay.py` (92 lines), and a dreaming
plugin with three phases. `SCRATCHPAD`/architecture Gap **G31** says the NREM/REM
mapping is `[CONJECTURE]`. That is the correct epistemic label and it is also an
admission that **the schedule was never chosen by anyone.** It is a default.

The vault does not leave this to taste. It holds a specification:

- `Learning/Spacing-Effect.md` — the best-replicated finding in the whole memory
  literature. Distributed practice beats massed practice, and the gap *is* the
  active ingredient. This is the literature's most robust effect and it is the
  entire justification for having an offline consolidation pass at all.
- `Consolidation/Targeted-Memory-Reactivation.md` — TMR: sleep replay is **not**
  indiscriminate. It preferentially replays *tagged* material (the study
  preceding a sleep period is preferentially reactivated). The tag-and-capture
  pair (`Synaptic-Tag-and-Capture.md`) is the mechanism: a synaptic tag set during
  learning captures the plasticity that arrives later.
- `Sleep-and-Cognition/Sleep-Dependent-Insight-Generation.md` — sleep specifically
  produces *insight*, not just stability. Distinct from online rehearsal.
- `Consolidation/Synaptic-Homeostasis-Hypothesis.md` (Tononi & Cirelli) —
  consolidation is **homeostatic**: it exists to free synaptic resources by
  downscaling, not only to strengthen. A consolidation pass that only strengthens
  is doing half the job and may be *net harmful* by consuming capacity.
- `Consolidation/Adaptive-Forgetting.md` + architecture #23 SCRUBJAY
  perishability — forgetting is a *feature with a schedule*, and the repo has no
  forgetting pass at all beyond working-memory decay.
- `Circadian-Rhythms/Circadian-Rhythms-and-Chronobiology-of-Cognition.md` — the
  consolidation window is not arbitrary; it tracks circadian phase.

**The current design — one nightly pass, three invented phases — ignores all of
it.** And critically: the vault's own *metacognition* work says sleep-time
consolidation of an agent's **own** prior errors may be actively harmful. ICLR 2026
"Illusion of Diminishing Returns" (already recorded in SCRATCHPAD OFFLINE
CONSOLIDATION Rank 1) finds **self-conditioning**: models err more when their
context contains their own prior errors, and this does not shrink with scale. That
is a direct, cited, landmine sitting under the nightly pass.

## C-4 INCUBATION — the single most replicable absent capability

`Creativity-and-Insight/Insight-Problem-Solving-and-Incubation-Effects.md`:
the incubation effect is **meta-analytically confirmed** across problem types,
moderated by problem type, incubation duration, and intervening activity. Mechanism
is *restructuring* (Ohlsson 1992; Knoblich 1999) — relaxing self-imposed
constraints and decomposing inappropriate chunks — plus Mednick-style spreading
activation where weakly-activated remote associates accumulate strength. The
neural signature is a gamma burst ~300 ms *before* the reported insight, and DMN
engagement prior to problem presentation.

**The repo has a DMN module with chronesthesia and counterfactual reasoning, and
neither is an incubation mechanism.** Chronesthesia is temporal imagination;
counterfactual is "what if X had gone otherwise." Incubation is a third thing: the
*deliberate absence of the problem* plus a later re-presentation. The vault is
explicit that intervening activity matters — so incubation is not idling, and not
"run the same prompt again at 3am."

**This connects to B-3's chronesthesia (never called, A-12) and to C-9.** See Rank 1.

## C-5 CURIOSITY — the information-gap mechanism, unused

`Metacognition/Epistemic-Emotions.md` gives the mechanism precisely: Loewenstein
(1994) information-gap theory — perceiving a gap in knowledge creates an aversive
state motivating gap-filling — and the **inverted-U**, confirmed by Kang et al.
(2009): curiosity is *highest at intermediate confidence*, lowest at zero and at
certainty. Berlyne's collative variables (novelty, complexity, ambiguity,
incongruity) are the tuning knobs. Surprise has a formal definition (Itti & Baldi:
KL divergence between posterior and prior) and captures 72–84% of gaze shifts.

**The repo has no curiosity signal, and it is missing the single most useful
property: curiosity peaks where confidence is intermediate.** A knowledge-seeking
agent that reads a document with 100% confidence has nothing to gain; one with 0%
confidence has no idea what to ask. The productive zone is the middle — **which is
exactly the zone metacognition (C-3) can measure and the repo currently cannot.**
C-5 and C-3 are the same project. The inverted-U is the routing rule.

Note also Gruber et al. (2014): high-curiosity state improves memory for
*incidental* material encountered during it. If true for agents, curiosity has a
second-order value — it is a memory-consolidation aid, not just a search policy.

## TOP 3 CANDIDATES (covering C-4, C-5, C-9, C-11, C-12)

**RANK 1 — Tagged, scheduled, selective consolidation ("tag and capture").**
Give the memory system a **synaptic tag**: when something is learned, stamp it
(`tag_set_at`, `tag_strength`, `importance`, `confidence`, `source`). The offline
pass replays **tagged, not recent, not all**. Scheduling follows the spacing
literature: interval lengthens with each successful recall of the item, and the
nightly window is placed against circadian phase rather than at a fixed hour.
Include a **homeostatic downscale** pass (synaptic-homeostasis), not only a
strengthen pass.
- PRO: every mechanism is in the vault with its citation, and TMR +
  Synaptic-Tag-and-Capture are unusually specific — they say *what* to replay, not
  just *when*.
- PRO: fixes the self-conditioning landmine by construction: tagged items are
  selected, so the pass does not blindly re-feed the agent its own errors.
- PRO: gives the existing `replay.py` a selection policy instead of a loop.
- PRO: homeostatic downscale is what makes consolidation *free capacity*, which is
  the actual physiological function; a strengthen-only pass is not consolidation.
- CON: requires `confidence` on items → blocked on C-3. Same dependency, third time.
- CON: interval scheduling needs recall history, which needs the retrieval log to
  be trustworthy — and A-03 says the retrieval instrumentation is currently void.
- BUILD: `tag`, `should_replay(item, now)`, interval table, and a separate
  `downscale_pass()`. Log what was replayed and what was downscaled.

**RANK 2 — Incubation queue for stuck problems.**
When the action gate or a solve attempt fails repeatedly on a structured problem,
park it (not the current context — a *queue*). On a later pass, re-present the
problem **with a deliberately different representation** (different framing,
different modality, a retrieved graph neighbourhood it has not seen), not the same
prompt. The vault says restructuring, not repetition, is the mechanism, and that
intervening activity matters.
- PRO: this is the only candidate that produces *novel* problem representations
  rather than more of the same, and the vault is blunt that the same prompt does nothing.
- PRO: pairs with the graph. A PPR neighbourhood over the failing problem's entities
  is a genuinely different representation, and the multi-hop machinery (B-5,
  HippoRAG) exists to supply it. **This is where the graph earns its keep** — not
  lookup, not fusion, but *deliberately different views of a stuck problem.*
- PRO: the failure signal already exists (action gate Go/No-Go at threshold 0.4,
  defeater-graph disputes).
- CON: "stuck" needs a definition; a queue of everything-that-failed will be noise.
- CON: re-presentation quality determines everything here, and that is an LLM
  judgement with no ground truth.
- BUILD: `IncubationQueue`, entry on repeated failure, drain on a slow cadence,
  each entry carrying `problem`, `attempts[]`, `representations_tried[]`.

**RANK 3 — Information-gap curiosity driver as the research trigger.**
Compute, per open question, the information gap (KL-style: how much the current
retrieved evidence would change the answer distribution) and prioritise research
by inverted-U curiosity: gap × intermediate confidence, not gap alone.
- PRO: directly implements the Loewenstein/Kang inverted-U, and it is the *only*
  candidate that makes "should I go research this?" a principled decision rather
  than a queue.
- PRO: converts the repo's research cron from a fixed schedule into a
  gap-driven one. The repo already has a research pipeline
  (`research-cron-knowledge-base` skill) that currently picks topics by agenda order.
- PRO: composes with the self-conditioning warning — curiosity is *intrinsic* and
  novelty-seeking, which is the opposite of replaying prior errors.
- CON: needs a distributional answer model; an extra forward pass per question.
- CON: novelty-seeking agents can rabbit-hole. Needs a budget cap and a boredom
  term (Eastwood: boredom = wants to engage but cannot; MAC model splits it into
  underload and overload, each motivating a different alternative).
- BUILD: extend the existing research cron to accept a *priority* signal rather
  than an agenda position.

### Why not the rest
- **Schmidhuber intrinsic reward / Pathak ICM** (in the vault) — designed for
  learned controllers in RL, assumes a trainable policy. A tool-using agent has no
  learned policy to reshape. Take the *idea* of prediction-improvement as the
  novelty metric; skip the RL machinery.
- **Dreaming plugin's three phases** — not a candidate, a constraint. Its phases
  stay; its selection policy is what Rank 1 supplies.
- **Letta sleep-time compute (SCRATCHPAD Rank 1)** — already ranked, and it is
  *query-time precomputation*, not periodic consolidation. Complementary, not
  competing. Rank 1 above is the periodic analogue; the self-conditioning warning
  in that same entry applies to both.

## THE CIRCULAR DEPENDENCY THE OWNER MUST SEE
Three separate gaps (C-3 confidence, C-11 scheduling, A-03 retrieval correctness)
each independently require the same missing foundation: **a trustworthy record of
what was retrieved, how confident we were, and whether it was right.** The repo has
none of the three. That shared substrate is now the critical path for the entire
offline cluster, and it is cheaper than any of the five components.

Recommend it be treated as **Phase 0 infrastructure**: a single append-only
`retrieval_log` + `confidence_log` pair, written by the retriever on every query,
consumed by confidence (C-3), scheduling (C-11), and the benchmark (A-03). It is
not a cognitive function; it is the instrument that makes three of them measurable.

## SEQUENCE
Phase 0: `retrieval_log` + `confidence_log` append-only. Instrumentation, not a claim.
Phase 1: tags on memory items + `should_replay` interval scheduling (Rank 1 skeleton).
Phase 2: incubation queue, fed by repeated-failure detection (Rank 2).
Phase 3: curiosity priority replacing agenda order in the research cron (Rank 3).
Phase 4: homeostatic downscale + perishability (SCRUBJAY #23) — needs Rank 1's schedule.
