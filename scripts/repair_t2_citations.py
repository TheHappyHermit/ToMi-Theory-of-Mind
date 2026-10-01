#!/usr/bin/env python3
"""
Repair the five bad citation identifiers in the Oracle vault, then
re-verify so the verdicts are RE-DERIVED rather than asserted.

The vault is gitignored, so these edits are not reversible by `git
checkout`. Every file is therefore copied to
~/.hermes/cache/scratch/vault-repair-backup/ before it is touched, and
--apply refuses to run without that backup having happened.

WHAT MAKES A REPAIR HONEST
  The five fixes were not derived from "the title looks similar". Each
  rests on an identifier that was fetched and confirmed in this
  session:

  1. arXiv:2605.11610 -> arXiv:2505.11610
     2505.11610 = "Foundation Models for AI-Enabled Biological Design"
     2605.11610 = "Fast and Accurate Prediction of Lattice Thermal
                  Conductivity via Machine Learning Surrogates"
     A clean digit transposition; both IDs are real, unrelated papers.

  2. arXiv:2605.24601 -> arXiv:2505.24601
     2505.24601 = "Taxonomic Networks: A Representation for
                  Neuro-Symbolic Pairing"
     2605.24601 = "Conformity-Based Bayesian Projective Prediction"
     Same cause.

  3. arXiv:2505.10468 -> doi:10.1017/langcog.2025.10
     The label is "Redefining Linguistic Categories Through Network
     Theory", which is a real Language and Cognition article by
     Hernandez Munoz, Tome Cornejo & Lopez (2025) -- confirmed via
     Crossref, with no arXiv version. The arXiv ID in the vault
     resolves to a different paper entirely ("AI Agents vs. Agentic
     AI").

     NOT A BLANKET SWAP: this file uses 2505.10468 for BOTH works.
     Line 251 already pairs it with its real title ("AI Agents vs.
     Agentic AI") and is therefore CORRECT and left alone. Only the
     lines that attach it to the linguistic-categories work are
     changed. A blind find-and-replace would have destroyed the one
     correct usage.

  4. arXiv:2601.12560 -> the self-published Cogitantia Synthetica
     The section body is genuinely about Cogitantia Synthetica: it
     lays out Domain -> Kingdom -> ... -> Species and names
     Instrumentidae / Orchestridae / Meta-agentia / Hyperagentia. That
     is not the Agentic AI survey, so the identifier was wrong, not
     the prose. The work is self-published with no arXiv record, so
     the ID is replaced by an explicit non-arXiv attribution rather
     than by a different arXiv ID that would be a new falsehood.

  5. arXiv:2602.06052 -> split, because the label splices two papers
     "Memory in the Age of AI Agents" + "47-author"  = 2512.13564
        (confirmed: 47 authors, title matches exactly)
     "3D-8Q taxonomy" (object / form / time x 8 quadrants)
        = 2504.15965
        (confirmed verbatim: "a categorization method based on three
         dimensions (object, form, and time) and eight quadrants")
     The cited 2602.06052 is a third survey ("A Survey of Agent
     Memory in the Second Half", 60 authors, TMLR). One ID cannot
     make a two-paper label true, so the citation is split to cite
     both sources for what each actually contributes.

NO VERDICT IS EDITED BY THIS SCRIPT
  It touches vault text and then re-runs the real verifier. The
  adjudication table is never written here -- a repair that hand-set
  its own verdict would be unfalsifiable.
"""
import argparse
import json
import os
import re
import shutil
import sys

BRAIN = '/home/operator/.hermes/oracle/brain/'
BACKUP = ('/home/operator/.hermes/cache/scratch/'
          'vault-repair-backup/')

# (relative path, [(old, new, note), ...])
# Each replacement is asserted to occur exactly the stated number of
# times, so a file that has since changed cannot be silently mangled.
REPAIRS = [
    ('research/frontier-research-taxonomy-comprehensive-2026-09-11-'
     'supplement-v2.md', [
         ('arXiv:2605.11610', 'arXiv:2505.11610', 1,
          'year transposition; 2505.11610 is the bio-design paper'),
     ]),
    ('research/frontier-research-taxonomy-september-2026-supplement-v2.md', [
         ('arXiv:2605.24601', 'arXiv:2505.24601', 1,
          'year transposition; 2505.24601 is Taxonomic Networks'),
     ]),
    # Case 3. Two files, and within each ONLY the linguistic-category
    # uses are wrong.
    ('research/frontier-research-taxonomy-comprehensive-2026-09-11.md', [
         ('"arXiv:2505.10468 — Redefining Linguistic Categories Through '
          'Network Theory"',
          '"doi:10.1017/langcog.2025.10 — Redefining Linguistic '
          'Categories Through Network Theory"', 1,
          'journal article, not an arXiv paper; real title confirmed '
          'via Crossref'),
         ('**Linguistic categories as network structures '
          '(arXiv:2505.10468)**',
          '**Linguistic categories as network structures '
          '(doi:10.1017/langcog.2025.10)**', 1,
          'same article, body citation'),
         # NOT replaced: line 251 pairs 2505.10468 with its real
         # title "AI Agents vs. Agentic AI" and is correct.
     ]),
    ('research/frontier-research-taxonomy-comprehensive-2026-09-10-v2.md', [
         ('"Redefining Linguistic Categories Through Network Theory '
          '(arXiv:2505.10468)"',
          '"Redefining Linguistic Categories Through Network Theory '
          '(doi:10.1017/langcog.2025.10)"', 1,
          'journal article, reference-list entry'),
     ]),
    # Case 4. Cogitantia Synthetica has no arXiv record.
    ('research/frontier-research-taxonomy-2027-supplement-v2.md', [
         ('"arXiv:2601.12560 — Cogitantia Synthetica: Taxonomic '
          'Classification of Transformer-Descended AI Systems"',
          '"Cogitantia Synthetica: Taxonomic Classification of '
          'Transformer-Descended AI Systems (self-published; Institute '
          'for Synthetic Intelligence Taxonomy, rev. 10.75, Aug 2026; '
          'synthetictaxonomy.com/paper/ai_taxonomy.pdf — no arXiv '
          'version)"', 1,
          'arXiv ID belonged to a different paper; this work is not on '
          'arXiv'),
         ('### 7.1 Cogitantia Synthetica: Taxonomic Classification of '
          'Transformer-Descended AI (arXiv:2601.12560)',
          '### 7.1 Cogitantia Synthetica: Taxonomic Classification of '
          'Transformer-Descended AI (self-published, no arXiv version)',
          1, 'section heading carried the same wrong ID'),
     ]),
    # Case 5. The label splices two surveys; split the citation.
    ('research/frontier-research-taxonomy-comprehensive-2026-09-11.md', [
         ('"arXiv:2602.06052 — Memory in the Age of AI Agents '
          '(47-author survey, three-dimensional taxonomy)"',
          '"arXiv:2512.13564 — Memory in the Age of AI Agents '
          '(47-author survey); 3D-8Q taxonomy: arXiv:2504.15965"', 1,
          'title+author count belong to 2512.13564; the three-axis '
          'eight-quadrant taxonomy is 2504.15965, per its abstract'),
     ]),
    ('research/frontier-research-taxonomy-2027-supplement.md', [
         ('"arXiv:2602.06052 — Memory in the Age of AI Agents: '
          '47-author survey (3D-8Q taxonomy)"',
          '"arXiv:2512.13564 — Memory in the Age of AI Agents: '
          '47-author survey; 3D-8Q taxonomy: arXiv:2504.15965"', 1,
          'same splice, reference-list entry'),
         ('### 11.3 47-Author Survey: 3D-8Q Taxonomy (arXiv:2602.06052)',
          '### 11.3 47-Author Survey: 3D-8Q Taxonomy (arXiv:2512.13564; '
          'taxonomy from arXiv:2504.15965)', 1,
          'section heading carried the same wrong ID'),
     ]),
]


def backup_all():
    os.makedirs(BACKUP, exist_ok=True)
    for rel, _edits in REPAIRS:
        dst = os.path.join(BACKUP, rel.replace('/', '__'))
        if not os.path.exists(dst):
            shutil.copy2(BRAIN + rel, dst)
            print('  backed up %s' % os.path.basename(rel)[:58])
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    # Always back up first, even on a dry run, so --apply can never be
    # the operation that discovers the files are unrecoverable.
    backup_all()

    total, problems = 0, []
    for rel, edits in REPAIRS:
        path = BRAIN + rel
        try:
            text = open(path, encoding='utf-8').read()
        except OSError as exc:
            problems.append('%s: %s' % (rel, exc))
            continue
        orig = text
        for old, new, want, note in edits:
            found = text.count(old)
            if found != want:
                problems.append(
                    '%s: expected %d occurrence(s) of %r, found %d'
                    % (os.path.basename(rel)[:44], want, old[:58], found))
                continue
            text = text.replace(old, new)
            total += 1
            print('  %-46s %s' % (os.path.basename(rel)[:46],
                                 note[:64]))
        if args.apply and text != orig:
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(text)

    print()
    print('  edits asserted : %d' % total)
    print('  problems       : %d' % len(problems))
    for p in problems:
        print('      %s' % p)
    if problems:
        return 1
    if not args.apply:
        print('  DRY RUN. Pass --apply to write.')
    else:
        print('  applied %d edits to the vault.' % total)
    return 0


if __name__ == '__main__':
    sys.exit(main())
