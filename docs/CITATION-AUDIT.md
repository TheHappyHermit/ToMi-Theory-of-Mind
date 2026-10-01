# Citation Audit — Oracle vault

Verified 2026-09-25. Method: `scripts/verify_citations.py`, which resolves each DOI
through Crossref and compares the resolved title against the title the vault claims.

**Why this exists.** A DOI that resolves to the *wrong paper* is worse than no DOI.
It looks verified, it survives a casual read, and it sends a reader to confident
nonsense. A human skimming a reference list will not catch it.

## Result: 8 of 8 citations in the file checked are broken

`oracle/brain/Prospective-Memory/Implementation-Intentions.md`

| DOI as cited | Status | Actually resolves to |
|---|---|---|
| `10.1037/0033-295X.106.4.593` | 404 | — (Gollwitzer 1999 is at a different DOI, below) |
| `10.1037/0033-295X.113.1.119` | 404 | — |
| `10.1146/annurev.psych.57.102904.190214` | 404 | — (wrong journal *and* wrong DOI) |
| `10.1016/j.pdpt.2006.03.001` | 404 | — |
| `10.1037/a0014922` | **MISMATCH** (0.25) | *"George G. Thompson (1914–2008)"*, American Psychologist |
| `10.1016/j.jrp.2008.12.003` | **MISMATCH** (0.00) | *"Appreciating life's complexities: Assessing narrative ego integrity in late midlife"*, J. Research in Personality |
| `10.1037/bul0000100` | **MISMATCH** (0.33) | *"The effects of acute stress on episodic memory: A meta-analysis and integrative review"*, Psychological Bulletin (2017) |
| `10.1080/17439760.2018.1445875` | 404 | — |

Three of the mismatches resolve to papers on **completely unrelated topics** — a
biographical note, narrative ego integrity, and acute stress and memory. A fourth
resolves to a real meta-analysis but about a different subject.

## Corrected DOIs for the works the file intends to cite

Found by querying Crossref for the actual titles, then verified:

| Work | Correct DOI | Venue |
|---|---|---|
| Gollwitzer (1999), "Implementation intentions: Strong effects of simple plans" | `10.1037/0003-066x.54.7.493` | American Psychologist 54(7) |
| Gollwitzer & Sheeran (2006), "Implementation Intentions and Goal Achievement: A Meta-analysis of Effects" | `10.1016/S0065-2601(06)38002-1` | Advances in Experimental Social Psychology |

Note the second is **not** in an *Annual Review of Psychology*, as the vault claims.

**These corrections are recorded, not applied.** The vault lives outside this repo
and is a separate body of work; editing it is a decision for its owner, not a
side effect of writing this file. The `docs/` in this repo never import the vault
directly, so nothing here is wrong *because* the vault is wrong — but any claim
sourced from that file needs its citation re-checked first.

## What this does and does not mean

**It does not mean the underlying scholarship is wrong.** Implementation intentions
is a large, well-replicated literature. The *ideas* in that file are broadly
consistent with it.

**It does mean the file's citations cannot be trusted as pointers**, and any specific
numeric claim attributed to a specific paper there should be re-verified against the
real paper before being used. The vault file itself flags `verified: []` and
`generated: by "unknown"`, so it is not claiming to be verified.

## The generalisable lesson

The vault contains high-quality synthesis — the `Adaptive-Forgetting.md` dossier, for
instance, grades its own evidence honestly and documents a replication crisis
(Basden et al. 2014 failed to replicate retrieval-induced forgetting at N=288;
Huettl et al. 2021 found a small reliable effect at N=630; Depret et al. 2020's
meta-analysis of 105 experiments puts the effect at d=0.31 falling to ~0.15 once
publication bias is corrected). That is the right way to handle contested evidence.

But **synthesis quality and citation accuracy are independent**, and a reader can
conflate them: a careful, hedged, well-organised document still sends you to the
wrong paper if its DOIs are wrong. Treating "this document is well-written" as
"this document is verified" is the failure mode this audit exists to prevent.

Run it over the vault before relying on any citation:

```bash
python3 scripts/verify_citations.py /path/to/vault/file.md
```

It is not wired to cron. It hits a public API, Crossref throttles aggressively, and
more importantly a citation audit that auto-fails on a transient rate limit trains
people to ignore it.
