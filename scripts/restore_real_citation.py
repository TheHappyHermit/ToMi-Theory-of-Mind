"""Restore the real citation that was removed in error.

WHAT HAPPENED. The phantom was

    "Language and Cognition 2025 -- Redefining Linguistic Categories
     Through Network Theory (arXiv:2505.10468)"

An arXiv search for the title returned nothing, and 2505.10468 resolves
to an unrelated agentic-AI paper, so the arXiv half of the citation was
judged fabricated. The TITLE half was not: the paper is real.

    doi:10.1017/langcog.2025.10
    "Redefining linguistic categories through network theory"
    Language and Cognition, vol 17, 2025
    Hern\u00e1n Mu\u00f1oz, Tom\u00e9 Cornejo, L\u00f3pez

So the source line carried a real paper under a fabricated identifier,
and the correct repair is to swap the identifier, not to delete the
source. Two files had the correct DOI already (comprehensive-2026-09-11
and -v2) and were the evidence that the title was real; my earlier pass
had already put that DOI in place there. The two files whose only
citation was the arXiv-flavoured one lost the source entirely, and the
body heading lost its attribution.

This restores all four, with the authoritative DOI.
"""
import json
import shutil
import sys
from pathlib import Path

BRAIN = Path('/home/operator/.hermes/oracle/brain')
BACKUP = Path('/home/operator/.hermes/cache/scratch/pre-restore-backup')
EVIDENCE = Path('/home/operator/hermes-brain/docs/audit/'
                't2-fabricated-citations.json')

DOI = '10.1017/langcog.2025.10'
TITLE = 'Redefining Linguistic Categories Through Network Theory'
VENUE = 'Language and Cognition 2025'
CANON = ('Redefining linguistic categories through network theory')

# the two files whose sources: entry was removed in error
RESTORE_SOURCE = [
    'research/frontier-research-taxonomy-metadata-categorization-'
    'linguistic-philosophical-2026-09-10.md',
    'research/frontier-research-taxonomy-september-2026-supplement-v3.md',
]

# the two files whose body heading lost its attribution
RESTORE_HEADING = [
    'research/frontier-research-taxonomy-comprehensive-2026-09-10.md',
    'research/frontier-research-taxonomy-comprehensive-2026-09-10-v2.md',
]

SOURCE_LINE = ('  - "Redefining Linguistic Categories Through Network '
               'Theory (https://doi.org/%s)"' % DOI)


def main():
    apply = '--apply' in sys.argv
    done = []
    for rel in RESTORE_SOURCE:
        full = BRAIN / rel
        text = full.read_text(encoding='utf-8')
        if DOI in text:
            print('  ALREADY  %s' % rel[-56:])
            continue
        if 'sources:' not in text:
            print('  NO SOURCES  %s' % rel[-56:])
            continue
        lines = text.split('\n')
        # insert as the first entry of the sources: list
        for i, ln in enumerate(lines):
            if ln.strip() == 'sources:':
                lines.insert(i + 1, SOURCE_LINE)
                break
        else:
            print('  NO sources: KEY  %s' % rel[-56:])
            continue
        done.append((rel, 'restored_source', SOURCE_LINE))
        if apply:
            dst = BACKUP / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(full, dst)
            full.write_text('\n'.join(lines), encoding='utf-8')
        print('  RESTORED source  %s' % rel[-56:])

    for rel in RESTORE_HEADING:
        full = BRAIN / rel
        text = full.read_text(encoding='utf-8')
        # The earlier pass stripped the whole parenthetical, taking the
        # paper's title with the false attribution, so the heading now
        # reads "### 2.1 Four Types of Linguistic Categories" with no
        # citation at all. Match on the heading, and restore both the
        # title and the DOI.
        hit = None
        for ln in text.split('\n'):
            if ln.startswith('### 2.1 Four Types of Linguistic '
                             'Categories') and DOI not in ln:
                hit = ln
                break
        if hit is None:
            print('  (no de-attributed heading) %s' % rel[-56:])
            continue
        new = '%s (%s, %s, doi:%s)' % (hit.rstrip(), TITLE, VENUE, DOI)
        done.append((rel, 'restored_attribution', new))
        if apply:
            dst = BACKUP / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists():
                shutil.copy2(full, dst)
            full.write_text(text.replace(hit, new, 1), encoding='utf-8')
        print('  RESTORED heading %s' % rel[-56:])
        print('      %s' % new.strip()[:104])

    if not apply:
        print('  DRY RUN. Pass --apply to write.')
        return 0

    # correct the evidence record: the paper was real, the ID was not
    data = json.loads(EVIDENCE.read_text(encoding='utf-8'))
    data['correction'] = {
        'superseded_finding': 'the source was removed as fabricated. '
                              'That was wrong: only the arXiv identifier '
                              'was fabricated.',
        'the_paper_is_real': {
            'doi': DOI,
            'title': CANON,
            'venue': 'Language and Cognition, vol 17, 2025',
            'authors': ['Hernandez Munoz', 'Tome Cornejo', 'Lopez'],
            'how_found': 'Crossref lookup of the DOI that two other '
                         'vault files already cited for this same title',
        },
        'what_was_fabricated': 'the arXiv:2505.10468 identifier. That '
                               'arXiv id belongs to "AI Agents vs. Agentic '
                               'AI", an unrelated agentic-AI survey.',
        'correct_repair': 'substitute the authoritative DOI, do not delete '
                          'the source',
        'restored': [{'path': p, 'kind': k, 'text': t} for p, k, t in done],
    }
    EVIDENCE.write_text(json.dumps(data, indent=1) + '\n', encoding='utf-8')
    print('  updated %s' % EVIDENCE)
    return 0


if __name__ == '__main__':
    sys.exit(main())
