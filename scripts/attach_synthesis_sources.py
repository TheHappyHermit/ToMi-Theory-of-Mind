#!/usr/bin/env python3
"""Lift the URLs already present in synthesis-file bodies into frontmatter.

the operator: "attach the sources so that we know where they came from and can
appropriately score them."

This handles the part of that which is ready. 88 of the 496 files
already contain a reference list in the body; extract_synthesis_sources
.py found 1,727 entries, 821 of which carry a resolvable URL. Those
821 URLs are copied into the frontmatter `sources:` list so that:

  - the file records where it came from, which is what the operator asked for
  - confidence_derivation can then tier them, because the rubric's
    method is "check the host plus the document status line" and it
    cannot do that without a URL in the frontmatter

WHAT IS DELIBERATELY NOT DONE
  - confidence is NOT changed here. Attaching a source is not the same
    as grading it. T2 additionally requires the DOI to resolve to a
    document whose title matches the citation as written, which needs
    a fetch per source, not a regex. Phase 5 grades them next.
  - files whose reference entries have no URL (38 files) are skipped.
    Their citations are real but not resolvable, and inventing a URL
    for them would be fabricating provenance.
  - files with no reference section at all (408) are skipped.

SAFETY
  - dry run by default
  - backup every touched file to archive/ first
  - `sources:` is a YAML list; the existing value is preserved if
    present and the new URLs appended, deduplicated. Nothing is
    removed, so a file that already had sources keeps them.
  - records the prior sources list per file in the manifest
"""
import argparse
import csv
import datetime
import json
import os
import re
import sys

N = chr(10)
REPO = '/home/operator/hermes-brain'
ROOTS = {
    'active-wiki': '/home/operator/.hermes/active-wiki',
    'oracle': '/home/operator/.hermes/oracle/brain',
}
FOUND_CSV = f'{REPO}/docs/audit/synthesis-sources-found.csv'
BACKUP_DIR = f'{REPO}/archive/sources_backup'
MANIFEST = f'{REPO}/docs/audit/sources-writes-manifest.json'

# Grab the existing frontmatter `sources:` block, which is either
#   sources: [a, b]        flow style
#   sources:              block style
#     - a
#     - b
#   sources: []  /  sources:
SRC_BLOCK = re.compile(
    r'^(?P<key>[\w-]*sources[\w-]*):[^\n]*'          # the key, whole line
    r'(?P<block>(?:\n[ \t]+-[^\n]*)*)', re.M)
LIST_LINE = re.compile(r'^\s*-\s+(.*?)\s*$')
FLOW = re.compile(r'\[(.*)\]\s*$')


def yaml_scalar(s):
    """Quote a string for safe YAML block-list use."""
    s = s.strip()
    if not s:
        return "''"
    if (re.match(r'^[A-Za-z0-9][A-Za-z0-9 ._/+()#-]*$', s)
            and s.lower() not in ('true', 'false', 'null', 'yes', 'no',
                                   'on', 'off')
            and not s.endswith(':')):
        return s
    return "'" + s.replace("'", "''") + "'"


def get_sources(text):
    m = SRC_BLOCK.search(text)
    if not m:
        return None, None
    out = []
    # The inline value, if any, sits between the colon and end of line.
    line = text[m.start():m.end()]
    val = line.split(':', 1)[1].split(N)[0].strip()
    fm = FLOW.match(val)
    if fm and fm.group(1).strip():
        for part in fm.group(1).split(','):
            part = part.strip().strip('"\'')
            if part:
                out.append(part)
    elif val and val not in ('[]', '~', 'null'):
        out.append(val.strip('"\''))
    for line in m.group('block').split(N):
        lm = LIST_LINE.match(line)
        if lm and lm.group(1) not in ('[]',):
            out.append(lm.group(1).strip('"\''))
    return out, m


def set_sources(text, urls):
    cur, m = get_sources(text)
    if m is None:
        return None, False
    existing = list(cur or [])
    merged, seen = [], set()
    for u in existing + list(urls):
        u = u.strip()
        if u and u not in seen:
            seen.add(u)
            merged.append(u)
    block = chr(10).join('  - ' + yaml_scalar(u) for u in merged)
    # The original `sources:` line may have carried a trailing value
    # (e.g. `sources: []` or `sources:` with a comment). Consuming only
    # up to the end of the LINE, not the whole match, is what keeps
    # this from emitting `sources:  - url`, which is invalid YAML. The
    # old match consumed trailing spaces plus any inline comment; take
    # the line itself and rebuild cleanly.
    # NOTE: block already begins with the indent, so it must start on
    # the NEXT line. "sources:" + block yields `sources:  - x`, which is
    # invalid YAML -- sequence entries are not allowed on a mapping line.
    new = "sources:" + N + block
    return text[:m.start()] + new + text[m.end():], True


def _selftest():
    """Prove the rewrite produces valid YAML and preserves everything else.

    This exists because the first version of this function emitted
    `sources:  - url` -- a sequence entry on a mapping line, which is a
    YAML error -- and the dry run reported 50 files ready to write
    without noticing. A dry run that does not check its own output is
    the same class of bug as a check that cannot fail. So the round trip
    is asserted here rather than eyeballed.
    """
    import yaml
    base = ('---' + N
            + 'okf_version: "0.2"' + N
            + 'id: x' + N
            + 'title: "T: with a colon"' + N
            + 'type: research-report' + N
            + 'confidence: medium' + N
            + 'sources: []' + N
            + 'tags: [a, b]' + N
            + '---' + N
            + '# Heading' + N
            + 'Body text with [1] marker.' + N)
    new, ok = set_sources(base, ['https://ex.org/a', 'https://ex.org/b'])
    assert ok, 'set_sources reported no change'
    e = new.find(N + '---', 3)
    d = yaml.safe_load(new[3:e])
    assert d['sources'] == ['https://ex.org/a', 'https://ex.org/b'], d['sources']
    assert d['confidence'] == 'medium'
    assert d['title'] == 'T: with a colon', 'title mangled'
    assert d['tags'] == ['a', 'b']
    assert '# Heading' in new and '[1] marker.' in new, 'body lost'
    # idempotent: running twice must not duplicate
    again, _ = set_sources(new, ['https://ex.org/a', 'https://ex.org/b'])
    e2 = again.find(N + '---', 3)
    d2 = yaml.safe_load(again[3:e2])
    assert d2['sources'] == d['sources'], 'not idempotent'
    # existing sources are preserved, not replaced
    pre = base.replace('sources: []',
                      'sources:' + N + '  - https://old.example/x')
    n3, _ = set_sources(pre, ['https://new.example/y'])
    e3 = n3.find(N + '---', 3)
    d3 = yaml.safe_load(n3[3:e3])
    assert d3['sources'] == ['https://old.example/x', 'https://new.example/y'], \
        d3['sources']
    print('  self-test passed: yaml valid, keys preserved, body intact,'
          ' idempotent, prior sources kept')
    return 0


def main():
    if '--selftest' in sys.argv:
        return _selftest()
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--max-per-file', type=int, default=0,
                    help='0 = no cap')
    args = ap.parse_args()

    rows = [r for r in csv.DictReader(open(FOUND_CSV, encoding='utf-8'))
            if int(r['n_with_url']) > 0]
    print(f'\n  {len(rows)} files carry reference URLs\n')

    plan, skipped = [], 0
    for r in rows:
        urls = [u for u in r['urls'].split(' | ') if u.strip()]
        if args.max_per_file:
            urls = urls[:args.max_per_file]
        p = ROOTS[r['vault']] + '/' + r['path']
        try:
            text = open(p, encoding='utf-8', errors='replace').read()
        except Exception:
            skipped += 1
            continue
        cur, m = get_sources(text)
        if cur is None:
            print(f'  SKIP no sources: key in {r["path"][:44]}')
            skipped += 1
            continue
        newtext, ok = set_sources(text, urls)
        if not ok:
            skipped += 1
            continue
        plan.append({'vault': r['vault'], 'path': r['path'],
                     'prior_sources': cur, 'adding': len(urls),
                     'after': len(set(map(str.strip, cur + urls))),
                     'abspath': p, 'newtext': newtext})

    tot_add = sum(c['adding'] for c in plan)
    print(f'  would write: {len(plan)} files, {tot_add} URLs added')
    print(f'  skipped: {skipped}')
    if not plan:
        return 1
    if not args.apply:
        print('\n  DRY RUN. Pass --apply to write.')
        return 0

    ts = datetime.datetime.now(datetime.timezone.utc).strftime(
        '%Y%m%dT%H%M%SZ')
    bdir = os.path.join(BACKUP_DIR, ts)
    os.makedirs(bdir, exist_ok=True)
    ok_n = fail = 0
    for c in plan:
        rel = c['vault'] + '__' + c['path'].replace('/', '__')
        try:
            import shutil
            shutil.copy2(c['abspath'], os.path.join(bdir, rel))
            with open(c['abspath'], 'w', encoding='utf-8') as fh:
                fh.write(c['newtext'])
            ok_n += 1
        except Exception as ex:
            print(f'  FAIL {c["path"]}: {ex}')
            fail += 1

    prev = json.load(open(MANIFEST, encoding='utf-8')) \
        if os.path.exists(MANIFEST) else {'writes': []}
    prev['writes'].extend(
        [{k: v for k, v in c.items() if k != 'newtext'} | {'backup': bdir}
         for c in plan])
    with open(MANIFEST, 'w', encoding='utf-8') as fh:
        json.dump(prev, fh, indent=1)

    print(f'\n  written: {ok_n}  failed: {fail}')
    print(f'  backups: {bdir}')
    print('  confidence values UNCHANGED -- attaching a source is not')
    print('  grading it. Phase 5 tiers these once the URLs are in place.')
    return 1 if fail else 0


if __name__ == '__main__':
    sys.exit(main())
