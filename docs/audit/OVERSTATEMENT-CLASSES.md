# Classifying the 1,229 — and retracting the word "overstated"

**the operator's correction, 2026-09-28:** *"We shouldn't do anything on all of
them because downgrading all of them would be wrong because not all of
them should be downgraded and it might be that none of them should be
downgraded once you've done the appropriate work on each of the files
individually."*

He was right, and the reason is that my original finding was framed
wrong. I called these 1,229 files **overstated** and asked whether to
downgrade them. The question was malformed: it assumed one file type
with one correct answer, when these are at least four different kinds
of thing, only one of which is actually overstating anything.

The pilot collapsed 1,229 files into a single bucket by asking one
question — *does this cite an external URL?* — and that question has
four different correct answers depending on what the file is.

## The result

| work class | files | what it is |
| --- | ---: | --- |
| `d_needs_individual_reading` | 527 | genuinely mixed; must be read |
| `a_unsourced_synthesis` | 496 | long LLM synthesis, no source — the real problem |
| `n_navigational_not_applicable` | 167 | a table of contents; confidence does not apply |
| `c_record_of_decision` | 37 | a record of what was decided |
| `b_first_party_description` | 2 | our own deployment, read from config |
| **total** | **1,229** | |

**Nothing was written to any wiki file.** Per-file rows are in
[`overstatement-classes.csv`](overstatement-classes.csv).

## Why four treatments, not one

**167 navigational — not a downgrade case at all.** The schema's own
`load_bearing_definition` says *"navigational metadata are not
load-bearing"*, and `page_level_formula` returns *ungraded* when there
is no load-bearing claim. A table of contents asserts nothing. The
`confidence: high` on these is **meaningless rather than false** —
a different problem with a different fix, arguably `not_applicable`
rather than any band.

**37 decision records.** A decision record cites *the decision*, not
literature. "The owner ruled X on date Y" is established by the record
itself plus session provenance. **The rubric has no tier for this**,
because the rubric was written for claims about the world, not records
of what was decided. Downgrading these would be flatly wrong, and
adding a tier for them is a schema change for the operator to make.

**2 first-party descriptions.** These cite `config.yaml`,
`honcho.json`, `cron/jobs.json`, `git describe`, `docker inspect` —
the actual state of the operator's deployment. That is authoritative
provenance. It is not a public URL and does not need to be.

**496 unsourced synthesis.** *This* is where the original charge holds.
`research/RESEARCH.md` is 17,361 words of LLM-generated industry
analysis with `sources: []`. E11 caps an unattributed AI-written page
at T5, so its `medium` is unearned. Still needs per-file work — some
of these are genuinely fine as T5 observations, and the right answer
might be `ungraded` rather than `low`.

## Two classifier bugs found and fixed

Both were caught by reading actual files rather than trusting the
first answer, and both would have produced confidently wrong labels.

**Length is not the test for navigational.** The first pass used word
count, and filed `research/RESEARCH-INDEX.md` — 1,336 words of
`| [[slug]] Title | done |` — into the *synthesis* class. Only 7 of 231
files typed `index` are link-dominant by markdown link alone; counting
`[[wikilinks]]` moves that to 121. The test is now link share, and an
index can never be a synthesis however long it is.

**First-party provenance is not a session id.** The check for own-system
documentation was `'session' in src_kinds | set(str(s) for s in
src_kinds)` — a union of a set of words with a set of single
characters, so it matched essentially at random. It fired on 1 file in
21. Fixing the test to a plain membership check exposed the real
finding: the genuine sources are `config.yaml` and `docker inspect`,
which the classifier had been treating as *unknown*, making a
well-documented page look undocumented. That is exactly backwards.

## What still needs you

Three decisions, and none of them are mine to make:

1. **Add a tier for decision records?** The rubric cannot currently
   express "authoritative, because it is the record of the ruling."
   37 files and growing.
2. **`not_applicable` vs `ungraded` for navigational pages?** 167
   files. A table of contents is not low-confidence, it is
   un-rateable.
3. **The 496 synthesis files.** Whether these get `ungraded`, `low`, or
   get sources attached is a per-file judgement — which is the work,
   not a batch operation.

The 527 in `d_needs_individual_reading` are the honest remainder. They
are `reference` files of 200–6,000 words where the source situation
varies within the file, and no rule I can write will grade them
correctly. They need reading.
