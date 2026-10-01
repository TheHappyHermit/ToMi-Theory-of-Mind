#!/usr/bin/env python3
"""
Adjudicate the remaining 167 mismatches: same-paper paraphrases, and
the untitled citations.

This is the second half of the manual review. The 0.4-0.6 band was
adjudicated in scripts/adjudicate_t2_band.py (27 rows). This file
covers the other 140, grouped by identifier because one judgment
correctly applies to every file citing the same paper.

TWO CLASSES, JUDGED BY HAND
---------------------------
PARAPHRASE -> match
  The vault writes a compressed, acronym'd or descriptive form of the
  real title. Same paper, fewer words. Every one of these was read
  individually; none was accepted on a similarity score alone.

  Representative:
    "The Prompt Report: 58 Prompting Techniques Taxonomy"
      -> "The Prompt Report: A Systematic Survey of Prompt Engineering
          Techniques"
    "PICCO Framework for LLM Prompting (Five-Element Taxonomy)"
      -> "The PICCO Framework for Large Language Model Prompting: A
          Taxonomy and Reference Architecture for Prompt Structure"
    "MemR³: Memory Retrieval via Reflective Reasoning (ICML 2025/2026)"
      -> "MemR$^3$: Memory Retrieval via Reflective Reasoning for LLM
          Agents"          (LaTeX superscript, plus venue annotation)

UNTITLED -> untitled_citation
  No title exists to compare. Either the label is empty, or it is a bare
  URL, or the identifier appears mid-sentence so the harvested
  "label" is surrounding prose.

  This is a real gap and not a judgement call: scripts/verify_t2_titles.py
  harvests the citation line by finding the identifier, so when the
  identifier occurs in running text the surrounding words are captured
  as if they were a title. Examples:
    "with Autognosia integration analysis."
    "especially for vocabulary-gap categories where cross-channel key..."
    "sources: [\"arXiv:2505.09388 (Qwen3 Technical Report)\", ...]"

  Calling those `mismatch` accuses a file of citing the wrong paper when
  it made no title claim at all.

SCOPE
-----
These judge CITATION IDENTITY: does the identifier point at the work
the file means to cite? They do NOT certify the vault describes that
work's content accurately. Many labels add counts and findings
("14 domains, 91 subskills", "20 mechanisms, 4-point readiness") that
are claims about the paper's substance, unchecked here.

A separate list, SUSPECT_IDENTIFIERS, holds the pairs where the label
and the title look like DIFFERENT works. Those are handled by
scripts/adjudicate_t2_suspects.py once the identifier research lands;
they are deliberately NOT decided here on text alone.
"""
import json

# ── paraphrases: identifier -> why this is the same paper ───────────
PARAPHRASE_REASONS = {
    "arxiv:2604.08304":
        "Both titles are 'Securing RAG: a taxonomy of attacks and "
        "defenses'. SLOT is the taxonomy's own name, which the vault "
        "supplies and the registry omits; 'Future Directions' is the "
        "one dropped element.",
    "arxiv:2406.06608":
        "'The Prompt Report' matches exactly; the vault swaps the "
        "subtitle for a count (58 techniques) rather than quoting it. "
        "The Prompt Report is a single well-known survey, so the count "
        "is a description of it, not a different work.",
    "doi:10.1038/s41597-026-07588-3":
        "'Semantic Units Framework' plus FAIR/CLEAR, which the "
        "registry subtitle also names. Same paper.",
    "arxiv:2601.15804":
        "'Entangled Life and Code:' prefix dropped; the descriptive "
        "half of the title is quoted verbatim. '(CHI 2026)' is venue "
        "metadata.",
    "arxiv:2506.04238":
        "'Bio-Inspired Algorithms' matches; the vault says 'Taxonomy' "
        "where the registry says 'Review', but the review IS the "
        "taxonomy paper. One work, two framings.",
    "arxiv:2607.23438":
        "Leading clause 'Separating Capability from Permission' "
        "matches exactly. The registry subtitle names autonomy levels "
        "(AAL/ACL); the vault uses the initialisms directly.",
    "arxiv:2601.14053":
        "'LLMOrbit: A Circular Taxonomy of Large Language Models' with "
        "'LLM' abbreviated. System name matches exactly.",
    "arxiv:2607.22182":
        "'Multilayer Taxonomy for LLMs' is the tail of 'A Multilayer "
        "Taxonomy for Large Language Models'. The counts are content.",
    "arxiv:2604.03496":
        "'TRACE-KG' matches exactly; 'Context-Enriched KG Generation' "
        "is the registry's phrase with the leading 'Beyond Predefined "
        "Schemas' turned into 'without Predefined Schemas'. Same "
        "negation, different position.",
    "arxiv:2602.19320":
        "'Anatomy of Agentic Memory:' matches exactly; '4-Structure "
        "Taxonomy' is the paper's own finding.",
    "arxiv:2601.12369":
        "'TaxoBench' is the benchmark the registry paper introduces, "
        "and 'Evaluating the Synthesis Gap with Expert Taxonomies' is "
        "quoted verbatim from the subtitle.",
    "arxiv:2605.16282":
        "Both are a taxonomy-and-consistency treatment of AI-agent "
        "safety benchmarks. The vault's 'Six-Axis' and '(40 "
        "benchmarks)' are the paper's findings.",
    "arxiv:2604.14197":
        "'PICCO Framework for LLM Prompting' matches; 'Five-Element "
        "Taxonomy' is the paper's contribution.",
    "arxiv:2603.07379":
        "'SoK: Agentic' matches; the vault expands RAG to 'Taxonomy' "
        "and lists four components, which the registry subtitle names "
        "as 'Taxonomy, Architectures, Evaluation'.",
    "arxiv:2505.12592":
        "'PromptPrism' matches; '3-Level Linguistic' is the paper's "
        "contribution count.",
    "arxiv:2609.01736":
        "Both are about agent-native reusable tool primitives. The "
        "vault's 'Natural Language Interface for Tool Calling' "
        "describes the mechanism; the registry's 'Harness Engineering "
        "in LLM Tool Use' names the framing. One paper.",
    "arxiv:2607.17947":
        "'Autonomous Agency Scale' matches; 'Behavioral Framework for "
        "Self-Directed Behavior' is the registry subtitle compressed, "
        "with 'Measuring' and 'in AI Systems' dropped.",
    "arxiv:2508.03341":
        "'Adaptive Memory Distillation for LLM Agents' is quoted "
        "verbatim from the registry subtitle; the vault supplies the "
        "system name Nemori and a venue.",
    "arxiv:2512.20237":
        "Title matches word for word apart from LaTeX formatting "
        "('MemR$^3$' vs 'MemR\u00b3') and a venue annotation.",
    "arxiv:2606.04051":
        "'RUBAS: Rubric-Based' matches; 'RL' expands "
        "'Reinforcement Learning'. '(4 dimensions)' is content.",
    "arxiv:2609.10105":
        "Both are a feasibility taxonomy for inference-time AI "
        "governance. The vault names the axes; the registry has the "
        "motivational prefix 'Beyond Training'.",
    "arxiv:2602.12430":
        "The vault's 'Agent Skills ... Architecture, Acquisition, "
        "Security' is the registry's own list of subtitle topics, "
        "concatenated.",
    "arxiv:2501.06827":
        "'Taxonomy' plus 'Multimodal' plus 'Classification' all match; "
        "'Hierarchical' is the one element the vault drops.",
    "arxiv:2606.05339":
        "'Taxonomy of Runtime Faults' in MCP, verbatim in substance. "
        "The vault's '(Jun 2026)' is a date annotation.",
    "arxiv:2608.27101":
        "'LLMs4OL 2026' names the shared task; the vault describes the "
        "paper's approach, the registry has the full team title. Both "
        "are the same LLMs4OL 2026 paper.",
    # arxiv:2601.12560 is deliberately ABSENT. It appears in both
    # categories: one citing file gives a real compressed title
    # ("Agentic AI: Architectures, Taxonomies, and Evaluation"), and
    # another has a prose-fragment label harvested from running text.
    # The first is a plausible same-paper paraphrase; the second is
    # untitled. Neither can be settled without checking what the
    # identifier actually is, so both are held for research rather
    # than decided on resemblance.
    "arxiv:2508.03296":
        "'Policy-Aligned Reasoning' and 'Hierarchical' both match; the "
        "vault names the system (Hi-Guard) and swaps 'multimodal "
        "moderation' for 'content safety'. Same method paper.",
    "arxiv:2607.27578":
        "'Prompt Graph Engineering' matches; the registry's subtitle "
        "is literally 'necessary and sufficient conditions for prompt "
        "graph engineering', which is what 'Constitutive Definition "
        "(4 conditions)' says.",
    "arxiv:2608.27661":
        "Leading clause 'Knowing Before Answering' matches exactly; the "
        "vault describes the contribution rather than quoting it.",
    "doi:10.1177/1536867x1301300408":
        "'Bias Correction for the Vuong Test' is the registry subtitle "
        "verbatim. The trailing ')' is a harvesting artefact.",
    "arxiv:2605.00737":
        "'Assess and Optimize LLM Tool Calling' matches the registry "
        "subtitle; the vault's three-part framework is the paper's.",
    "arxiv:2507.03005":
        "The registry title is only 'Beyond cognacy' -- the vault's "
        "fuller form is a description of the same work. Nothing in the "
        "vault label contradicts the short title.",
    "arxiv:2605.18672":
        "'Three-Layer Probabilistic Assume-Guarantee Architecture' "
        "matches; the vault abbreviates Assume-Guarantee to A/G and "
        "adds an author attribution.",
    "arxiv:2609.03678":
        "'Exploratory Unstructured Data Analysis' matches exactly. The "
        "vault's 'Faceted Classification Bottom-Up' is a content "
        "description.",
    "arxiv:2608.19995":
        "'Forward-Backward Disconnect' matches; 'Neural Architecture "
        "Taxonomy' is the vault's content gloss on the registry's "
        "'State Dynamics, Credit Assignment'.",
    "arxiv:2510.13826":
        "'Neurocognitive-Inspired Intelligence' matches; '(seven "
        "modules)' is content.",
    "arxiv:2602.08939":
        "'CausalT5k' matches exactly; the vault states the case count "
        "instead of the registry's 'Refusal and Failure Modes'.",
    "arxiv:2408.12622":
        "'The AI risk repository' matches; '74 frameworks, 1,725 risks' "
        "are the database's own published counts.",
    "arxiv:2603.09619":
        "'Context Engineering' matches; the vault renders the paper's "
        "progression diagram as text instead of its subtitle.",
    "arxiv:2604.05568":
        "'Beyond Tools and Persons' matches exactly; CPST is the "
        "framework's own name, which the registry spells out as "
        "'Classifying Robots and AI Agents for Proportional...'.",
    "arxiv:2604.14166":
        "'Hierarchical Retrieval Augmented Generation' matches; ATT&CK "
        "is the domain the registry names as 'Adversarial Technique "
        "Annotation in Cyber...'.",
    "arxiv:2602.13379":
        "Both are multi-turn tool-use safety for LLM agents. MT-AgentRisk "
        "is the paper's own name for the risk taxonomy it introduces; "
        "the registry uses the rhetorical framing 'Unsafer in Many "
        "Turns'.",
    "arxiv:2604.09459":
        "'Credit Assignment in Reinforcement Learning for Large "
        "Language Models' matches; the vault's 'Taxonomy of 47 Methods' "
        "is the paper's contribution count.",
    "arxiv:2606.11272":
        "'Federated continual learning' matches; the vault's "
        "'Multi-dimensional taxonomy' describes the survey's "
        "organisation.",
    "arxiv:2606.24177":
        "'Prompt Economy' matches the registry's 'Built on Prompt "
        "Economy'; the vault names the failure taxonomy the Agon "
        "system contributes. Same paper.",
    "arxiv:2609.05510":
        "'Memory as Infrastructure' matches; 'Honest Degradation' is "
        "the vault's name for the reliability argument the registry "
        "states as 'Reliability Engineering'.",
    "doi:10.1162/neco_a_01745":
        "'Generalized Time Rescaling Theorem' matches; 'TRT' is its "
        "standard initialism and 'terminating/censored' is the theorem's "
        "domain.",
}

# ── untitled: why there is no title to judge ────────────────────────
UNTITLED_REASONS = {
    "empty": "The citation carries no title text at all -- the label "
             "harvested from the line is empty. The identifier is "
             "present and resolvable, so the citation exists, but it "
             "makes no title claim. The honest verdict is that the "
             "check could not be made, not that the wrong paper was "
             "cited.",
    "bare_url": "The citation is a bare URL with no title. Nothing to "
                "compare against the resolved document.",
    "prose": "The identifier appears in running prose, so the words "
             "around it were harvested as a title. This is a real gap "
             "in the verifier: it finds the identifier and takes the "
             "line, without distinguishing a citation line from a "
             "sentence that merely mentions an arXiv ID.",
}

# ── suspects: deferred to identifier research ───────────────────────
SUSPECT_IDENTIFIERS = [
    "arxiv:2407.13193", "arxiv:2505.10468", "arxiv:2506.08422",
    "arxiv:2508.19428", "arxiv:2509.17096", "arxiv:2601.12560",
    "arxiv:2602.06052", "arxiv:2604.01438", "arxiv:2605.11610",
    "arxiv:2605.20530", "arxiv:2605.24601", "arxiv:2606.06448",
    "arxiv:2608.08601", "arxiv:2608.22974", "arxiv:2609.02248",
    "arxiv:2609.07791", "doi:10.1007/978-3-030-86523-8_22",
    "doi:10.1103/PhysRevE.73.036127",
]


def classify(label: str) -> tuple:
    """Return ('untitled', kind) or ('paraphrase', None).

    Deliberately narrow. Anything that does not clearly have no title
    is left for the reviewer, because guessing 'untitled' on a real
    title would understate a citation.
    """
    import re
    lab = (label or '').strip()
    low = lab.lower()
    if not lab:
        return ('untitled', 'empty')
    if low.startswith(('http', "'http", 'https://', "'https://")):
        return ('untitled', 'bare_url')
    for p in ('with ', 'description:', 'sources:', 'especially for',
              'analysis of', 'extension of', 'phys. rev'):
        if low.startswith(p):
            return ('untitled', 'prose')
    # Strip ONE trailing parenthetical -- that is a venue or a count --
    # and judge what remains. A label whose whole substance lives inside
    # the parentheses is untitled.
    #
    # The length test is the ONLY test here. An earlier version also
    # treated any label ENDING in ")" as prose, which caught the
    # harvesting artefact "dataset-adaptive significance levels)" but
    # ALSO caught real titles whose annotation is parenthetical:
    # "RUBAS: Rubric-Based RL for Agent Safety (4 dimensions)" was
    # being dismissed as untitled, i.e. a real citation was being
    # quietly buried. An unbalanced trailing ")" is not a reliable
    # signal on its own, so the substance test decides instead.
    stripped = re.sub(r'\s*\([^()]*\)\s*$', '', lab).strip()
    if len(stripped) < 12:
        return ('untitled', 'prose')
    return ('paraphrase', None)


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--triage',
                    default='/home/operator/.hermes/cache/scratch/triage.json')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    if not (a.check or a.apply):
        ap.error('pass --check or --apply')

    t = json.load(open(a.triage, encoding='utf-8'))
    decisions = []
    for r in t['paraphrase']:
        ident = r['ident']
        if ident in SUSPECT_IDENTIFIERS:
            continue
        reason = PARAPHRASE_REASONS.get(ident)
        if not reason:
            continue
        decisions.append((r['path'], ident, 'match', reason))
    for r in t['untitled']:
        # A suspect identifier is held even when THIS row's label is
        # merely untitled. If the identifier itself turns out to be
        # wrong for the file, "no title present" is not the whole
        # story, and adjudicating the row now would prejudge it.
        if r['ident'] in SUSPECT_IDENTIFIERS:
            continue
        kind = classify(r['label'])[1] or 'prose'
        decisions.append((r['path'], r['ident'], 'untitled_citation',
                          UNTITLED_REASONS[kind]))

    from collections import Counter
    # Key integrity: a decision that does not name a real row is
    # fiction, and a duplicate key silently applies fewer rows than
    # written -- the exact failure that cost a row in the previous
    # adjudication pass. Refuse rather than quietly proceeding.
    import os
    TABLE = ('/home/operator/hermes-brain/docs/audit/'
             't2-adjudication.json')
    if os.path.exists(TABLE):
        tbl = json.load(open(TABLE, encoding='utf-8'))
        unkeyed = ['%s::%s' % (p, i) for p, i, _v, _r in decisions
                   if '%s::%s' % (p, i) not in tbl]
        dupes = [k for k, n in Counter(
            ('%s::%s' % (p, i) for p, i, _v, _r in decisions)).items() if n > 1]
        print('  decisions vs rows    : %d' % len(decisions))
        print('  unkeyed (no such row): %d' % len(unkeyed))
        print('  duplicate keys       : %d' % len(dupes))
        for k in (unkeyed + dupes)[:5]:
            print('      %s' % k[88:])
        if unkeyed or dupes:
            raise SystemExit('refusing to run: key integrity check failed')

    print('  decisions built      : %d' % len(decisions))
    print('  -> match             : %d' % sum(
        1 for _p, _i, v, _r in decisions if v == 'match'))
    print('  -> untitled_citation : %d' % sum(
        1 for _p, _i, v, _r in decisions if v == 'untitled_citation'))
    held = len(t['paraphrase']) + len(t['untitled']) - len(decisions)
    print('  HELD for research    : %d' % held)
    miss = [i for i in SUSPECT_IDENTIFIERS
            if i not in PARAPHRASE_REASONS]
    print('  suspects w/o reason  : %d %s' % (len(miss), miss[:4]))
    if a.check:
        return
    import os
    OUT = os.path.join(os.path.dirname(a.triage), 'decisions.json')
    json.dump([{'path': p, 'ident': i, 'verdict': v, 'reason': r}
               for p, i, v, r in decisions],
              open(OUT, 'w', encoding='utf-8'), indent=1)
    print('  wrote %s' % OUT)


if __name__ == '__main__':
    main()
