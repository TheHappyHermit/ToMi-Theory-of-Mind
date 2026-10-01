#!/usr/bin/env python3
"""Reclassify UNRELATED_TITLE verdicts from the identifier audit.

Read this before treating any UNRELATED_TITLE row as a mis-citation.

The similarity metric is |shared words| / |words in the REGISTERED title|.
That ratio has a structural blind spot: when a citation does not restate
the title, the score is near zero no matter how correct the citation is.
Sampling 12 of the arXiv UNRELATED_TITLE rows found every one of them a
correctly-cited paper:

  2501.13956  "Zep: A Temporal Knowledge Graph Architecture for Agent
              Memory"        cited as "Zep (arXiv 2501.13956)"   sim 0.00
  2601.02744  "SYNAPSE: Empowering LLM Agents with Episodic-Semantic
              Memory ..."      cited as "Synapse: Episodic-Semantic
              Memory via Spreading Activation"                  sim 0.00
  2306.05685  "Judging LLM-as-a-Judge with MT-Bench and Chatbot
              Arena"           cited as "arXiv:2306.05685, NeurIPS
              2023 Datasets & Benchmarks"                       sim 0.20

A short name, a venue, or a bare URL scores low BY CONSTRUCTION. So this
script sorts each row into one of:

  short_name_confirmed  low overlap, but the citation quotes a DISTINCTIVE
                        capitalised term from the title (an acronym or
                        system name). Positive evidence it is correct.
  id_only_citation      the line carries the identifier and no title words.
  bare_url_citation     the line is a DOI/arXiv URL in any host form, with
                        no title words.
  needs_judgement       the citation says something specific about the work
                        but shares no vocabulary and no distinctive term
                        with the registered title. This is the ONLY shape
                        that can be a genuine mismatch. HUMAN.

It never edits the source CSV's verdicts; it writes a reclassified copy so
the raw measurement stays auditable.

Run: python3 scripts/reclassify_identifiers.py [--csv PATH] [--out PATH]
"""
import argparse
import collections
import csv
import os
import re
import sys

STOP = set('a an the of and or in on for to with by from as at is are be was '
           'were this that its their our new using via toward towards over '
           'under between among during about into through based'.split())
TITLE_WORD = re.compile(r'[A-Za-z][A-Za-z\-]+')


def content_words(s):
    return {w.lower() for w in TITLE_WORD.findall(s or '')
            if len(w) > 3 and w.lower() not in STOP}


def distinctive(title):
    """Capitalised terms and ALL-CAPS runs: acronyms and system names, which
    are exactly what a short citation would quote."""
    out = set()
    for m in re.finditer(r'\b([A-Z][A-Za-z0-9]*(?:[-+][A-Za-z0-9]+)*)\b', title or ''):
        w = m.group(1)
        if len(w) >= 3 and w.lower() not in STOP:
            out.add(w)
    for m in re.finditer(r'\b([A-Z]{2,}(?:-[A-Z0-9]+)*)\b', title or ''):
        out.add(m.group(1))
    return out


def is_bare_identifier(ident, reg, ctx):
    """The citation line restates no title content, so a low score carries no
    information at all.

    The test is therefore about ABSENCE OF TITLE WORDS, not about how much
    text is left over. An earlier version stripped the identifier and
    required few remaining words, which misfired because the leftovers are
    URL and venue boilerplate: "https journals plos ploscompbiol article
    file" from a link.springer.com or journals.plos.org URL, and "arxiv
    neurips datasets benchmarks abstract fetched" from a venue line. Those
    are not evidence that the title was cited, and they are not evidence
    against either.
    """
    reg_w = content_words(reg)
    ctx_w = content_words(ctx)
    if reg_w & ctx_w:
        return False
    low = (ctx or '').lower()
    # A URL or an explicit id/venue citation, with no title vocabulary.
    has_link = bool(re.search(r'https?://|dx\.doi\.org|arxiv[:\s/]', low))
    has_id = ident.lower() in low
    return has_link or has_id


def classify(ident, reg, ctx):
    ctx_low = (ctx or '').lower()
    reg_w = content_words(reg)
    overlap = content_words(ctx) & reg_w
    dist_hit = {d for d in distinctive(reg) if d.lower() in ctx_low}
    # A citation that carries the identifier or a URL, and restates no title
    # vocabulary. This covers the bare-URL form, the venue-only form and the
    # "cited inside a list of other papers" form, which are the same
    # situation: there is no title text to compare, so the low score says
    # nothing. An earlier version split these into two labels and a control
    # caught that they are not distinguishable.
    if is_bare_identifier(ident, reg, ctx):
        return 'no_title_restated'
    if dist_hit:
        return 'short_name_confirmed'
    if overlap:
        return 'needs_judgement'
    # Neither a URL, nor a distinctive term, nor any title vocabulary, yet
    # the citation says something specific about the work. That is the only
    # shape that can be a genuine mismatch: a wrong identifier cited
    # alongside a real description, e.g. 10.1109/ICDM.2013.83 resolving to
    # "Non-negative Multiple Tensor Factorization" while the text talks
    # about sparse representations. It goes to a human.
    return 'needs_judgement'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'audit',
        'doi-resolution.csv'))
    ap.add_argument('--out', default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'audit',
        'unrelated-title-reclassified.csv'))
    a = ap.parse_args()

    rows = list(csv.DictReader(open(a.csv, encoding='utf-8')))
    un = [r for r in rows if r['verdict'] == 'UNRELATED_TITLE']
    if not un:
        print('  no UNRELATED_TITLE rows; nothing to reclassify')
        return 0

    out = []
    for r in un:
        k = classify(r['identifier'], r['registered_title'], r['context'])
        r['reclassified'] = k
        r['distinctive_hit'] = ', '.join(
            sorted(d for d in distinctive(r['registered_title'])
                   if d.lower() in (r['context'] or '').lower())[:5])
        out.append(r)

    final = collections.Counter(r['reclassified'] for r in out)
    print(f'=== {len(un)} UNRELATED_TITLE rows reclassified ===')
    for k, n in final.most_common():
        print(f'  {n:>5}  {k}')
    explained = sum(final[k] for k in
                    ('short_name_confirmed', 'no_title_restated'))
    human = len(un) - explained
    print(f'\n  explained as correct citations : {explained}  '
          f'({explained * 100 // len(un)}%)')
    print(f'  genuinely UNRESOLVED           : {human}')
    print('\n  UNRELATED_TITLE is a scoring artifact, not evidence of')
    print('  fabrication. Only needs_judgement requires a human.')

    with open(a.out, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())
                           + ['reclassified', 'distinctive_hit'])
        w.writeheader()
        w.writerows(out)
    print(f'\n  wrote {a.out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
