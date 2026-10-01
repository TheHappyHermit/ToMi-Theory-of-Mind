"""Write the authoritative title over an abbreviated vault label.

The journal-cut fix in _has_title_words turned a class of false
"untitled" verdicts into honest "mismatch" ones. Those sources were
never missing a title -- they carried an ABBREVIATION that is not a
title:

    Xie et al., 2013, Science          -> author, year, venue
    SimHash, Charikar 2002             -> method name, author, year
    FEDD, IEEE IJCNN 2025              -> acronym, venue, year
    Embodied AI Survey                 -> a nickname
    Claude Code                        -> a product name

Each identifier's real title was fetched from Crossref or arXiv and is
recorded in the evidence file. This rewrites only the source line whose
current label is listed, and refuses if the line no longer matches what
was reviewed -- so a stale entry cannot silently overwrite a fix.
"""
import json
import re
import shutil
import sys
from pathlib import Path

BRAIN = Path('/home/operator/.hermes/oracle/brain')
TITLES = ('/home/operator/.hermes/cache/scratch/'
          'authoritative_titles.json')
BACKUP = Path('/home/operator/.hermes/cache/scratch/pre-abbrev-backup')
EVIDENCE = Path('/home/operator/hermes-brain/docs/audit/'
                't2-abbreviated-labels.json')

# (relative path, identifier, the exact label reviewed on disk)
REVIEWS = [
    ('Neurovascular/Meningeal-Lymphatics-Glymphatic-Clearance.md',
     'doi:10.1126/science.1241224',
     'Xie et al., 2013, Science'),
    ('Neurovascular/Meningeal-Lymphatics-Glymphatic-Clearance.md',
     'doi:10.1126/scitranslmed.3003748',
     'Iliff et al., 2012, Sci Transl Med'),
    ('research/memory-write-deduplication-amplification-control.md',
     'doi:10.1145/509907.509965',
     'Similarity estimation techniques from rounding algorithms'),
    ('research/drift-strength-adaptive-suppression-policy.md',
     'doi:10.1109/ijcnn64981.2025.11228919',
     'FEDD, IEEE IJCNN 2025'),
    ('research/hierarchical-empirical-bayes-preference-rates.md',
     'doi:10.1080/01621459.1981.10477731',
     'Deely & Lindley 1981, Bayes Empirical Bayes, JASA'),
    ('research/hierarchical-empirical-bayes-preference-rates.md',
     'doi:10.1093/biostatistics/kxl008',
     'Wakefield 2006, Small area estimation for count data with '
     'covariates'),
    ('research/hierarchical-empirical-bayes-preference-rates.md',
     'doi:10.1145/3511808.3557066',
     'Empirical Bayes for Cold-Start Product Search, CIKM 2022'),
    ('research/seasonal-decomposition-burstiness-interaction.md',
     'doi:10.1103/PhysRevE.94.032311',
     'Kim & Jo 2016 — Phys. Rev. E'),
    ('research/calibrate-absence-model-on-real-sessions.md',
     'doi:10.1103/PhysRevE.73.036127',
     'Vazquez et al. 2005, Phys Rev E — non-Poisson scaling of '
     'human dynamics'),
    ('research/calibrate-absence-model-on-real-sessions.md',
     'doi:10.1111/2041-210x.12333',
     'Zero-inflated models for abundance data'),
    ('research/calibrate-absence-model-on-real-sessions.md',
     'doi:10.2307/2532959',
     'Van den Broek 1995 score test for zero-inflation'),
    ('research/cbor-tag-6-dependent-type-formalization.md',
     'arxiv:2505.17335',
     'EverCBOR/EverCDDL, Microsoft Research, 2025'),
    ('domains/ai-cognition/missing-brain-systems-deep-dive.md',
     'arxiv:2509.20021',
     'Embodied AI Survey'),
    ('domains/ai-cognition/missing-brain-systems-deep-dive.md',
     'arxiv:2604.14228',
     'Claude Code'),
    ('research/frontier-research-ontology-llm-reasoning-failures-large-'
     'ontology-model-2026-09-03.md',
     'arxiv:2602.06176',
     'LLM Reasoning Failures Comprehensive Survey, Feb 2026'),
    ('research/signal-weight-calibration-real-data.md',
     'doi:10.1007/978-3-030-86523-8_22',
     'Ensembling Shift Detectors — dataset-adaptive significance '
     'testing'),  # exact disk text checked below
    ('research/band4-phi-regression.md',
     'doi:10.1007/s00521-023-08328-z',
     'A systematic review of integrated information theory: a '
     'perspective from artificial intelligence'),
    ('research/frontier-research-taxonomy-comprehensive-2026-09-11'
     '-supplement-v2.md',
     'arxiv:2501.09136',
     'Agentic RAG Survey (Taxonomy of Agentic RAG)'),
    ('research/frontier-research-taxonomy-september-2026-supplement-v3'
     '.md',
     'arxiv:2505.10468',
     'Redefining Linguistic Categories Through Network Theory'),
    ('research/frontier-research-taxonomy-metadata-categorization-'
     'linguistic-philosophical-2026-09-10.md',
     'arxiv:2505.10468',
     'Redefining Linguistic Categories Through Network Theory'),
]


def main():
    titles = json.load(open(TITLES, encoding='utf-8'))
    apply = '--apply' in sys.argv
    per_file = {}
    skipped, ready = [], []

    for rel, ident, old_label in REVIEWS:
        real = (titles.get(ident) or {}).get('title')
        if not real:
            skipped.append((rel, ident, 'no authoritative title fetched'))
            continue
        full = BRAIN / rel
        text = full.read_text(encoding='utf-8')
        bare = ident.split(':', 1)[-1]
        # the line must carry the identifier AND the reviewed label
        hits = [ln for ln in text.split('\n')
                if bare in ln and ln.strip().startswith('- ')]
        if not hits:
            skipped.append((rel, ident, 'no source line carries it'))
            continue
        target = None
        for ln in hits:
            if old_label in ln:
                target = ln
                break
        if target is None:
            # already repaired, or written differently than reviewed
            if any(real[:40] in ln for ln in hits):
                skipped.append((rel, ident, 'already carries the title'))
            else:
                skipped.append((rel, ident,
                                'reviewed label %r not found' % old_label[:40]))
            continue
        # rewrite: keep the entry's own URL/quoting, swap the label
        new = re.sub(r'\(%s\)' % re.escape(old_label), '(%s)' % real,
                     target, count=1)
        if new == target:
            skipped.append((rel, ident, 'rewrite produced no change'))
            continue
        ready.append({'path': rel, 'identifier': ident,
                      'old_label': old_label, 'title': real,
                      'old_line': target, 'new_line': new})
        per_file.setdefault(rel, []).append(new)

    print('  ready to repair : %d' % len(ready))
    print('  skipped         : %d' % len(skipped))
    for rel, ident, why in skipped:
        print('     SKIP %-34s %s' % (ident, why[:56]))
    for r in ready:
        print('     %-34s %s' % (r['identifier'], r['title'][:56]))

    if not ready:
        return 0
    if not apply:
        print('  DRY RUN. Pass --apply to write.')
        return 0

    written = 0
    for rel, newlines in per_file.items():
        full = BRAIN / rel
        text = full.read_text(encoding='utf-8')
        out = text
        for r in ready:
            if r['path'] != rel:
                continue
            if r['old_line'] not in out:
                raise SystemExit('stale review for %s: %r'
                                 % (r['identifier'], r['old_line'][:60]))
            out = out.replace(r['old_line'], r['new_line'], 1)
        if out != text:
            dst = BACKUP / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(full, dst)
            full.write_text(out, encoding='utf-8')
            written += 1
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(
        json.dumps({'repairs': ready, 'skipped': [
            {'path': p, 'identifier': i, 'reason': w}
            for p, i, w in skipped]}, indent=1) + '\n',
        encoding='utf-8')
    print('  files written: %d' % written)
    return 0


if __name__ == '__main__':
    sys.exit(main())
