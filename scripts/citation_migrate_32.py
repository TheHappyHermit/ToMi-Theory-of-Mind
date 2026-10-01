#!/usr/bin/env python3
"""Phase 3.2 -- apply the three citation fixes that can be PROVEN.

Three distinct shapes, each with a different correct action:

  A. KEYED FOOTNOTE   a real reference list exists. Replace the body
                      [[N]] marker with [^key] and replace the list line
                      with a [^key]: definition, keyed from the reference's
                      own text. Only markers that HAVE a definition move;
                      an undefined number is left alone and reported.

  B. INLINE LINK      [[N]](url) is a dead label on a link that already
                      states its source. Drop the number, keep the link.
                      No footnote, because the source is already inline.

  C. FM-INDEXED       [[N]] indexes frontmatter sources[N-1] and there is
                      no body list at all. The reference text IS the
                      frontmatter entry, so the footnote definition is
                      generated from it and the marker is keyed to it.
                      Guarded by max(N) <= len(sources), and by requiring
                      the frontmatter source to be a bare string or a
                      mapping, never a guess.

What this NEVER does:
  - touch a marker with no definition it can point at
  - invent a reference
  - create a page
  - touch a number above 100, because those are page numbers in a
    generated index, not citations
  - touch frontmatter sources; the frontmatter is left byte-identical
    except where a source needs a stable id for the footnote to join to

Every write is preceded by a body-preservation gate: after the transform,
stripping markers, footnote definitions and reference lines must reproduce
the original prose exactly.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import citation_refs as cr          # noqa: E402
import yaml                        # noqa: E402

ROOTS = {
    'active-wiki': '/home/operator/.hermes/active-wiki',
    'oracle': '/home/operator/.hermes/oracle/brain',
}
BACKUP = '/home/operator/.hermes/wikis-backup/citation-3.2'
MARKER = cr.MARKER
# Numbers at or above this are page numbers in generated indexes.
PAGE_NUMBER_FLOOR = 100


def split_fm(text):
    """Return (frontmatter, body).

    IMPORTANT: the frontmatter is returned WITHOUT the '---' delimiters,
    because the writer reconstructs the file as
        '---\\n' + fm + '\\n---' + body
    and returning them here silently produced files that started with
    "\\nokf_version:" -- no opening delimiter, unparseable as YAML, and
    invisible to any checker that assumed well-formed input. Ten files were
    written that way before a verifier that diffed the bytes caught it.
    """
    if not text.startswith('---'):
        return None, text
    end = text.find('\n---', 3)
    if end == -1:
        return None, text
    return text[3:end], text[end + 4:]


def is_pagenum(n):
    return n >= PAGE_NUMBER_FLOOR


def _source_text(s):
    """Readable text for one frontmatter source entry.

    These files are inconsistent: some sources are bare URL strings, some
    are mappings, and some are single-key mappings whose KEY is the paper
    name and whose VALUE is the detail ("GrOIL: Graph-Grounded ...").
    Reading only .get('title') silently produced '' for the third shape
    and the file was then reported as unrepairable.
    """
    if isinstance(s, str):
        return s
    if isinstance(s, dict):
        for f in ('title', 'url', 'doi', 'note', 'description'):
            v = s.get(f)
            if isinstance(v, str) and v.strip():
                return v.strip()
        for k, v in s.items():
            if isinstance(v, str) and v.strip():
                return f'{k}: {v.strip()}'
        return ''
    return str(s) if s else ''


def key_for(reftext, used):
    """A stable key, de-duplicated so two references never collide."""
    base = cr.key_for(reftext)
    k, i = base, 2
    while k in used:
        k = f'{base}-{i}'
        i += 1
    used.add(k)
    return k


def plan_text(text, rel=''):
    """plan_file() on a string. Needed to re-plan from a backup when the
    file on disk has already been transformed."""
    fm_raw, body = split_fm(text)
    return _plan(fm_raw, body)


def plan_file(path, rel):
    """Return (kind, detail) with no writes. The decision record."""
    text = open(path, encoding='utf-8', errors='replace').read()
    fm_raw, body = split_fm(text)
    return _plan(fm_raw, body)


def _plan(fm_raw, body):
    markers = [int(x) for x in MARKER.findall(body)]
    if not markers:
        return None, None

    refs = cr.ref_entries(body)
    if refs:
        used = set()
        # key per definition number, so the body and the definition agree
        keys = {n: key_for(t, used) for n, t in sorted(refs.items())}
        undefined = sorted({n for n in markers if n not in refs})
        return 'KEYED', {
            'refs': len(refs), 'markers': len(markers),
            'keys': keys, 'undefined': undefined,
        }

    inline = cr.inline_link_markers(body)
    if inline:
        return 'INLINE', {'count': len(inline)}

    if fm_raw:
        try:
            d = yaml.safe_load(fm_raw) or {}
        except Exception:
            return 'FM_UNPARSEABLE', None
        src = d.get('sources') or []
        # A single marker above the floor is not a reason to abandon the
        # other 31: an earlier version vetoed whole files for this, and
        # Hierarchical-Temporal-Memory.md has 32 markers of which exactly
        # one ([[339]], a report number) is a page number.
        low = [n for n in markers if not is_pagenum(n)]
        pagenums = sorted({n for n in markers if is_pagenum(n)})
        if low and src and max(low) <= len(src):
            used = set()
            keys = {}
            for n in sorted(set(low)):
                txt = _source_text(src[n - 1])
                if not txt:
                    return 'FM_NO_TEXT', {'n': n, 'raw': str(src[n - 1])[:70]}
                keys[n] = key_for(txt, used)
            return 'FMIDX', {'markers': len(low), 'keys': keys,
                             'sources': len(src), 'pagenums': pagenums}
        return 'FM_SHORT', {'max': max(low) if low else max(markers),
                            'sources': len(src), 'pagenums': pagenums}
    if all(is_pagenum(n) for n in markers):
        return 'PAGENUM', {'high': sorted({n for n in markers})[:8]}
    return 'NO_FM', None


def apply_keyed(body, keys, refs):
    """Replace markers with [^key] and rewrite the list lines as definitions."""
    out_lines = []
    in_list = False
    used_defs = set()
    for l in body.split('\n'):
        if cr.LIST_HEADINGS.match(l):
            in_list = True
            out_lines.append(l)
            continue
        if in_list and re.match(r'^#{1,4}\s', l):
            in_list = False
        if in_list:
            hit = cr._match_line(l)
            if hit:
                n, txt = hit
                if n in keys:
                    out_lines.append(f'[^{keys[n]}]: {txt}')
                    used_defs.add(keys[n])
                    continue
        out_lines.append(l)
    text = '\n'.join(out_lines)

    def sub(mo):
        n = int(mo.group(1))
        return f'[^{keys[n]}]' if n in keys else mo.group(0)

    text = MARKER.sub(sub, text)
    return text, used_defs


def apply_inline(body):
    """Drop the dead number, keep the link."""
    def sub(mo):
        open_b, url, close_b = mo.group(2), mo.group(3), mo.group(4)
        return f'({open_b}{url}{close_b})'
    return cr.INLINE_LINK.sub(sub, body), None


def apply_fmidx(body, keys, src):
    """Key the markers and APPEND the definitions they point at.

    Appending rather than rewriting in place matters: the reference text
    lives in the frontmatter, which must stay byte-identical, so the
    footnote definitions are emitted at the end of the body under a
    heading that did not previously exist.
    """
    def sub(mo):
        n = int(mo.group(1))
        return f'[^{keys[n]}]' if n in keys else mo.group(0)

    text = MARKER.sub(sub, body)
    defs = []
    for n in sorted(keys):
        defs.append(f'[^{keys[n]}]: {_source_text(src[n - 1])}')
    if defs:
        block = '\n\n## Sources\n\n' + '\n'.join(defs) + '\n'
        text = text.rstrip('\n') + block
    return text, set(keys.values())


def body_gate(orig_body, new_body, kind):
    """The prose must be unchanged once citation syntax is removed.

    Removing markers/definitions from both sides and comparing catches a
    transform that ate a line of knowledge. It cannot catch a transform
    that deletes prose AND adds a matching definition, so this is a real
    check and not a formality.
    """
    def strip(t):
        # Both citation syntaxes are replaced by NOTHING, so the two sides
        # differ by whatever whitespace surrounded them. Normalizing
        # whitespace to a single space is the whole job, and the only
        # reliable way to do it is to remove the syntax, collapse runs of
        # space, and then fix the seams.
        #
        # Three wrong versions came first, all caught by
        # verify_body_gate.py:
        #   bare MARKER.sub left a leading space on list lines
        #   line-anchored-only left in-text markers untouched
        #   greedy \\s* around the marker ate the space BEFORE it
        # The pattern below removes the marker and any space on either
        # side, then the final pass re-inserts a single space at seams so
        # "finding [[1]] holds" and "finding [^k] holds" compare equal.
        # Replace with nothing rather than a space at the START of a line,
        # and with a space in the middle, then trim:
        #   line-leading marker  "[[5]] text"  -> "text"
        #   in-text marker       "a [[1]] b"  -> "a  b" -> "a b"
        # That split is what makes both sides normalize identically.
        t = re.sub(r'^\s*\[\[\d{1,3}\]\]\s*', '', t, flags=re.M)
        t = re.sub(r'\s*\[\[\d{1,3}\]\]\s*', ' ', t)
        t = re.sub(r'^ +', '', t, flags=re.M)
        t = re.sub(r'^\s*\[([0-9]{1,3})\]:\s*', '', t, flags=re.M)
        # A new footnote definition: "[^key]: text". This strip MUST run
        # before the footnote-USE strip below. Ordered the other way, the
        # use strip consumes "[^key]" first and the definition is left as a
        # bare ": text" that no later pattern can clean up, so the gate
        # reports a one-character difference on every correctly-migrated
        # file. The first version of this function had that order wrong.
        t = re.sub(r'^\s*\[\^[^\]]+\]:\s*', '', t, flags=re.M)
        t = re.sub(r'\s*\[\^[^\]]+\]\s*', ' ', t)
        # An OLD reference line, all five syntaxes.
        #
        # These patterns must match ONLY the OLD numeric forms. An earlier
        # version used a permissive marker class, "\\[\\^?[\\w-]*\\]?\\]?",
        # to catch "**[1]**" in one pattern. That class ALSO matches the NEW
        # "[^key]:" definition, so the new side was left with a stray ":"
        # and the gate reported a one-character difference on files the
        # transform had handled correctly. The gate was right to complain;
        # the pattern was wrong. Each form now gets its own literal class.
        for pat in (
            r'^\s*[-*]\s*\*\*\[\d+\]\*\*\s*[:]?\s*',   # - **[1]** x
            r'^\s*\*\*\[\d+\]\*\*\s*[:]?\s*',           # **[1]** x
            r'^\s*[-*]\s*\*\*\[\[\d+\]\]\*\*\s*[:]?\s*',  # - **[[1]]** x
            r'^\s*[-*]\s*\[\[\d+\]\]\s*[:]?\s*',          # - [[1]] x
            r'^\s*[-*]\s*\[\d+\]\s*[:]?\s*',              # - [1] x
            r'^\s*[-*]\s*\d+[.)]\s*[:]?\s*',              # - 1. x
            r'^\s*\[\[\d+\]\]\s*[:]?\s*',                  # [[1]] x
            r'^\s*\[\d+\]\s*[:]?\s*',                      # [1] x
            r'^\s*\d+[.)]\s*[:]?\s*',                      # 1. x
        ):
            t = re.sub(pat, '', t, flags=re.M)
        return re.sub(r'[ \t]+', ' ', '\n'.join(
            l.rstrip() for l in t.split('\n') if l.strip()))

    a, b = strip(orig_body), strip(new_body)
    if a == b:
        return True, None
    # report the first differing line for diagnosis
    al, bl = a.split('\n'), b.split('\n')
    for i, (x, y) in enumerate(zip(al, bl)):
        if x != y:
            return False, f'line {i}: {x[:70]!r} != {y[:70]!r}'
    return False, f'length {len(al)} vs {len(bl)}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--queue', default='/home/operator/.hermes/cache/scratch/phase3-judgement-queue.json')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--only-kind', default=None)
    args = ap.parse_args()

    q = json.load(open(args.queue))
    seen, results = set(), []
    for e in q:
        if e['path'] in seen:
            continue
        seen.add(e['path'])
        path = os.path.join(ROOTS[e['vault']], e['path'])
        if not os.path.isfile(path):
            continue
        kind, detail = plan_file(path, e['path'])
        results.append({'vault': e['vault'], 'path': e['path'],
                        'markers': e['markers'], 'kind': kind,
                        'detail': {k: v for k, v in (detail or {}).items()
                                   if k != 'keys'}})
        if not args.apply or kind in (None, 'PAGENUM') or not detail:
            continue
        if args.only_kind and kind != args.only_kind:
            continue
        if kind not in ('KEYED', 'INLINE', 'FMIDX'):
            continue

        text = open(path, encoding='utf-8', errors='replace').read()
        fm_raw, body = split_fm(text)
        if kind == 'KEYED':
            new_body, defs = apply_keyed(body, detail['keys'], detail.get('refs'))
        elif kind == 'INLINE':
            new_body, defs = apply_inline(body)
        else:
            import yaml as _y
            _src = (_y.safe_load(fm_raw or "") or {}).get('sources') or []
            new_body, defs = apply_fmidx(body, detail['keys'], _src)

        ok, why = body_gate(body, new_body, kind)
        if not ok:
            results[-1]['blocked'] = f'body gate: {why}'
            continue
        if new_body == body:
            results[-1]['skipped'] = 'no change'
            continue

        os.makedirs(BACKUP, exist_ok=True)
        stamp = time.strftime('%H%M%S')
        shutil.copy2(path, os.path.join(
            BACKUP, f'{stamp}-' +
            hashlib.sha1(e['path'].encode()).hexdigest()[:8] + '.md'))
        with open(path, 'w', encoding='utf-8') as f:
            # The delimiters are explicit here on purpose. split_fm returns
            # the frontmatter WITHOUT them, so reconstructing the file is
            # this line's job and nothing else's.
            f.write('---\n' + (fm_raw or '').strip('\n') + '\n---' + new_body)
        results[-1]['written'] = True
        if defs:
            results[-1]['defs'] = len(defs)

    for r in results:
        if r['kind'] is None:
            # Fully migrated: no markers left, so there is nothing to plan.
            flag = 'CLEAN' if r.get('written') else 'CLEAN'
            print(f'  {flag:>10}  {r["markers"] or 0:>4}mk  {"-":<14} '
                  f'{r["path"][:52]}')
            if r.get('detail') and len(r['detail']) < 4:
                print(f'             {r["detail"]}')
            if r.get('blocked'):
                print(f'             {r["blocked"][:80]}')
            continue
        flag = ('WROTE' if r.get('written') else
                r.get('blocked', r.get('skipped', r['kind'])))
        print(f'  {flag:>10}  {r["markers"]:>4}mk  {r["kind"]:<14} '
              f'{r["path"][:52]}')
        if r.get('detail') and len(r['detail']) < 4:
            print(f'             {r["detail"]}')
        if r.get('blocked'):
            print(f'             {r["blocked"][:80]}')

    tally = {}
    for r in results:
        tally[r['kind']] = tally.get(r['kind'], 0) + 1
    print(f'\n  {len(results)} distinct files: {tally}')
    wrote = sum(1 for r in results if r.get('written'))
    print(f'  written: {wrote}   apply={args.apply}')
    json.dump(results, open(
        '/home/operator/.hermes/cache/scratch/phase3.2-results.json', 'w'),
        indent=1)


if __name__ == '__main__':
    main()
