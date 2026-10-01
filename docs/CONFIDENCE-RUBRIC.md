# The confidence rubric — researched, cited, and awaiting your ruling

Written 2026-09-28. You asked for this to be researched before the handoff
prompt was written. It is now in `schemas/okf-schema.yaml` as
`confidence_derivation`, validated, and **gated on two decisions that are
yours to make.**

Nothing has been applied to any wiki file. `owner_ruling_required: true`.

## What OKF actually says

Verified against `SPEC.md` (37,748 bytes): **`confidence` appears 0 times,
`epistemic` 0 times.** Upstream has no confidence scale at all.

It does something more interesting instead. §5.1 records per-source
credibility signals — `author`, `usage_count`, `last_modified` — and says
explicitly:

> It does not store a credibility score: a score is subjective, unportable
> across consumers, and goes stale. Credibility is *inferred* from the
> signals, the same way trust tiers are, not stored.

So **deriving rather than storing is upstream's own position.** Our rubric is
aligned with that principle, but it is a **local invention, not an OKF
conformance claim**, and the schema says so.

## The spine: GRADE, adopted

- **GRADE** (Guyatt 2008, [doi:10.1136/bmj.39489.470347.AD](https://www.bmj.com/content/336/7650/924)) — 4 levels, **downgrade-first**, ceiling-not-floor. ([GRADEbook](https://book.gradepro.org/guideline/principles-for-assessing-the-certainty-of-interventions))
- **Cochrane Handbook ch.14** — certainty is **per-outcome**, may vary within one review.
- **SIFT** (Caulfield 2019) — supplies the modifier mechanics.
- **Wikipedia:Reliable_sources** — supplies the source-type table.

**Rejected, with reasons:** Oxford CEBM (needs a PICO question to index its grid; the 2011 redesign explicitly moved away from ranking designs). CERIF (models provenance, not evidential weight). FAIR (grades data hygiene, not truth). CRAAP (self-critiqued as leading students astray; its axes aren't decidable from a file).

**Adopted from the other side:** GRADE's structure, SIFT's modifiers, WP:RS's source judgements. Nothing supplies a machine-decidable *source tier* — that gap is what we fill.

## The tiers

| Tier | Source | Level |
|---|---|---|
| T1 | Published standard (RFC, ISO, W3C Rec, NIST SP, IANA) | **high** |
| T1b | Internet-Draft (has `Expires:`, no RFC number) | **medium** |
| T2 | Peer-reviewed, DOI resolves and matches | **high (ceiling)** |
| T3 | Preprint, textbook, journalism, gov statistics | **medium** |
| T4 | Vendor docs, blog, marketing, no independent coverage | **low** |
| T5 | Consumer reviews, LLM inference | **low** |
| T6 | Personal experience, anecdote | **low** |

Semantics are GRADE's: *high* = further retrieval unlikely to change the
claim; *low* = likely to overturn it.

Two rules that will surprise you:

- **A blog + news story + vendor page all citing one paper = ONE source.** Reliability is judged on the original, not the count.
- **Page confidence = the weakest claim on the page.** Not the average. Grounded in Cochrane's per-outcome certainty — and it's the rule that stops 2,855 files from averaging their way to `high`.

## Two decisions I need from you

### C1 — is peer-reviewed a ceiling or automatic?

**You said:** peer-reviewed → high.
**Research says:** GRADE treats design as a *starting* rating. Peer-reviewed
designs are routinely downgraded for bias, inconsistency, indirectness,
imprecision, publication bias.

**Evidence that makes this non-obvious:** the research hit a real example
while working. `doi.org/10.1109/ICDM.2013.83` resolves to *"Non-negative
Multiple Tensor Factorization"* — completely unrelated. A guessed DOI
produced a real, resolving, **wrong** paper. With **1,088 doi.org URLs in
the corpus**, this is not hypothetical.

- **Ceiling (research position):** peer-reviewed starts at high; modifiers can lower it. *Many currently-`high` pages will drop to medium.*
- **Flat (your original):** peer-reviewed *is* high, no downgrade.

### C2 — do consumer reviews mean medium?

**You said:** highly reviewed product → medium.
**Research says: low**, on peer-reviewed evidence. He, Hollenbeck &
Proserpio, *"The Market for Fake Reviews,"* **Marketing Science** (INFORMS):
of products caught soliciting fake reviews, *"roughly half of their reviews
were eventually deleted... average lag of over 100 days,"* and
manipulation *"mostly centers on low-quality products."*

**A review count is a purchasable quantity.** Under this rubric, a product
with 5,000 possibly-purchased reviews would rank *below* a preprint.

- **Keep medium (your original):** volume counts.
- **Research position:** volume never raises confidence; the medium criterion becomes *independent review under conflict disclosure*.

I lean toward the research on both, but C2 is a direct downgrade of what you
asked for, so it's your call, not mine.

## A correction: the survey measured the wrong corpus

**Every corpus number the research reported was wrong**, in one direction —
it measured the Active Wiki (622 files) and **never touched the Oracle vault
(2,382)**. I re-measured everything:

| Claim | Research said | Actually |
|---|---:|---:|
| corpus size | 622 | **2,855** |
| `confidence: high` | 381 | **1,577** |
| `confidence: medium` | 30 | **759** |
| float confidence values | 112 | **222** |
| `verified: []` | 352 | **2,107** |
| internal wikilink bullets | 313 | **1,868** |
| arxiv.org URLs | 166 | **5,036** |
| structured `sources[]` adopted | 1 | **2** |

**The ratios still hold** — the research's judgement is sound, its
denominator was wrong. But the *volume* of work roughly quadruples, and
`5,036` arXiv URLs means the DOI-resolution step is much bigger than planned.

**A worse finding: 222 files carry a float** (`0.85`, `0.92`, `0.88`) —
not 112, and not the 225 the linter reported. Those files violate
`confidences: [high, medium, low]`. The corpus doesn't conform to its own
schema, and that's a *separate* defect from the confidence re-derivation.

## Also found: a stale third vault

`/home/operator/personal-agent/oracle/brain` — 381 files, a git repo, last
committed **Aug 22**, last written **Sep 1**, 115 uncommitted changes, no
remote. It is **not** live and nothing writes to it (the health check
references `personal-agent/secrets`, not the vault — I checked, because
"two live jobs write into a stale clone" was my first read and it was wrong).

**Flagged, not touched.** It is exactly the kind of directory that makes an
agent edit the wrong tree over 20 context windows, so the handoff prompt
names the two real vaults explicitly and lists this one as off-limits.

## One more thing I found

`~/scripts/brain_sync.py` still uses `AUTOGNOSIA_HOME`. **It is not broken** —
it defaults to `Path.home() / ".hermes"`, which is correct. But it's one
environment variable away from ingesting 14,930 files from
`bak_autognosia`. Noted in the prompt; not changed.

## What happens next

Once you rule on C1 and C2:

1. Set `owner_ruling_required: false` with your decisions recorded inline.
2. Write the handoff prompt with the tracking MD file.
3. Confidence re-derivation becomes a phase — per-claim, weakest-link,
   with the 222 floats handled as a schema violation first.

**Sequencing note from the research:** DOI resolution is the highest-value
and most expensive step. Run it as a batch job *first* — it will find
identifier mismatches that are currently invisible, and it's the check most
likely to catch a real fabrication. 1,088 DOIs and 5,036 arXiv URLs.
