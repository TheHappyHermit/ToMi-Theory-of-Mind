# Where sources belong — upstream settles it, and it contradicts our corpus

Written 2026-09-28 from `SPEC.md` of
`GoogleCloudPlatform/open-knowledge-format` (37,748 bytes, verified
2026-09-28). The owner asked: "do whatever's in our front matter schema or
whatever Google OKF v0.2 dictates; if we don't have it in our schema because
it should be added, then add it."

## The answer, in three parts

### 1. Our schema was silent, and the spec is explicit

A search of `schemas/okf-schema.yaml` for `body`, `inline`, `prose`,
`References`, `citation` and `footnote` found **no rule about where
references may live.** The one `body` mention is about a generated
snapshot, unrelated.

Google says it outright, §13.1, listed as a **deliberate breaking change**:

> **The body `# Citations` list is superseded by `sources`.** Provenance
> moves to frontmatter (§5.1). Consumers SHOULD read `sources` and MAY
> still parse a legacy `# Citations` body list for v0.1 documents.

So the rule exists upstream and was missing locally. It has been added to
`schemas/okf-schema.yaml` as `citation_placement`.

### 2. Where the corpus is wrong

33 Oracle files keep their bibliography as loose body text under
`References` / `Sources`. Per §13.1 that is a **v0.1 legacy shape**, and
consumers MAY still read it. So these files are not *invalid* — they are
**on the deprecated path**, and `sources` is currently being satisfied by
whatever loose entries the page happens to carry.

This is worth stating precisely, because it changes what the fix is. These
33 files are not broken in a way that loses information. They are shaped the
old way.

### 3. The bigger finding: positional markers are the wrong shape entirely

This is the part that changes the remediation, and it was not in scope until
the upstream text was read in full.

§5.1, **Per-claim attribution**:

> To attribute a specific claim, use a markdown footnote whose label is a
> `sources[].id`
>
> The footnote label is the join key into `sources`; consumers resolve
> attribution through the matching entry, not by parsing the footnote
> prose. **Labels are keyed rather than positional (`sources[0]`) because
> agents constantly rewrite these documents: a positional index
> misattributes silently the moment the list is reordered, whereas a stable
> `id` survives reordering.**

Upstream names our exact defect and explains why it is dangerous: a
positional number **silently misattributes the moment the list is
reordered.** Not loudly — silently. In a corpus that agents rewrite
constantly, that is a correctness bug that grows with use.

Upstream also says (§4.2) that per-claim attribution uses markdown
footnotes **keyed to `sources` entries rather than a body citations list**.

## What this means for the 689

The mechanical fix I originally proposed — rewrite `[[7]]` to `[7]` and
leave the references in the body — **is not the right target.** It would
convert a positional marker into a *different* positional marker, and keep
the bibliography in the place upstream just retired.

The upstream-conformant target is:

```markdown
---
sources:
  - id: howard-kahana-2002
    resource: https://doi.org/10.1016/S0896-3623(02)00157-6
    title: A distributed representation of temporal context
    author: human:howard
---

The principle of **chronotopic organization** posits that the cerebral
cortex is arranged along a gradient of temporal receptive window.[^howard-kahana-2002]

[^howard-kahana-2002]: Howard & Kahana (2002)
```

i.e. every `[[n]]` becomes a **keyed** footnote, and every body reference
entry becomes a `sources[]` item with a stable `id`.

## The honest cost, which the owner should see

Keying is *not* mechanical in the way a bracket swap is. Each source needs a
**stable identifier** derived from the citation — author, year, and a short
title slug is the natural choice (`howard-kahana-2002`). Deriving that slug
is scriptable for a well-formed reference line, but it is a real
transformation of 689 markers and ~1,400 reference lines across 33 files,
and a wrong slug produces a footnote that joins to the wrong source.

Two mitigating facts:

- The `id` only has to be **stable and unique within the file**. It is not a
  database key and does not have to be globally canonical.
- 26 of 33 files have every number resolving, so those can be keyed
  mechanically with verification that each resulting footnote joins to a
  real `sources[]` entry.

## Recommendation

**Do the upstream-correct thing, not the cheaper thing.** The whole reason
to consult §5.1 was to find out whether the cheap fix was right. It is not.
Positional-to-positional is a formatting cleanup that leaves the silent
misattribution risk in place.

Cost difference is real but bounded: a keyed migration is one extra
derivation step per reference, and it is verifiable — every footnote label
must join to a `sources[].id`, and that join is checkable. A positional
migration is unverifiable, because a misattribution looks exactly like a
correct one.

## What was added to the schema

`citation_placement` in `schemas/okf-schema.yaml`, recording:

- `sources` is the canonical location; the body bibliography is legacy v0.1
- in-body markers MUST be keyed footnotes, not positional numbers
- `sources[].id` SHOULD be present when the body cites the source (§5.1)
- a legacy body list is accepted, not invalid, per §13.1

The rule was **not** enforced as a new lint class. Adding one would mark
every existing file invalid at once, and the owner's standard is that nothing
is flagged until it can be fixed. Enforcement is Phase-gated in the handoff
prompt, behind the bulk migration.
