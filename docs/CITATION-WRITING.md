WRITING A CITATION — the part that decides whether your page can be graded

Every source entry you write needs a **title**, not just a link.

## Why this matters, concretely

When the wiki is graded, the system resolves each identifier you wrote, fetches
the real document, and compares the real title against the title you recorded.
Three outcomes:

| You wrote | What the grader can do | Your page |
| --- | --- | --- |
| `arxiv:2509.20021 (Embodied AI Survey)` | resolve + title-match | eligible for **high** |
| `https://arxiv.org/abs/2509.20021` | resolve, nothing to compare | **capped at medium** |
| `arxiv:2509.20021 (Some Other Title)` | resolve + **mismatch** | **capped at low** |

That third row is the dangerous one. A title from memory that differs from the
real one is not a formatting slip — it is a fabrication signature, and the
grader treats it as one.

Measured on the current corpus: **1,605 of 2,661** identifier-bearing citations
carried no title at all. That is the single largest reason pages are not graded
`high`. Writing the title is the highest-value thing you can do.

## The rule

**Every source entry carrying a DOI, arXiv id, or other resolvable identifier
must carry the title exactly as the source states it.**

Good:

```yaml
sources:
  - arXiv:2509.20021 (Embodied AI Survey)
  - doi:10.1109/PROC.1975.9939 (The protection of information in computer systems)
  - https://www.nature.com/articles/x (Attention Is All You Need)
```

Or as a mapping, when you want the author too:

```yaml
sources:
  - resource: doi:10.1038/s41534-025-01078-x
    title: Entanglement-induced provable and robust quantum learning advantages
    author: Wang et al.
```

Bad, and why:

- `https://arxiv.org/abs/2607.18704` — resolvable but untitled. **Capped at
  medium.** This is the most common mistake and it is silent.
- `arxiv:2607.18704` — same problem, in the other citation shape.
- `see the paper` — unresolvable. Treated as an unretrievable source, capped
  at low, and flagged.
- A title you reconstructed from memory — if it differs from the real one this
  is a mismatch, which is worse than having no title at all.

## Where the title comes from

**Fetch it.** The arXiv abstract page, the DOI landing page, the PDF's first
page. Copy what is there.

- Do not paraphrase it.
- Do not reconstruct it from memory or from a search snippet.
- Do not tidy it, lowercase it, or "fix" its capitalisation.
- A version suffix (`2607.01977v1`) is harmless either way — the grader strips
  it.

## If you genuinely cannot get the title

Do **not** invent one. Write the identifier without a title and record the
entry as unverified:

```yaml
sources:
  - https://example.com/paper (UNVERIFIED: paywalled, title not retrieved)
status: unverified
```

An honest untitled entry is a known gap that can be filled later. A fabricated
title is a permanent defect that has to be found and expunged.

## Before you finish

Run the gate. It now blocks any page with an identifier-bearing source that
has no title:

```bash
python3 /home/operator/hermes-brain/scripts/okf_gate.py <file>
```

A non-zero exit means the page cannot be graded. Fix the citations, or mark
them honestly unverified — do not proceed by removing the source.

## The rest of the frontmatter

The canonical field list and enum values are in the schema. Do not restate
them from memory — read them:

- format: `/home/operator/hermes-brain/schemas/okf-schema.yaml`
- rules: `/home/operator/hermes-brain/docs/WIKI-STANDARDS.md`
