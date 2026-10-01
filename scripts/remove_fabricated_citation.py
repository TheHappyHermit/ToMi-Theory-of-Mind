"""Remove a fabricated citation and record why it was fabricated.

FINDING. Five vault files attribute a taxonomy table to a paper that
does not exist:

    "Language and Cognition 2025 -- Redefining Linguistic Categories
     Through Network Theory (arXiv:2505.10468)"

  * An arXiv full-text/keyword search for that exact title returns 0
    hits. No such paper exists in the arXiv corpus.
  * arXiv:2505.10468 IS real, and is "AI Agents vs. Agentic AI: A
    Conceptual Taxonomy, Applications and Challenges" (Sapkota,
    Roumeliotis, Karkee; cs.AI; 2025-05-15) -- an agentic-AI survey
    with no linguistic-categorisation content.
  * The table's content is genuine cognitive linguistics (the
    natural/taxonomic, ad hoc, radial, schema typology), but the
    ATTRIBUTION is invented. A real-looking identifier attached to a
    real-looking title, pointing at a paper that was never written.

This is the one class of defect that no amount of titling can fix,
because there is no title to write: the citation itself is the error.

WHAT THIS SCRIPT DOES, AND DELIBERATELY DOES NOT DO.

  * In the two files where the phantom appears only in the
    `sources:` list, the source line is removed -- the file never
    relied on it, and a citation to a non-existent paper cannot be
    repaired, only deleted.
  * In the two files where a body heading attributes the taxonomy to
    the phantom, the heading keeps its content and loses the false
    attribution.
  * The fifth file, frontier-research-taxonomy-comprehensive-2026-09-11
    .md, cites 2505.10468 CORRECTLY as "AI Agents vs. Agentic AI". It
    is listed here only to prove it was checked and left alone. A
    blanket "remove every mention" would have deleted a correct
    citation.

NO REPLACEMENT IDENTIFIER IS INVENTED. The real typology is Lakoff's,
but Crossref could not confirm a DOI for the chapter, and writing an
unverified identifier is precisely the failure being fixed here. The
files are left citing nothing rather than citing something unchecked,
and the gap is recorded in docs/audit/t2-fabricated-citations.json for
a human to fill from a source they can read.
"""
import json
import shutil
import sys
from pathlib import Path

BRAIN = Path('/home/operator/.hermes/oracle/brain')
BACKUP = Path('/home/operator/.hermes/cache/scratch/pre-fabricated-backup')
EVIDENCE = Path('/home/operator/hermes-brain/docs/audit/'
                't2-fabricated-citations.json')

PHANTOM_ID = '2505.10468'
PHANTOM_TITLE = 'Redefining Linguistic Categories Through Network Theory'
ACTUAL_TITLE = ('AI Agents vs. Agentic AI: A Conceptual Taxonomy, '
                'Applications and Challenges')

# files where the phantom is a sources: entry and nothing else
SOURCE_ONLY = [
    'research/frontier-research-taxonomy-metadata-categorization-'
    'linguistic-philosophical-2026-09-10.md',
    'research/frontier-research-taxonomy-september-2026-supplement-v3.md',
]

# files where a BODY heading attributes the taxonomy to the phantom
BODY_ATTRIBUTION = [
    'research/frontier-research-taxonomy-comprehensive-2026-09-10.md',
    'research/frontier-research-taxonomy-comprehensive-2026-09-10-v2.md',
]

# cited correctly elsewhere; listed so the exclusion is explicit
CORRECT_USE = ('research/frontier-research-taxonomy-comprehensive-'
               '2026-09-11.md')


def main():
    apply = '--apply' in sys.argv
    actions, unchanged = [], []

    for rel in SOURCE_ONLY:
        full = BRAIN / rel
        text = full.read_text(encoding='utf-8')
        hits = [ln for ln in text.split('\n')
                if PHANTOM_ID in ln and ln.strip().startswith('- ')]
        if len(hits) != 1:
            unchanged.append((rel, 'expected 1 source line, found %d'
                              % len(hits)))
            continue
        if PHANTOM_TITLE not in hits[0]:
            unchanged.append((rel, 'source line does not carry the '
                                     'phantom title; left alone'))
            continue
        actions.append({'path': rel, 'kind': 'removed_source',
                        'line': hits[0]})
        if apply:
            out = '\n'.join(ln for ln in text.split('\n')
                            if ln != hits[0])
            dst = BACKUP / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(full, dst)
            full.write_text(out, encoding='utf-8')

    for rel in BODY_ATTRIBUTION:
        full = BRAIN / rel
        text = full.read_text(encoding='utf-8')
        hits = [ln for ln in text.split('\n')
                if PHANTOM_ID in ln and PHANTOM_TITLE in ln]
        if not hits:
            unchanged.append((rel, 'no attributed body heading found'))
            continue
        for ln in hits:
            new = ln.replace(
                ' (%s, arXiv:%s, Language and Cognition 2025)'
                % (PHANTOM_TITLE, PHANTOM_ID), '')
            new = new.replace(
                '(%s, arXiv:%s, Language and Cognition 2025)'
                % (PHANTOM_TITLE, PHANTOM_ID), '')
            if new == ln:
                unchanged.append((rel, 'heading text did not match the '
                                         'expected form; left alone'))
                continue
            actions.append({'path': rel, 'kind': 'deattributed_heading',
                            'old': ln, 'new': new})
            if apply:
                dst = BACKUP / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                if not dst.exists():
                    shutil.copy2(full, dst)
                full.write_text(text.replace(ln, new, 1), encoding='utf-8')
                text = full.read_text(encoding='utf-8')

    print('  actions: %d' % len(actions))
    for a in actions:
        print('     %-18s %s' % (a['kind'], a['path'][-58:]))
    print('  left alone: %d' % len(unchanged))
    for rel, why in unchanged:
        print('     %-58s %s' % (rel[-56:], why))
    print('  correct use kept: %s' % CORRECT_USE)

    if not apply:
        print('  DRY RUN. Pass --apply to write.')
        return 0
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps({
        'finding': 'fabricated citation: a source attributed to a paper '
                   'that does not exist in the arXiv corpus',
        'phantom_title': PHANTOM_TITLE,
        'phantom_identifier': 'arXiv:' + PHANTOM_ID,
        'identifier_actually_resolves_to': ACTUAL_TITLE,
        'why_not_replaced': 'the real typology is Lakoff\'s, but no DOI '
                            'could be confirmed from Crossref, and an '
                            'unverified identifier is the failure being '
                            'fixed here; the source was removed and the '
                            'gap left for a human to fill from a readable '
                            'source',
        'actions': actions,
        'left_alone': [{'path': r, 'reason': w} for r, w in unchanged],
        'correct_use_kept': CORRECT_USE,
    }, indent=1) + '\n', encoding='utf-8')
    print('  wrote %s' % EVIDENCE)
    return 0


if __name__ == '__main__':
    sys.exit(main())
