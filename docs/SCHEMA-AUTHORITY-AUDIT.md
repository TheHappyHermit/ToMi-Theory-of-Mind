# Which schema is the gold standard? — authority audit

Written 2026-09-28 in response to a direct question: *are there other
schemas with extra fields that were worked on as an improvement, or is
the one I am looking at the broadest?*

**Answer: `schemas/okf-schema.yaml` is the broadest, and no rival schema
holds an unrecovered improvement.** The near-miss is
`wiki-frontmatter.schema.json`, which looks like a rival but is a
generated mirror. That is a trap worth recording, because it will read
as a second schema to anyone who finds it first.

## The candidates, ranked by real field count

| File | Fields | Verdict |
|------|-------:|---------|
| `schemas/okf-schema.yaml` | 22 | **GOLD STANDARD.** Format authority, per `WIKI-STANDARDS.md` |
| `schemas/wiki-frontmatter.schema.json` | 23 | Generated mirror of the YAML. Not a rival |
| `schemas/SCHEMA.md` | 20 | Narrative. Identical to `wiki-schema.md` (md5 `d4435c2c`) |
| `bak_autognosia/.../oracle-wiki-frontmatter-complete.md` | 11 | Strict subset. No new fields |
| `bak_autognosia/.../okf-v02-schema.md` | 11 | Strict subset. No new fields |
| `bak_autognosia/.../wiki-frontmatter-standards.md` | 12 | Subset. Adds only `title`, already in the YAML |
| `skills/wiki-management/references/okf-standard.md` | 4 | Abbreviated. No new fields |

The backup-era files under `bak_autognosia/` are the retired
`autognosia` filesystem. **None of them introduces a field the gold
standard lacks.** The one extra field any of them mentions is `title`,
and `okf-schema.yaml` already has it.

## The near-miss: wiki-frontmatter.schema.json

This is the file that looks like an improvement and is not. Its own
description says:

> Derived from `schemas/okf-schema.yaml` by `scripts/okf_export_json.py`.
> **DO NOT EDIT BY HAND.** The YAML is the single source of truth.

Verified in sync, not merely claimed: re-ran the generator and the
md5 was unchanged (`e0374889` before and after).

Its `required` list is **9 keys**, and it is *stricter* than the YAML's
6: `confidence`, `sources`, and `tags` are required there but only
recommended in `SCHEMA.md`. That difference is the thing to understand
if this file is ever mistaken for an independent standard — it is a
stricter *view*, not a different *design*.

## Which tools actually load the YAML

```
okf_lint.py     -> okf-schema.yaml   (authority, live)
okf_repair.py   -> okf-schema.yaml   (authority, live)
okf_gate.py     -> okf_lint.load_schema()  (delegates, correct)
```

Three tools. Everything else either needs no schema or handles a
different store:

- `verify_okf_index.py` — index structure, not frontmatter.
- `verify_schema_conformance.py` — `research-request.schema.json`, a
  different artifact entirely. Not a wiki schema.
- `apply_schema_upgrades.py` — SQLite stores, not wiki files.
- `migrate_frontmatter_timestamps.py` — timestamps only.
- `repair_okf_compliance.py` — no schema reference; check it in Phase 1
  before trusting it to write.

## The real finding: a fourth copy still differs

Three copies are byte-identical (`SCHEMA.md`, `SCHEMA_ORACLE.md`,
`wiki-schema.md`, md5 `d4435c2c`). A fourth does not:

```
/home/operator/.hermes/oracle/brain/SCHEMA.md   md5 0ac58058
```

That is the drift the owner predicted, and it remains open work
(Phase 7 of the remediation plan). The JSON mirror is *not* a
contender to it; it regenerates from the YAML.

## Answering the question directly

No rival schema has an extra field or two that was lost. The gold
standard is the broadest, it is self-declared, it is machine-readable,
it has a migration map covering every historical spelling, and 2,713
files have already been linted against it.

The risk is not a lost improvement. It is that `wiki-frontmatter.schema.json`
is discoverable, looks authoritative, says "DO NOT EDIT BY HAND", and
would tempt a future agent into treating it as a second standard. Phase 7
should make the relationship machine-checkable rather than a comment in
a file nobody reads.
