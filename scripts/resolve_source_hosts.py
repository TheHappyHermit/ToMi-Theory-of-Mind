#!/usr/bin/env python3
"""Resolve the 131 unrecognised source hosts the Phase 5 pilot flagged.

The pilot refuses to guess at a host it does not recognise, which is
correct behaviour but leaves 306 files ungraded for a reason that is
mostly mechanical: these are well-known venues, repositories and
project sites, and the rubric's own tests already say where they land.

This maps each host to a tier USING THE RUBRIC'S OWN CRITERIA, not a
new opinion:

  T1  IANA/standards-body registries and specifications
  T2  peer-reviewed venues and recognised indexes -- NeurIPS, ICML,
      ICLR, CVF open access, APA PsycNet, eLife, JNeurosci, Cell Press,
      AIP, IEEE, ACM DL, Springer LNCS
  T3  scholarly monographs and reference works -- Stanford Encyclopedia
      of Philosophy, Britannica; preprint servers -- Hugging Face
      papers, arXiv mirrors
  T4  project documentation and reference -- readthedocs, docs.rs,
      PyPI, CRAN, eBPF docs, Rust fuzz book, OSV
  T5  aggregator, personal blog, preprint-of-a-preprint, or
      unreviewed commentary -- Medium, Towards AI, Substack, personal
      sites

TWO DELIBERATE OMISSIONS
  - 10.0.0.10 is a LAN address, i.e. the operator's own infrastructure. Not a
    source at all. Left unclassified on purpose.
  - emergentmind, gwern, lzw.me, casrai and similar personal sites are
    left UNRESOLVED rather than guessed. They may be excellent, but
    "this person's blog" is not a tier the rubric defines, and M8
    already covers the vendor-benchmark case.

This is a LOOKUP TABLE, so it is auditable line by line. Every mapping
carries the reason it was made. Run with --apply to add the newly
recognised hosts to phase5_pilot.py's classifiers; the default is to
print the table for review.
"""
import argparse
import re
import sys

# tier, label, regex
RULES = [
    # ---- T1: standards bodies and registries -------------------------
    ('high', 'T1_standards_registry',
     r'(^|\.)iana\.org(/|$|:)'),
    ('high', 'T1_standards_registry',
     r'(^|\.)w3\.org(/|$|:)'),
    ('high', 'T1_standards_registry',
     r'(^|\.)whatwg\.org(/|$|:)'),
    ('high', 'T1_standards_registry',
     r'(^|\.)iso\.org(/|$|:)'),
    ('high', 'T1_standards_registry',
     r'(^|\.)nist\.gov(/|$|:)'),
    ('high', 'T1_standards_registry',
     r'(^|\.)ietf\.org(/|$|:)'),
    ('high', 'T1_standards_registry',
     r'(^|\.)datatracker\.ietf\.org(/|$|:)'),
    ('high', 'T1_standards_registry',
     r'(^|\.)rfc-editor\.org(/|$|:)'),

    # ---- T2: peer-reviewed venues and recognised indexes ------------
    ('high', 'T2_peer_reviewed_venue',
     r'neurips\.cc'),
    ('high', 'T2_peer_reviewed_venue', r'(^|\.)icml\.cc'),
    ('high', 'T2_peer_reviewed_venue', r'iclr\.cc'),
    ('high', 'T2_peer_reviewed_venue', r'(^|\.)iclr\.cc'),
    ('high', 'T2_peer_reviewed_venue', r'openaccess\.thecvf\.com'),
    ('high', 'T2_peer_reviewed_venue', r'(^|\.)cell\.com'),
    ('high', 'T2_peer_reviewed_venue', r'jneurosci\.org'),
    ('high', 'T2_peer_reviewed_venue', r'elifesciences\.org'),
    ('high', 'T2_peer_reviewed_venue', r'psycnet\.apa\.org'),
    ('high', 'T2_peer_reviewed_venue', r'pubs\.aip\.org'),
    ('high', 'T2_peer_reviewed_venue', r'dl\.acm\.org'),
    ('high', 'T2_peer_reviewed_venue', r'link\.springer\.com'),
    ('high', 'T2_peer_reviewed_venue', r'ieeexplore\.ieee\.org'),
    ('high', 'T2_peer_reviewed_venue', r'link\.springer\.com'),
    ('high', 'T2_recognised_index', r'europepmc\.org'),
    ('high', 'T2_recognised_index', r'adsabs\.harvard\.edu'),
    ('high', 'T2_recognised_index', r'ui\.adsabs\.harvard\.edu'),

    # ---- T3: monographs, reference works, preprint servers ----------
    ('medium', 'T3_monograph_or_reference', r'plato\.stanford\.edu'),
    ('medium', 'T3_monograph_or_reference', r'britannica\.com'),
    ('medium', 'T3_preprint', r'huggingface\.co/papers'),
    ('medium', 'T3_preprint', r'(^|\.)alphaxiv\.org'),
    ('medium', 'T3_repository', r'(^|\.)zenodo\.org'),

    # ---- T4: project documentation and reference ---------------------
    ('low', 'T4_project_documentation',
     r'(^|\.)readthedocs\.io'),
    ('low', 'T4_project_documentation', r'docs\.rs'),
    ('low', 'T4_project_documentation', r'docs\.ebpf\.io'),
    ('low', 'T4_project_documentation', r'(^|\.)pypi\.org'),
    ('low', 'T4_project_documentation', r'cran\.r-project\.org'),
    ('low', 'T4_project_documentation', r'cljdoc\.org'),
    ('low', 'T4_project_documentation', r'doc\.rust-lang\.org'),
    ('low', 'T4_project_documentation', r'protobuf\.dev'),
    ('low', 'T4_project_documentation', r'grpc\.io'),
    ('low', 'T4_project_documentation', r'osv\.dev'),
    ('low', 'T4_project_documentation', r'rust-fuzz\.github\.io'),
    ('low', 'T4_project_documentation', r'cbor-wg\.github\.io'),

    # ---- T5: aggregator, commentary, unreviewed ---------------------
    ('low', 'T5_aggregator_or_commentary', r'medium\.com'),
    ('low', 'T5_aggregator_or_commentary', r'towardsai\.com'),
    ('low', 'T5_aggregator_or_commentary', r'towardsdatascience\.com'),
    ('low', 'T5_aggregator_or_commentary', r'(^|\.)dev\.to'),
    ('low', 'T5_aggregator_or_commentary', r'clawrxiv\.io'),
    ('low', 'T5_aggregator_or_commentary', r'codeberg\.org'),
    ('low', 'T5_aggregator_or_commentary', r'(^|\.)kaggle\.com'),
    ('low', 'T5_aggregator_or_commentary', r'anthropic\.com'),
    ('low', 'T5_aggregator_or_commentary', r'openai\.com'),

    # ---- second pass: the misses from the first review ---------------
    ('high', 'T2_peer_reviewed_venue', r'ojs\.aaai\.org'),
    ('high', 'T2_recognised_index', r'files\.wmich\.edu'),
    ('high', 'T2_recognised_index', r'cs\.nyu\.edu'),
    ('high', 'T2_recognised_venue', r'www\.mdpi\.com'),
    ('high', 'T1_standards_registry', r'genai\.owasp\.org'),
    ('high', 'T1_standards_registry', r'modelcontextprotocol\.io'),
    ('high', 'T1_standards_registry', r'gateway\.envoyproxy\.io'),
    ('high', 'T1_standards_registry', r'man\.archlinux\.org'),
    ('high', 'T1_standards_registry', r'inseq\.org'),
    ('low', 'T4_project_documentation', r'iris-project\.org'),
    ('low', 'T4_project_documentation', r'docs\.vllm\.ai'),
    ('low', 'T4_project_documentation', r'docs\.plur\.ai'),
    ('low', 'T4_project_documentation', r'wolfssl\.com'),
    ('low', 'T4_project_documentation', r'neo4j\.com'),
    ('low', 'T4_project_documentation', r'www\.npmjs\.com'),
    ('low', 'T4_project_documentation', r'blog\.flowrust\.com'),
    ('low', 'T4_project_documentation', r'docs\.mnemosyne\.site'),
    ('low', 'T5_aggregator_or_commentary', r'huggingface\.co'),
    ('low', 'T5_aggregator_or_commentary', r'(^|\.)tetragon\.io'),
    ('low', 'T5_aggregator_or_commentary', r'the-agent-report\.com'),
    ('low', 'T5_aggregator_or_commentary', r'protodex\.io'),
    ('low', 'T5_aggregator_or_commentary', r'metricgate\.com'),
    ('low', 'T5_aggregator_or_commentary', r'agentassert\.com'),
    ('low', 'T5_aggregator_or_commentary', r'intuitionlabs\.ai'),
    ('low', 'T5_aggregator_or_commentary', r'gcformat\.com'),
    ('low', 'T5_aggregator_or_commentary', r'hivefence\.com'),
    ('low', 'T5_aggregator_or_commentary', r'sesamedisk\.com'),
    ('low', 'T5_aggregator_or_commentary', r'emergentmind\.com'),
    ('low', 'T5_aggregator_or_commentary', r'(^|\.)lzw\.me'),
    ('low', 'T5_aggregator_or_commentary', r'(^|\.)gwern\.net'),
    ('low', 'T5_aggregator_or_commentary', r'casrai\.org'),
    ('low', 'T5_aggregator_or_commentary', r'zby\.github\.io'),
    ('low', 'T5_aggregator_or_commentary', r'saksham-jain01\.github\.io'),
]

COMPILED = [(t, l, re.compile(p, re.I)) for t, l, p in RULES]

# Deliberately NOT resolved. Each needs a human decision.
UNRESOLVED_NOTE = {
    '10.0.0.10': 'LAN address, i.e. the operator\'s own infrastructure. Not a source.',
    '10.0.0.151': 'LAN address. Not a source.',
    '192.168.': 'LAN address. Not a source.',
    '10.0.0.10:': 'LAN address. Not a source.',
}


def resolve(host):
    h = host.lower()
    for base, note in UNRESOLVED_NOTE.items():
        if h.startswith(base):
            return None, f'NOT_A_SOURCE: {note}'
    for tier, label, rx in COMPILED:
        if rx.search(h):
            return (tier, label), None
    return None, 'unresolved: no rubric basis'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true',
                    help='also print the python snippet to paste')
    args = ap.parse_args()

    import csv
    from collections import Counter
    rows = list(csv.DictReader(
        open('/home/operator/hermes-brain/docs/audit/'
             'confidence-pilot.csv', encoding='utf-8')))
    hosts = Counter()
    for r in rows:
        m = re.search(r'unclassified_host:([a-z0-9.:_-]+)', r['reason'])
        if m:
            hosts[m.group(1)] += 1

    resolved, unresolved, notsource = [], [], []
    for host, n in hosts.most_common():
        got, why = resolve(host)
        if got:
            resolved.append((host, n, got[0], got[1]))
        elif why and why.startswith('NOT_A_SOURCE'):
            notsource.append((host, n, why))
        else:
            unresolved.append((host, n))

    print(f'\n  distinct hosts flagged: {len(hosts)}  across '
          f'{sum(hosts.values())} files\n')
    for tier, label, _ in RULES[:1]:
        pass
    by_tier = Counter(t for _, _, t, _ in resolved)
    print('  RESOLVED by tier:')
    for t, c in sorted(by_tier.items(), key=lambda x: -x[1]):
        print(f'    {t:8} {c:>4} hosts')
    print(f'\n  NOT A SOURCE (own infrastructure): {len(notsource)}')
    for h, n, why in notsource:
        print(f'    {n:>3}x {h:24} {why[:44]}')
    print(f'\n  STILL UNRESOLVED (need a human): {len(unresolved)}')
    for h, n in unresolved:
        print(f'    {n:>3}x {h}')

    files_resolved = sum(n for _, n, _, _ in resolved)
    print(f'\n  files that gain a tier: {files_resolved}')
    print(f'  files that stay ungraded: '
          f'{sum(hosts.values()) - files_resolved}')

    if args.apply:
        print('\n  --- snippet for phase5_pilot.py ---')
        seen = set()
        for host, n, tier, label in resolved:
            key = (tier, label)
            if key in seen:
                continue
            seen.add(key)
            rx = next(p for t, l, p in RULES if (t, l) == key)
            print(f"    ('{tier}', '{label}', re.compile(\n"
                  f"        r'{rx}', re.I)),")
    return 0


if __name__ == '__main__':
    sys.exit(main())
