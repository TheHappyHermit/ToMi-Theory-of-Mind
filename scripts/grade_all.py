#!/usr/bin/env python3
"""Grade every file in both vaults with the schema rubric, and write only
where the new system DISAGREES with the current value.

THE OPERATOR'S RULE, 2026-09-28:
  "as long as that's what it would be if we did it with the new system
   then they can be left like that. If the new system would change them
   from high to something else then they should be changed."

So this is not "restamp everything with the rubric". It is: derive the
band, compare it to what is already there, and change only the files
where they differ. A file that already says `high` and still derives
`high` is left completely alone.

THE DERIVATION, IN ORDER
  0. navigational        link_share >= 45  -> not_applicable
  1. decision record     type in (decision, lesson) -> high
                         (M0_decision_record, the operator's ruling)
  2. first-party         type in (system, project) with
                         session/first_party provenance -> high
  3. no load-bearing     ungraded
  4. otherwise           T1 -> high, T2 -> high, T3 -> medium,
                         T4/T5 -> low, then:
                           high    needs T1 or T2, or 2+ independent T3+
                           medium  needs at least one source at T3+
                           low     anything with a source at all
                           ungraded nothing
  5. minimum_source_rule caps everything at low without a T1/T2 or 2x T3+
  6. E11  an AI-written page with no external source is at most T5

WHAT THIS WILL AND WILL NOT DO
It reads URLs. It does not open documents. So it will NOT award `high`
on a T2 venue alone: T2's ceiling_qualifier requires the DOI to resolve
to a document whose title and authors match the citation as written.
That check needs a fetch per source, which is a separate pass and is
run separately (--verify-hosts). Without it, a T2 host is treated as
"capped at medium pending title verification", which is the honest
reading rather than the generous one.

DRY RUN BY DEFAULT. --apply writes. Backups always.
"""
import argparse
import csv
import datetime
import json
import os
import re
import shutil
import sys
from collections import Counter

import yaml

N = chr(10)


def _home():
    """Locate the Hermes home from the environment, not from a literal path.

    A hardcoded absolute vault path made this script machine-specific and
    invisible to the folder rename: the paths it globbed simply stopped
    matching and the tool reported success over an empty file list. The
    init_db.py and init_experience_db.py pair had the same flaw and had been
    scanning a directory that no longer existed.
    """
    for v in ('HERMES_HOME', 'HERMES_DATA_DIR', 'CORTEX_HOME'):
        val = os.environ.get(v)
        if val and os.path.isdir(val):
            return val
    return os.path.expanduser('~/.hermes')


_HERMES = _home()
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOTS = {
    'active-wiki': os.path.join(_HERMES, 'active-wiki'),
    'oracle': os.path.join(_HERMES, 'oracle', 'brain'),
}
BACKUP = f'{REPO}/archive/grade_backup'
REPORT = f'{REPO}/docs/audit/grade-decisions.csv'

WIKILINK = re.compile(r'\[\[[^\]]*\]\]')
MDLINK = re.compile(r'\[[^\]]*\]\(([^)]+)\)')
CONF_LINE = re.compile(r'^confidence:(.*)$', re.M)
T2_VENUE = re.compile(
    r'(arxiv\.org|doi\.org|ieeexplore|nature\.com|science\.org|'
    r'acm\.org|aclanthology\.org|springer\.com|wiley|sciencedirect\.com|'
    r'pubmed\.ncbi\.nlm\.nih\.gov|pmc\.ncbi\.nlm\.nih\.gov|'
    r'ncbi\.nlm\.nih\.gov|frontiersin\.org|plos\.org|copernicus\.org|'
    r'neurips\.cc|(^|\.)icml\.cc|iclr\.cc|openaccess\.thecvf\.com|'
    r'(^|\.)cell\.com|jneurosci\.org|elifesciences\.org|psycnet\.apa\.org|'
    r'pubs\.aip\.org|dl\.acm\.org|link\.springer\.com|ieeexplore\.ieee\.org|'
    r'(^|\.)mdpi\.com|ojs\.aaai\.org|files\.wmich\.edu|cs\.nyu\.edu)', re.I)
T1_STD = re.compile(
    r'((^|\.)iana\.org|(^|\.)w3\.org|(^|\.)whatwg\.org|(^|\.)iso\.org|'
    r'(^|\.)nist\.gov|rfc-editor|datatracker\.ietf|(^|\.)ietf\.org|'
    r'genai\.owasp\.org|modelcontextprotocol\.io|gateway\.envoyproxy\.io|'
    r'man\.archlinux\.org|inseq\.org|(^|\.)ietf\.org)', re.I)
T3 = re.compile(
    r'(plato\.stanford\.edu|britannica\.com|alphaxiv|zenodo|'
    r'huggingface\.co/papers|(^|\.)github\.io|readthedocs|docs\.rs|'
    r'uspapers|ssrn|semanticscholar|researchgate|\.edu/|europepmc|'
    r'adsabs\.harvard\.edu|arxiv\.org|doi\.org)', re.I)
T4 = re.compile(
    r'((^|\.)readthedocs\.io|docs\.rs|docs\.ebpf\.io|(^|\.)pypi\.org|'
    r'cran\.r-project\.org|cljdoc\.org|doc\.rust-lang\.org|'
    r'protobuf\.dev|grpc\.io|osv\.dev|docs\.vllm\.ai|wolfssl\.com|'
    r'neo4j\.com|(^|\.)npmjs\.com|docs\.kernel\.org|kubernetes\.io|'
    r'iris-project\.org|next\.redhat\.com|rfcinfo\.com|'
    r'(^|\.)statsmodels\.org|docs\.plur\.ai)', re.I)
T5 = re.compile(
    r'(medium\.com|towardsai|towardsdatascience|(^|\.)dev\.to|substack|'
    r'clawrxiv\.io|codeberg\.org|(^|\.)kaggle\.com|anthropic\.com|'
    r'openai\.com|huggingface\.co|(^|\.)tetragon\.io|'
    r'the-agent-report\.com|protodex\.io|metricgate\.com|'
    r'agentassert\.com|intuitionlabs\.ai|emergentmind|(^|\.)lzw\.me|'
    r'(^|\.)gwern\.net|casrai\.org|blogspot|wordpress\.com|'
    r'(^|\.)blog\.|infoq\.com|thenewstack\.io|thoughtworks\.com|'
    r'zapier\.com|hubspot|reddit\.com|quora\.com)', re.I)
LAN = re.compile(r'^\d{1,3}(\.\d{1,3}){3}(:\d+)?$')
FIRST_PARTY = re.compile(
    r'(session:|^(local |git |docker |nas://)|\.(ya?ml|json|toml|py|'
    r'sql|sh)$|^config|^cron/|^honcho|^git )', re.I)
SESSION = re.compile(r'^session:', re.I)

DECISION_TYPES = ('decision', 'lesson')
FIRST_PARTY_TYPES = ('system', 'project')


T2_TABLE = {}   # populated from --with-t2


def link_share(body):
    n = len(WIKILINK.findall(body)) + len(MDLINK.findall(body))
    toks = max(1, len(body.split()))
    return min(100, 100 * (n * 4) // toks)


def tier_of(url):
    """Tear one source entry into a host, then into a tier.

    The first version of this did
        host = re.sub(r'^\\w+://', '', s).split('/')[0]
    which silently threw away every NON-URL identifier. arXiv alone is
    2,866 entries across the corpus and nearly all of them are written
    as `arxiv:2609.07816`, not as an https URL. Those all reduced to
    the string `arxiv:2609.07816`, matched no tier pattern, and were
    reported as "none tierable yet" -- so a file with 39 genuine arXiv
    citations was graded as if it had none. That is the same class of
    error as mistyping a filename: a transformation that looks right
    and throws the data away.

    Measured shapes in the corpus: 7,501 http URLs, 226 arxiv:ID,
    78 url: prefixes, 8 doi:, and 5,191 other (session ids, nas paths,
    local file paths, bare prose). Only the first four are sources.
    """
    s = str(url).strip()
    if not s:
        return None
    low = s.lower()

    if low.startswith('arxiv:'):
        host = 'arxiv.org'                     # arXiv:ID form
    elif low.startswith('doi:'):
        host = 'doi.org'                       # doi:10.xxxx/yyy form
    elif low.startswith('url:'):
        s = s[4:].strip().strip('\'"')
        host = re.sub(r'^https?://', '', s).split('/')[0].lower()
    elif low.startswith(('http://', 'https://')):
        host = re.sub(r'^https?://', '', s).split('/')[0].lower()
    else:
        return None                            # not an external source
    if not host or LAN.match(host):
        return None                            # our own infrastructure
    if T1_STD.search(host):
        return 1
    if T2_VENUE.search(host):
        return 2
    if T3.search(host):
        return 3
    if T4.search(host):
        return 4
    if T5.search(host):
        return 5
    return None


def derive(path, text, meta):
    """Return (band, reason). Never returns None."""
    e = text.find(N + '---', 3)
    fm, body = text[3:e], text[e + 4:]
    ty = meta.get('type')
    ty = ty if isinstance(ty, str) else ''
    words = len(body.split())
    share = link_share(body)

    # 0. navigational
    if share >= 45:
        return 'not_applicable', f'link_share={share}%: body is an index'
    if ty == 'index' and words <= 400 and share >= 20:
        return 'not_applicable', f'index, {words}w, {share}% links'

    srcs = meta.get('sources') or []
    if isinstance(srcs, str):
        srcs = [srcs]
    srcs = [str(s).strip() for s in srcs if str(s).strip()]

    # 1. decision record (M0)
    if ty in DECISION_TYPES:
        return 'high', f'{ty}: M0_decision_record, ruling is the authority'

    ext = [s for s in srcs
           if s.lower().startswith(('http://', 'https://', 'doi:', 'arxiv:',
                                    'url:'))]
    fp = [s for s in srcs if FIRST_PARTY.search(s)]

    # 2. first-party description of our own system
    if ty in FIRST_PARTY_TYPES and (fp or not ext):
        return 'high', f'{ty}: first-party provenance, system is the source'

    # 3. nothing to grade
    if not ext:
        if not srcs:
            return 'ungraded', 'no source of any kind; E11 caps at T5'
        return 'low', f'only non-external provenance {len(srcs)}'

    tiers = [t for t in (tier_of(s) for s in ext) if t is not None]
    unclassified = len(ext) - len(tiers)
    if not tiers:
        return 'low', f'{len(ext)} external sources, none tierable yet'
    best = min(tiers)
    has12 = any(t <= 2 for t in tiers)
    t3plus = sum(1 for t in tiers if t >= 3)

    # 5. minimum_source_rule
    if not has12 and t3plus < 2:
        return 'low', (f'best=T{best}, {t3plus} T3+; no T1/T2 and no 2 '
                       f'independent T3+')
    # T2 cannot be called high without resolving the document
    if best == 2:
        if T2_TABLE:
            ok, why = t2_all_match(srcs, T2_TABLE, rel_path=path)
            if ok:
                return 'high', 'T2 verified: ' + why
            return 'medium', f'T2 pending: {why}'
        return 'medium', f'T2 host present but title match unverified'
    if best == 1:
        return 'high', f'T1 standards source: {len(tiers)} tiered'
    return 'high', f'{t3plus} independent T3+ sources'


def walk():
    for vault, root in ROOTS.items():
        for dp, dn, fn in os.walk(root):
            if '.meta' in dp.split(os.sep):
                continue
            for f in sorted(fn):
                if f.endswith('.md'):
                    yield vault, os.path.join(dp, f)


# arXiv identifiers appear in THREE shapes in this corpus, and the first
# version of this pattern only matched one of them:
#
#   arxiv:2607.18704              (bare prefix -- matched)
#   https://arxiv.org/abs/2607.18704   (abstract URL -- NOT matched)
#   https://arxiv.org/pdf/2607.18704   (PDF URL -- NOT matched)
#
# The alternation `arxiv[:/]` looks like it covers the URLs, but
# 'arxiv.org/abs/' has ".org/" between 'arxiv' and the slash, so neither
# branch fires. Measured on this corpus: the old pattern found 537 arXiv
# identifiers, the corrected one finds 1,950 -- 1,413 citations were
# invisible, and a file whose only strong evidence was an arXiv URL was
# reported as "T2 pending: no T2 identifier" and demoted.
#
# The version suffix (2607.01977v1, 2601.23014v2) is stripped: the table is
# keyed on the bare identifier, and a suffixed form would miss every lookup.
ARXIV_ID = re.compile(
    r'arxiv[:/]|arxiv\.org/(?:abs|pdf|html)/',   # any of the three shapes
    re.I)
DOI_ID = re.compile(r'doi[:/](?P<id>10\.\d{4,9}/[^\s"\'<>,;]+)', re.I)
URL_ID = re.compile(r'https?://(?:dx\.)?doi\.org/'
                    r'(?P<id>10\.\d{4,9}/[^\s"\'<>,;]+)', re.I)


def t2_ids(srcs):
    """The identifiers a file's T2 verdict depends on.

    Three arXiv shapes, one canonical form. The bare `arxiv:` prefix, the
    abstract URL and the PDF URL all normalize to 'arxiv:NNNN.NNNNN' with
    any version suffix (v1, v2) removed -- the evidence table is keyed on
    the bare identifier, so a suffixed form would miss every lookup.
    """
    out = set()
    for s in srcs:
        s = str(s).strip()
        # Any of the three shapes -> capture the NNNN.NNNNN immediately after.
        m = re.search(r'arxiv[:/]\s*(\d{4}\.\d{4,5})', s, re.I) or \
            re.search(r'arxiv\.org/(?:abs|pdf|html)/(\d{4}\.\d{4,5})', s, re.I)
        if m:
            out.add('arxiv:' + m.group(1))
            continue
        for pat in (DOI_ID, URL_ID):
            mm = pat.search(s)
            if mm:
                out.add('doi:' + re.sub(r'[.,;)\]]+$', '',
                                           mm.group('id').strip()))
                break
    return out


def t2_all_match(srcs, table, rel_path=None):
    """True only if every resolvable T2 identifier in the file was
    checked and matched. A single unresolvable or mismatched identifier
    blocks the promotion, because the rubric's qualifier is about THE
    citation as written -- one wrong DOI means the file cites something
    it should not.

    The lookup key is `path::identifier`, NOT the bare identifier.

    The evidence table is keyed that way because two vault files can
    cite one identifier and need not cite it equally well: arXiv:
    2505.17335 is correct in research/cboritem-2026-ecosystem-survey.md
    and an annotation in research/cbor-tag-6-...md. Keying by
    identifier alone made every lookup miss, so every file reported
    "N of N not matched: absent" and T2 could never promote anything --
    the gate was structurally impossible to pass, whatever the quality
    of the citations. Which means a green T2 would have had to come
    from this bug being fixed, not from the citations being right.
    """
    ids = t2_ids(srcs)
    if not ids:
        return False, 'no T2 identifier'
    verdicts = []
    for i in sorted(ids):
        v = lookup_verdict(table, rel_path, i)
        verdicts.append((i, v))
    bad = [x for x in verdicts if x[1] != 'match']
    if bad:
        return False, f'{len(bad)} of {len(ids)} not matched: ' + ', '.join(
            f'{a.split(":", 1)[0]}:{b}' for a, b in bad[:3])
    return True, f'all {len(ids)} T2 identifiers resolved and title-matched'


def lookup_verdict(table, rel_path, ident):
    """Resolve one identifier's verdict for one file.

    Prefers the file-scoped key. Falls back to an identifier-only key
    only when the table genuinely uses that shape, so a table written
    either way still works -- but never guesses a path.
    """
    if rel_path:
        rel = rel_path
        for pre in ('active-wiki/', 'oracle/brain/'):
            if rel.startswith(pre):
                rel = rel[len(pre):]
        row = table.get('%s::%s' % (rel, ident))
        if row is not None:
            return row.get('verdict', 'absent')
    row = table.get(ident)
    if isinstance(row, dict):
        return row.get('verdict', 'absent')
    if isinstance(row, str):
        return row
    return 'absent'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--with-t2', default='',
                    help='path to t2-verification.json; a file whose T2 '
                         'sources all resolved with a matching title may '
                         'be promoted from medium to high')
    ap.add_argument('--only-t2', action='store_true',
                    help='apply only the T2 promotions, and only where a '
                         'previous run already set everything else')
    ap.add_argument('--report', action='store_true',
                    help='regenerate docs/audit/grade-decisions.csv. Off by '
                         'default: that file is tracked and can hold '
                         'hand-edited work, and a dry run used to clobber it '
                         'even though it changed no vault file')
    args = ap.parse_args()

    t2 = {}
    if args.with_t2:
        if not os.path.exists(args.with_t2):
            print(f'  no T2 table at {args.with_t2}')
            return 1
        t2 = json.load(open(args.with_t2, encoding='utf-8'))
        print(f'  T2 table: {len(t2)} identifiers, '
              f'{Counter(v["verdict"] for v in t2.values())}')
    global T2_TABLE
    T2_TABLE = t2

    rows = []
    agree = Counter()
    changes = []
    unread = 0
    for vault, p in walk():
        try:
            text = open(p, encoding='utf-8', errors='replace').read()
        except Exception:
            unread += 1
            continue
        if not text.startswith('---'):
            unread += 1
            continue
        e = text.find(N + '---', 3)
        if e == -1:
            unread += 1
            continue
        try:
            meta = yaml.safe_load(text[3:e]) or {}
        except Exception:
            unread += 1
            continue
        cur = meta.get('confidence')
        if cur in (None, '', 'not_applicable'):
            continue                      # nothing to compare against
        # derive() must receive the VAULT-RELATIVE path, not the absolute one.
        #
        # The T2 evidence table is keyed `path::identifier` where path is
        # relative to the vault root (research/batch264-...md::doi:10.1109/...).
        # lookup_verdict() strips the 'active-wiki/' or 'oracle/brain/'
        # prefix off whatever it is given, and that strip is a no-op on an
        # absolute path -- so every lookup missed, returned 'absent', and
        # every T2-bearing file was demoted high -> medium with the reason
        # "T2 pending: 4 of 4 not matched: doi:absent".
        #
        # The failure was silent and looked exactly like a legitimate
        # demotion: 946/946 identifiers verify as 'match' when looked up
        # with the relative path. This is the same shape as the
        # identifier-only keying bug documented in t2_all_match -- a lookup
        # that can never hit turns a real promotion into a fake penalty.
        rel = p.split('/.hermes/')[-1]
        band, why = derive(rel, text, meta)
        agree[band] += 1
        row = {'vault': vault, 'path': rel, 'current': cur,
               'derived': band, 'reason': why, 'abspath': p}
        rows.append(row)
        if band != cur:
            changes.append(row)

    # The report is only written when explicitly asked for. Writing it
    # unconditionally meant a plain dry run (no --apply, so the vault was
    # untouched) still clobbered a tracked file that can hold hand-edited
    # work. That happened on 2026-09-29. A check that silently destroys a
    # tracked artifact is not a check, so the write now has a gate of its own
    # and does not ride along on --apply.
    if args.report:
        with open(REPORT, 'w', newline='', encoding='utf-8') as fh:
            w = csv.DictWriter(fh, fieldnames=['vault', 'path', 'current',
                                               'derived', 'reason'])
            w.writeheader()
            w.writerows([{k: v for k, v in r.items() if k != 'abspath'}
                         for r in rows])
        print(f'\n  report written: {REPORT}')
    else:
        print('\n  report NOT written (pass --report to regenerate '
              'docs/audit/grade-decisions.csv)')

    print(f'\n  files graded: {len(rows)}   unreadable: {unread}')
    print('\n  derived distribution:')
    for k, v in agree.most_common():
        print(f'    {v:>5}  {k}')

    move = Counter()
    for c in changes:
        move[(c['current'], c['derived'])] += 1
    print(f'\n  files where the new system DISAGREES: {len(changes)}')
    print('  transitions:')
    for (a, b), n in move.most_common(12):
        print(f'    {n:>5}  {a} -> {b}')
    print(f'\n  files left untouched because they already agree: '
          f'{len(rows) - len(changes)}')
    if args.report:
        print(f'  report -> {REPORT}')

    if not args.apply:
        print('\n  DRY RUN. Pass --apply to write.')
        return 0

    ts = datetime.datetime.now(datetime.timezone.utc).strftime(
        '%Y%m%dT%H%M%SZ')
    os.makedirs(f'{BACKUP}/{ts}', exist_ok=True)
    ok = fail = 0
    for c in changes:
        p = c['abspath']
        try:
            # Preserve the vault-relative directory structure, NOT the bare
            # basename.
            #
            # The two vaults hold mirrored copies of the same page
            # (active-wiki/80_Models/X.md and oracle/brain/concepts/X.md), and
            # a basename-flat backup made the second overwrite the first.
            # A 109-file write produced only 106 backups -- three files were
            # silently unrecoverable, and the loss was invisible because the
            # run reported "written: 109 failed: 0".
            #
            # The write itself was correct; only the recovery path was
            # incomplete. A backup that cannot restore what it claims to have
            # backed up is worse than none, because it invites you to skip
            # the manual copy.
            rel = c['path'].replace('/', '__')
            dest = os.path.join(BACKUP, ts, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(p, dest)
            t = open(p, encoding='utf-8', errors='replace').read()
            nt, n = CONF_LINE.subn(f'confidence: {c["derived"]}', t, 1)
            if n != 1:
                raise RuntimeError('confidence line not found')
            open(p, 'w', encoding='utf-8').write(nt)
            ok += 1
        except Exception as ex:
            print(f'  FAIL {c["path"]}: {ex}')
            fail += 1
    print(f'\n  written: {ok}  failed: {fail}')
    print(f'  backups: {BACKUP}/{ts}')
    return 1 if fail else 0


if __name__ == '__main__':
    sys.exit(main())
