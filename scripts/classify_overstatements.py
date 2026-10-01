#!/usr/bin/env python3
"""Classify the 1,229 "overstated" files by what they ACTUALLY are.

THE FINDING THAT WAS WRONG
The Phase 5 pilot reported 1,229 files claiming confidence: high or
medium with no resolvable source, and I called them "overstated". That
framing was wrong, and the operator caught it: "we shouldn't do anything on all
of them because downgrading all of them would be wrong because not all
of them should be downgraded."

He is right, and the reason is visible in the data. The pilot collapsed
1,229 files into one bucket by asking a single question -- does it cite
an external URL? -- and that question has four different correct
answers depending on what the file is.

WHAT THE FILES ACTUALLY ARE
  type=index          231 files, MEDIAN 30 WORDS. These are tables of
                     contents. The schema's own
                     load_bearing_definition says "navigational
                     metadata are not load-bearing", and the
                     page_level_formula returns "ungraded if no
                     load-bearing claim". A 30-word index therefore has
                     NO load-bearing claims, and the correct output is
                     not a downgrade at all -- it is that confidence is
                     not applicable to this kind of page. Their
                     existing `high` is meaningless rather than false,
                     which is a different problem with a different fix.

  type=decision        35 files, median 263 words. A decision record
                     cites the DECISION, not literature. "The owner
                     ruled X on date Y" is established by the record
                     itself and by session provenance. The rubric has
                     no tier for this because the rubric was written
                     for claims about the world, not records of what
                     was decided. Downgrading these would be wrong.

  type=reference      674 files, median 1,096 words, p90 6,126, max
                     15,327. Mixed. Some are descriptive notes about
                     the operator's own systems, where the authority is the
                     system itself. Some make claims about the world
                     and genuinely need sources. These need individual
                     reading, not a bulk rule.

  type=research-report 213 files, median 3,710 words. These are the
                     ones where E11 bites hardest: long LLM-generated
                     synthesis with no attached source. This is where
                     the "unearned confidence" charge is real.

  Other types (person, system, entity, idea, log, lesson, temporal,
  project) total 76 files and need their own treatment.

THE POINT OF THIS SCRIPT
It does not assign a band. It assigns a WORK CLASS, so that the work
can be batched by the kind of judgement each class needs instead of
being applied uniformly to 1,229 files that need at least four
different treatments.

NOTHING IS WRITTEN. This classifies and reports.
"""
import argparse
import csv
import os
import re
import sys
from collections import Counter

import yaml

N = chr(10)
ROOTS = {
    'active-wiki': '/home/operator/.hermes/active-wiki',
    'oracle': '/home/operator/.hermes/oracle/brain',
}
PILOT_CSV = '/home/operator/hermes-brain/docs/audit/confidence-pilot.csv'
OUT_CSV = '/home/operator/hermes-brain/docs/audit/overstatement-classes.csv'

# A page with no load-bearing claim is not a low-confidence page. It is
# a page to which confidence does not apply. The schema says so at
# load_bearing_definition, and the median index page is 30 words, which
# is what a table of contents looks like.
NAV_MAX_WORDS = 400

# "Is this a table of contents?" cannot be answered by word count.
# Measured across the 231 files typed index: only 7 are link-dominant by
# markdown link alone, but 121 are navigational once [[wikilinks]] are
# counted, and 110 are genuine prose. The first pass of this script used
# length and misfiled RESEARCH-INDEX.md -- a 1,336-word table of entries
# built from wikilinks -- into the synthesis class. So the test is now
# link share, with wikilinks included, and word count is only a
# tiebreaker for very short bodies.
WIKILINK = re.compile(r'\[\[[^\]]*\]\]')
MDLINK = re.compile(r'\[[^\]]*\]\(([^)]+)\)')
TOKENS_PER_LINK = 4  # measured: '[[a-very-long-slug-name]] Title' ~ 4 tokens


def link_share(body):
    """Percentage of body tokens that are part of a link. >=45 navigational,
    20-44 mixed, <20 prose."""
    n = len(WIKILINK.findall(body)) + len(MDLINK.findall(body))
    toks = max(1, len(body.split()))
    return min(100, 100 * (n * TOKENS_PER_LINK) // toks)


def work_class(meta, body_words, src_kinds, share=0):
    """Return (class, rationale). Deliberately coarse -- it groups files
    by the KIND OF WORK they need, not by the answer."""
    ty = meta.get('type', '?')

    # 1. Navigational. The body IS a table of contents, so it makes no
    #    load-bearing claim and confidence does not apply to it. This is
    #    judged on link share, not length: 1,336 words of table rows is
    #    still a table of contents.
    if share >= 45:
        return ('n_navigational_not_applicable',
                f'{ty}, {body_words} words, {share}% links: the body IS '
                f'the index, so it asserts nothing load-bearing and '
                f'confidence does not apply. NOT a downgrade case.')
    if body_words <= NAV_MAX_WORDS and ty == 'index' and share >= 20:
        return ('n_navigational_not_applicable',
                f'{ty}, {body_words} words, {share}% links: short and '
                f'navigational. confidence does not apply. NOT a '
                f'downgrade case.')
    if body_words <= 120 and ty in ('reference', 'system', 'entity',
                                    'project'):
        return ('n_navigational_not_applicable',
                f'{ty}, {body_words} words: too short to carry a '
                f'load-bearing claim. confidence does not apply. NOT a '
                f'downgrade case.')

    # 2. A record of what was decided or observed, not a claim about the
    #    world. Session provenance is the authority.
    if ty in ('decision', 'lesson'):
        return ('c_record_of_decision',
                f'{ty}: the authority is the decision record itself and '
                f'session provenance {sorted(src_kinds)}. The rubric has '
                f'no tier for this because it grades claims about the '
                f'world.')

    # 3. Descriptive material about the operator's own systems. The system is the
    #    source; it is not in a public URL. (The first version of this
    #    clause tested `'session' in src_kinds | set(str(s) for s in
    #    src_kinds)`, which built a union of a set of strings with a set
    #    of one-character strings and so only ever matched by accident.
    #    It fired on 1 of 21 system/project files. Now it is a plain
    #    membership test, which is what it was always meant to be.)
    if ty in ('system', 'project') and (
            'session' in src_kinds or 'first_party_artifact' in src_kinds):
        return ('b_first_party_description',
                f'{ty} with first-party provenance {sorted(src_kinds)}: '
                f'describes our own deployment, read from the config and '
                f'the running system. The system is the source, not a '
                f'public URL.')

    # 4. Long LLM-generated synthesis with no external source. This is
    #    where E11 bites and where the charge is real.
    #    An index is NEVER a synthesis, however long: its length is
    #    table rows, not argument. RESEARCH-INDEX.md is 1,336 words of
    #    `| [[slug]] Title | done |` and asserts nothing at all.
    if (ty != 'index' and body_words >= 1000
            and not (src_kinds - {'NONE'})):
        return ('a_unsourced_synthesis',
                f'{ty}, {body_words} words, no source of any kind: E11 '
                f'caps an unattributed AI-written page at T5. This is '
                f'the genuine overstatement class.')

    # 5. Everything else needs individual reading.
    return ('d_needs_individual_reading',
            f'{ty}, {body_words} words, sources={sorted(src_kinds)}')


def src_kinds_of(meta):
    """Classify the source list. The important discovery here is that
    first-party provenance is NOT a session id.

    Real examples found in the corpus:
        ['local config.yaml', 'honcho.json', 'cron/jobs.json',
         'git describe', 'pyproject.toml', 'docker inspect']

    Those are the actual state of the operator's own deployment, and they are
    just as authoritative as a session record. The first version of this
    function only recognised 'session:' and 'http', so a system page
    documented straight from config.yaml and docker inspect came out
    looking unsourced -- which is exactly backwards.

    'other' therefore means a real first-party artifact, not a
    mystery. The previous version lumped a bare path and a prose string
    together and could not tell them apart."""
    srcs = meta.get('sources') or []
    if isinstance(srcs, str):
        srcs = [srcs]
    kinds = set()
    for s in srcs:
        s = str(s).strip()
        if not s:
            continue
        low = s.lower()
        if low.startswith('session:'):
            kinds.add('session')
        elif low.startswith(('http://', 'https://', 'doi:',
                             'arxiv:', '10.')):
            kinds.add('external_url')
        elif low.startswith('nas://'):
            kinds.add('nas_path')
        elif low.endswith(('.yaml', '.yml', '.json', '.toml', '.py',
                           '.sql', '.sh')) or '/' in s or \
                low.startswith(('local ', 'git ', 'docker ')):
            kinds.add('first_party_artifact')
        else:
            kinds.add('other')
    return kinds or {'NONE'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=OUT_CSV)
    args = ap.parse_args()

    rows = list(csv.DictReader(open(PILOT_CSV, encoding='utf-8')))
    flagged = [r for r in rows if not r['derived_band']
               and r['current_confidence'] in ('high', 'medium')]

    out = []
    for r in flagged:
        p = ROOTS[r['vault']] + '/' + r['path']
        try:
            t = open(p, encoding='utf-8', errors='replace').read()
            e = t.find(N + '---', 3)
            meta = yaml.safe_load(t[3:e]) or {}
            body_words = len(t[e + 4:].split())
        except Exception as ex:
            out.append({**r, 'work_class': 'e_unreadable',
                        'rationale': str(ex)[:60], 'body_words': 0,
                        'link_share': 0, 'file_type': '?'})
            continue
        kinds = src_kinds_of(meta)
        share = link_share(t[e + 4:])
        cls, why = work_class(meta, body_words, kinds, share)
        out.append({**r, 'work_class': cls, 'rationale': why,
                    'body_words': body_words, 'link_share': share,
                    'file_type': meta.get('type', '?')})

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)

    c = Counter(r['work_class'] for r in out)
    print(f'\n  {len(out)} files classified into {len(c)} work classes\n')
    for k, v in sorted(c.items()):
        print(f'    {v:>5}  {k}')
    print()
    for k in sorted(c):
        ex = next(r for r in out if r['work_class'] == k)
        print(f'  {k}')
        print(f'    e.g. {ex["path"][:54]}  ({ex["file_type"]}, '
              f'{ex["body_words"]}w)')
        print(f'    {ex["rationale"][:96]}')
        print()
    print(f'  audit written to {args.out}')
    print('  NOTHING WAS WRITTEN TO ANY WIKI FILE.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
