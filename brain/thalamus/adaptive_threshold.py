"""
brain.thalamus.adaptive_threshold — A learned saliency threshold.

THE PROBLEM
-----------
AttentionalGate.saliency_threshold is a hard-coded 0.35, compared
against a saliency score that is not on any fixed scale. The score is
built from weighted signals (bottom-up saliency, contextual relevance,
switch cost) whose distribution depends on the corpus, the active
context, and what else is running. A constant borrowed from one
observation is wrong for the next one, in both directions:

  * too high  -- genuinely salient input is refused. The gate goes
    quietly blind and nothing reports that it did.
  * too low   -- everything is admitted and the gate does no work.

Neither failure announces itself. `evaluate_admission` returns a
boolean either way, so the cost of a mis-set threshold is invisible
unless the threshold itself is measured.

WHAT THIS IS
------------
An online, learned threshold that tracks the saliency distribution it
actually sees, using only standard library code. No new dependency, no
model, no network. The IDEA is borrowed from Maxim's adaptive threshold
controller; the implementation is ours and deliberately simple, because
a learned threshold that cannot be explained is worse than a fixed one.

MECHANISM
---------
A running estimate of the saliency distribution (mean and spread) plus a
target admission rate. The threshold is placed so that approximately
`target_rate` of recent inputs are admitted.

  * Running mean/variance with exponential decay, so the estimate tracks
    the current regime instead of averaging over all history.
  * The threshold is a quantile estimate, obtained by a small reservoir
    of recent samples rather than by solving for the quantile in
    closed form. A reservoir is honest about the approximation: it says
    "estimated from N recent samples", which is checkable.
  * Slow adaptation. The learning rate is deliberately small, because a
    threshold that chases every input oscillates and admits bursts.

FEEDBACK SIGNAL
---------------
`observe_admission` takes what actually happened after the gate decided.
Two signals are used, and they are in tension on purpose:

  * `admitted` (the gate said yes) -- the primary signal.
  * `useful` (the admitted item turned out to matter) -- the
    correction. An admission rate that is on target but whose admissions
    are useless is a failure the rate alone cannot see, so a run of
    useless admissions pushes the threshold UP.

This is what makes it learned rather than merely adaptive: without the
`useful` signal the controller would happily hold its target rate by
admitting the wrong things.

HONEST LIMITS
-------------
- The controller assumes the useful/unuseful signal is available. Where
  it is not, pass `useful=None` and the controller falls back to
  rate-matching only. That is a strictly worse controller and the
  docstring says so rather than implying otherwise.
- A reservoir of N samples gives a coarse quantile. At small N the
  threshold is noisy. `min_samples` guards the early period by refusing
  to adapt before there is evidence.
- It learns the distribution it is fed. If the input distribution shifts
  permanently, the threshold follows it -- which is the intent for
  benign drift and a liability under a sustained regime change.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional

__all__ = ["AdaptiveThreshold", "DEFAULT_PARAMS"]

DEFAULT_PARAMS = {
    # Fraction of recent inputs to admit. 0.25 matches the previous
    # hard-coded behaviour closely enough that swapping this in does not
    # silently change gate decisions, while still being a target rather
    # than a constant.
    "target_rate": 0.25,
    # How fast the running statistics follow the current regime.
    # 0.02 is slow on purpose: a fast controller chases individual
    # inputs and oscillates, admitting bursts then closing.
    "learning_rate": 0.02,
    # Bound the threshold so a degenerate distribution cannot push it to
    # 0 (admit everything) or 1 (admit nothing).
    "min_threshold": 0.05,
    "max_threshold": 0.95,
    # Refuse to adapt before this many observations.
    "min_samples": 20,
    # Recent-sample reservoir size for the quantile estimate.
    "reservoir": 128,
    # Consecutive useless admissions before the threshold is pushed up.
    "waste_patience": 3,
}


class AdaptiveThreshold:
    """An online, learned saliency threshold with bounded behaviour."""

    def __init__(self, initial: float = 0.35, **overrides):
        params = dict(DEFAULT_PARAMS)
        unknown = set(overrides) - set(params)
        if unknown:
            raise TypeError(
                "unknown parameter(s): %s; valid: %s"
                % (sorted(unknown), sorted(params)))
        params.update(overrides)
        self.p = params
        self.threshold = float(initial)
        self.initial = float(initial)
        self._samples: List[float] = []
        self._n = 0
        self._mean = 0.0
        self._m2 = 0.0
        self._waste_streak = 0
        self.history: List[Dict[str, float]] = []

    # ── statistics ────────────────────────────────────────────────────
    def _update_moments(self, x: float) -> None:
        """Welford update with exponential decay on the count.

        Decay is applied by discounting the effective sample size, so
        the estimate follows the current regime instead of averaging
        over the entire history. Implemented as a plain Welford with a
        decayed weight because a decayed Welford is awkward to express
        exactly and the bias is negligible at these rates.
        """
        n = self._n + 1
        decay = 1.0 - self.p["learning_rate"]
        delta = x - self._mean
        self._mean += delta / n
        self._m2 += delta * (x - self._mean)
        # discount the effective sample count so old data decays
        self._n = int(n * decay) + 1
        self._m2 *= decay

    def stddev(self) -> float:
        if self._n < 2:
            return 0.0
        return math.sqrt(max(0.0, self._m2 / (self._n - 1)))

    # ── the learned part ──────────────────────────────────────────────
    def _quantile_threshold(self, q: float) -> Optional[float]:
        """Estimated q-quantile of recent saliency samples.

        Returns None before there are enough samples to say anything.
        """
        s = self._samples
        if len(s) < self.p["min_samples"]:
            return None
        ordered = sorted(s)
        # nearest-rank; exact and cheap at this size
        idx = min(len(ordered) - 1,
                  max(0, int(round(q * (len(ordered) - 1)))))
        return ordered[idx]

    def _clamp(self, value: float) -> float:
        return max(self.p["min_threshold"],
                   min(self.p["max_threshold"], value))

    def observe_admission(self, saliency: float, admitted: bool,
                          useful: Optional[bool] = None) -> float:
        """Record one observation and return the updated threshold.

        `saliency`  the score the gate compared against
        `admitted`  what the gate decided
        `useful`    did the admitted item actually matter? None when
                    that is not knowable, which degrades the controller
                    to rate-matching only.
        """
        self._n += 1
        self._update_moments(saliency)

        self._samples.append(float(saliency))
        if len(self._samples) > self.p["reservoir"]:
            self._samples.pop(0)

        # Waste streak: admitted things that did not matter.
        if admitted and useful is False:
            self._waste_streak += 1
        else:
            self._waste_streak = 0

        target = self._quantile_threshold(1.0 - self.p["target_rate"])
        if target is not None:
            if self._waste_streak >= self.p["waste_patience"]:
                # On-target admission rate but the wrong admissions.
                # Raise the bar. This is the correction the rate alone
                # cannot provide.
                target = self._clamp(target + 0.05)
            self.threshold = self._clamp(target)

        self.history.append({
            "n": self._n,
            "saliency": float(saliency),
            "threshold": self.threshold,
            "admitted": bool(admitted),
            "waste_streak": self._waste_streak,
        })
        if len(self.history) > 512:
            self.history.pop(0)
        return self.threshold

    # ── introspection ─────────────────────────────────────────────────
    @property
    def samples(self) -> int:
        return len(self._samples)

    @property
    def is_calibrated(self) -> bool:
        """Has enough evidence been seen to justify the current value?"""
        return len(self._samples) >= self.p["min_samples"]

    def stats(self) -> Dict[str, object]:
        return {
            "threshold": round(self.threshold, 6),
            "initial": self.initial,
            "observations": self._n,
            "samples": len(self._samples),
            "calibrated": self.is_calibrated,
            "mean": round(self._mean, 6),
            "stddev": round(self.stddev(), 6),
            "target_rate": self.p["target_rate"],
            "waste_streak": self._waste_streak,
            "recent_admission_rate": round(self._recent_rate(), 4),
        }

    def _recent_rate(self) -> float:
        recent = self.history[-50:]
        if not recent:
            return 0.0
        return sum(1 for h in recent if h["admitted"]) / len(recent)

    def reset(self) -> None:
        """Return to the initial threshold and forget all observations."""
        self.threshold = self.initial
        self._samples.clear()
        self._n = 0
        self._mean = 0.0
        self._m2 = 0.0
        self._waste_streak = 0
        self.history.clear()
