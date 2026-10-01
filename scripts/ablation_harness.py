"""Ablation harness: does each cortex subsystem earn its cost?

WHY THIS EXISTS
---------------
ZenBrain, in our own Oracle vault under "Honest Negatives", reports that
"under moderate load, fourteen of the fifteen ablations look costless --
the architecture reads as mostly dead weight", and that "mild-load
ablation systematically underestimates architectural contributions".

That is the finding that governs this file. It means:

  * "this module looks small" and "this module does nothing" are
    indistinguishable without a measurement, and
  * a measurement run at light load will report that nothing matters,
    which is the expected result of measuring at the wrong load, not
    evidence about the modules.

So the harness is built around one requirement: measure under STRESS,
and make the load level an explicit, reported input rather than an
accident of whoever ran it.

WHAT AN ABLATION IS HERE
------------------------
Not "delete the module." The subsystems are gated inside
CognitiveWiring.run(). Ablating means suppressing one gate's firing
while everything else runs identically -- same input, same order, same
seed. That isolates the subsystem's contribution from the confounds
that make whole-architecture ablations unreadable: interaction effects
(the thalamus changes what the hippocampus does) and start-order
effects.

Interaction effects are the hard limit here and are stated rather than
hidden. Single-gate ablations measure each subsystem's marginal
contribution GIVEN the others are present. They cannot attribute a
subsystem's value when it is only load-bearing in the absence of
another. A subsystem that shows a near-zero delta here is not proven
useless; it is proven not to matter on its own terms, which is the
question worth asking first and the one this harness answers.

USAGE
-----
    python3 scripts/ablation_harness.py --load stressed
    python3 scripts/ablation_harness.py --load baseline --load stressed

Every run writes JSON to docs/audit/ablation-<load>.json. Results are
committed so a later change can be compared against them; the point is
to detect a regression, not to produce a one-time number.
"""
from __future__ import annotations

import json
import os
import random
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from brain.cortex.wiring import GATE_NAMES, CognitiveWiring  # noqa: E402

AUDIT = REPO / "docs" / "audit"

# ── Workloads ────────────────────────────────────────────────────────────
#
# Each is a list of (text, mode) turns. A turn is the unit of load: it
# is one full pass through CognitiveWiring.run().
#
# The stressed workload is not "more of the same". It is built to
# trigger every gate, which is the only way an ablation can see a
# subsystem's cost. At light load most gates never fire, so ablating
# them changes nothing -- which is precisely the ZenBrain trap.
LOADS: Dict[str, List[Tuple[str, str]]] = {
    # Deliberately weak. Every gate is expected to skip. Useful only as
    # the control that proves the stressed workload is doing more.
    "baseline": [
        ("hello", "chat"),
        ("what can you do", "chat"),
        ("thanks", "chat"),
        ("ok", "chat"),
    ],
    # Every turn is constructed to fire a gate, plus repeats so the
    # per-turn cost is measured at a rate the gates actually see in
    # production rather than only on their first invocation.
    #
    # mode="SYSTEM_2", not "chat" or "deliberate". The gates do not
    # recognise those names: counterfactual returns "routed {mode}, not a
    # deliberation point" for anything except SYSTEM_2, and
    # associative_graph returns the same for its deliberative branch.
    # Getting this wrong fires 3 of 6 gates and looks like a negative
    # ablation result, which is the exact failure this harness exists to
    # avoid. Verified by probe, not assumed.
    #
    # chronesthesia additionally needs recorded timeline state, seeded by
    # seeding the first turn so later turns have a history to consult.
    "stressed": [
        # seeds a timeline entry that chronesthesia can consult
        ("last week i believed the loader was fine", "SYSTEM_2"),
        # defeater_graph: negation next to a belief term
        ("actually that is not true, i believe the deployment is broken",
         "SYSTEM_2"),
        # agm + dialectic: contradicted belief
        ("i no longer believe the port collision was harmless", "SYSTEM_2"),
        # chronesthesia: temporal reference, with history now recorded
        ("what did i believe about the loader last week instead", "SYSTEM_2"),
        # counterfactual: decision marker under SYSTEM_2
        ("should we ship if the verifier regressed again, or hold", "SYSTEM_2"),
        # associative_graph: deliberative route
        ("connect hippocampus replay to the ablation harness findings",
         "SYSTEM_2"),
    ] * 5,  # 30 turns: enough for a stable mean, short enough to rerun
}

# Every gate must fire for the stressed workload to be valid. If any of
# these never fire, the numbers are not measuring ablation at all and the
# run is reported as INVALID rather than as "no effect".
#
# All six, not a subset. An early draft required only defeater_graph and
# counterfactual, and that was not enough: a run where 3 of 6 gates never
# fired still printed a table of deltas, and every dead gate's delta read
# as a confident "this subsystem costs nothing". Requiring all six turns
# the most dangerous failure mode -- a negative result produced by a
# workload that never exercised the subsystem -- into a hard error.
MUST_FIRE = GATE_NAMES


class AblationRun:
    """One pass of the workload with a set of gates suppressed."""

    def __init__(self, disabled: Sequence[str] = ()):
        self.disabled = set(disabled)

    def measure(self, turns: Sequence[Tuple[str, str]]) -> Dict[str, Any]:
        from brain.hermes_brain import HermesBrain

        brain = HermesBrain()
        wiring = CognitiveWiring(brain)

        # Seed the timeline. gate_chronesthesia refuses to fire while
        # timeline_events is empty, so without a recorded event the gate
        # is permanently dead under every workload -- and a dead gate
        # reports a clean zero-delta ablation, which reads as "chronesthesia
        # costs nothing" rather than "chronesthesia was never called".
        # Seeding is done identically for control and ablated runs, so it
        # does not bias the comparison.
        brain.chronesthesia.record_timeline_event(
            event_id="ablation-seed-0",
            description="initial state before the ablation workload",
            state_snapshot={},
        )

        fired: Dict[str, int] = {n: 0 for n in GATE_NAMES}
        ran_any = 0
        errors = 0
        durations: List[float] = []

        for text, mode in turns:
            # The suppression is applied by wrapping each gate so a
            # disabled subsystem reports "did not run" without the rest
            # of run() knowing anything changed. Editing run() to
            # understand ablations would put experiment code in the
            # production path.
            for name in self.disabled:
                setattr(wiring, f"gate_{_gate_method(name)}",
                        _suppressed(wiring, f"gate_{_gate_method(name)}"))
            t0 = time.perf_counter()
            try:
                out = wiring.run(text, mode, "ablation")
                durations.append(time.perf_counter() - t0)
                if any(entry.get("ran") for entry in out.values()):
                    ran_any += 1
                for name, entry in out.items():
                    if entry.get("ran"):
                        fired[name] = fired.get(name, 0) + 1
            except Exception:
                errors += 1
            finally:
                for name in self.disabled:
                    # restore so the next turn starts from the same
                    # state; a leaked wrapper would disable a gate
                    # permanently and silently shrink later trials.
                    _restore(wiring, name)

        return {
            "disabled": sorted(self.disabled),
            "fired": fired,
            "turns": len(turns),
            "turns_with_any_subsystem": ran_any,
            "errors": errors,
            "mean_turn_s": round(statistics.mean(durations), 6)
            if durations else None,
            "median_turn_s": round(statistics.median(durations), 6)
            if durations else None,
        }


_GATE_TO_METHOD = {
    "defeater_graph": "defeater",
    "agm": "agm",
    "dialectic": "dialectic",
    "chronesthesia": "chronesthesia",
    "counterfactual": "counterfactual",
    "associative_graph": "associative_graph",
}

_ORIGINALS: Dict[int, Dict[str, Any]] = {}


def _gate_method(gate: str) -> str:
    return _GATE_TO_METHOD[gate]


def _suppressed(wiring, attr: str):
    """Wrap a gate so it always reports 'not run'."""
    def _off(*_a, **_k):
        return False, f"ablated: {attr}"
    return _off


def _restore(wiring, gate: str) -> None:
    # Re-instantiating the wiring object is the reliable restore; the
    # suppression is a bound-attribute change, not a state change, and
    # CognitiveWiring is cheap to build. Restoring a saved function
    # object instead is subtly wrong because they are bound methods.
    wiring.__dict__.pop(f"gate_{_gate_method(gate)}", None)


def run_load(load_name: str, trials: int = 3) -> Dict[str, Any]:
    if load_name not in LOADS:
        raise SystemExit(f"unknown load {load_name!r}; "
                         f"choose from {sorted(LOADS)}")
    turns = LOADS[load_name]

    # WARMUP, discarded.
    #
    # Without this every single delta came out negative -- ablating a
    # subsystem appeared to make the turn SLOWER, which is impossible.
    # Cause: the control trials ran first and paid all the first-call
    # costs (imports, lazy attribute init, allocator warmup), so the
    # ablated trials ran later on a warmer process and came out faster.
    # Every gate then looked like it was costing negative time.
    #
    # This is the same class of error as measuring at light load: the
    # harness reports a confident number, and the number is an artifact
    # of the harness rather than of the thing being measured.
    AblationRun().measure(turns)
    AblationRun().measure(turns)

    # Control and ablated trials are INTERLEAVED, round by round. An
    # earlier draft ran all controls then all ablations and documented
    # sequential ordering as a "known limit"; interleaving is strictly
    # better for a few lines, so the limit is removed rather than
    # documented. Drift now hits every condition equally instead of
    # penalising whichever ran last.
    conditions: List[str] = ["<control>"] + list(GATE_NAMES)
    acc: Dict[str, List[Dict[str, Any]]] = {c: [] for c in conditions}
    for _round in range(trials):
        for cond in conditions:
            disabled = () if cond == "<control>" else (cond,)
            acc[cond].append(AblationRun(disabled).measure(turns))

    controls = acc["<control>"]
    results = {g: acc[g] for g in GATE_NAMES}

    control_mean = statistics.mean(
        c["mean_turn_s"] for c in controls if c["mean_turn_s"] is not None)
    control_fired = {n: statistics.mean(c["fired"].get(n, 0) for c in controls)
                     for n in GATE_NAMES}

    table: Dict[str, Any] = {}
    for gate, trials_for_gate in results.items():
        m = statistics.mean(t["mean_turn_s"] for t in trials_for_gate
                            if t["mean_turn_s"] is not None)
        fired_here = statistics.mean(t["fired"].get(gate, 0)
                                    for t in trials_for_gate)
        table[gate] = {
            "mean_turn_s": round(m, 6),
            "delta_s": round(m - control_mean, 6),
            "delta_pct": round((m - control_mean) / control_mean * 100, 2)
            if control_mean else None,
            "times_fired": fired_here,
            "times_fired_when_present": control_fired.get(gate, 0),
            "fired_delta": round(fired_here - control_fired.get(gate, 0), 2),
            "errors": sum(t["errors"] for t in trials_for_gate),
        }

    fired_any = max((c["fired"].get(n, 0) for c in controls for n in GATE_NAMES),
                    default=0)
    invalid = [g for g in MUST_FIRE if control_fired.get(g, 0) == 0]

    return {
        "load": load_name,
        "turns_per_trial": len(turns),
        "trials": trials,
        "control_mean_turn_s": round(control_mean, 6),
        "control_fired": control_fired,
        "gates": table,
        "valid": not invalid,
        "invalid_reason": (
            f"gates never fired under this load: {invalid}. Ablating a gate "
            f"that never runs cannot show an effect, so these numbers "
            f"measure nothing. Use --load stressed." if invalid else None),
        "known_limits": [
            "Single-gate ablation measures marginal contribution given the "
            "other five present. A subsystem that only matters when another "
            "is absent will read as zero here.",
            "Wall-clock delta is a proxy for cost, not for value. A slow "
            "subsystem can be earning its keep; a fast one can be dead "
            "weight. Read both columns.",
            "Per-turn times are sub-millisecond, so they are within "
            "range of scheduler noise. Treat any delta under ~5% as "
            "unresolved rather than as zero. Raise --trials before "
            "believing a small number.",
        ],
    }


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(
        description=(__doc__ or "ablation harness").split("\n")[0])
    ap.add_argument("--load", action="append", choices=sorted(LOADS),
                    help="repeatable; default stressed")
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    loads = args.load or ["stressed"]
    AUDIT.mkdir(parents=True, exist_ok=True)

    for load_name in loads:
        print(f"\n=== ablation: {load_name} ===")
        res = run_load(load_name, trials=args.trials)
        print(f"  control mean turn: {res['control_mean_turn_s']}s "
              f"over {res['turns_per_trial']} turns")
        print(f"  {'gate':22} {'delta_s':>10} {'delta_%':>8} "
              f"{'fired':>7} {'err':>4}")
        for gate, row in res["gates"].items():
            print(f"  {gate:22} {row['delta_s']:>10.6f} "
                  f"{str(row['delta_pct']):>8} {row['times_fired']:>7} "
                  f"{row['errors']:>4}")
        if not res["valid"]:
            print(f"  INVALID: {res['invalid_reason']}")

        out = Path(args.out) if args.out and len(loads) == 1 else \
            AUDIT / f"ablation-{load_name}.json"
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=1, sort_keys=True)
        print(f"  -> {out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
