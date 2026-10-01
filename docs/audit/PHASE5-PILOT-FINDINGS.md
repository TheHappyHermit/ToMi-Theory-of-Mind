# Phase 5 pilot — what the evidence actually supports

Pilot run 2026-09-28. **Analysis only: no wiki file was written.** The
per-file audit is [`confidence-pilot.csv`](confidence-pilot.csv), 2,574
rows, one per file, with the reason for every call.

## What this pilot did and did not do

It did **not** map `confidence_reported: 0.85` to a band. The research
([`CONFIDENCE-RESEARCH.md`](../CONFIDENCE-RESEARCH.md)) established that
0.85 is an unvalidated self-report from an unrecorded rubric, so any
float→band cut-off would be an invented threshold written down as though
it were derived.

It applied `schemas/okf-schema.yaml` → `confidence_derivation` to each
file's **actual sources**, using only the mechanical parts of the rubric:
T1/T1b/T2/T3/T4/T5 classification, `minimum_source_rule`, and the
weakest-link `page_level_formula`.

## The result, over the full corpus

| derived band | files |
| --- | ---: |
| UNGRADED (rubric yields no grade) | 1,495 |
| low | 622 |
| medium | 233 |
| high | 224 |
| **total examined** | **2,574** |

**1,951 of 2,574 (76%) need a human decision**, and the pilot refuses to
make it. That is the honest output, not a failure to finish.

### After host resolution

`scripts/resolve_source_hosts.py` classified **62 of the 132** unrecognised
hosts against the rubric's own tests — NeurIPS/ICML/ICLR/CVF venues and
DBLP-style indexes are T2, W3C/OWASP/MCP/Envoy/ArchLinux docs are T1,
readthedocs/PyPI/CRAN and project docs are T4, personal and aggregator
sites are T5. Effect on the totals:

| | before | after |
| --- | ---: | ---: |
| high | 155 | **224** |
| medium | 197 | 233 |
| low | 726 | **622** |
| UNGRADED | 1,496 | 1,495 |

`high` rose because real peer-reviewed venues were previously
unrecognised. `low` fell by 104 because files whose *only* sources were
unrecognised hosts are now correctly identified as weak sources rather
than treated as unclassifiable.

**69 hosts remain unresolved**, almost all appearing once or twice. They
are individual project sites, university pages and personal blogs, and
deciding them is a per-site judgement rather than a rule. That is the
honest place to stop.

Two invariants were checked explicitly after the change:

- **5 files cite the operator's own LAN address** (`10.0.0.10:8080`) as a
  source. Those are not sources at any tier, and the classifier says so
  explicitly rather than grading them.
- **Zero files reach `high` on a T5 source alone.** The
  `minimum_source_rule` holds: `high` requires a T1 or T2, or two
  independent T3+.

## The finding that matters

**1,229 files currently declare `confidence: high` or `medium` while
carrying no resolvable source whatsoever** — `sources: []`, or a source
list the rubric cannot tier.

| vault | files claiming high/medium with no resolvable source |
| --- | ---: |
| oracle-brain | 1,161 |
| active-wiki | 68 |

Verified on two real examples: `AGENTS.md` (445 words) and
`GAP-ANALYSIS-ROUND2.md` (3,291 words) both declare `confidence: high`
with `sources: []`.

Under the rubric, E11 is decisive: *"All claims are at most T5 until an
external source is attached... `generated.by` alone confers nothing."*
These files are almost entirely LLM-generated, so their declared
confidence is currently **unearned**.

This is not an argument that the content is wrong. A 3,291-word gap
analysis may be perfectly good. It is an argument that `high` is a claim
about *evidence*, and there is no evidence recorded to support it. The
research report's over-trust finding is about exactly this: a number that
out-competes the evidence behind it.

## Why 80% needs a human

The rubric grades each **load-bearing claim** separately and takes the
minimum (E7). Deciding which sentences are load-bearing requires reading
the page and judging intent. That is not mechanical.

1,186 files have **no resolvable source at all** — correctly UNGRADED.
272 more have sources the classifier could not tier, and the pilot
refuses to guess at a host it does not recognise.

The classifier was widened once during the pilot. It initially missed
`iana.org`, which the rubric's own T1 test names explicitly ("IANA
registry entry"), and the peer-review indexes T2 names by name (DBLP,
PMLR, ACL Anthology, PubMed, OpenReview). Fixing that moved `high` from
11 to 32 in the 400-file sample. **The remaining 272 are genuinely
unrecognised**, not known-and-ignored.

## What happens next, and what it costs

The 2,048 flagged files fall into three groups, in descending order of
value:

1. **The 1,229 overstated files.** A decision is needed: either attach
   sources, or set them to `ungraded`/`low` to match the evidence. This
   is the highest-value work in the whole project, because until it is
   done the corpus advertises confidence it cannot support.
2. **The 69 hosts still unresolved.** Mostly single-occurrence project
   sites, university pages and personal blogs. Each is a lookup, not a
   judgement. The other 203 were resolved by
   `scripts/resolve_source_hosts.py`; see the table above.
3. **The ~547 graded files.** These are the ones where the rubric
   produced a defensible answer. They still need spot-checking, because
   the classifier reads URLs, not documents: it cannot tell whether a
   DOI *resolves to a document whose title and authors match the
   citation as written*, which T2's own test requires.

**Recommendation: do not bulk-apply.** 155 files would move to `high`
on the strength of a URL pattern alone. That is the same class of error
as the 0.85 mapping, at a larger scale.

## What is safe to do now

Nothing writes. The CSV is an audit artifact: every row carries a
reason, so any single decision can be reviewed or overturned without
re-running the analysis. The pilot script is `scripts/phase5_pilot.py`
and defaults to analysis.

If Phase 5 proceeds, the defensible order is:

1. Resolve the 272 unclassified hosts (mechanical, no judgement).
2. Decide the 1,229 overstated files — this needs an owner ruling on
   whether an LLM-written page with no source may be anything but
   `ungraded`. **That is a policy question, not a research one.**
3. Verify DOIs resolve and titles match, for the files that would
   become `high`. That is the T2 `ceiling_qualifier` and it is the only
   thing standing between a URL pattern and an earned `high`.

Step 2 is blocked on the operator. Steps 1 and 3 are not.

## Appendix: the search sync is slow, not hung

Recorded 2026-09-28 because it will look like a failure to anyone
checking on it, and the obvious response — kill and restart — is
exactly the wrong one.

The resync sat at 202 files for several minutes with a completely quiet
log. Checked rather than assumed:

- log growth over 20s, 60s and 80s: zero new bytes
- process state `S` (sleeping), 0.2% CPU, single-threaded
- `wchan` = `poll_schedule_timeout`, i.e. blocked on a socket read
- 2 established connections to the embedding server on `:18082`
- the server healthy: `/v1/models` 200 in 1ms, live embedding succeeds
- CPU time delta over 15s: 1 tick, so it is not spinning
- no `.md` file open, so not stuck on disk I/O

Every signal said "waiting on the network", and the network was fine.
Waiting 200s produced the answer:

    [ok] research/BUILD-PLAN-AGENDA.md: 249 chunks

**One file produced 249 chunks.** `embed_texts_with_retry` sets
`timeout = 120 + 10 * len(texts)`, so a 249-chunk batch allows 2,610
seconds per attempt, and the log prints nothing for the whole duration
because per-chunk progress is not logged.

It is a long tail, not a hang:

| | |
| --- | ---: |
| files processed | 203 |
| total chunks | 3,157 |
| median chunks | 14 |
| p90 chunks | 21 |
| max chunks | 249 |

The median file takes seconds. The tail takes tens of minutes and is
indistinguishable from a hang in the log.

**Do not kill it.** A restart would discard the work done so far, and
because the sync is incremental on `file_hash`, most of it would have
to be redone. Waiting 200 seconds answered the question definitively;
killing on a quiet log would have cost 58 minutes of embedding.
