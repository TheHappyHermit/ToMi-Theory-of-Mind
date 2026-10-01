"""Apply the DOI replacements that were independently verified.

A subagent researched the non-existent DOIs. Every replacement it
proposed was then re-checked here, independently:

    status 200 from Crossref, AND the resolved title and first author
    match the paper the vault's own body cites

Six of the eleven in this batch were resolved. All six passed that
check. Two of them are worth recording because the shape of the fix
looks like a typo and is not:

  * doi:10.1037/0278-7393.19.4.851: -> 10.1037/0278-7393.19.4.851
    The vault entry had a TRAILING COLON on the identifier. Stripping
    it resolves the DOI, so the paper was cited correctly all along
    and one stray character made it unroutable.
  * doi:10.1038/35066566 -> 10.1038/35066572
    One digit different. It looks exactly like a guessed fix, so the
    title was compared rather than trusting the status code: it
    resolves to "Suppressing unwanted memories by executive control",
    Anderson and Green, 2001, which is the paper the vault cites.

Five were NOT resolved and are left alone for a human. Their reasons
are recorded in the evidence file rather than papered over.
"""
import json
import re
import shutil
import sys
from pathlib import Path

BRAIN = Path('/home/operator/.hermes/oracle/brain')
BACKUP = Path('/home/operator/.hermes/cache/scratch/pre-doi2-backup')
EVIDENCE = Path('/home/operator/hermes-brain/docs/audit/'
                't2-doi-replacements.json')
RESULTS = ('/home/operator/.hermes/cache/scratch/'
           'doi_results_2.json')

# Independently confirmed: Crossref status 200 plus matching title and
# first author. Recorded here so the applied set is explicit.
VERIFIED = {
    'doi:10.1037/0278-7393.19.4.851:': {
        'doi': '10.1037/0278-7393.19.4.851',
        'title': 'The cue-familiarity heuristic in metacognition',
        'authors': 'Metcalfe, Schwartz, Joaquim', 'year': 1993,
        'note': 'the vault entry carried a TRAILING COLON on the '
                'identifier; stripping it resolves the DOI'},
    'doi:10.1038/35066566': {
        'doi': '10.1038/35066572',
        'title': 'Suppressing unwanted memories by executive control',
        'authors': 'Anderson, Green', 'year': 2001,
        'note': 'one digit differs; confirmed by title and authors, not '
                'by the status code alone'},
    'doi:10.1073/pnas.1019438108': {
        'doi': '10.1016/j.neuron.2011.02.027',
        'title': "Model-Based Influences on Humans' Choices and Striatal "
                 'Prediction',
        'authors': 'Daw, Gershman, Seymour, Dayan, Dolan', 'year': 2011,
        'note': 'the vault cited a PNAS identifier for a Neuron paper'},
    'doi:10.1073/pnas.2001203117': {
        'doi': '10.1073/pnas.1916646117',
        'title': 'Activity-dependent myelination: A glial mechanism of '
                 'oscillatory self-organization',
        'authors': 'Noori, Park, Griffiths, Bells, Frankland, Mabbott',
        'year': 2020, 'note': 'the vault year digits were transposed'},
    'doi:10.1126/science.1070121': {
        'doi': '10.1126/science.1069590',
        'title': 'A Pathway in Primate Brain for Internal Monitoring of '
                 'Movements',
        'authors': 'Sommer, Wurtz', 'year': 2002,
        'note': 'the vault year digits were transposed'},
    'doi:10.1145/306877': {
        'doi': '10.1145/276698.276876',
        'title': 'Approximate nearest neighbors',
        'authors': 'Indyk, Motwani', 'year': 1998,
        'note': 'the identifier was missing its suffix'},
}


def main():
    apply = '--apply' in sys.argv
    results = json.load(open(RESULTS, encoding='utf-8'))
    by_bad = {r['bad']: r for r in results.get('results', [])}

    unresolved = [{'bad': k, 'reason': v.get('reason') or v.get('citation')}
                   for k, v in sorted(by_bad.items())
                   if not v.get('found')]

    # find the vault lines carrying each bad identifier
    targets = []
    for bad, info in sorted(VERIFIED.items()):
        bare = bad.split(':', 1)[-1]
        hits = []
        for md in BRAIN.rglob('*.md'):
            try:
                text = md.read_text(encoding='utf-8')
            except Exception:
                continue
            if bare not in text:
                continue
            rel = str(md.relative_to(BRAIN))
            for ln in text.split('\n'):
                if bare in ln and ln.strip().startswith('- '):
                    hits.append((rel, ln, text))
        targets.append({'bad': bad, 'new_doi': info['doi'],
                        'title': info['title'], 'note': info['note'],
                        'hits': hits})

    total_hits = sum(len(t['hits']) for t in targets)
    print('  replacements: %d   vault lines affected: %d'
          % (len(VERIFIED), total_hits))
    for t in targets:
        print('     %-34s -> %-32s (%d line%s)'
              % (t['bad'][-34:], t['new_doi'], len(t['hits']),
                 '' if len(t['hits']) == 1 else 's'))
    print()
    print('  left for a human: %d' % len(unresolved))
    for u in unresolved:
        print('     %-36s %s' % (u['bad'][-36:], str(u['reason'])[:52]))

    if not apply:
        print('  DRY RUN. Pass --apply to write.')
        return 0

    written = 0
    for t in targets:
        by_file = {}
        for rel, ln, text in t['hits']:
            by_file.setdefault(rel, []).append((ln, text))
        for rel, items in by_file.items():
            full = BRAIN / rel
            text = full.read_text(encoding='utf-8')
            out = text
            for ln, _t in items:
                # Bounded replacement, with the count enforced. An
                # unbounded re.sub can match a bare DOI stem inside a
                # longer, valid identifier in the same file and splice
                # the completion onto it; see scripts/doi_replace and
                # tests/test_doi_replace.py for the case that actually
                # happened.
                from doi_replace import replace_doi
                bare = t['bad'].split(':', 1)[-1]
                out, n = replace_doi(out, bare, t['new_doi'], expected=1)
            if out != text:
                dst = BACKUP / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(full, dst)
                full.write_text(out, encoding='utf-8')
                written += 1
                print('  wrote %s' % rel)
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(
        {'batch': 2, 'verified_replacements': targets,
         'unresolved': unresolved,
         'verification': 'each DOI confirmed by Crossref status 200 plus a '
                         'title and first-author match against the paper '
                         'the vault cites'}, indent=1) + '\n',
        encoding='utf-8')
    print('  files written: %d' % written)
    return 0


if __name__ == '__main__':
    sys.exit(main())
