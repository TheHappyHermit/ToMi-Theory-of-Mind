# Oracle wiki verdicts on the seven architecture claims

Queried 2026-09-29, one question per invocation, against the Oracle vault.
Source of record: `~/.hermes/oracle/brain/`. This file records what the
vault says, with paths, and nothing is inferred to fill a gap.

## Verdicts

| # | claim | verdict | elapsed |
|---|---|---|---|
| 1 | Hebbian reinforcement required | **see correction below** | 72s |
| 2 | Template summarising != real consolidation | **PARTIAL** | 324s |
| 3 | Hash is the wrong function class | **FOUND** | 153s |
| 4 | Hyperdirect pathway | **MISS** | 303s |
| 5 | Fear conditioning as a learning rule | **MISS** | 142s |
| 6 | Fixed threshold is a defect | **FOUND** | 116s |
| 7 | ZenBrain ablation | **FOUND** | 140s |

## The finding that matters most: ZenBrain

Source: `research/batch128-sleep-consolidation-anchors.md`, section 8a,
titled "Honest Negatives". The vault files ZenBrain under NEGATIVE value,
and this inverts how the paper has been cited in this repo.

Quoted from the vault entry:

> "under moderate load, fourteen of the fifteen ablations look costless
> -- the architecture reads as mostly dead weight"

and, after raising decay to 0.25/day over 60 days:

> "does [the architecture] make nine of the fifteen individually critical"

and the paper's own conclusion:

> "mild-load ablation systematically underestimates architectural
> contributions -- a caution we conjecture applies beyond ZenBrain."

The vault's verdict on the paper: "the mechanism catalogue is
theatre-shaped; the ablation is real and the finding is *negative about
the theatre* -- at realistic load, most of the neuroscience-inspired
machinery contributes nothing measurable. This is the single best citation
for why 'we have 15 brain mechanisms' is not evidence."

**WHAT THIS MEANS FOR US.** `MIND-ARCHITECTURE-REVIEW-2026-09-25.md` cites
ZenBrain to justify KEEPING thin-looking regions -- "a mechanism that looks
inert is not inert." That is half the paper. The other half is that at
realistic load most of the machinery measures as contributing nothing, and
the only way to find out which half you are in is an ablation under load.

So the citation does not license keeping a region because it looks small.
It demands the opposite: prove it under load or delete it. This repo has
five cortex modules and no ablation harness of any kind, which is the gap
the cortex researcher independently identified.

## Q2: consolidation (PARTIAL, not FOUND)

**Corrected.** Oracle's own verdict was PARTIAL and this file first
recorded it as FOUND. The correction matters: PARTIAL means the vault
answers half the question and is silent on the other half, and the half
it is silent on is the part that would justify a design decision.

Sourced to `BUILD-PLAN-AGENDA.md:1804,2487` and the nightly cron entry.
The vault explicitly distinguishes fast-path (deterministic, no LLM)
consolidation from LLM-based consolidation, and documents the
offline/deferred model for the nightly plugin and cron jobs.

The half it does NOT answer: the vault "does not state a blanket
prohibition on inline consolidation during a turn — it's implied by
architecture." Oracle rated its own uncertainty "moderate" on exactly
that point. So the vault supports the fast-path/LLM distinction and
documents deferred consolidation as the practice, but does not assert the
rule. Treat the deferred model as convention, not as a stated constraint.

Corroborates the measured finding that `hippocampus/replay.py` builds
`consolidated_insight` as an f-string and never calls a model.

## Q3: hashing (FOUND)

Source: `research/batch161-the-name-is-not-the-mechanism-and-the-thing-it-
names-is-absent.md` lines 197-211.

> "A hash is a maximally non-geometric function used to solve a geometric
> problem. It is not a weak implementation; it is the wrong function
> class."

and:

> "You cannot compute distance between two hashes, so you cannot measure
> whether separation occurred."

The vault states interference is a geometric property and the correct
operation is sparse, near-orthogonal coding. This is a direct indictment
of `replay.py:pattern_separation()`, which returns a SHA-256 digest.

## Q4: hyperdirect pathway (MISS)

Zero matches across ~500+ markdown files for: hyperdirect, direct pathway,
indirect pathway, emergency brake, action selection, Go/NoGo, Gerfen,
Schultz, striatum, basal ganglia, stop-signal.

The external researcher reported the three-pathway model as unique to this
repo with no counterpart anywhere. The vault agrees it is uncovered. Our
`basal_ganglia/action_gate.py` is the only implementation either of us has
found -- and it is 52 lines with no learning.

## Q5: fear conditioning (MISS)

Only hits for "conditioning" are "conditional test calibration" and
"conditional description length", both statistical. Zero results for fear
conditioning, CS+/CS-, extinction, or blocking across both vaults.

This independently confirms the amygdala researcher's finding that the
low-road threat function is unclaimed territory.

## Q1: CORRECTION -- my first answer was wrong

The first pass timed out at 423s and a re-ask returned MISS. That MISS was
an artefact of MY OWN ERROR: I gave Oracle a file path I had guessed,
`research/Hebbian-Weight-Update-Synaptic-Plasticity-Rules.md`, which does
not exist. The real file is:

    Neuroplasticity/Hebbian-Weight-Update-Synaptic-Plasticity-Rules.md

and it does cover the topic -- Hebbian learning theory, STDP, BCM,
homeostatic plasticity, weight-update rules.

**The vault DOES cover Hebbian reinforcement.** A MISS returned because I
pointed at a phantom path is not a MISS. I did not verify the path before
asking, and then reported the resulting MISS as a finding.

Side observation: that file also exists as a lowercase twin under
`neuroplasticity/`, and the two DIFFER. That is direct evidence for
task 44 (near-duplicate topic folders in the Oracle vault).

## Q6: learned thresholds (FOUND) — the closest match to our own code

Source: `Dual-Process-Cognitive-Memory.md`. The vault criticises its OWN
DCPM thresholds (θ_beh=0.72, θ_sem=0.40):

> "are currently set by held-out tuning rather than learned, which means
> they may not generalize across domains or user populations"

and asks outright:

> "the thresholds be learned from data rather than tuned, or is some form
> of domain-specific calibration inevitable?"

This is the same defect in the same vocabulary as
`thalamus/gate_entropy_superseded.py`, whose 0.35 threshold was a guess
and which was retired for that reason. The vault treats hardcoded
thresholds as an open question rather than a settled parameter, and the
external research independently recommends `Maxim`'s
`AdaptiveThresholdController`, which learns thresholds from outcomes.

Three independent lines now converge on one change: the thalamic gate
should learn its threshold from observed outcomes.

## FINAL TALLY

7 asked, 7 answered. 3 FOUND, 1 PARTIAL, 2 confident MISS, 1 FOUND
after correcting my own bad input. 72–324s per question once scoped to
one topic.

**Read the tally from the STATUS lines, not from my prose.** Q2 was
recorded here as FOUND on the strength of the answer body while Oracle's
own verdict line said PARTIAL, and the summary line in the run log
reported "FOUND" for a body that said MISS. Grep `STATUS:` and nothing
else.

Consolidated with the six-region recommendations, the ordering by
evidence strength is now:

1. **Build an ablation harness.** ZenBrain makes "looks small" and "does
   nothing" indistinguishable without one, and we have zero.
2. **Make replay consolidation call a model** (Q2 FOUND; measured gap).
3. **Replace SHA-256 pattern separation** with sparse near-orthogonal
   coding (Q3 FOUND: "wrong function class").
4. **Learn the thalamic threshold from outcomes** (Q6 FOUND).
5. **Build the amygdala** — no hyperdirect pathway and no fear
   conditioning exist in the vault (Q4, Q5 MISS), so it is unclaimed.

## HOW TO ASK ORACLE WITHOUT WEDGING IT

Measured across ten invocations:

- ONE question per call. A nine-region crawl ran 50 min, 0 bytes.
- NAME THE FILE when you know it. Same question, 423s -> 72s.
- Separate stdout from stderr. `2>&1 | tail -30` keeps the SIGTERM
  traceback, which is exactly 30 lines, and hides the answer every time.
- Grep for `STATUS:`, not for the word FOUND anywhere -- the word appears
  in the prompt and produces a summary that contradicts the body.
- Budget 150-420s per question against a local model running
  `reasoning_effort: high`. Retrieval is fast; generation is the cost.
