---
name: verifying-scholarly-citations
description: Use when auditing whether a citation is real.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [research, citations, doi, verification, knowledge-base, audit, provenance]
    related_skills: [grounded-citations, verifier-integrity, bulk-corpus-remediation, ml-paper-writing]
---

# Verifying Scholarly Citations

Classifying citations that already exist in a document: **real / dead
identifier / misattributed (real paper, wrong year-journal) / fabricated (no
such paper) / untitled-but-live**. Also trigger before any bulk "clean up the
references" pass, and when inheriting a handoff that has already classified
some rows.

## When to Use

Audit whether a citation or DOI in a knowledge base, wiki, paper, or report is
real, dead, misattributed, or fabricated — and trigger before editing any
file's reference list. Not for generating new citations (that is
`grounded-citations`); not for formatting a bibliography (`ml-paper-writing`).

The governing asymmetry: **a resolver tells you a DOI exists, never that it is
the work the document means.** Every verdict is a comparison between what the
resolver returned and what the document itself asserts. A green status alone is
not evidence of a correct citation.

## The central discipline

**A 404 is a coverage verdict, not a nonexistence verdict.** Resolver backfiles
have era- and publisher-shaped holes. "The index does not have it" and "it does
not exist" are different claims, and only one of them is usually what you
proved. Pre-2000 print book chapters carry no DOI. Some society prefixes are
never deposited. A single decade of one journal's backfile can be missing
entirely.

Before deleting a citation because its identifier will not resolve, search for
the **paper** — by author, title, and venue — rather than probing the
identifier. This is the expensive mistake: an audit that deleted on 404s would
have destroyed a genuine, body-cited source, because the inherited handoff
instructed exactly that deletion.

## The defect taxonomy — classify before you fix

Run every unresolved row into exactly one bucket. They need opposite remedies.

| Class | Meaning | Remedy |
|---|---|---|
| **untitled** | Resolves, no title in the entry | Write the resolved title in |
| **wrong identifier** | Resolves, but the title is someone else's | Replace the identifier |
| **fabricated** | Work does not exist in any index | Replace **or** withdraw the claim |
| **unattributable** | Identifier dead AND the document never says what it meant | Withdraw, or ask |
| **unregistered but real** | Resolves nowhere; the paper is verifiably real | Cite without a DOI, and say why |

Only the first two are mechanical. The rest are content decisions, and a
citation can be real while still attached to a sentence it does not support.

## Procedure

① **Read the file's body and reference list before touching any identifier.**
Establish what the file *claims* the source says. An identifier you were told
is a duplicate may be the only entry for a paper the body cites. Deleting
first is how a genuine source gets removed from a file that depends on it.

② **Check the DOI stem against a real record before assuming its journal.**
`https://api.crossref.org/journals/<issn-or-stem>` returns the journal title
directly. Stems get misremembered — a stem assumed to be a general psychology
journal is the *review* journal — and a wrong stem guess sends every
subsequent probe at an identifier that could never have existed. A stem that
contradicts the cited venue is itself proof the record is internally
inconsistent.

③ **Measure the resolver's coverage for that journal+year BEFORE reading any
404 as absence.** Two numbers settle it: how many records the index holds for
that journal and year, and whether an article you *know* is in that issue is
present. An index holding a few dozen records for a full volume of a flagship
journal, or missing a known article, cannot refute anything by silence. State
the coverage finding explicitly — it is what licenses or forbids each later
conclusion.

④ **Run a positive control on every instrument, inside the same batch as the
real probe.** Look up an identifier you already know is good. If the control
fails, the whole batch is void. Keep controls in the same run, because an
instrument can rate-limit or bot-block partway through and you will not notice
which result was affected.

⑤ **Treat an empty result from a throttled or blocked API as tooling failure,
never as a literature finding.** If backoff is exhausted and responses are 429
/ 403 / interstitial, the endpoint told you nothing about the paper. Escalate
to non-API routes — third-party bibliographies, citing reference lists, search
snippets, publisher TOCs — rather than reporting the empty set as a finding.

⑥ **Refute fabricated citations with coherence tests that need no resolver.**
These are the strongest instruments and they are free:
   - **Page-span collision.** Enumerate the volume's real articles and their
     page ranges. If the claimed span is already occupied by other articles,
     the citation cannot be a garbled reference to a real paper at that
     location — there was no article there to be garble. Reproduce the issue's
     full page tiling to confirm no gap exists.
   - **Volume/issue emptiness.** A claimed volume+issue holding no such article,
     while neighbouring issues are densely populated.
   - **Author never published in that venue.** Check the author's record.
   - **Year impossible for the venue.** The journal did not exist yet, or the
     volume numbering is inconsistent with the year.

⑦ **Prefer stronger proof when it is available.** A 404 cannot show the paper
did not exist — an unregistered paper and a garbled identifier look identical.
Enumerate the issue instead. Reach for that whenever the claim is "this paper
is fake."

⑧ **Never infer an identifier from a venue pattern.** A stem plus volume and
pages is a guess, not a record. Take identifiers only from something a
resolver returned. A plausible-looking fabricated DOI is worse than an absent
one, because it survives a casual re-check.

⑨ **Re-resolve every identifier a subagent hands you.** Delegates return
confident, well-formatted identifiers for papers that do not support the
claim; one supplied DOI resolved to a completely unrelated paper during this
work. A delegate reporting *no DOI found* is more trustworthy than one
offering a tidy identifier, and a delegate that discards a self-guessed
identifier after a failed probe is behaving correctly.

⑩ **Verify the load-bearing claim too.** "The paper is real" is not "the paper
says this." A correct citation attached to an unsupported sentence is still a
defect. Where the document's own text and the source disagree, record it.

⑪ **For a genuine-but-unregistered work, cite it without an identifier and say
so explicitly.** Note that the source is a pre-registration-era print chapter
with no DOI in any registry. Attaching a plausible DOI to recreate the exact
error being repaired is the failure mode this skill exists to stop.

## Do not force scientific consensus

A citation being real does not make the claim settled. Where reputable work
disagrees, record **each side with its proponent** rather than adjudicating to
one answer. Present both readings, each with its own identifier, and say which
you weight and why. Absence of a consensus verdict is a finding, not a gap to
paper over — and forcing a single answer destroys the information that makes
the entry useful later.

## When a work has no DOI, that is the finding

Pre-2000 book chapters routinely have no DOI and Crossref returns nothing.
Verify the work another way — the authors' own lab hosting the chapter PDF, a
citing paper naming the Festschrift, an independent bibliography — then record
the absence as a verified property. Do not supply an identifier to fill the
gap.

## Bulk-edit safety

The silent-success family: a transformation that matches a pattern, writes
nothing because nothing matched, and exits 0. Guard every bulk edit with a
measured before/after count of what it was supposed to touch, and a
zero-occurrence check before any *removal*. Prove the target strings are
actually gone afterward with an independent grep — not by trusting the writer
that made the change.

A repair script whose guard rejects its own explanatory prose is a good guard
hitting a false positive. Scope the guard to the region being protected (the
source list, the pre-note region) rather than loosening it, and never let a
broad test flag a legitimate bystander — a bare stem match once flagged a
correct *Psychological Bulletin* DOI in the same file.

## Verification

Before declaring the audit closed:

- Re-run the verifier and confirm the counts moved as expected.
- Re-read the edited files on disk, not the diff you intended to write.
- Confirm the full reference list is still contiguous.
- Grep the whole corpus for each removed identifier and confirm zero hits.
- Parse the frontmatter of every touched file.
- Run the project's test suite, and expect a test that asserts the corpus
  *contains* a known defect to fail — the repairs removed the fixture it
  used. Rewrite that test against a synthetic fixture rather than weakening it.
