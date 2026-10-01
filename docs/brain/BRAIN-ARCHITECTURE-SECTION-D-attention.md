# BRAIN ARCHITECTURE — SECTION D: ATTENTION (C-2)
Read after Section A.

## WHAT EXISTS TODAY, AND WHY IT IS NOT ATTENTION

`brain/thalamus/gate.py` (73 lines) is the whole of it. It computes:

```
saliency = (char_entropy * 0.4) + urgency_regex_boost + context_overlap - redundancy_penalty
```

and admits / compresses / attenuates against a fixed 0.35 threshold. This is a
**novelty filter on incoming text**. It is not a model of attention, and three
specific failures follow from the difference.

**D1. Character entropy is not semantic novelty.** `compute_entropy` counts
character frequencies in a string. A log file full of JSON braces and UUIDs scores
as high-entropy as a genuinely surprising insight; a dense technical paragraph in a
consistent domain scores low. The measure is of the *byte distribution*, not the
content. It is also English-text-tuned with no validation.

**D2. There is no selectivity, so there is no interference.** FIT's core claim
(vault `Feature-Integration-Theory.md`) is that attention is a *binding* operation
under a *capacity limit*: properties are registered in parallel, then bound to
objects — and binding fails under load. A gate with one threshold and no
competition has no notion of what is being displaced by what. Nothing in the repo
models the thing attention is *for*.

**D3. There is no top-down channel.** Saliency is computed from the text alone plus
word-overlap with `active_context`. Goal-directed selection — "of everything
noticeable, pick what serves the current objective" — is approximated by counting
shared words. `Executive-Control/Cognitive-Control-Conflict.md` and
`Dual-Process-Theories.md` in the vault are about exactly the control problem this
cannot express.

**D4. It is not wired.** Per A-12, six instances are constructed and never called.
The gate is not in that list, but nothing in `hermes_brain.py`'s per-turn flow
demonstrably consults it on the answer path.

## THE VAULT'S MOST ACTIONABLE FINDING — AND IT IS A NUMBER WE VIOLATE

`Attention/Attentional-Residue.md` is not a survey; it is a specification, and it
carries a field observation that describes this agent's actual behaviour:

> Direct observation of 24 information workers: **11.7 distinct "working spheres,"
> ~11 minutes per sphere before switching, 57% of working spheres interrupted**,
> with more than two intervening activities typically occurring before interrupted
> work was resumed. Peer-reviewed resumption delays **≈ 22–29 minutes** depending
> on interruption source.

And the cost model has **three separable components**, which the repo currently
prices at zero:

1. **Executive cost of reconfiguration** — hundreds of ms, laboratory scale.
2. **Memory-based resumption cost** — governed by associative priming between
   *environmental cues* and *suspended goals*; seconds to minutes. **This is the
   one we can actually build against** — resumption cost is a function of whether
   the cue that re-activates the goal is present when work resumes.
3. **Perseverative-cognition cost (residue)** — depends on whether the task was
   *finished* and under what time pressure. "Merely finishing Task A before
   switching is not sufficient to prevent it."

**The agent in this repo is structurally the interrupted knowledge worker.** It has
5 Hermes instances (B-3 ToM is explicitly multi-agent), a Telegram front end, a cron
system, and a research queue. It is interrupted by design. The vault says the
interruption-resumption loop is ~22–29 minutes of degraded work in humans, and that
completion ≠ closure. **Nothing in the repo models the cost of coming back.**

This is the finding that converts attention from an abstract gap into a concrete
engineering requirement: **an agent that switches every turn and has no
re-activation cue pays the resumption cost on every turn, and does not know it is
paying it.**

## TOP 3 CANDIDATES

**RANK 1 — Goal-bound selection with an explicit working set (top-down + bottom-up).**
Separate the two channels the current gate conflates. Bottom-up keeps the existing
novelty signal. Top-down scores candidates against *the active goal's* embedding
and the *task's* deadline/urgency, not word overlap. Bind the winner to a goal slot.
- PRO: fixes D3 directly; the goal is already a first-class object
  (`prospective/intentions.py`, 340 lines — the largest module in the repo). The
  selection signal should be the same object that intentions manages.
- PRO: cheap; this is a scoring-function change plus a slot binding, not a new subsystem.
- PRO: makes the gate answer a question worth answering — "what serves the goal" —
  instead of "is this string unusual."
- CON: needs a goal representation better than free text. ACT-R's
  `Cognitive-Architecture-ACTR.md` in the vault maps modules to agent components and
  is the obvious reference for the retrieval-goal interface.
- BUILD: `saliency = w_b * bottom_up + w_t * goal_similarity + w_u * urgency`, with
  the weights and the goal vector exposed in config; log the winning component per
  admission so the choice is auditable.

**RANK 2 — Residue-aware task switching (the vault's 3-component cost model).**
Track unfinished goals, and on resumption explicitly re-activate rather than assume
continuity. Bind each suspended goal to its *environmental cues* (file path, thread
id, doc ids) so the cue can re-trigger the goal.
- PRO: this is the finding with a hard number attached (22–29 min; 11.7 spheres;
  57% interrupted), and the repo is exactly the workload it describes.
- PRO: the infrastructure is half-there. `prospective/intentions.py` already
  holds goals; the vault's resumption cost is a *function of cue presence*, and we
  can store the cue.
- PRO: it makes the "re-activating rather than assuming continuity" decision
  explicit and therefore falsifiable, which the current flow is not.
- CON: the human numbers do not transfer to an LLM agent — the residue mechanism in
  humans involves representations the model does not have. Treat the *mechanism*
  (cue-bound re-activation) as the transferable part and the 22–29 minutes as
  motivation, not as an expected effect size. Do not carry the human number into a
  Hermes performance claim.
- BUILD: `intentions` gains `suspended_at`, `cue_keys`, `resumed_count`. On resume,
  log whether cues were present. The *ratio* is the measurement, not an absolute time.

**RANK 3 — Interruptibility / deferral arbitration (Inhibitory Control).**
Vault: `Inhibitory-Control-Go-NoGo.md`, `Cognitive-Control-Conflict.md`,
`Cognitive-Flexibility-Set-Shifting.md`. Decide not merely what to attend to but
whether the current task should be *preempted at all* — the Go/No-Go discipline
that already exists in `basal_ganglia/action_gate.py` (threshold 0.4), applied to
task switching rather than to tool actions.
- PRO: reuses existing code and an existing decision primitive.
- PRO: the repo has 5 agents and a cron system; without preemption arbitration it
  has no policy for a high-value nightly consolidation colliding with a live user turn.
- CON: the action gate is unwired (A-12), so this inherits that debt.
- BUILD: extend the existing gate with a preemption-appropriateness check, and wire it.

### Why not the rest
- **FIT proper** (`Feature-Integration-Theory.md`) — the binding mechanism is
  visual and pre-verbal. There is no honest agent analogue that isn't a metaphor.
  Take the *capacity-limit* insight, not the binding stages. Same treatment the
  architecture already gives GWT in §12.3: engineering heuristic, no scientific claim.
- **Attentional Residue's replication caveats** — the file flags contested
  chronic-multitasking findings. Do not import contested parts as design law.
- **Prefrontal-Attention-Networks** — brain substrate, not an agent mechanism.

## RELATION TO C-1 AND C-3
Attention *is* the allocator; working memory is the space it allocates into;
metacognition supplies the signal that says allocation failed. All three must land
together or none of them work. Ranking D before C-1 is deliberate: the gap is
bigger (no model at all, vs. working memory having code but no policy).

## SEQUENCE
Phase 0: wire the gate into the per-turn flow; log admissions. (A-12 debt.)
Phase 1: Rank 1 — split top-down from bottom-up. Small, high leverage.
Phase 2: Rank 2 — cue-bound re-activation in `intentions`.
Phase 3: Rank 3 — preemption arbitration, reusing `action_gate`.
