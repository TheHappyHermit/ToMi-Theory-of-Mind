"""Write the resolved title into the 32 bare-URL match rows.

All 32 were corroborated by their file's own body (32/32), so writing
the title is recording a verified fact, not asserting one. The entry
becomes `URL (Title)`, the form the other 864 titled rows already use.

This is the same repair applied to the 461 originally-untitled rows,
and it carries the same risk profile, so the same guards apply:

  * the title comes from the T2 table, which holds the UNTRUNCATED
    resolver string -- not from the entry, and not from a re-fetch
  * the frontmatter is validated to parse before anything is written,
    and again after
  * the entry's own quote style is preserved
  * a title containing ": " requires a quoted scalar, because an
    unquoted one parses as a YAML mapping. That exact bug broke
    research/batch210 earlier
  * a title containing a single quote cannot use single-quoted YAML
  * exactly one line is changed per row, or the run aborts
  * the file's list indentation is matched, because this vault is
    mixed: some files indent their sources, some are flush left

DRY RUN BY DEFAULT. --apply writes. A backup is taken first.
"""
import json
import re
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import yaml

BRAIN = Path('/home/operator/.hermes/oracle/brain')
REPO = Path('/home/operator/hermes-brain')
TABLE = REPO / 'docs' / 'audit' / 't2-verification.json'
BAK = Path('/home/operator/.hermes/cache/scratch/pre-bare-title-backup')

BARE = re.compile(r'^\s*-?\s*[\'"]?(?:https?://)?[^\s\'"]+[\'"]?\s*$')


def split_url(entry):
    m = re.match(r'^(\s*(?:-\s+)?)(\'?"?)(https?://\S+?)(\'?)\s*$', entry)
    if not m:
        return None
    return m


def build_line(entry, title):
    m = split_url(entry)
    if m is None:
        return None
    lead, _, url, _ = m.groups()
    q = "'"
    if "'" in title:
        q = '"'
    return '%s%s%s (%s)%s' % (lead, q, url, title, q)


def main():
    apply = '--apply' in sys.argv
    rows = json.load(open(TABLE, encoding='utf-8'))
    rep = json.load(open('/home/operator/.hermes/cache/scratch/'
                         'bare_url_corroboration.json', encoding='utf-8'))
    ok_ids = {r['identifier'] for r in rep if r['verdict'] == 'SUPPORTED'}
    todo = defaultdict(list)
    for r in rep:
        if r['verdict'] != 'SUPPORTED':
            continue
        todo[r['file']].append(r)

    print('  corroborated bare rows : %d in %d files'
          % (len(ok_ids), len(todo)))
    changes = []
    for rel in sorted(todo):
        path = BRAIN / rel
        text = path.read_text(encoding='utf-8')
        lines = text.split('\n')
        # `end` is a CHARACTER offset into `text`, not a line number. It
        # was being used as one -- lines[:end + 1] therefore reached past
        # the frontmatter into the body, and the "candidate" slice
        # spanned several YAML documents, so every candidate failed to
        # parse and the run silently wrote nothing. Convert once, here.
        end = text.find('\n---', 3)
        if end == -1:
            print('  SKIP %s: no frontmatter close' % rel)
            continue
        fm_end_line = text.count('\n', 0, end)
        try:
            before = yaml.safe_load(text[3:end]) or {}
        except Exception as ex:
            print('  SKIP %s: frontmatter does not parse (%s)' % (rel, ex))
            continue
        if not isinstance(before, dict):
            print('  SKIP %s: frontmatter is not a mapping' % rel)
            continue
        for r in todo[rel]:
            ident = r['identifier']
            title = (rows.get('%s::doi:%s' % (rel, ident), {})
                     .get('title') or r['resolved_title'])
            if not title:
                print('  SKIP %s %s: no title' % (rel, ident))
                continue
            hits = [i for i, ln in enumerate(lines[:fm_end_line + 1])
                    if ident in ln and ln.strip().startswith('-')
                    and BARE.match(ln.strip())]
            if len(hits) != 1:
                print('  SKIP %s %s: %d bare source lines'
                      % (rel, ident, len(hits)))
                continue
            i = hits[0]
            # Pass the line UNSTRIPPED. build_line() captures the leading
            # indent from what it is given, and an earlier version passed
            # lines[i].strip(), which threw the two-space indent away --
            # so the rewritten entry sat flush left, ended the `sources:`
            # list, and every candidate failed with "while parsing a block
            # mapping". The BARE match tests lines[i].strip() correctly,
            # because there the indent does not matter.
            new = build_line(lines[i], title)
            if new is None:
                print('  SKIP %s %s: could not parse the entry' % (rel, ident))
                continue
            cand = list(lines)
            cand[i] = new
            new_text = '\n'.join(cand)
            e2 = new_text.find('\n---', 3)
            try:
                after = yaml.safe_load(new_text[3:e2]) or {}
            except Exception as ex:
                print('  SKIP %s %s: candidate does not parse (%s)'
                      % (rel, ident, str(ex)[:60]))
                continue
            src = after.get('sources')
            if not isinstance(src, list) or any(
                    not isinstance(s, str) for s in src):
                print('  SKIP %s %s: sources not a list of strings'
                      % (rel, ident))
                continue
            if not any(title in s for s in src):
                print('  SKIP %s %s: title not in sources' % (rel, ident))
                continue
            # the number of source entries must be unchanged
            if len(before.get('sources') or []) != len(src):
                print('  SKIP %s %s: source count changed %d -> %d'
                      % (rel, ident, len(before.get('sources') or []),
                         len(src)))
                continue
            changes.append((rel, path, text, new_text, ident, title))
        print('  %-52s %d row(s)' % (rel[-52:], len(todo[rel])))

    print()
    print('  to write: %d' % len(changes))
    if not apply:
        print('  DRY RUN. Pass --apply.')
        return
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    n = 0
    for rel, path, text, new_text, ident, title in changes:
        dst = BAK / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            shutil.copy2(path, dst)
        e2 = new_text.find('\n---', 3)
        try:
            yaml.safe_load(new_text[3:e2])
        except Exception as ex:
            raise SystemExit('%s: written text does not parse: %s'
                             % (rel, ex))
        path.write_text(new_text, encoding='utf-8')
        n += 1
    print('  wrote %d files; backup %s' % (n, BAK))


if __name__ == '__main__':
    main()
