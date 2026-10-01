"""Title 7 source entries that re-derivation exposed as untitled.

Re-deriving the 26 corroborated bare-URL rows invalidated 27 keys, and
the verifier then walked rows it had previously served from cache. Seven
came back `untitled_citation` that had been sitting behind a cached
`match`:

  research/batch264-the-verdict-nobody-reads.md   4 entries, lines 12-15
  research/batch276-...                          1 entry
  research/batch275-... (it-speaks-a-language)   2 entries

None of them is among the 26 this pass wrote -- verified directly
against the corroboration list. They are the SAME defect as the 461
originally-untitled rows: a source line carrying a bare identifier in a
file whose every other source line carries `URL (Title)`. batch264 is
the clearest case, because its own body cites all four papers with full
titles and even marks them "Crossref-verified by me this run":

  10.1109/PROC.1975.9939        MacKenzie (1975), mediation
  10.1109/TDSC.2004.2           Laprie, Randell & Landwehr (2004)
  10.1609/aaai.v32i1.11797      Topcu et al. (2018), AAAI 32(1)
  10.1371/journal.pone.0110274  Salas-Boni et al. (2014), PLoS ONE 9(10)

The titles come from the resolver, not from the body, so the two
independently corroborate each other. Same guards as the 461 pass: the
candidate must parse, the source count must not change, the entry's
quote style and indent are preserved, and a title containing ": "
forces a quoted scalar.

DRY RUN BY DEFAULT. --apply writes.
"""
import json
import re
import shutil
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

BRAIN = Path('/home/operator/.hermes/oracle/brain')
TABLE = Path('/home/operator/hermes-brain/docs/audit/t2-verification.json')
BAK = Path('/home/operator/.hermes/cache/scratch/pre-revealed-title-backup')
UA = {'User-Agent': 'hermes-brain-t2/1.0 (citation verification)'}

TARGETS = {
    'research/batch264-the-verdict-nobody-reads.md': [
        '10.1109/PROC.1975.9939', '10.1109/TDSC.2004.2',
        '10.1609/aaai.v32i1.11797', '10.1371/journal.pone.0110274'],
}
# The two research/ files whose arXiv entries have no https:// URL.
# The arXiv entries are cited as a BARE "arXiv:NNNN.NNNNN" with no URL
# at all -- '- arXiv:2512.24722' and '- "arXiv:2509.14347"'. The first
# version of this gate keyed on the DataCite form
# 10.48550/arXiv.NNNNN.NNNNN, which appears in one file's BODY but not in
# any frontmatter source line, so all three were skipped silently.
ARXIV_TARGETS = {'2512.24722', '2509.14347', '2609.26836'}


def crossref(doi):
    url = 'https://api.crossref.org/works/' + urllib.request.quote(doi, '')
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        m = json.loads(r.read().decode('utf-8'))['message']
    t = m.get('title')
    t = t[0] if isinstance(t, list) and t else t
    return re.sub(r'\s+', ' ', str(t)).strip()


def arxiv_title(aid):
    url = 'http://export.arxiv.org/api/query?id_list=' + aid
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        body = r.read().decode('utf-8')
    m = re.search(r'<entry>.*?<title>(.*?)</title>', body, re.S)
    return re.sub(r'\s+', ' ', m.group(1)).strip() if m else None


def build(line, url, title):
    m = re.match(r'^(\s*(?:-\s+)?)(\'?"?)', line)
    lead, _q = m.group(1), m.group(2)
    q = "'" if "'" not in title else '"'
    return '%s%s%s (%s)%s' % (lead, q, url, title, q)


def main():
    apply = '--apply' in sys.argv
    table = json.load(open(TABLE, encoding='utf-8'))
    changes = []

    for rel, idents in sorted(TARGETS.items()):
        path = BRAIN / rel
        if not path.exists():
            print('  MISSING %s' % rel)
            continue
        text = path.read_text(encoding='utf-8')
        lines = text.split('\n')
        end = text.find('\n---', 3)
        if end == -1:
            print('  SKIP %s: no frontmatter' % rel)
            continue
        before = yaml.safe_load(text[3:end]) or {}
        base = text
        accepted = []
        for ident in idents:
            try:
                title = crossref(ident)
            except Exception as ex:
                print('  SKIP %s: %s' % (ident, str(ex)[:50]))
                continue
            # Work against `base` -- the file as it stands AFTER the
            # previous accepted edit -- not against the snapshot read
            # before the loop. Building every candidate from the stale
            # original meant each write discarded the previous ones: in
            # batch264 four rows were reported written and only the last
            # survived, so three edits the script claimed were never on
            # disk. And every title accepted so far must still be
            # present in the running candidate, or an earlier edit has
            # been lost.
            blines = base.split(chr(10))
            bend = base.find(chr(10)+'---', 3)
            if bend == -1:
                print('  SKIP %s: candidate lost its frontmatter' % ident)
                continue
            hits = [n for n, ln in enumerate(blines[:bend])
                    if ident in ln and ln.strip().startswith('-')]
            if len(hits) != 1:
                print('  SKIP %s: %d source lines in the running candidate'
                      % (ident, len(hits)))
                continue
            i = hits[0]
            m = re.search(r"""(https?://\S+?)(?:'|")?\s*$""",
                          blines[i].strip())
            url = m.group(1) if m else 'https://doi.org/' + ident
            new = build(blines[i], url, title)
            if new is None:
                print('  SKIP %s: could not build the entry' % ident)
                continue
            cand = list(blines)
            cand[i] = new
            nt = chr(10).join(cand)
            e2 = nt.find(chr(10)+'---', 3)
            try:
                after = yaml.safe_load(nt[3:e2]) or {}
            except Exception as ex:
                print('  SKIP %s: does not parse (%s)' % (ident, str(ex)[:50]))
                continue
            src = after.get('sources')
            if not isinstance(src, list) or any(
                    not isinstance(s, str) for s in src):
                print('  SKIP %s: sources not a string list' % ident)
                continue
            if len(before.get('sources') or []) != len(src):
                print('  SKIP %s: source count changed' % ident)
                continue
            if not any(title in s for s in src):
                print('  SKIP %s: title not in sources' % ident)
                continue
            lost = [t for t in accepted if not any(t in s for s in src)]
            if lost:
                print('  SKIP %s: an earlier edit was lost (%r)'
                      % (ident, lost[0][:40]))
                continue
            base = nt
            accepted.append(title)
            changes.append((rel, path, nt, nt, ident, title))
            print('  %-34s -> %s' % (ident, title[:62]))

    # the arXiv entries, found by table key rather than a hardcoded path
    for key, row in sorted(table.items()):
        if row.get('verdict') != 'untitled_citation':
            continue
        if '::' not in key:
            continue
        rel, ident = key.split('::', 1)
        # The KIND is the first field of the identifier, not the start
        # of the key: the key is `path::arxiv:2512.24722`, so testing
        # key.startswith('arxiv:') never matches and the whole arXiv
        # branch ran zero times without a word of complaint.
        if not ident.startswith('arxiv:'):
            continue
        bare = ident.split(':', 1)[-1]
        if bare not in ARXIV_TARGETS:
            continue
        path = BRAIN / rel
        if not path.exists():
            continue
        try:
            title = arxiv_title(bare)
        except Exception as ex:
            print('  SKIP arXiv %s: %s' % (bare, str(ex)[:44]))
            continue
        if not title:
            print('  SKIP arXiv %s: no title returned' % bare)
            continue
        text = path.read_text(encoding='utf-8')
        lines = text.split('\n')
        end = text.find('\n---', 3)
        if end == -1:
            continue
        before = yaml.safe_load(text[3:end]) or {}
        hits = [i for i, ln in enumerate(lines[:end])
                if bare in ln and ln.strip().startswith('-')]
        if len(hits) != 1:
            print('  SKIP arXiv %s: %d source lines' % (bare, len(hits)))
            continue
        i = hits[0]
        url = 'https://arxiv.org/abs/' + bare
        new = build(lines[i], url, title)
        cand = list(lines)
        cand[i] = new
        nt = '\n'.join(cand)
        e2 = nt.find('\n---', 3)
        try:
            after = yaml.safe_load(nt[3:e2]) or {}
        except Exception as ex:
            print('  SKIP arXiv %s: does not parse (%s)' % (bare,
                                                           str(ex)[:50]))
            continue
        src = after.get('sources')
        if not isinstance(src, list) or len(before.get('sources') or []) \
                != len(src):
            print('  SKIP arXiv %s: sources unusable' % bare)
            continue
        changes.append((rel, path, text, nt, bare, title))
        print('  arXiv %-28s -> %s' % (bare, title[:62]))

    print()
    print('  to write: %d' % len(changes))
    if not apply:
        print('  DRY RUN. Pass --apply.')
        return
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    n = 0
    for rel, path, text, nt, ident, title in changes:
        dst = BAK / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            shutil.copy2(path, dst)
        e2 = nt.find('\n---', 3)
        try:
            yaml.safe_load(nt[3:e2])
        except Exception as ex:
            raise SystemExit('%s: written text does not parse: %s'
                             % (rel, ex))
        path.write_text(nt, encoding='utf-8')
        n += 1
    print('  wrote %d files; backup %s' % (n, BAK))


if __name__ == '__main__':
    main()
