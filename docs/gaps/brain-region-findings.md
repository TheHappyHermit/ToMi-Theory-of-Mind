# Brain-region build-vs-link: first/second/third choice per region

Date: 2026-09-29. Six researcher subagents surveyed GitHub + arXiv per
region; findings were verified against our own source before use.
Verdict shape: **EXTEND almost everywhere.** Nothing in this niche is
both good and adoptable. The dominant failure mode is not absence of
prior art -- it is absence of *licensed* prior art.

Three repos named as authoritative turned out to be empty shells:
`lixiaochuan2020/agentic-context-management` (main.py is 5 prints),
`Tencent/ContextPilot` (4 files), `ADaM-BJTU/MemAct` (2 files).
`alinvdu/computational-somatic-markers` markets itself as
state-of-the-art and contains one README and zero code.

## Verified against our source

Confirmed by reading the files, not by trusting the report:

| claim | verdict |
|---|---|
| `epistemology/dialectic.py` is string templating | CONFIRMED, 36 lines, fixed `scope_differentiation` f-string |
| `epistemology/agm.py` is not AGM | CONFIRMED, 82 lines, no closure/remainder/partial-order |
| `social/tom.py` has no recursion | CONFIRMED, 109 lines, 5 methods, no level-2/recursive method |
| `hippocampus/replay.py` consolidates nothing | CONFIRMED, `consolidated_insight` is an f-string, no LLM call |
| `thalamus/buffer.py` has no policy | CONFIRMED, `deque(maxlen=100)`, no eviction logic |
| hippocampus edges are not bi-temporal | CONFIRMED for hippocampus: `superseded_by` only ever READ there. CORRECTION: it IS written by decision_logger and to-do-capture, so the column is not dead everywhere |
| `thalamus` saliency never written | CORRECTED -- it IS written, `hermes_brain.py:249`. The gate is live; the *buffer* is the part with no policy |
