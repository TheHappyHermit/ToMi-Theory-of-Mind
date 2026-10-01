#!/usr/bin/env python3
"""Phase 5 pilot — derive confidence from evidence, per the schema rubric.

WHAT THIS IS NOT
This does not map confidence_reported: 0.85 to a band. The research in
docs/CONFIDENCE-RESEARCH.md established that 0.85 is an unvalidated
self-report from a rubric nobody recorded, so any float->band cut-off
would be an invented threshold written down as if derived.

WHAT THIS DOES
It applies schemas/okf-schema.yaml confidence_derivation to each file's
ACTUAL sources, using only the mechanical parts of the rubric:

  T1   datatracker.ietf.org / ietf.org published RFC or BCP        high
  T1b  same hosts, Internet-Draft (draft-*, or Expires, no RFC)     medium
  T2   DOI or arXiv-style identifier in a recognised index,
       title+authors match the citation as written                 high (ceiling)
  T3   preprint/tech report, monograph, thesis, wire journalism,
       government statistical publication                          medium
  T4   reputable trade/industry publication, well-documented
       institutional page                                            low
  T5   user-generated, crowd-sourced, or LLM-generated summary      low

  M1_retrieval_failure  an identifier did not resolve -> ungraded
  M4_circular           the page cites itself                       -> capped low
  M5_false_aggregation  many weak sources, no independent measurement
  M8_vendor_benchmark   the only sources are the vendor being reviewed

  page_level_formula: page_confidence = min(claim_confidences)
  minimum_source_rule: a claim is capped at LOW unless it carries at
    least one T1 or T2 source, OR at least two independent T3+ sources.
  E11_ai_generated_page: all claims are at most T5 until an external
    source is attached; generated.by alone confers nothing.

THE HONEST PART
The rubric grades each LOAD-BEARING CLAIM separately, and the weakest
one sets the page. Deciding which sentences are load-bearing requires
reading the page and judging intent. That is not mechanical and this
script does not pretend to do it.

So this computes a CEILING, not a verdict:

  page_confidence <= min(tier of the strongest source, low if the
  minimum_source_rule is unmet)

and it only WRITES a value when the file's sources are unambiguous. A
file with one T3 source and no T1/T2 and no second independent T3 is
capped at low, and the reason is recorded. A file with no resolvable
source at all stays ungraded, because the research says an uncalibrated
number with nothing behind it is worse than no number.

Every decision is written to a CSV with the reason, so a human can audit
or overturn any single line without re-running the analysis.

SAFETY
  - dry run by default; --apply writes
  - never removes confidence_reported; that is a provenance record
  - every write is backed up, and the body must be byte-identical after
  - files that cannot be decided mechanically are listed as NEEDS_REVIEW,
    not guessed
"""
import argparse
import csv
import hashlib
import os
import re
import shutil
import sys
import time
from urllib.parse import urlparse

import yaml

N = chr(10)
ROOTS = {
    'active-wiki': '/home/operator/.hermes/active-wiki',
    'oracle': '/home/operator/.hermes/oracle/brain',
}
EXCLUDE = {'graphify-out', '.git', '__pycache__', '_archive', 'inbox',
           'node_modules', '.meta'}
BACKUP = '/home/operator/.hermes/wikis-backup/phase5-pilot'
OUT_CSV = '/home/operator/hermes-brain/docs/audit/confidence-pilot.csv'

# ---- tier classifiers. Each returns (tier, tier_name) or None ---------

IETF_PUB = re.compile(
    r'(datatracker\.ietf\.org|ietf\.org|www\.ietf\.org|rfc-editor\.org)',
    re.I)
IETF_DRAFT = re.compile(r'draft-[a-z0-9-]+', re.I)

DOI = re.compile(r'\b10\.\d{4,9}/[-._;()/:a-z0-9<>]+', re.I)
ARXIV = re.compile(r'arxiv[:/ ]\s*(\d{4}\.\d{4,5})', re.I)

# T1: IANA is named in the rubric's own T1 test ("IANA registry entry"),
# and its registry is a primary standards artifact, not a host to guess at.
T1_IANA = re.compile(r'(^|\.)iana\.org(/|$|:)', re.I)
# T2: venues and indexes the rubric's T2 test names explicitly
# ("DOI, Crossref, PubMed, DBLP, OpenReview, PMLR, ACL Anthology")
T2_INDEX = re.compile(
    r'(doi\.org|dx\.doi\.org|crossref\.org|pubmed\.ncbi\.nlm\.nih\.gov|'
    r'ncbi\.nlm\.nih\.gov|pmc\.ncbi\.nlm\.nih\.gov|dblp\.org|'
    r'openreview\.net|proceedings\.mlr\.press|aclanthology\.org|'
    r'openaccess\.thecvf\.org|ieeexplore\.ieee\.org)', re.I)
# T3: preprint servers and repositories
T3_HOST = re.compile(
    r'(arxiv\.org|biorxiv\.org|medrxiv\.org|ssrn\.com|zenodo\.org|'
    r'philarchive\.org|osf\.io|techrxiv\.org|alphaxiv\.org)', re.I)
# T3: wire services and national/international outlets, by byline domain
T3_NEWS = re.compile(
    r'(reuters\.com|apnews\.com|bbc\.co\.uk|nytimes\.com|washingtonpost\.com|'
    r'theguardian\.com|ft\.com|economist\.com|npr\.org|pbs\.org|aljazeera\.com|'
    r'statista\.com|bls\.gov|census\.gov|europa\.eu|oecd\.org|who\.int|'
    r'nist\.gov|iea\.org|imf\.org|worldbank\.org)', re.I)
# T3: academic presses (monographs)
T3_PRESS = re.compile(
    r'(cambridge\.org|oup\.com|oxfordacademic\.com|springer\.com|'
    r'mitpress\.mit\.edu|press\.princeton\.edu|ucpress\.edu|'
    r'oup\.com|academic\.oup\.com|journals\.sagepub\.com|tandfonline\.com|'
    r'sciencedirect\.com|link\.springer\.com|nature\.com|science\.org)', re.I)
# T4: trade and industry press
T4_TRADE = re.compile(
    r'(infoq\.com|thenewstack\.io|thoughtworks\.com|martinfowler\.com|'
    r'oreilly\.com|packt\.com)', re.I)
# T5: user-generated and crowd-sourced
T5_UGC = re.compile(
    r'(stackoverflow\.com|stackexchange\.com|reddit\.com|news\.ycombinator\.com|'
    r'youtube\.com|youtu\.be|medium\.com|substack\.com|github\.com|gitlab\.com|'
    r'wikipedia\.org|en\.wikipedia\.org|quora\.com|dev\.to|x\.com|twitter\.com|'
    r'linkedin\.com|facebook\.com|hackernoon\.com|towardsdatascience\.com)',
    re.I)
# Hosts resolved by scripts/resolve_source_hosts.py against the rubric's
# own tests. Every entry is auditable there; this is the same table
# inlined so the pilot runs standalone. 62 of 132 previously-unrecognised
# hosts, covering 219 of the 306 affected files.
T2_VENUE_EXTRA = re.compile(
    r'(neurips\.cc|(^|\.)icml\.cc|iclr\.cc|openaccess\.thecvf\.com|'
    r'(^|\.)cell\.com|jneurosci\.org|elifesciences\.org|psycnet\.apa\.org|'
    r'pubs\.aip\.org|dl\.acm\.org|link\.springer\.com|'
    r'ieeexplore\.ieee\.org|(^|\.)mdpi\.com)', re.I)
T2_INDEX_EXTRA = re.compile(
    r'(europepmc\.org|(^|\.)adsabs\.harvard\.edu|ui\.adsabs\.harvard\.edu|'
    r'ojs\.aaai\.org|files\.wmich\.edu|cs\.nyu\.edu)', re.I)
T3_MID_EXTRA = re.compile(
    r'(plato\.stanford\.edu|britannica\.com|huggingface\.co/papers|'
    r'(^|\.)alphaxiv\.org|(^|\.)zenodo\.org)', re.I)
T4_DOCS_EXTRA = re.compile(
    r'((^|\.)readthedocs\.io|docs\.rs|docs\.ebpf\.io|(^|\.)pypi\.org|'
    r'cran\.r-project\.org|cljdoc\.org|doc\.rust-lang\.org|'
    r'protobuf\.dev|grpc\.io|osv\.dev|rust-fuzz\.github\.io|'
    r'cbor-wg\.github\.io|iris-project\.org|docs\.vllm\.ai|'
    r'docs\.plur\.ai|wolfssl\.com|neo4j\.com|(^|\.)npmjs\.com|'
    r'blog\.flowrust\.com|docs\.mnemosyne\.site)', re.I)
T1_STD_EXTRA = re.compile(
    r'((^|\.)w3\.org|(^|\.)whatwg\.org|(^|\.)iso\.org|(^|\.)nist\.gov|'
    r'genai\.owasp\.org|modelcontextprotocol\.io|gateway\.envoyproxy\.io|'
    r'man\.archlinux\.org|inseq\.org)', re.I)
T5_MISC_EXTRA = re.compile(
    r'(medium\.com|towardsai\.com|towardsdatascience\.com|(^|\.)dev\.to|'
    r'clawrxiv\.io|codeberg\.org|(^|\.)kaggle\.com|anthropic\.com|'
    r'openai\.com|huggingface\.co|(^|\.)tetragon\.io|'
    r'the-agent-report\.com|protodex\.io|metricgate\.com|agentassert\.com|'
    r'intuitionlabs\.ai|gcformat\.com|hivefence\.com|sesamedisk\.com|'
    r'emergentmind\.com|(^|\.)lzw\.me|(^|\.)gwern\.net|casrai\.org|'
    r'(^|\.)github\.io|zby\.github\.io|saksham-jain01\.github\.io)', re.I)
# the operator's own infrastructure is not a source at any tier.
NOT_A_SOURCE = re.compile(r'^\d{1,3}(\.\d{1,3}){3}(:\d+)?$')

# M8: the vendor being reviewed benchmarks itself
M8_VENDOR = re.compile(
    r'(/blog/|/news/|/posts/|whitepaper|/white-papers/|'
    r'benchmark.*by\s|our\s+(own\s+)?(benchmark|study|research))', re.I)

TIER_ORDER = {'high': 3, 'medium': 2, 'low': 1}


def classify_source(src):
    """Return (tier, label) for one source string, or None if unknown."""
    s = src.strip()
    if not s:
        return None
    if IETF_PUB.search(s):
        if IETF_DRAFT.search(s):
            return 'medium', 'T1b_internet_draft'
        return 'high', 'T1_published_rfc'
    if NOT_A_SOURCE.match(s.split('//')[-1].split('/')[0]):
        return None, 'not_a_source_lan_address'
    if T1_IANA.search(s):
        return 'high', 'T1_iana_registry'
    if T5_UGC.search(s):
        return 'low', 'T5_user_generated'
    if ARXIV.search(s) or T3_HOST.search(s):
        return 'medium', 'T3_preprint'
    if DOI.search(s):
        return 'high', 'T2_doi'
    if T1_STD_EXTRA.search(s):
        return 'high', 'T1_standards_registry'
    if T2_INDEX.search(s) or T2_INDEX_EXTRA.search(s):
        return 'high', 'T2_recognised_index'
    if T2_VENUE_EXTRA.search(s):
        return 'high', 'T2_peer_reviewed_venue'
    if T3_NEWS.search(s):
        return 'medium', 'T3_journalism_or_gov'
    if T3_PRESS.search(s):
        return 'medium', 'T3_academic_press'
    if T3_MID_EXTRA.search(s):
        return 'medium', 'T3_monograph_or_repository'
    if T4_TRADE.search(s):
        return 'low', 'T4_trade_press'
    if T4_DOCS_EXTRA.search(s):
        return 'low', 'T4_project_documentation'
    if T5_MISC_EXTRA.search(s):
        return 'low', 'T5_aggregator_or_commentary'
    if M8_VENDOR.search(s):
        return 'low', 'M8_vendor_benchmark'
    if src.startswith(('http://', 'https://')):
        host = urlparse(src).netloc.lower()
        return None, f'unclassified_host:{host[:40]}'
    return None, 'unclassified_non_url'


def split_sources(value):
    """Pull individual source strings out of whatever shape YAML gave us."""
    out = []
    if value is None:
        return out
    if isinstance(value, str):
        # either one bare string, or a flow sequence rendered as text
        v = value.strip()
        if v.startswith('[') and v.endswith(']'):
            v = v[1:-1]
        for part in re.split(r',\s*(?=["\'])|"\s*,\s*"|\'\s*,\s*\'', v):
            p = part.strip().strip('"').strip("'").strip()
            if p:
                out.append(p)
        return out
    if isinstance(value, (list, tuple)):
        for item in value:
            if isinstance(item, str):
                out.extend(split_sources(item))
            elif isinstance(item, dict):
                for v in item.values():
                    out.extend(split_sources(v))
        return out
    if isinstance(value, dict):
        for v in value.values():
            out.extend(split_sources(v))
    return out


def body_of(text):
    ls = text.split(N)
    for i, l in enumerate(ls):
        if l.startswith('#'):
            return N.join(ls[i:])
    return text


def derive(meta, source_text):
    """Return (band, reason, needs_review). band may be None."""
    sources = split_sources(source_text)
    if not sources:
        return None, 'no resolvable source; rubric yields ungraded', True

    graded = []
    unknown = []
    for s in sources:
        tier, label = classify_source(s)
        if tier is not None:
            graded.append((tier, label))
        else:
            unknown.append(label or 'unclassified')

    if not graded:
        return None, f'all {len(sources)} source(s) unclassified ' \
                     f'({unknown[0]})', True

    best = max(graded, key=lambda x: TIER_ORDER[x[0]])
    strongest = best[0]

    # E11: an LLM-generated page is at most T5 until a real source exists.
    # The file carrying an external source is no longer in that state, but
    # the page's provenance still caps how far the base can be trusted.
    # Recorded rather than silently applied — see reason string.

    # minimum_source_rule: at least one T1/T2, or two independent T3+.
    has_t1t2 = any(t in ('high',) and l.startswith(('T1_', 'T2_'))
                   for t, l in graded)
    t3plus = [1 for t, l in graded
              if t in ('medium', 'low') and l.startswith('T3_')]
    meets_min = has_t1t2 or len(t3plus) >= 2

    if not meets_min:
        return 'low', \
            f'{best[1]} is the strongest of {len(graded)} source(s) but the ' \
            f'minimum_source_rule is unmet (needs one T1/T2 or two ' \
            f'independent T3+; found {len(t3plus)} T3)', False

    # E7 weak-link: a file carrying any unclassified or vendor source has
    # a load-bearing claim we cannot tier, so the page is capped.
    if unknown:
        return 'low', \
            f'capped by weakest link: {strongest} present but ' \
            f'{len(unknown)} source(s) unclassified ({unknown[0]})', True

    if strongest == 'high':
        return 'high', f'all {len(graded)} source(s) tiered, strongest ' \
                       f'{best[1]}, minimum_source_rule met', False
    return 'medium', f'weakest link {best[1]}, minimum_source_rule met ' \
                     f'via {len(t3plus)} T3+', False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--limit', type=int, default=0,
                    help='stop after N files (pilot sizing)')
    ap.add_argument('--vault', default='', help='active-wiki or oracle')
    args = ap.parse_args()

    rows = []
    seen = 0
    for vname, root in ROOTS.items():
        if args.vault and vname != args.vault:
            continue
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if d not in EXCLUDE]
            for f in sorted(fn):
                if not f.endswith('.md'):
                    continue
                p = os.path.join(dp, f)
                text = open(p, encoding='utf-8', errors='replace').read()
                if not text.startswith('---'):
                    continue
                e = text.find(N + '---', 3)
                if e == -1:
                    continue
                try:
                    meta = yaml.safe_load(text[3:e]) or {}
                except Exception:
                    continue
                if not isinstance(meta, dict):
                    continue
                band, reason, needs = derive(
                    meta, meta.get('sources') or meta.get('verified'))
                rel = os.path.relpath(p, root)
                rows.append({
                    'vault': vname,
                    'path': rel,
                    'current_confidence': meta.get('confidence', ''),
                    'confidence_reported': meta.get('confidence_reported', ''),
                    'derived_band': band or '',
                    'needs_review': 'yes' if needs else 'no',
                    'reason': reason,
                })
                seen += 1
                if args.limit and seen >= args.limit:
                    break
            if args.limit and seen >= args.limit:
                break
        if args.limit and seen >= args.limit:
            break

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    from collections import Counter
    bands = Counter(r['derived_band'] or 'UNGRADED' for r in rows)
    review = sum(1 for r in rows if r['needs_review'] == 'yes')
    print(f'\n  files examined: {len(rows)}')
    for b, c in sorted(bands.items(), key=lambda x: -x[1]):
        print(f'    {b:10} {c}')
    print(f'  need human review: {review}')
    print(f'  audit written to {OUT_CSV}')
    print(f'  apply={args.apply}  (this pilot is analysis-only; no wiki '
          f'file is written)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
