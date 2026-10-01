# Cortex ablation: pilot results

Produced by `scripts/ablation_harness.py`. Raw evidence:
`docs/audit/ablation-stressed.json`. Reproduce with:

    python3 scripts/ablation_harness.py --load stressed --trials 6

## What was measured

Single-gate ablation under a deliberately stressed workload: 30 turns
per trial, 6 trials, control and ablated conditions interleaved
round-by-round, two discarded warmup passes first.

Ablating a gate means suppressing that one subsystem inside
`CognitiveWiring.run()` while the other five run identically — same
input, same order, same state. Not whole-architecture removal.

| gate | ablated | time saved | share of turn | fired |
|---|---|---|---|---|
| counterfactual | 258 µs | 1204 µs | **82.4 %** | 5 / 30 |
| defeater_graph | 1241 µs | 221 µs | 15.2 % | 5 / 30 |
| chronesthesia | 1394 µs | 68 µs | 4.7 % | 15 / 30 |
| dialectic | 1399 µs | 63 µs | 4.3 % | 5 / 30 |
| agm | 1432 µs | 30 µs | 2.1 % | 5 / 30 |
| associative_graph | 1470 µs | −8 µs | ~0 % | 30 / 30 |

Control: 1462 µs/turn.

## The one result that matters

**`counterfactual` is 82 % of cortex turn cost.** Ablating it takes a
turn from 1462 µs to 258 µs — an 82 % reduction — and it fires on only
5 of 30 turns. The cost is concentrated: when it fires, it dominates.

That is a real, actionable finding and it is the opposite of what the
subsystem count suggests. Five of the six gates are noise; one carries
nearly everything.

**But cost is not value.** A subsystem that is 82 % of the bill may be
paying for a rollout nobody uses, or it may be the only thing that makes
the other five worth having. Deleting it on a timing number alone would
be exactly the mistake ZenBrain's entry warns about. The correct next
step is to establish what the rollouts *produce*, not what they cost.

**The other five are unresolved, not exonerated.** At 0–5 % they sit
within scheduler noise on a sub-millisecond turn. "No measurable cost" is
not "no contribution" — most of them fire on 5 of 30 turns, so their real
cost is concentrated into a small number of expensive turns that a mean
hides. Raising `--trials` and looking at the fired-turn distribution,
rather than the per-turn mean, is the next measurement.

## Load discipline (why this is not the ZenBrain result)

ZenBrain, in our own Oracle vault under "Honest Negatives": *"under
moderate load, fourteen of the fifteen ablations look costless — the
architecture reads as mostly dead weight"*, and *"mild-load ablation
systematically underestimates architectural contributions"*.

At `--load baseline` this harness fires **zero** of six gates and reports
`valid: false` with the reason. It refuses to print a table of zeros as
though that were a finding — that is the trap, reproduced in-house and
then caught. `--load stressed` fires all six.

Two things had to be right for the stressed load to measure anything,
and both were wrong in the first draft:

- **mode must be `SYSTEM_2`.** Not `"chat"`, not `"deliberate"`. The gates
  do not recognise those names and every one returns early with
  `"routed {mode}, not a deliberation point"`. Three of six gates still
  fired, which is worse than none: the run looked plausible and reported
  confident zeros for gates that had never been called.
- **the timeline must be seeded.** `gate_chronesthesia` refuses to fire
  while `timeline_events` is empty. Unseeded, it is dead under every
  workload, and a permanently-dead subsystem produces a clean zero-delta
  ablation that reads as "chronesthesia costs nothing".

`MUST_FIRE` is all six gates, and a run where any gate failed to fire is
reported INVALID rather than as a result. `tests/test_ablation_harness.py`
asserts both of these, so the trap cannot be re-entered silently.

## A measurement bug this harness produced, and fixed

The first valid-looking run reported **every** gate as a negative cost —
ablating a subsystem appeared to make the turn *slower*, which is
impossible.

Cause: controls ran first and paid every first-call cost (imports, lazy
init, allocator warmup), so ablated trials ran later on a warmer process
and came out faster. Every gate then appeared to cost negative time.

Fixed with discarded warmup passes plus round-by-round interleaving, so
drift hits all conditions equally instead of penalising whichever ran
last. Worth recording because the failure produced a *confident,
plausible, wrong* table — a measurement artifact that looked exactly like
a result. It is the same class of error as measuring at light load: the
harness reports a number, and the number is about the harness.

## Known limits

- **Marginal contribution only.** Each gate is ablated with the other
  five present. A subsystem that only matters when another is *absent*
  reads as zero here. Interaction effects are not measured; measuring
  them is a factorial sweep, not a single-gate harness.
- **Cost, not value.** See above. Nothing here says a subsystem is
  earning its keep.
- **Noise floor.** Sub-millisecond turns mean anything under ~5 % is
  unresolved.
- **Single region.** This is a cortex pilot, by decision. The harness
  is written against `GATE_NAMES` and `CognitiveWiring`, so extending it
  to another region means supplying that region's gates — configuration,
  not a rewrite. That was the reason for doing cortex first: prove the
  load methodology, then widen.

## What it does not license

Keeping all six because they exist. Deleting five because they are
cheap. Both are unearned conclusions from a cost measurement. The
defensible statements today are: `counterfactual` dominates cortex turn
cost, and the remaining five are individually unmeasured in value.
