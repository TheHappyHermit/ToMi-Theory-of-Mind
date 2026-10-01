#!/usr/bin/env python3
"""Bring the last 9 non-compliant files up to the gold standard.

Found by auditing all 2,863 files against the schema's REQUIRED keys
(okf_version, id, type, status, description, generated, tags, sources,
confidence). 2,854 already comply. These 9 do not, and they are three
distinct problems rather than one:

  5 with NO frontmatter at all
      - graphify-out/index.md            29 words, an index
      - research/batch244-... .md        1,565 words
      - research/batch245-... .md        1,974 words
      - research/batch246-... .md        1,748 words
      - research/batch247-... .md        3,514 words
    These are recent files. Batches 244-247 were appended to the
    research agenda on 2026-09-28, the same day the generator was last
    run, so they were created after it and never picked up.

  3 missing `generated`
      - active-wiki/research/RESEARCH.md   17,425 words
      - oracle/research/RESEARCH.md
      - oracle/inbox/index.md
    Also missing from inbox/index.md: sources and confidence. And it
    carries `type: Index` with a capital I, which is not in the enum.

  1 missing `id`
      - oracle/Software-Defined-Radio/NO.md
    This one hides a real defect. `id: no` is parsed by YAML as the
    BOOLEAN false, not the string "no" -- YAML 1.1 treats no/yes/on/off
    as booleans. So the key is present in the file and absent in the
    parsed data. Quoting it fixes the parse.

TWO RULES HONOURED
  - Existing content is never deleted. Every value here is derived from
    the file's own body: the title from the H1, the description from
    the first prose line, dates from the Date: line or mtime.
  - sources is left EMPTY for the files that genuinely have none. An
    empty list is compliant. Inventing a URL to fill it would be
    fabricating provenance, which is the one thing this whole project
    exists to prevent.
"""
import datetime
import glob
import os
import re
import shutil
import sys

import yaml

N = chr(10)
REPO = '/home/operator/hermes-brain'
BACKUP = f'{REPO}/archive/fix9_backup'

TARGETS = [
    ('/home/operator/.hermes/oracle/brain/graphify-out/index.md', 'index'),
    ('/home/operator/.hermes/active-wiki/research/RESEARCH.md', None),
    ('/home/operator/.hermes/oracle/brain/research/RESEARCH.md', None),
    ('/home/operator/.hermes/oracle/brain/inbox/index.md', None),
    ('/home/operator/.hermes/oracle/brain/Software-Defined-Radio/NO.md',
     None),
]

# Batch filenames are long, and transcribing them is a bug factory. An
# earlier version of this list hardcoded
#   batch246-...-in-a-column-nobody-filters.md
# when the real file is
#   batch246-...-in-the-column-nobody-filters.md
# and the script cheerfully reported "UNREADABLE ... No such file" for a
# file that plainly exists. These are resolved by glob so a long slug
# can never be mistyped again.
TARGETS += [(p, 'research-report') for p in sorted(glob.glob(
    '/home/operator/.hermes/oracle/brain/research/batch24[4-7]-*.md'))]

TYPES = ('research-report', 'note', 'report', 'reference', 'index',
         'concept', 'entity', 'person', 'decision', 'project', 'system',
         'log', 'lesson', 'idea', 'temporal', 'comparison', 'resource')

H1 = re.compile(r'^#\s+(.+?)\s*$', re.M)
DATE = re.compile(r'\*\*Date:?\*\*\s*(\d{4}-\d{2}-\d{2})')
CREATED = re.compile(r'^\s*created:\s*"?([\dT:-]+Z?)"?\s*$', re.M)


def slug(title):
    s = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    return s[:60] or 'untitled'


def derive(path, body, ftype):
    """Derive the missing values from the file's own content."""
    m = H1.search(body)
    title = m.group(1).strip() if m else os.path.basename(path)[:-3]

    # first prose line that is not a heading, bold label, or list
    desc = ''
    for line in body.split(N):
        s = line.strip()
        if not s or s.startswith(('#', '-', '*', '|', '>')):
            continue
        if re.match(r'^\*\*[A-Za-z ]+:?\*\*', s):
            continue
        desc = re.sub(r'[*`]', '', s)
        break
    if len(desc) > 200:
        desc = desc[:197].rstrip() + '...'
    if not desc:
        desc = title

    d = DATE.search(body)
    date = d.group(1) if d else None
    return title, desc, date


def build_fm(path, body, ftype, existing):
    title, desc, date = derive(path, body, ftype)
    mt = datetime.datetime.fromtimestamp(
        os.path.getmtime(path), datetime.timezone.utc)
    iso = mt.strftime('%Y-%m-%dT%H:%M:%SZ')
    day = date or mt.strftime('%Y-%m-%d')

    m = existing or {}
    ty = m.get('type') or ftype or 'reference'
    if str(ty) not in TYPES:
        ty = 'index' if str(ty).lower() == 'index' else (
            ftype or 'reference')

    def q(s):
        return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"') + '"'

    ident = m.get('id')
    if not ident or ident is False or ident is True:
        # `id: no` parses as the boolean False, which is the whole
        # reason NO.md was flagged. Quote it so it stays a string.
        ident = slug(os.path.basename(path)[:-3])

    tags = m.get('tags') or []
    if not isinstance(tags, list) or not tags:
        tags = [w for w in re.findall(r'[a-z][a-z0-9-]{2,}',
                                      title.lower())[:5] if w] or \
            [str(m.get('type', 'note'))]

    srcs = m.get('sources')
    if not isinstance(srcs, list):
        srcs = []

    lines = [
        '---',
        f'okf_version: {q(m.get("okf_version", "0.2"))}',
        f'id: {q(ident)}',
        f'title: {q(m.get("title") or title)}',
        f'description: {q(desc)}',
        f'type: {ty}',
        f'status: {m.get("status", "active")}',
        f'created: {q(m.get("created") or day)}',
        f'updated: {q(m.get("updated") or day)}',
        f'tags: [{", ".join(tags)}]',
        'sources:',
    ]
    lines += [f'  - {q(u)}' for u in srcs] if srcs else ['  []']
    lines += [
        f'confidence: {m.get("confidence", "ungraded")}',
        'generated:',
        f'  by: {q((m.get("generated") or {}).get("by", "hermes-agent"))}'
        if isinstance(m.get("generated"), dict) else
        '  by: "hermes-agent"',
        f'  at: {q(iso)}',
        '---',
        '',
    ]
    return N.join(lines)


def main():
    dry = '--apply' not in sys.argv
    ts = datetime.datetime.now(datetime.timezone.utc).strftime(
        '%Y%m%dT%H%M%SZ')
    if not dry:
        os.makedirs(f'{BACKUP}/{ts}', exist_ok=True)

    ok = fail = 0
    for path, ftype in TARGETS:
        try:
            raw = open(path, encoding='utf-8', errors='replace').read()
        except Exception as ex:
            print(f'  UNREADABLE {path}: {ex}')
            fail += 1
            continue
        if raw.startswith('---'):
            e = raw.find(N + '---', 3)
            existing = yaml.safe_load(raw[3:e]) or {}
            body = raw[e + 4:]
        else:
            existing = {}
            body = raw
        head = build_fm(path, body, ftype, existing)
        newtext = head + body.lstrip(N)
        # verify before writing
        e = newtext.find(N + '---', 3)
        try:
            chk = yaml.safe_load(newtext[3:e])
        except Exception as ex:
            print(f'  BAD YAML {path}: {ex}')
            fail += 1
            continue
        REQ = ['okf_version', 'id', 'type', 'status', 'description',
               'generated', 'tags', 'sources', 'confidence']
        miss = [k for k in REQ
                if not chk.get(k) and chk.get(k) != []]
        if 'sources' in miss and chk.get('sources') == []:
            miss.remove('sources')
        if miss:
            print(f'  STILL MISSING {os.path.basename(path)}: {miss}')
            fail += 1
            continue
        if dry:
            print(f'  would fix: {os.path.basename(path)[:54]}')
        else:
            shutil.copy2(path, f'{BACKUP}/{ts}/'
                        + os.path.basename(path))
            open(path, 'w', encoding='utf-8').write(newtext)
            print(f'  fixed: {os.path.basename(path)[:54]}')
        ok += 1
    print(f'\n  {"would fix" if dry else "fixed"}: {ok}  failed: {fail}')
    if not dry:
        print(f'  backups: {BACKUP}/{ts}')
    return 1 if fail else 0


if __name__ == '__main__':
    sys.exit(main())
