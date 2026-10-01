---
name: whole-corpus-reading
description: Use when reading a corpus exhaustively, file by file.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [corpus, reading, audit, verification, checkpoints, manifest]
    related_skills: [verifying-scholarly-citations, bulk-corpus-remediation, grounded-citations]
---

# Whole-Corpus Reading

Reading a body of documents end to end — every line of every file, with a
durable verdict per file and load-bearing claims checked against primary
sources — without running out of context or quietly substituting summaries
for sources.

## When to Use

The user asks you to read a corpus exhaustively — every file, every line, one
at a time — and produce a durable verdict per file. Typical triggers: a
knowledge base to be absorbed before designing something, a document set to be
audited for accuracy, a corpus to be mined for decisions.

Not for answering a question about a few known documents
(`grounded-citations`), and not for bulk-editing files to a schema
(`bulk-corpus-remediation`).

## Standing rules

These are standing constraints, not defaults to be tuned:

- **No scripts on the reading path.** No batching, hashing, condensing,
  extracting, or summarizing helpers. Open each source directly.
- **No subagents for reading or judgment.**
- **No generated substitutes.** Digests, head/tail windows, chunk files,
  category pre-screens, and dedup output are *research leads only*. They never
  count as having read the source.
- **Every exact path gets read**, including byte-identical duplicates and files
  that look irrelevant. Deciding what to skip is the user's call.
- **Whole-file reads.** If a read returns `truncated`, re-read the remainder
  before forming any view of the file.
- **Report less, read more.** See tranche discipline — this is the single
  most-repeated correction.

## Tranche discipline

Read a tranche, then report once, at a genuine turn boundary rather than per
file.

- Target **10–25 files per tranche** when files are small; **3–6** when they
  run 20–60KB each and each is verified against external sources.
- Report what the tranche established, what remains, and any decision the user
  needs to make. Do not narrate progress per file.

## Procedure

① **Build a manifest first.** An ordered, durable list of every path in scope,
written to disk. Navigate by the manifest, never by directory globbing —
globbing silently changes scope as files are added, and the read set drifts
from the agreed set.

② **Read one file, whole, top to bottom.** Form a verdict before moving on.

③ **Check load-bearing claims against primary sources.** A claim that carries
weight gets verified, not absorbed. Record the verdict with its evidence.

④ **Append the verdict to a durable record** as you go — a JSONL or CSV keyed
by path. If the session dies, the work resumes; if you later disagree with a
verdict, the original reasoning is still visible.

⑤ **Checkpoint at each tranche boundary**: files completed, files remaining,
findings by category, anything blocked.

## Keeping the work going

- On a context reset, resume from the manifest and the verdict record, not from
  memory. Re-reading is cheap; a silently restarted scan is not.
- Report progress as counts against the manifest so a stall is visible.
- If a file cannot be read, record *why* and continue. One unreadable file does
  not stop the tranche.

## Pitfalls

- **Reporting per file.** Interruptions are the most-repeated complaint; batch
  them.
- **Sampling and calling it exhaustive.** A representative sample is a
  different, lesser deliverable. Say which one you did.
- **Trusting a pre-screened shortlist** as if it were the corpus.
- **Reading a truncated window** and forming a view of the whole file.
- **Letting an early finding set the frame** for the rest of the tranche —
  read before concluding.
- **Losing the verdict record** so the pass cannot be audited or resumed.
- **Silently narrowing scope** when something is blocked. Report the gap.
