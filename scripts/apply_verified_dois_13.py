"""Apply the DOI replacements from research batches 1 and 3.

Ten replacements, each independently confirmed before being listed
here: Crossref status 200 AND a resolved title and first author that
match the paper the vault's own citation names. Four are worth
recording because the shape of the fix looks like a typo and is not:

  * 10.1016/0010-0285 -> 10.1016/0010-0285(74)90009-7
    A bare journal ISSN stem is the prefix of a full Elsevier DOI, not
    a DOI. Confirmed by title AND by author: Bjork and Whitten, 1974,
    "Recency-sensitive retrieval processes in long-term free recall".
  * 10.1016/0028-3932 -> 10.1016/0028-3932(95)00100-X
    Same shape, same resolution.
  * 10.1016/0364-0213 -> 10.1207/s15516709cog1401_3
    Both prefixes are real journals in this corpus. The vault cites
    Spelke 1990 "Principles of Object Perception" from a
    Developmental-Origins-of-Cognition file, and the resolved record
    is exactly that: Spelke, 1990.
  * 10.1177/0956797614556681 -> 10.1126/science.171.3972.701
    A publisher AND journal change, in a Mental-Rotation file. The
    vault's own citation says "Shepard, R. N., & Metzler, J. (1971).
    Mental rotation of three-dimensional objects", and the resolved
    record is Shepard and Metzler 1971 in Science. The Sage DOI the
    vault held was wrong; this is the paper the file means.

Fifteen of the twenty-five were NOT resolved and are left alone. Their
reasons are recorded rather than papered over -- several are cases
where no article matching the vault's description exists at all, which
is a fact about the citation, not a gap in the search.
"""
import json
import re
import shutil
import sys
from pathlib import Path

BRAIN = Path('/home/operator/.hermes/oracle/brain')
BACKUP = Path('/home/operator/.hermes/cache/scratch/pre-doi13-backup')
EVIDENCE = Path('/home/operator/hermes-brain/docs/audit/'
                't2-doi-replacements.json')
RESULTS = ['/home/operator/.hermes/cache/scratch/doi_results_1.json',
           '/home/operator/.hermes/cache/scratch/doi_results_3.json']

# Independently confirmed: Crossref 200 plus a title and first-author
# match against the paper the vault cites. Recorded explicitly so the
# applied set is auditable without re-running the research.
VERIFIED = {
    # NOT APPLIED. The vault stores the full, correct SICI DOI in a
    # numbered reference at line 192; only the sources entry is
    # truncated, and the sources entry is the line that needs a title
    # rather than an identifier. Rewriting it here would duplicate a
    # citation the file already gets right. Keyed with a _skip_ prefix
    # so the audit trail shows the decision instead of dropping it.
    '_skip_10.1002/(SICI)1099-0720(199812)12:6': (
        '10.1002/(SICI)1099-0720(1998120)12:6<617::AID-ACP542>3.0.CO;2-5',
        'Context-dependent memory for meaningful material: Information '
        'for students',
        'Grant, Bredahl, Clay, Ferrie, Groves, McDorman, Dark', 1998,
        'SKIPPED: the full DOI is already in the file body; only the '
        'sources entry is short'),
    '10.1016/0010-0285': (
        '10.1016/0010-0285(74)90009-7',
        'Recency-sensitive retrieval processes in long-term free recall',
        'Bjork, Whitten', 1974,
        'bare journal ISSN stem, which is a DOI prefix and not a DOI'),
    '10.1016/0028-3932': (
        '10.1016/0028-3932(95)00100-X',
        'Recency effect in anterograde amnesia: Evidence for distinct '
        'memory retrieval processes',
        'Carlesimo, Marfia, Loasses, Caltagirone', 1996,
        'bare journal ISSN stem, same shape'),
    '10.1016/0364-0213': (
        '10.1207/s15516709cog1401_3',
        'Principles of Object Perception',
        'Spelke', 1990,
        'both prefixes are real journals; the resolved record is the '
        'Spelke paper the vault cites'),
    # The vault stores this identifier TRUNCATED -- "10.1016/S0079-7421
    # (08" with no closing bracket. Three other files in the corpus
    # cite 10.1016/S0079-7421(08)60536-8 (McCloskey & Cohen 1989), a
    # DIFFERENT paper in the same journal, and they contain the
    # truncated string only as a substring of that intact DOI. So the
    # prefix is ambiguous across the corpus and the key used here is
    # the truncated form, which matches exactly the one file where it
    # is a real citation: research/batch210-..., whose line 113 names
    # the source as Nelson & Narens, "Metamemory: A theoretical
    # framework and new findings", Psychology of Learning and
    # Motivation 26, 125-173. That is the paper the completion
    # resolves to.
    '10.1016/S0079-7421(08': (
        '10.1016/S0079-7421(08)60053-5',
        'Metamemory: A Theoretical Framework and New Findings',
        'Nelson', 1990,
        'stored truncated in the vault; completed from the paper the '
        'file names in its own reference list'),
    '10.1016/S0361-9230(03)00131-7': (
        '10.1016/j.brainresbull.2003.09.004',
        'Sleep and synaptic homeostasis: a hypothesis',
        'Tononi, Cirelli', 2003,
        'the vault held a ScienceDirect PII, not a DOI'),
    '10.1016/S1364-6613(99)01293-3': (
        '10.1016/S1364-6613(99)01294-2',
        'Catastrophic forgetting in connectionist networks',
        'French', 1999, 'one digit off; confirmed by title and author'),
    '10.1146/annurev-psych-010418-103141': (
        '10.1146/annurev-psych-010213-115117',
        'Properties of the Internal Clock: First- and Second-Order '
        'Principles',
        'Allman, Teki, Griffiths, Meck', 2014,
        'the year and article number in the vault string were wrong'),
    '10.7551/mitpress/9780262112833.001.0001': (
        '10.7551/mitpress/9780262014038.001.0001',
        'The Extended Mind',
        'Menary (ed.)', 2010, 'one digit off in the ISBN part'),
    '10.1177/0956797614556681': (
        '10.1126/science.171.3972.701',
        'Mental Rotation of Three-Dimensional Objects',
        'Shepard, Metzler', 1971,
        'the vault held a Sage DOI; the paper it means is Shepard and '
        'Metzler 1971 in Science, which the vault body already said'),
}


def main():
    apply = '--apply' in sys.argv
    unresolved = []
    for p in RESULTS:
        data = json.load(open(p, encoding='utf-8'))
        for r in data.get('results', []):
            if not r.get('found'):
                unresolved.append({'bad': r['bad'],
                                   'reason': r.get('reason')
                                   or r.get('citation') or ''})

    targets = []
    skipped = []
    for bad, (new, title, au, yr, note) in sorted(VERIFIED.items()):
        if bad.startswith('_skip_'):
            skipped.append({'bad': bad[6:], 'new_doi': new, 'title': title,
                            'authors': au, 'year': yr, 'note': note})
            print('  SKIP  %-32s %s' % (bad[6:][-32:], note[:40]))
            continue
        hits = []
        for md in BRAIN.rglob('*.md'):
            try:
                text = md.read_text(encoding='utf-8')
            except Exception:
                continue
            if bad not in text:
                continue
            end = text.find('\n---', 3)
            fm = text[:end] if end != -1 else text
            for ln in fm.split('\n'):
                if bad in ln and ln.strip().startswith('- '):
                    hits.append((str(md.relative_to(BRAIN)), ln, text))
                    break
        if not hits:
            raise SystemExit('no frontmatter source line for %r -- the '
                             'key does not match disk' % bad)
        targets.append({'bad': bad, 'new_doi': new, 'title': title,
                        'authors': au, 'year': yr, 'note': note,
                        'hits': hits})

    print('  replacements: %d   vault lines: %d'
          % (len(targets), sum(len(t['hits']) for t in targets)))
    for t in targets:
        print('     %-34s -> %-46s %d line%s'
              % (t['bad'][-34:], t['new_doi'][:46], len(t['hits']),
                 '' if len(t['hits']) == 1 else 's'))
    print()
    print('  left for a human: %d' % len(unresolved))
    for u in sorted(unresolved, key=lambda x: x['bad']):
        print('     %-34s %s' % (u['bad'][-34:], str(u['reason'])[:48]))

    if not apply:
        print('  DRY RUN. Pass --apply to write.')
        return 0

    written = 0
    for t in targets:
        for rel, ln, text in t['hits']:
            full = BRAIN / rel
            out = full.read_text(encoding='utf-8')
            # Bounded replacement. An unbounded re.sub matched the stem
            # INSIDE two longer, valid DOIs in Feature-Integration-
            # Theory.md and spliced the completion onto them:
            # 10.1016/0010-0285(80)90005-5 became
            # 10.1016/0010-0285(74)90009-7(80)90005-5. Two good
            # citations destroyed by a repair. See scripts/doi_replace.
            from doi_replace import replace_doi
            new, n = replace_doi(out, t['bad'], t['new_doi'], expected=1)
            if new == out:
                raise SystemExit('no change for %s in %s'
                                 % (t['bad'], rel))
            dst = BACKUP / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(full, dst)
            full.write_text(new, encoding='utf-8')
            written += 1
            print('  wrote %s' % rel)

    prev = {}
    if EVIDENCE.exists():
        try:
            prev = json.loads(EVIDENCE.read_text(encoding='utf-8'))
        except Exception:
            prev = {}
    data = {'verification': 'each DOI confirmed by Crossref status 200 '
                           'plus a title and first-author match against '
                           'the paper the vault cites'}
    data.update(prev)
    data['batch_2'] = prev.get('batch_2')
    data['batches_1_and_3'] = targets
    data['skipped_with_reason'] = skipped
    data['unresolved'] = unresolved
    EVIDENCE.write_text(json.dumps(data, indent=1) + '\n', encoding='utf-8')
    print('  files written: %d' % written)
    return 0


if __name__ == '__main__':
    sys.exit(main())
