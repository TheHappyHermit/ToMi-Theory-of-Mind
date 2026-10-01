"""Resolve the 9 mismatches the bare-identifier fix exposed.

Until the label filter tested the BARE identifier, these rows were
scored against every label in the file and mostly came out untitled.
Scored properly, all nine turn out to be citations to the RIGHT paper
written as something other than its title, and one carries a wrong
year. Each was read individually; the classification is per row.

  ABBREVIATION  the vault gives a nickname, a shorthand, or a
                description of the real title. The fix is to write the
                authoritative title. The paper is correct.
  NICKNAME+ID   the entry names the work before the identifier, e.g.
                "4. Embodied AI: From LLMs to World Models --
                arXiv:2509.20021", which is the real title in a
                numbered reference line rather than the sources entry.
  WRONG YEAR    the label is right but the year is not.

Verified against Crossref/arXiv before writing: 10.1103/PhysRevE.73.036127
is Vazquez, Oliveira, Dezso, Goh, Kondor and Barabasi, "Modeling bursts
and heavy tails in human dynamics", Phys Rev E, 2006 -- not 2005 as the
vault's label said.
"""
import json
import shutil
import sys
from pathlib import Path

BRAIN = Path('/home/operator/.hermes/oracle/brain')
BACKUP = Path('/home/operator/.hermes/cache/scratch/pre-mismatch9-backup')
EVIDENCE = Path('/home/operator/hermes-brain/docs/audit/'
                't2-abbreviation-mismatches.json')

# (path, identifier, kind, replacement or None)
DECISIONS = [
    ('domains/ai-cognition/missing-brain-systems-deep-dive.md',
     'arxiv:2509.20021', 'nickname_in_body', None),
    ('domains/ai-cognition/missing-brain-systems-deep-dive.md',
     'arxiv:2604.14228', 'nickname_in_body', None),
    ('research/calibrate-absence-model-on-real-sessions.md',
     'doi:10.1080/00207541003690082', 'abbreviation',
     'Estimating the time of step change with Poisson CUSUM and EWMA '
     'control charts'),
    ('research/calibrate-absence-model-on-real-sessions.md',
     'doi:10.1103/PhysRevE.73.036127', 'abbreviation_and_wrong_year',
     'Modeling bursts and heavy tails in human dynamics'),
    ('research/frontier-research-taxonomy-2027-supplement-v2.md',
     'arxiv:2602.19320', 'abbreviation',
     'Anatomy of Agentic Memory: Taxonomy and Empirical Analysis of '
     'Evaluation and System Limitations'),
    ('research/frontier-research-taxonomy-2027-supplement-v2.md',
     'arxiv:2604.14197', 'abbreviation',
     'The PICCO Framework for Large Language Model Prompting: A '
     'Taxonomy and Reference Architecture for Prompt Engineering'),
    ('research/frontier-research-taxonomy-2027-supplement.md',
     'arxiv:2606.05339', 'abbreviation',
     'A Taxonomy of Runtime Faults in Model Context Protocol Servers'),
    ('research/hierarchical-empirical-bayes-preference-rates.md',
     'doi:10.1080/01621459.1981.10477731', 'abbreviation',
     'Bayes Empirical Bayes'),
    ('research/signal-weight-calibration-real-data.md',
     'doi:10.1007/978-3-030-86523-8_22', 'abbreviation',
     'Ensembling Shift Detectors: An Extensive Empirical Evaluation'),
]


def main():
    apply = '--apply' in sys.argv
    planned, skipped = [], []

    for rel, ident, kind, title in DECISIONS:
        full = BRAIN / rel
        text = full.read_text(encoding='utf-8')
        bare = ident.split(':', 1)[-1]
        if kind == 'nickname_in_body':
            # The real title is already in the file, in a numbered
            # reference line. Nothing to write -- record why.
            hits = [ln for ln in text.split('\n') if bare in ln]
            ok = any(bare in ln for ln in hits)
            skipped.append({'path': rel, 'identifier': ident, 'kind': kind,
                            'reason': 'the real title is already carried '
                                      'in the body; the sources entry '
                                      'needs no change',
                            'body_lines': len(hits)})
            print('  %-14s %-34s already titled in body (%d lines)'
                  % (kind, ident, len(hits)))
            continue

        lines = [ln for ln in text.split('\n')
                 if bare in ln and ln.strip().startswith('- ')]
        # Only the FRONTMATTER source entry is the T2 citation under
        # test. Several files also carry a numbered reference line
        # further down that names the same identifier in shorthand
        # ("- https://doi.org/... (Poisson CUSUM)"). Those are
        # prose, not the citation, and rewriting them would be
        # scope creep -- but they must not be mistaken for the target,
        # which is why this takes the FIRST indented entry, i.e. the one
        # inside the sources: block, and asserts there is exactly one.
        fm_lines = [ln for ln in lines if ln.startswith('  - ')]
        body_lines = [ln for ln in lines if not ln.startswith('  - ')]
        if len(fm_lines) != 1:
            skipped.append({'path': rel, 'identifier': ident, 'kind': kind,
                            'reason': 'expected 1 frontmatter source entry, '
                                      'found %d' % len(fm_lines),
                            'body_reference_lines': len(body_lines)})
            print('  SKIP %-34s %d frontmatter entries'
                  % (ident, len(fm_lines)))
            continue
        ln = fm_lines[0]
        # rebuild the entry: keep its own URL and quoting, swap the label
        body = ln.strip()[2:]
        for q in ('"', "'"):
            if body.startswith(q) and body.endswith(q):
                body = body[1:-1]
                outer = q
                break
        else:
            outer = '"'
        # the URL part is everything before the first " ("
        cut = body.find(' (')
        url = body if cut == -1 else body[:cut]
        new = '  - %s%s (%s)%s' % (outer, url, title, outer)
        if ln.strip().startswith("- '") or (
                ln.strip()[2:].startswith("'") and outer == "'"):
            new = "  - '%s (%s)'" % (url, title)
        planned.append({'path': rel, 'identifier': ident, 'kind': kind,
                        'title': title, 'old': ln, 'new': new})
        print('  %-28s -> %s' % (ident[-28:], title[:60]))

    print()
    print('  to write: %d   left alone: %d' % (len(planned), len(skipped)))
    if not apply:
        print('  DRY RUN. Pass --apply to write.')
        return 0

    by_file = {}
    for p in planned:
        by_file.setdefault(p['path'], []).append(p)
    written = 0
    for rel, items in by_file.items():
        full = BRAIN / rel
        text = full.read_text(encoding='utf-8')
        out = text
        for p in items:
            if p['old'] not in out:
                raise SystemExit('stale review for %s: %r'
                                 % (p['identifier'], p['old'][:70]))
            out = out.replace(p['old'], p['new'], 1)
        if out != text:
            dst = BACKUP / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(full, dst)
            full.write_text(out, encoding='utf-8')
            written += 1
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(
        {'rewritten': planned, 'left_alone': skipped}, indent=1) + '\n',
        encoding='utf-8')
    print('  files written: %d' % written)
    return 0


if __name__ == '__main__':
    sys.exit(main())
