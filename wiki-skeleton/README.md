# Active Wiki — Structure, Conventions, and How to Work With It

This directory is a **skeleton**: the folder layout and one `index.md` per
folder, with nothing else in it. The live vault is at
`~/.hermes/active-wiki` and holds personal notes, which are deliberately never
committed. What belongs in GitHub is the *shape* and the *rules* — the thing you
need in order to write a note that the next reader, and the next agent, will
file correctly.

The skeleton is generated. `scripts/publish_wiki_skeleton.py` owns the
taxonomy, so the docs, the tests, and the published folders cannot drift apart:

```sh
python3 scripts/publish_wiki_skeleton.py            # write
python3 scripts/publish_wiki_skeleton.py --check     # assert the committed copy is current
python3 scripts/publish_wiki_skeleton.py --dry-run   # show what would change
```

If you edit a folder's purpose by hand here, `--check` will fail until the
generator agrees. That is intentional: change `TAXONOMY` in the script, not
this directory.

---

## The layout

Thirteen numbered areas. The numbers are load-bearing: they sort, so a
directory listing reads in the order content should be considered, and
`00_` and `90_` leave room at both ends for the rulebook and the cold storage
without renumbering anything.

| Folder | Holds | Sub-folders |
| :--- | :--- | :--- |
| `00_System` | The rulebook: how the vault governs itself | `Templates`, `Proposals` |
| `01_Raw` | Immutable intake, unclassified | `Web`, `Conversations`, `Quick-Captures`, `Documents`, `Imports`, `Attachments` |
| `02_Log` | Episodic memory: dated events with outcomes | `Daily`, `Agent-Sessions`, `Meetings`, `Experiments`, `Incidents` |
| `10_Self` | The durable model of the user | `Goals`, `Preferences`, `Constraints`, `Principles` |
| `20_Areas` | Ongoing responsibilities, no finish line | `Standards`, `Health` |
| `30_Projects` | Finite work with a definition of done | `Active`, `Paused`, `Completed` |
| `40_Entities` | Operationally relevant people, orgs, things | `People`, `Organizations`, `Systems`, `Products`, `Models`, `Places` |
| `50_Beliefs` | Interpretations graded by epistemic certainty | `Claims`, `Hypotheses`, `Theses`, `Principles` |
| `60_Decisions` | Append-only record of choices made | `Superseded` |
| `70_Questions` | Known unknowns worth answering | — |
| `80_Models` | Assembled understanding built from other notes | `Syntheses`, `Mental-Models`, `Maps`, `Current-State` |
| `85_Procedures` | How work gets done | `Human-Runbooks`, `Policies`, `Skill-References` |
| `90_Archive` | Cold storage, excluded from routine attention | — |

The empty folders are intentional. They are the vault's declared vocabulary: a
capture that does not fit an existing folder is a signal, not a reason to invent
a fourteenth area. They fill from automation, not from ambition.

`85_Procedures` sits after `80_Models` rather than at `90_` because procedures
are more frequently consulted than models. Numbering encodes attention, not
importance.

---

## Routing: where does this note go?

Ask in order, stop at the first match.

1. **Unprocessed intake** — a web page, conversation, document, quick thought,
   or file? → `01_Raw/`, sub-folder by source. **Stop.** Never classify or
   interpret at capture time.
2. **A dated event with an outcome** — meeting, session, experiment, incident,
   day? → `02_Log/`, sub-folder by kind.
3. **About the user** — profile, goals, preferences, constraints, principles?
   → `10_Self/`.
4. **A choice that was made**, with alternatives and rationale? →
   `60_Decisions/`.
5. **An interpretation held at a stated confidence?** → `50_Beliefs/`:
   checkable assertion → `Claims/`; unconfirmed explanation or prediction →
   `Hypotheses/`; interpretation assembled from several claims → `Theses/`;
   rule for how to decide → `Principles/`.
6. **An ongoing responsibility with no finish line?** → `20_Areas/`.
7. **Finite work with a definition of done?** → `30_Projects/Active/`. Lifecycle
   is `Active` → `Paused` → `Completed` → `90_Archive/`.
8. **A person, org, system, product, model, or place that matters
   operationally?** → `40_Entities/<kind>/`.
9. **An unresolved question worth answering?** → `70_Questions/`.
10. **A how-to, runbook, or standing rule for recurring work?** →
    `85_Procedures/`.
11. **A bigger picture assembled from other notes?** → `80_Models/`.
12. **Long-form research or reference material?** → **not this vault.** It
    belongs to the Oracle vault at `~/.hermes/oracle/brain`.
13. **Still unsure?** → `01_Raw/` and let curation decide. Never force a guess
    into a compiled folder.

Step 12 is the one agents get wrong most often, and it has a recorded
rationale: `60_Decisions/2026-09-28_research-consolidates-to-oracle-vault.md`
in the live vault. Research consolidates in the Oracle vault; this one is the
working store. That decision is why the active wiki has 85 notes and the Oracle
has 2,388.

---

## Write rules

- **`01_Raw/` is immutable.** The only permitted change is marking processing
  status. A raw capture that no longer reflects the source has been corrupted,
  not improved. `scripts/check_raw_drift.py` hashes the body of every raw note
  and fails on drift, because the alternative is an intake layer that quietly
  becomes a draft layer.
- **History and decisions are append-only.** Never rewrite or delete a
  decision or a timeline. Supersede it: write a new note that points at the old
  one, and move the old one to `60_Decisions/Superseded/`.
- **Claims in compiled notes must trace to evidence** — a raw capture, a log
  entry, or a decision, cited by note id. An unsourced claim in `80_Models/` is
  an assertion wearing a citation's clothes.
- **No secrets in any note, ever.** Not a token, not a private key path, not a
  connection string with a password in it. Public copies are additionally
  redacted by `scripts/redact_skill.py`, but redaction is a backstop, not a
  licence to write one.
- **Substantive changes to compiled folders go through `00_System/Proposals/`.**
  New raw captures and new log entries are always allowed without one.

---

## Frontmatter

The schema is shared with the Oracle vault and lives in
[`schemas/okf-schema.yaml`](../schemas/okf-schema.yaml). This structure adds **no
types of its own**. Folder and `type:` are different things: the folder says
where content is routed and how it ages, `type:` says what kind of thing it is,
and the mapping between them is documented in
[`docs/audit/active-wiki-folder-type-map.md`](../docs/audit/active-wiki-folder-type-map.md).

Minimum for any note:

```yaml
---
type: reference          # from the OKF enum — not a folder name
epistemic: verified-inference
confidence: medium
sources:
  - "[[some-note-id]]"   # where the claim came from
---
```

Field reference: [`docs/CONFIDENCE-RUBRIC.md`](../docs/CONFIDENCE-RUBRIC.md)
for what each confidence band means, and
[`docs/CITATION-WRITING.md`](../docs/CITATION-WRITING.md) for the citation
contract — including the rule that a resolvable identifier must carry a title.

---

## Links

Two forms, and the difference is not cosmetic.

- **`[[wikilinks]]` resolve by page *name*, not by path.** Depth does not
  matter and folder names are not part of the key. A link written as
  `[[decisions/foo]]` is not "a link to foo inside decisions" — it is a
  malformed link to the page named `decisions/foo`, which resolves to nothing.
  Write `[[foo]]`. When the numbered folders replaced the old names on
  2026-09-30, 17 of these had to be repaired, and the repair was deletion of
  the prefix, not substitution of a new one.
- **Relative markdown links** (`[x](../60_Decisions/y.md)`) *do* encode the
  path, so they break on a rename. 82 of them were rewritten during the same
  migration. Prefer wikilinks for notes; prefer relative links for index pages
  that enumerate sub-folders, where the path is the information.

To check a restructure did not break anything:

```sh
python3 scripts/rename_wiki_folders.py --verify
```

It re-resolves every relative link against the filesystem and exits non-zero on
any that fail. It is not a string comparison — the migration that produced this
structure passed three separate checks that each found a different bug, and two
of those bugs produced plausible-looking output rather than an error.

---

## Scripts

| Script | Does |
| :--- | :--- |
| `scripts/publish_wiki_skeleton.py` | Generates this directory. `--check` asserts it is current. |
| `scripts/rename_wiki_folders.py` | The 2026-09-30 rename. `--dry-run`, `--undo`, `--verify`. |
| `scripts/make_wiki_skeleton.py` | Creates the numbered tree in the live vault. Idempotent. |
| `scripts/migrate_wiki_folders.py` | Per-note filing by declared type. Kept for reference; **not applied**. |
| `scripts/check_raw_drift.py` | Hashes raw bodies; fails on drift. |
| `scripts/okf_gate.py` | Frontmatter gate for a set of notes. |
| `scripts/okf_lint.py` | Citation and provenance validation. |
| `scripts/grade_all.py` | Recomputes derived confidence. `--apply` to write, `--report` to regenerate the CSV. |
| `scripts/publish_profiles_and_skills.py` | Generates the tracked, PII-stripped profile and skill copies. |
| `scripts/redact_skill.py` | The PII redactor. |
| `scripts/graphify_active_wiki_py.py` | The graph extraction job. |

---

## Rollback

The 2026-09-30 rename is reversible. The snapshot, its 94-file sha256 manifest,
the move journal, and the retired folder indexes are all outside the repo:

```
~/.hermes/cache/scratch/active-wiki-PRE-restructure-20260930T062903Z/
~/.hermes/cache/scratch/active-wiki-PRE-manifest-20260930T062903Z.json
~/.hermes/cache/scratch/wiki-rename-journal-20260930T063629Z.json
~/.hermes/cache/scratch/graphify-out-PRE-rebuild-20260930T001139Z/
```

---

## Evidence

Claims in this vault that rest on outside research cite their source, and the
citation tables that make those checkable are
[`docs/CITATION-VERDICTS.md`](../docs/CITATION-VERDICTS.md) and
[`docs/CITATION-AUDIT.md`](../docs/CITATION-AUDIT.md). The distinction the
schema enforces is between a claim that resolved to a real document with a
matching title, and one that merely *has* an identifier. Those are not the same
thing, and the gap between them is where fabricated citations live.

Where the structure itself is a considered decision rather than a convention,
the reasoning is in
[`docs/audit/active-wiki-taxonomy-assessment.md`](../docs/audit/active-wiki-taxonomy-assessment.md)
— including the parts of the evidence that argued *against* the design that
shipped, which are left in rather than tidied away.
