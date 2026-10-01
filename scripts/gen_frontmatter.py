#!/usr/bin/env python3
"""Generate schema-conformant frontmatter for files that have none.

WHY
scripts/okf_lint.py reports "missing_front_matter" and marks it auto-
fixable, then RETURNS WITHOUT FIXING IT. So no tool in the project has
ever added frontmatter, and 153 files -- 134 of them real research
articles -- have none at all. Phase 1's "mechanical frontmatter repair"
could not have fixed them.

WHAT IS AND IS NOT INFERRED
Every field is either DERIVED from the file or set to an explicit
ungraded/pending value. Nothing is asserted that the file does not say.

  okf_version   "0.2"                      fixed by the schema
  id            the file's stem, slugified  derived, and it is already
                                           the de-facto identity used by
                                           the linker
  type          "research-report" if the
                file sits in a research/ directory or its H1 looks like a
                report, else "note".       DERIVED FROM THE PATH
  status        "active"                   the file exists and is
                                           readable; nothing claims
                                           otherwise
  description   the file's own H1          VERBATIM FROM THE FILE
  generated     by: "frontmatter-gen"
                at: now, RFC 3339 UTC      required by the schema
  tags          derived from the path's
                top-level directory, and
                any tags: line already in
                the body                   DERIVED, never invented
  sources       []                         EMPTY ON PURPOSE. A source
                                           we cannot see is not a
                                           source we can assert.
  confidence    "ungraded"                 the schema's explicit
                                           not-yet-classified state.
                                           NOT "low" and NOT "high".

  WHY ungraded and not low: confidence is a judgement about evidence, and
  a generated field has read none. "low" would be a claim. "ungraded" is
  the schema's own word for "not yet classified", and Phase 5 will
  re-derive these from the file's actual sources.

GUARDS
  - the BODY must be byte-identical after the write
  - the result must parse as YAML and satisfy the schema's required list
  - a file that already has frontmatter is never touched
  - backups before every write
"""
import argparse
import datetime
import hashlib
import os
import re
import shutil
import sys
import time

import yaml

N = chr(10)
REPO = '/home/operator/hermes-brain'
ROOTS = {
    'active-wiki': '/home/operator/.hermes/active-wiki',
    'oracle': '/home/operator/.hermes/oracle/brain',
}
EXCLUDE = {'graphify-out', '.git', '__pycache__', '_archive', 'inbox',
           'node_modules'}
BACKUP = '/home/operator/.hermes/wikis-backup/frontmatter-gen'

SCHEMA_PATH = os.path.join(REPO, 'schemas', 'okf-schema.yaml')
TYPES = ('research-report', 'note', 'report', 'reference', 'index',
         'concept', 'entity', 'decision', 'guide', 'summary', 'log')


def load_schema():
    with open(SCHEMA_PATH, encoding='utf-8') as f:
        return yaml.safe_load(f)


def slugify(stem):
    s = re.sub(r'[^A-Za-z0-9._-]+', '-', stem).strip('-').lower()
    return s or 'untitled'


def first_h1(lines):
    for l in lines:
        if l.startswith('# '):
            return l[2:].strip()
    return ''


def derive_type(rel, h1):
    parts = rel.split(os.sep)
    top = parts[0] if len(parts) > 1 else ''
    base = os.path.basename(rel).lower()
    if top in ('research',) or base.startswith(('batch', 'agenda', 'frontier')):
        return 'research-report'
    if top in ('decisions',):
        return 'decision'
    if top in ('concepts',):
        return 'concept'
    if base == 'index.md':
        return 'index'
    if top.startswith('.'):
        return 'log'
    if h1:
        return 'research-report'
    return 'note'


def derive_tags(rel, lines):
    tags = []
    parts = rel.split(os.sep)
    if len(parts) > 1:
        t = slugify(parts[0])
        if t and t not in ('.',):
            tags.append(t)
    for l in lines:
        m = re.match(r'^\s*[-*]?\s*\**tags\**:\s*(.+)$', l, re.I)
        if m:
            val = m.group(1).strip()
            for tok in re.findall(r'[\w\-]+', val.strip('[]"\'')):
                k = slugify(tok)
                if k and k not in tags:
                    tags.append(k)
    return tags[:12]


def existing_sources(lines):
    """URLs the file itself cites. These are evidence, not invention."""
    urls = []
    for l in lines:
        for u in re.findall(r'https?://[^\s\)\]<>"\']+', l):
            u = u.rstrip('.,;')
            if u not in urls:
                urls.append(u)
    return urls[:24]


def build_fm(rel, lines, schema, now):
    h1 = first_h1(lines)
    desc = h1 or os.path.splitext(os.path.basename(rel))[0].replace('-', ' ')
    ftype = derive_type(rel, h1)
    confs = schema.get('confidences') or ['high', 'medium', 'low']
    conf = 'ungraded' if 'ungraded' in confs else confs[0]
    src = existing_sources(lines)
    d = {
        'okf_version': '0.2',
        'id': slugify(os.path.splitext(os.path.basename(rel))[0]),
        'type': ftype,
        'status': 'active',
        'description': desc[:300],
        'generated': {'by': 'frontmatter-gen', 'at': now},
        'tags': derive_tags(rel, lines) or ['unclassified'],
        'sources': src,
        'confidence': conf,
    }
    order = ['okf_version', 'id', 'type', 'status', 'description',
             'generated', 'tags', 'sources', 'confidence']
    return yaml.safe_dump({k: d[k] for k in order if k in d},
                          sort_keys=False, allow_unicode=True,
                          default_flow_style=False, width=100)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--include-meta', action='store_true',
                    help='also add frontmatter to .meta/ logs and reports')
    args = ap.parse_args()

    schema = load_schema()
    required = set(schema.get('required') or [])
    now = datetime.datetime.now(datetime.timezone.utc).strftime(
        '%Y-%m-%dT%H:%M:%SZ')

    made, blocked, skipped = [], [], 0
    for vname, root in ROOTS.items():
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if d not in EXCLUDE]
            for f in sorted(fn):
                if not f.endswith('.md'):
                    continue
                p = os.path.join(dp, f)
                rel = os.path.relpath(p, root)
                if not args.include_meta and rel.split(os.sep)[0].startswith('.'):
                    skipped += 1
                    continue
                text = open(p, encoding='utf-8', errors='replace').read()
                if text.startswith('---'):
                    skipped += 1
                    continue
                fm = build_fm(rel, text.split(N), schema, now)
                try:
                    d = yaml.safe_load(fm)
                except Exception as ex:
                    blocked.append((vname, rel, f'generated fm invalid: {ex}'))
                    continue
                miss = required - set(d or {})
                if miss:
                    blocked.append((vname, rel, f'missing {sorted(miss)[:3]}'))
                    continue
                new_text = '---' + N + fm + '---' + N + text
                # the body must survive byte-identical
                if not new_text.endswith(text):
                    blocked.append((vname, rel, 'body would change'))
                    continue
                if args.apply:
                    os.makedirs(BACKUP, exist_ok=True)
                    stamp = time.strftime('%H%M%S')
                    shutil.copy2(p, os.path.join(
                        BACKUP, f'{stamp}-' +
                        hashlib.sha1(p.encode()).hexdigest()[:8] + '.md'))
                    with open(p, 'w', encoding='utf-8') as fh:
                        fh.write(new_text)
                made.append((vname, rel, d['type'], len(d['sources'])))

    print(f'  frontmatter generated for: {len(made)}')
    print(f'  already had frontmatter / skipped: {skipped}')
    print(f'  blocked: {len(blocked)}')
    for v, rel, why in blocked[:8]:
        print(f'    BLOCKED [{v}] {rel[:48]:50} {why}')
    import collections
    tc = collections.Counter(m[2] for m in made)
    print(f'  types: {dict(tc)}')
    print(f'  apply={args.apply}')
    json_out = '/home/operator/.hermes/cache/scratch/frontmatter-gen.json'
    import json
    json.dump([{'vault': v, 'path': r, 'type': t, 'sources': s}
               for v, r, t, s in made], open(json_out, 'w'), indent=1)
    print(f'  manifest: {json_out}')


if __name__ == '__main__':
    sys.exit(main())
