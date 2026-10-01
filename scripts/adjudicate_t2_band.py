#!/usr/bin/env python3
"""
Manual adjudication of the 0.4-0.6 mismatch band, case by case.

WHY THIS IS A DATA FILE AND NOT A RULE
--------------------------------------
The automated matcher resolves these as `mismatch`, meaning "the file
cites the wrong paper". On reading all 27 individually, that is false
for 26 of them. Each is the SAME paper cited with a compressed title:

  "ReasoningLens: ... Diagnostic Auditing for LRMs"
      vs "ReasoningLens: ... Diagnostic Auditing for Large Reasoning Models"

  "Structured ADI Reasoning via Algebraic Invariants"
      vs "Structured Abductive-Deductive-Inductive Reasoning for LLMs via
          Algebraic Invariants"

The one exception is a prose fragment carrying no title at all, which
is `untitled_citation` rather than either of the above.

Loosening the matcher to catch this shape would be the wrong fix and
was explicitly rejected: a false MATCH inflates confidence invisibly,
which is worse than a false mismatch because it is silent. These 27 are
individual human-equivalent judgments, each recorded with its own
reason, and future cases of this shape still require review.

WHAT "SAME PAPER" DOES AND DOES NOT MEAN
----------------------------------------
These adjudications concern CITATION IDENTITY: does the identifier
point at the work the file means to cite? They do NOT certify that the
vault describes that work's CONTENT accurately. Where the vault adds
detail the title does not contain -- "4 components: representation/
storage, extraction, retrieval/routing, maintenance" -- that is a claim
about the paper's substance, and checking it is a different question
than the one T2 asks. Conflating the two would let a citation-identity
pass stand in for a content-fidelity check it never performed.

Usage: scripts/apply_t2_adjudication.py --check (dry run) / --apply
"""
import json
from collections import Counter

# One entry per (vault file, identifier) in the band. `verdict` is what
# the human review concluded; `reason` must state why, because an
# unexplained override is indistinguishable from a bug.
ADJUDICATION = [
    # -- arxiv:2606.24775 : "Agent-Native Memory System ..." ---------
    ("research/frontier-research-taxonomy-2027-supplement-v2.md",
     "arxiv:2606.24775", "match",
     "Vault title is a descriptive paraphrase, not a fabrication. The "
     "distinctive phrase 'Agent-Native Memory System' appears verbatim in "
     "the registry title, and the paper is a survey of that same system, "
     "so the identifier points at the intended work. The appended "
     "'4 components' breakdown is a content claim and is NOT certified "
     "here."),
    ("research/frontier-research-taxonomy-2027-january-comprehensive-update.md",
     "arxiv:2606.24775", "match",
     "Same paper as the 2027-supplement case: the shared distinctive "
     "phrase 'Agent-Native Memory System' identifies it, and only the "
     "date annotation differs. '(Jun 2026)' is vault metadata, not part "
     "of a title claim."),

    # -- arxiv:2608.22974 : "OaK: Dynamic Ontology for LLM Agents" -----
    # Four files cite this identically; one judgment, four rows.
    ("research/frontier-research-taxonomy-advances-2026-09-10.md",
     "arxiv:2608.22974", "match",
     "Method-name title for a paper whose registry title is the "
     "motivational framing of the same work. 'Dynamic Ontology' and "
     "'LLM Agents' both appear in the registry title; 'OaK' is the "
     "system's own name and appears in neither. Topic identity is "
     "unambiguous."),
    ("research/frontier-research-taxonomy-comprehensive-2026-09-10-v2.md",
     "arxiv:2608.22974", "match",
     "Identical label and identical identifier to the advances file. "
     "Same judgment, applied to a second citing file."),
    ("research/frontier-research-taxonomy-comprehensive-2026-09-11.md",
     "arxiv:2608.22974", "match",
     "Identical label and identical identifier. Same judgment applied to "
     "a fifth citing file (the band spans five files citing this paper)."),
    ("research/frontier-research-taxonomy-september-2026-supplement-v2.md",
     "arxiv:2608.22974", "match",
     "Identical label and identical identifier. Same judgment applied to "
     "a fourth citing file."),

    # -- Compressed subtitles ------------------------------------------
    ("research/frontier-research-taxonomy-2025-2026-supplement.md",
     "arxiv:2505.16782", "match",
     "Full distinctive prefix 'Reasoning Beyond Language' matches, and "
     "'Latent' + 'CoT' is 'Latent Chain-of-Thought'. '(Dec 2025)' is a "
     "date annotation. Survey is correctly identified as a survey."),
    ("research/frontier-research-taxonomy-september-2026-supplement-v2.md",
     "arxiv:2601.06002", "match",
     "'The Molecular Structure of Thought' matches exactly; 'Topology of "
     "Long CoT' is 'Mapping the Topology of Long Chain-of-Thought "
     "Reasoning' with 'Mapping' and 'Reasoning' dropped. CoT is the "
     "standard abbreviation. Same paper."),
    ("research/frontier-research-taxonomy-september-2026-supplement-v3.md",
     "arxiv:2601.06002", "match",
     "Same label and identifier as the v2 supplement. Same judgment "
     "applied to a second citing file."),
    ("research/frontier-research-taxonomy-2027-supplement.md",
     "arxiv:2605.29801", "match",
     "'AgentDoG 1.5' is a version-stamped system name matching exactly. "
     "'Lightweight Alignment Framework' is the leading phrase of the "
     "registry title. '(updated 3D safety taxonomy)' is vault metadata. "
     "The paper is indeed about agent safety, so the security framing is "
     "consistent."),
    ("research/frontier-research-taxonomy-late-2026-supplement.md",
     "arxiv:2602.04261", "match",
     "Shared prefix 'Data Agents: Levels, State of the Art' is long and "
     "distinctive. The vault substituted 'L0-L5 taxonomy' for the "
     "registry's trailing 'and Open Problems', which is a "
     "characterisation of content rather than of title -- but the cited "
     "work is unambiguously the same survey."),

    # -- Acronym expansion ---------------------------------------------
    ("research/frontier-research-taxonomy-september-2026-supplement-v2.md",
     "arxiv:2606.23404", "match",
     "System name 'ReasoningLens' and the full phrase 'Hierarchical "
     "Visualization and Diagnostic Auditing' both match. Only 'LRMs' vs "
     "'Large Reasoning Models' differs, a pure abbreviation."),
    ("research/frontier-research-taxonomy-september-2026-supplement-v3.md",
     "arxiv:2606.23404", "match",
     "Same label and identifier as the v2 supplement. Same judgment "
     "applied to a second citing file."),
    ("research/frontier-research-taxonomy-2027-january-comprehensive-update.md",
     "arxiv:2604.15727", "match",
     "Second citing file, same identifier. Label differs from the row "
     "above only in framing ('ADI Protocol:' vs 'Structured ADI "
     "Reasoning'), and both expand to the same paper. Same judgment."),
    ("research/frontier-research-taxonomy-2027-supplement.md",
     "arxiv:2604.15727", "match",
     "Third citing file, same identifier and same underlying paper. "
     "Label is the 'Structured ADI Reasoning' form, matching the first "
     "row of this group. This entry was initially filed against the "
     "wrong citing file, which is why the first --apply only moved 26 of "
     "27 rows; the count mismatch is what surfaced it."),

    # -- Paraphrase with added specificity -----------------------------
    ("research/frontier-research-taxonomy-2027-supplement.md",
     "arxiv:2511.12485", "match",
     "'ARCHE' and 'Latent Reasoning Chain Extraction' both match. The "
     "registry title frames it as a novel evaluation task; the vault "
     "names the task's method. '(Reasoning Logic Tree)' is vault "
     "metadata. Same paper."),
    ("research/frontier-research-taxonomy-2027-supplement-v2.md",
     "arxiv:2505.12592", "match",
     "'PromptPrism' and 'Linguistically-Inspired' match; 'Prompt "
     "Taxonomy' is 'Taxonomy for Prompts' reordered. The 'Three-Level' "
     "enumeration is the paper's own content, not a title claim."),
    ("research/frontier-research-taxonomy-2027-january-comprehensive-update.md",
     "arxiv:2608.07994", "match",
     "System name 'VDGR-RAG' matches, and the expanded list 'Vectors, "
     "Directories, Graphs, Reflection' matches exactly against the "
     "registry's 'Vectors, Directories, Graphs, and Reflection'. Only "
     "the trailing clause is shortened."),
    ("research/frontier-research-taxonomy-comprehensive-2026-09-11-supplement-v2.md",
     "arxiv:2510.27183", "match",
     "Title prefix 'Simple Additions, Substantial Gains' matches exactly "
     "and 'URIEL+' matches exactly. The vault replaced 'Expanding "
     "Scripts, Languages, and Lineage Coverage in' with 'Expanding "
     "URIEL+ Linguistic Knowledge Base', a description of the same "
     "expansion. Same paper."),
    ("research/frontier-research-taxonomy-2027-january-comprehensive-update.md",
     "arxiv:2601.15804", "match",
     "'Entangled Life and Code' matches exactly, as does 'Bio-Digital' "
     "and 'Taxonomy'. 'CHI 2026' is venue metadata. The vault dropped "
     "'A Computational Design ... for Synergistic' and the Systems "
     "suffix."),
    ("research/frontier-research-taxonomy-2027-january-comprehensive-update.md",
     "arxiv:2602.04813", "match",
     "'Agentic AI in Healthcare' and 'Seven-Dimensional Taxonomy' both "
     "match. The registry title additionally carries the '&amp;' HTML "
     "entity, which is a defect in the FETCHED TITLE, handled "
     "separately in the fix_entity_bug case and not evidence about the "
     "citation."),

    # -- ATBench, four citing files ------------------------------------
    ("research/frontier-research-taxonomy-advances-2026-09-10.md",
     "arxiv:2604.02022", "match",
     "'ATBench' matches exactly, and 'Trajectory Benchmark' plus 'Agent "
     "Safety' covers the registry's 'Agent Trajectory Benchmark for "
     "Safety Evaluation'. Compressed, same paper."),
    ("research/frontier-research-taxonomy-comprehensive-2026-09-10-v2.md",
     "arxiv:2604.02022", "match",
     "Identical label and identifier. Same judgment, second citing file."),
    ("research/frontier-research-taxonomy-comprehensive-2026-09-10.md",
     "arxiv:2604.02022", "match",
     "Identical label and identifier. Same judgment, third citing file."),
    ("research/frontier-research-taxonomy-comprehensive-2026-09-11.md",
     "arxiv:2604.02022", "match",
     "Identical label plus the annotation '(three-orthogonal-dimensions "
     "taxonomy)', which is vault metadata describing the benchmark. Same "
     "judgment, fourth citing file."),

    # -- Remaining two -------------------------------------------------
    ("research/frontier-research-taxonomy-september-2026-supplement-v3.md",
     "arxiv:2508.04227", "match",
     "'Continual Learning for VLMs' matches exactly. The registry's "
     "subtitle is 'A Survey and Taxonomy Beyond Forgetting'; the vault "
     "wrote 'Challenge-driven taxonomy', which characterises the survey "
     "rather than quoting it. A VLM continual-learning survey is "
     "unambiguously the cited work."),
    ("research/frontier-research-taxonomy-2027-supplement.md",
     "arxiv:2606.05339", "untitled_citation",
     "NOT a same-paper paraphrase -- there is no title to compare. The "
     "label captured is the prose fragment 'with Autognosia integration "
     "analysis.', which means the identifier appears mid-sentence in "
     "running text rather than in a citation. The honest verdict is that "
     "no title was present, not that the wrong paper was cited. This "
     "also reveals a real gap: identifiers occurring in prose are "
     "harvested with surrounding words as if they were citation labels."),
]


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--table', default='/home/operator/hermes-brain/'
                                     'docs/audit/t2-verification.json')
    ap.add_argument('--out', default='/home/operator/hermes-brain/'
                                     'docs/audit/t2-adjudication.json')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    if not (a.check or a.apply):
        ap.error('pass --check or --apply')

    # A duplicate key silently overwrites the earlier judgment, so the
    # applied count comes out one short with nothing to explain it. That
    # is exactly how one row went unadjudicated the first time. Refuse
    # to run rather than quietly applying fewer rows than were written.
    seen = {}
    dupes = [k for k, n in Counter(
        (p, i) for p, i, _v, _r in ADJUDICATION).items() if n > 1]
    if dupes:
        for p, i in dupes:
            print('  DUPLICATE ENTRY: %s :: %s' % (p, i))
        raise SystemExit('refusing to run: %d duplicate key(s)' % len(dupes))
    for p, i, _v, _r in ADJUDICATION:
        seen.setdefault((p, i), 0)

    table = json.load(open(a.table, encoding='utf-8'))
    changes, missing, unchanged = [], [], 0

    for path, ident, verdict, reason in ADJUDICATION:
        key = '%s::%s' % (path, ident)
        if key not in table:
            missing.append(key)
            continue
        cur = table[key].get('verdict')
        if cur == verdict:
            unchanged += 1
            continue
        changes.append((key, cur, verdict))

    print('  band entries      : %d' % len(ADJUDICATION))
    print('  found in table    : %d' % (len(ADJUDICATION) - len(missing)))
    print('  already correct   : %d' % unchanged)
    print('  would change      : %d' % len(changes))
    for key, cur, new in changes[:6]:
        print('      %-58s %s -> %s' % (key[58:], cur, new))
    if len(changes) > 6:
        print('      ... and %d more' % (len(changes) - 6))
    if missing:
        print('  NOT IN TABLE      : %d' % len(missing))
        for k in missing[:5]:
            print('      %s' % k)
    if a.check:
        return
    for key, _cur, verdict in changes:
        table[key]['verdict'] = verdict
        table[key]['adjudicated'] = True
        table[key]['auto_verdict'] = 'mismatch'
    with open(a.out, 'w', encoding='utf-8') as fh:
        json.dump(table, fh, indent=1, sort_keys=True)
    print('  wrote %s' % a.out)


if __name__ == '__main__':
    main()
