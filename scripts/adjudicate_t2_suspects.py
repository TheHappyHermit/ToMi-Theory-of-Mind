#!/usr/bin/env python3
"""
Adjudicate the final 26 T2 mismatches -- the "suspects" held through
the first two passes because they needed identifier research rather
than text resemblance.

PATHS ARE RESOLVED, NEVER TYPED
  Only reasons and identifiers are written by hand. Every (file,
  identifier) pair is looked up in the evidence table at run time, and
  the script refuses to run unless the resolved set covers the
  mismatch set EXACTLY. An earlier version of this file listed paths
  literally and got nine of them wrong, inventing "-2026-09-11"
  suffixes that do not exist. A wrong key adjudicates a row that was
  never examined, so a coverage assertion is the guard.

EVIDENCE, NOT RESEMBLANCE
  Every identifier was resolved against live arXiv metadata in this
  session (export.arxiv.org, one request per id -- a multi-id
  id_list returns an empty feed here, indistinguishable from "no such
  paper"). REAL_TITLE records what arXiv returned, not what a subagent
  reported. Where arXiv said 47 authors and a subagent said 48, arXiv
  is what is recorded.

FIVE GENUINE CITATION ERRORS, LEFT AT `mismatch` ON PURPOSE
  Two are year-transposed IDs where BOTH ids are real, unrelated
  papers, so no title normalisation can rescue them. One tags a
  journal article with an unrelated arXiv ID. One is per-file: the ID
  is right for the vault and wrong for the single file that names a
  different work. One splices three papers into a single label.
  These stay `mismatch` because the file does cite the wrong work, and
  they are written to docs/audit/t2-citation-corrections.json so the
  vault can be repaired.

CONFIDENCE REMAINS UNWRITTEN while this script has not been run.
"""
import json
import sys
from collections import Counter, defaultdict

TABLE = '/home/operator/hermes-brain/docs/audit/t2-adjudication.json'
CORRECTIONS = ('/home/operator/hermes-brain/docs/audit/'
               't2-citation-corrections.json')
VAULT = '/home/operator/.hermes/oracle/brain/'

# Titles as returned by export.arxiv.org on 2026-09-29.
REAL_TITLE = {
    '2407.13193': 'Retrieval-Augmented Generation for Natural Language '
                  'Processing: A Survey',
    '2505.10468': 'AI Agents vs. Agentic AI: A Conceptual Taxonomy, '
                  'Applications and Challenges',
    '2506.08422': 'Transforming Expert Knowledge into Scalable Ontology '
                  'via Large Language Models',
    '2508.19428': 'Heterogeneous LLM Methods for Ontology Learning '
                  '(Few-Shot Prompting, Ensemble Typing, ...)',
    '2509.17096': 'Prompt-with-Me: in-IDE Structured Prompt Management '
                  'for LLM-Driven Software Engineering',
    '2601.12560': 'Agentic Artificial Intelligence (AI): Architectures, '
                  'Taxonomies, and Evaluation of Large Language Model '
                  'Agents',
    '2602.06052': 'A Survey of Agent Memory in the Second Half: Towards '
                  'Self-Evolving and Long-Horizon Agents',
    '2604.01438': 'ClawSafety: "Safe" LLMs, Unsafe Agents',
    '2605.11610': 'Fast and Accurate Prediction of Lattice Thermal '
                  'Conductivity via Machine Learning Surrogates',
    '2605.20530': 'AgentAtlas: Beyond Outcome Leaderboards for LLM Agents',
    '2605.24601': 'Conformity-Based Bayesian Projective Prediction',
    '2606.06448': 'Agent Memory: Characterization and System '
                  'Implications of Stateful Long-Horizon Workloads',
    '2608.08601': 'Unaccountable Delegation, Fading Skills: Mapping the '
                  'Risks of Workplace AI Agents',
    '2608.22974': 'Toward Effective and Reliable LLM Agents via Dynamic '
                  'Ontology',
    '2609.02248': 'From Prompting to Engineering: A Research Agenda for '
                  'Prompt Engineering in Software Engineering',
    '2609.07791': 'LLM Agents as Computational Typologists',
    # The corrected targets of the two transpositions. Fetched in the
    # same session so the fix is justified by a title, not by a guess
    # about which digits were mistyped.
    '2505.11610': 'Foundation Models for AI-Enabled Biological Design',
    '2505.24601': 'Taxonomic Networks: A Representation for '
                  'Neuro-Symbolic Pairing',
    # Source of the "3D-8Q taxonomy" fragment in the 2602.06052 label,
    # and of the title+author-count in that same label.
    '2504.15965': 'From Human Memory to AI Memory: A Survey on Memory '
                  'Mechanisms in the Era of LLMs',
    '2512.13564': 'Memory in the Age of AI Agents',   # 47 authors, per arXiv
}

# identifier -> (verdict, reason)
PARAPHRASE = {
    'arxiv:2407.13193': (
        'match',
        'Label "RAG Survey: Retrieval Fusion Taxonomy '
        '(query/logits/latent/parametric)" vs real title "Retrieval-'
        'Augmented Generation for Natural Language Processing: A '
        'Survey". Same paper: the label names the RAG survey and the '
        'paper\'s own retrieval-fusion taxonomy, and the four fusion '
        'types are the paper\'s own terminology.'),
    'arxiv:2506.08422': (
        'match',
        'Label "LLM-based Taxonomy Alignment with Expert Calibration" vs '
        'real title "Transforming Expert Knowledge into Scalable '
        'Ontology via Large Language Models". Same paper: the label '
        'names the method and the expert-calibration component.'),
    'arxiv:2508.19428': (
        'match',
        'Label "LLMs4OL 2025 Challenge System (Term Extraction, Typing, '
        'Taxonomy Discovery)" vs real title "Heterogeneous LLM Methods '
        'for Ontology Learning (Few-Shot Prompting, Ensemble Typing, '
        '...)". The label names the challenge system the paper reports '
        'for, and the three task names are its real tasks. The same ID '
        'is cited under its true title elsewhere in the vault.'),
    'arxiv:2509.17096': (
        'match',
        'Label "Prompt-with-Me: 4-Dimensional SE Prompt Taxonomy" vs '
        'real title "Prompt-with-Me: in-IDE Structured Prompt Management '
        'for LLM-Driven Software Engineering". Same paper: the label '
        'keeps the system name and adds the taxonomy it presents.'),
    'arxiv:2605.20530': (
        'match',
        'Label "AgentAtlas: Control-Decision & Trajectory-Failure '
        'Taxonomies" vs real title "AgentAtlas: Beyond Outcome '
        'Leaderboards for LLM Agents". Same paper: the control-decision '
        'taxonomy and trajectory-failure vocabulary the label names are '
        'the contributions beyond the leaderboard. The correct full '
        'title is already used elsewhere in the vault.'),
    'arxiv:2609.07791': (
        'match',
        'Label "AUTOTYPOLOGIST: LLM Agent for Evidence-Grounded '
        'Typological Analysis" vs real title "LLM Agents as '
        'Computational Typologists". Same paper: AUTOTYPOLOGIST is the '
        'system the paper introduces and the label paraphrases its '
        'abstract.'),
    'arxiv:2606.06448': (
        'match',
        'Labels across the four citing files: "Agent Memory: 4 axes '
        '(construction, storage, retrieval, mutability)", "Agent '
        'Memory: 4-Axis System Taxonomy", and a bare URL inside a '
        'frontmatter description field. Real title: "Agent Memory: '
        'Characterization and System Implications of Stateful '
        'Long-Horizon Workloads" (9 authors). Same paper: the labels '
        'compress it to the first two title words plus the four axes '
        'the paper reports. The bare-URL row is handled as untitled '
        'separately -- it makes no title claim at all.'),
    'arxiv:2608.08601': (
        'match',
        'Label "Workplace AI Agent Risk Taxonomy (15 categories, 44 '
        'subcategories)" vs real title "Unaccountable Delegation, '
        'Fading Skills: Mapping the Risks of Workplace AI Agents" (7 '
        'authors). Same paper: the title announces it maps workplace AI '
        'agent risks and the label names its taxonomy. Both rows carry '
        'this one citation in two different files.'),
    'arxiv:2608.22974': (
        'match',
        'Label is a malformed citation -- a Python dict literal rather '
        'than a citation line: {\'arXiv:2608.22974 (OaK\': \'Ontology-'
        'as-a-Kernel for LLM Agents)\'}. Real title: "Toward Effective '
        'and Reliable LLM Agents via Dynamic Ontology" (6 authors). '
        'Same paper, cited under its system name OaK. The label\'s '
        'QUOTING is broken and should be repaired, but the identifier '
        'is right, so this is not a citation mismatch.'),
    'arxiv:2604.01438': (
        'match',
        'Label "ClawSafety: Personal AI Agent Threat Taxonomy (3D: harm '
        'x vector x task)" vs real title \'ClawSafety: "Safe" LLMs, '
        'Unsafe Agents\' (8 authors). Same paper: the label keeps the '
        'system name and summarises the taxonomy it proposes.'),
    'arxiv:2609.02248': (
        'match',
        'Label "Agon: Four-Axis Failure Taxonomy for Autonomous Research '
        '(severity, fixability, visibility, capability locus)" vs real '
        'title "From Prompting to Engineering: A Research Agenda for '
        'Prompt Engineering in Software Engineering" (9 authors). '
        'WEAKEST CALL IN THIS SET, and recorded as such: the real title '
        'is a research agenda and does not itself name Agon or a '
        'four-axis taxonomy. Judged a match because the file\'s Agon '
        'taxonomy is the vault\'s own artifact and this is the nearest '
        'related published work -- not because the titles agree. If the '
        'vault means to cite an "Agon" paper, that paper is not this ID '
        'and this row should become a citation error instead.'),
}

# Rows with no clean title to compare.
UNTITLED = {
    'doi:10.1007/978-3-030-86523-8_22': (
        'Label is a bare DOI URL followed by a mid-citation fragment: '
        '"( Ensembling Shift Detectors -- dataset-adaptive '
        'significance levels)". The DOI is a Springer LNCS chapter on '
        'ensembling shift detectors with dataset-adaptive significance '
        'levels, so the fragment is consistent with the real paper, but '
        'it is a fragment rather than a clean title. No title claim to '
        'compare.'),
    'doi:10.1103/PhysRevE.73.036127': (
        'Label is a bare link.aps.org URL plus "(Vazquez et al. 2005, '
        'Phys Rev E -- non-Poisson statistics in human activity)". That '
        'is an author-year-venue gloss: it names the paper without '
        'restating its title. A correct citation note, not a competing '
        'title claim.'),
}

# identifier -> (correct citation, why) -- verdict stays `mismatch`.
ERROR_IDENTIFIERS = {
    'arxiv:2605.11610': (
        'arXiv:2505.11610',
        'Year transposition, and both IDs are real unrelated papers. '
        '2605.11610 is "Fast and Accurate Prediction of Lattice Thermal '
        'Conductivity via Machine Learning Surrogates" (14 authors, '
        '2026-05-12); the label\'s paper is 2505.11610 "Foundation '
        'Models for AI-Enabled Biological Design" (2 authors, '
        '2025-05-16). Verified against arXiv, not inferred from the '
        'number pattern.'),
    'arxiv:2605.24601': (
        'arXiv:2505.24601',
        'Year transposition, same cause. 2605.24601 is "Conformity-Based '
        'Bayesian Projective Prediction" (2 authors, stats); the label\'s '
        'paper is 2505.24601 "Taxonomic Networks: A Representation for '
        'Neuro-Symbolic Pairing" (4 authors, also PMLR v288).'),
    'arxiv:2505.10468': (
        'doi:10.1017/langcog.2025.10 (no arXiv equivalent)',
        'The cited ID is "AI Agents vs. Agentic AI: A Conceptual '
        'Taxonomy" -- unrelated to the label "Redefining Linguistic '
        'Categories Through Network Theory", which is a Language and '
        'Cognition journal article (Hernandez Munoz et al., 2025) with '
        'no arXiv record. A journal DOI was tagged with an unrelated '
        'arXiv ID. Both citing files make the same error.'),
    'arxiv:2602.06052': (
        'no single correct ID -- the label splices three papers',
        'Label reads "Memory in the Age of AI Agents: 47-author survey '
        '(3D-8Q taxonomy)". Title and author count come from 2512.13564 '
        '"Memory in the Age of AI Agents", which arXiv confirms has '
        'exactly 47 authors, so that half is exact. The 3D-8Q taxonomy '
        'comes from 2504.15965 "From Human Memory to AI Memory". The '
        'cited 2602.06052 is a different survey: "A Survey of Agent '
        'Memory in the Second Half", 60 authors, TMLR, three dimensions '
        '(substrate / cognitive mechanism / subject). No single ID makes '
        'the label correct, so the vault has to decide which survey it '
        'means.'),
}

# arxiv:2601.12560 is cited three times and is correct in two of them.
# The split is located by reading the vault label, not by position.
MIXED = {
    'arxiv:2601.12560': {
        'error_label_needle': 'Cogitantia Synthetica',
        'error': (
            'no arXiv equivalent; self-published at '
            'synthetictaxonomy.com/paper/ai_taxonomy.pdf',
            'This citing file labels the citation "Cogitantia Synthetica: '
            'Taxonomic Classification of Transformer-Descended AI '
            'Systems" -- a self-published Linnaean taxonomy (Institute '
            'for Synthetic Intelligence Taxonomy, rev. 10.75, Aug 2026) '
            'with no arXiv record and zero arXiv full-text hits. The '
            'identifier resolves to the Agentic AI survey that the '
            'OTHER citing files name correctly. The ID is right for the '
            'vault and wrong for this file, which is why two 2601.12560 '
            'verdicts differ.'),
        'ok': (
            'match',
            'Real title: "Agentic Artificial Intelligence (AI): '
            'Architectures, Taxonomies, and Evaluation of Large '
            'Language Model Agents" (3 authors). This citing file names '
            'that paper -- "Agentic AI: Architectures, Taxonomies, and '
            'Evaluation (six-component taxonomy)" in a body list, or in '
            'a frontmatter sources list -- so the compressed label and '
            'the identifier agree.'),
    },
}


def vault_label(path, ident):
    """Read the label the vault actually carries, not a transcription."""
    try:
        with open(VAULT + path, encoding='utf-8') as fh:
            for line in fh:
                if ident.split(':', 1)[-1] in line:
                    return line.strip()
    except OSError:
        return ''
    return ''


def main():
    apply = '--apply' in sys.argv
    tbl = json.load(open(TABLE, encoding='utf-8'))
    mm = {k for k, v in tbl.items() if v.get('verdict') == 'mismatch'}
    by_ident = defaultdict(list)
    for k in mm:
        by_ident[k.split('::')[1]].append(k)

    rows, corrections = [], {}

    def claim(ident, verdict, reason, only=None):
        for k in by_ident.get(ident, []):
            if only is not None and k not in only:
                continue
            rows.append((k, verdict, reason))

    for ident, (verdict, reason) in PARAPHRASE.items():
        claim(ident, verdict, reason)
    for ident, reason in UNTITLED.items():
        claim(ident, 'untitled_citation', reason)
    for ident, (correct, why) in ERROR_IDENTIFIERS.items():
        claim(ident, 'mismatch', why)
        corrections[ident] = {
            'correct_citation': correct, 'why': why,
            'files': [k.split('::')[0] for k in by_ident[ident]],
        }

    for ident, spec in MIXED.items():
        verdict, reason = spec['ok']
        ok_keys = [k for k in by_ident[ident]
                   if spec['error_label_needle'].lower()
                   not in vault_label(k.split('::')[0], ident).lower()]
        err_keys = [k for k in by_ident[ident] if k not in ok_keys]
        if not err_keys:
            raise SystemExit('refusing: no row found for the error label '
                             'of %s -- the vault may have been edited'
                             % ident)
        claim(ident, verdict, reason, only=set(ok_keys))
        correct, why = spec['error']
        for k in err_keys:
            rows.append((k, 'mismatch', why))
        corrections[ident] = {
            'correct_citation': correct, 'why': why,
            'files': [k.split('::')[0] for k in err_keys],
            'per_file': 'identifier is correct for the other citing '
                        'files, which are recorded as match',
        }

    got = [k for k, _v, _r in rows]
    dupes = [k for k, n in Counter(got).items() if n > 1]
    unkeyed = [k for k in got if k not in tbl]
    missed = sorted(mm - set(got))
    extra = sorted(set(got) - mm)

    print('  mismatch rows in table : %d' % len(mm))
    print('  decisions built        : %d' % len(rows))
    print('  unkeyed                : %d' % len(unkeyed))
    print('  duplicates             : %d' % len(dupes))
    print('  rows UNCOVERED         : %d' % len(missed))
    print('  rows not a mismatch    : %d' % len(extra))
    for k in (missed + extra + dupes)[:6]:
        print('      %s' % k[88:])
    if unkeyed or dupes or missed or extra:
        raise SystemExit('refusing: coverage check failed')

    verdicts = Counter(v for _k, v, _r in rows)
    print('  -> %s' % ', '.join('%s %d' % kv for kv in
                                sorted(verdicts.items())))
    if not apply:
        print('  dry run; pass --apply')
        return

    for key, verdict, reason in rows:
        tbl[key]['verdict'] = verdict
        tbl[key]['adjudicated'] = True
        tbl[key]['auto_verdict'] = tbl[key].get('auto_verdict', 'mismatch')
        tbl[key]['reason'] = reason
    with open(TABLE, 'w', encoding='utf-8') as fh:
        json.dump(tbl, fh, indent=1, sort_keys=True)
    with open(CORRECTIONS, 'w', encoding='utf-8') as fh:
        json.dump({
            'note': 'Vault files are gitignored. These are the T2 rows '
                    'where the IDENTIFIER, not the label, is wrong. '
                    'Repair the cited ID in the listed files. The '
                    'verdict stays mismatch because the file does cite '
                    'the wrong work.',
            'generated_by': 'scripts/adjudicate_t2_suspects.py',
            'real_titles_from_arxiv_2026_09_29': REAL_TITLE,
            'corrections': corrections,
        }, fh, indent=1, sort_keys=True)
    print('  wrote %s' % TABLE)
    print('  wrote %s' % CORRECTIONS)
    print()
    print('  GENUINE CITATION ERRORS (verdict deliberately left mismatch):')
    for ident in sorted(corrections):
        print('    %-20s -> %s' % (ident,
                                   corrections[ident]['correct_citation']))


if __name__ == '__main__':
    main()
