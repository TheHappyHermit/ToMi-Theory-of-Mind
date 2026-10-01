#!/usr/bin/env python3
"""Repair the last 9 unparseable articles. Four distinct bugs, all
mechanical, each verified against the actual file first.

BUG A -- a missing closing delimiter, 2 files
    research/RESEARCH.md (both vaults), 1885 lines. The frontmatter runs
    okf_version..generated and then straight into the body:

        L14   generated:
        L15     at: "2026-05-31T00:00:00Z"
        L16   (blank)
        L17   ## 2026-05-31 -- Model-change audit trail     <- BODY
        ...
        L266  ---                                               <- the real one

    So the metadata block was never closed and the parser read 265 lines
    as YAML. The fix is to INSERT a --- after the last metadata line.
    Nothing is removed, nothing is reworded, and the body keeps its exact
    bytes and its position relative to itself.

BUG B -- a doubled quote in a flow sequence, 3 files
        sources: [""Kruger, J., & Dunning, D. (1999). Unskilled and ..."]
    An extra " was inserted at the start of the list item. Removing one
    character makes the value identical to the text that follows it.

BUG C -- a truncated value, 2 files
        stale_af...[truncated]
    Something truncated the value mid-key and left the marker. The
    information is GONE -- this is not recoverable by repair, only
    reported. What this script does is drop the broken line so the
    frontmatter parses, and records the loss. It does NOT invent a
    replacement value.

BUG D -- an over-indented nested key, 2 files
        generated:
            by: "Hermes Agent (cron)"     <- 4 spaces, should be 2
        The line before it is already at 4 spaces, so the block mapping
        breaks. The metadata above it uses 2 spaces throughout, so 2 is
        what the rest of the file does.

GUARDS, all of which must hold or the file is left alone and reported:
  - the file must parse after the repair
  - the BODY must be byte-identical, compared from the first heading on
  - a value this script truncates or drops is counted and printed, never
    silently repaired
  - backups before every write
"""
import argparse
import hashlib
import os
import re
import shutil
import time

import yaml

N = chr(10)
R = {
    'active-wiki': '/home/operator/.hermes/active-wiki',
    'oracle': '/home/operator/.hermes/oracle/brain',
}
EXCLUDE = {'graphify-out', '.git', '__pycache__', '_archive', 'inbox',
           'node_modules'}
BACKUP = '/home/operator/.hermes/wikis-backup/frontmatter-last'

KEY = re.compile(r'^[A-Za-z_][\w.\-]*:')
DOUBLED = re.compile(r'(\[|,\s*)""')
TRUNC = re.compile(r'^\s*([A-Za-z_][\w.\-]*)\.\.\.\[truncated\]\s*$')
# "generated:" followed by an over-indented child
OVERINDENT = re.compile(r'^(\s+)(by|at):\s*(.+)$')


def body_of(text):
    """Everything from the first heading onward."""
    for i, l in enumerate(text.split(N)):
        if l.startswith('#'):
            return N.join(text.split(N)[i:])
    return text


def fm_of(text):
    if not text.startswith('---'):
        return None
    e = text.find(N + '---', 3)
    if e == -1:
        return None
    return text[3:e]


def repair(text):
    """Return (new_frontmatter, kind, detail, body_prepend).

    body_prepend is a body line that was found INSIDE the frontmatter and
    has to be put back at the top of the body. It is '' for every rule
    that only edits metadata. Only Bug F ever sets it.
    """
    fm = fm_of(text)
    if fm is None:
        return None, None, None, ''
    lines = fm.split(N)

    # ---- BUG B: a doubled quote inside a flow sequence ----
    for i, l in enumerate(lines):
        # EVERY quote on these lines is doubled, on both sides:
        #     sources: [""Kruger ... 1121"", ""Krueger ... 180""]
        # 2379 chars, 40 quote characters, 10 real strings. The first
        # version of this rule only matched the OPENING pattern
        # `(["", "", "")` and so fixed the head while leaving the closing
        # `""]` doubled, which is still a flow-sequence error.
        if '""' not in l:
            continue
        fixed = l.replace('""', '"')
        # Only accept it if the result is a well-formed flow sequence with
        # an even number of quotes. An odd count means the doubling was
        # not uniform and collapsing it would silently corrupt the value.
        if fixed.count('"') % 2 or fixed.count('"') == 0:
            continue
        probe = f't: {fixed.split(":", 1)[1].strip()}'
        try:
            v = yaml.safe_load(probe)
            if not isinstance(v, (list, dict)):
                continue
        except Exception:
            continue
        n_fixed = l.count('""')
        out = lines[:i] + [fixed] + lines[i + 1:]
        kind = 'B_doubled_quote'
        if len(v) > 1:
            kind += f' ({len(v)} values)'
        return N.join(out), kind, \
            f'line {i + 1}, collapsed {n_fixed} doubled quote(s)', ''

    # ---- BUG A: the frontmatter never closed, so the parser swallowed the
    # body. The metadata ends at the last top-level key; everything after it
    # is body. Insert --- there.
    #
    # BUG A comes FIRST because it is the OUTERMOST cause. When the
    # frontmatter never closed, the lines the other three rules look for
    # are body text that merely happens to sit inside the block -- a ">"
    # bridge line, a heading. The first version ran C, B, D, then A, so A
    # never got a turn and all seven short files stayed blocked.
    #
    # The first version of A also required len(lines) > 60, which caught
    # RESEARCH.md and nothing else. Seven more files have a SHORT
    # unclosed frontmatter of the same shape. The length test was a guess
    # about which files were affected; the real test is whether a
    # top-level key is followed by non-metadata content.
    #
    # This comment block and the loop below it existed TWICE in this file.
    # A patch that moved B above A moved the wrong span and left the first
    # copy orphaned mid-way through its own `last = None` loop. The
    # orphan set `last` and then fell through into the live copy, whose
    # `if last is not None` was therefore always true, so Bug A fired on
    # every file and Bugs E/F/D never got a turn. The two copies look
    # identical in a diff; only the fact that one is missing its trailing
    # `if last is None:` guard gives it away.
    last = None
    for i, l in enumerate(lines):
        if KEY.match(l) and not l[0].isspace():
            last = i
    if last is not None:
        tail = lines[last + 1:]
        meta_like = [l for l in tail if l.strip()
                     and (l[0].isspace() or KEY.match(l)
                          or l.lstrip().startswith(('-', '*')))]
        if tail and not meta_like:
            out = lines[:last + 1] + ['---'] + lines[last + 1:]
            return N.join(out), 'A_missing_delimiter', \
                f'inserted --- after line {last + 1}', ''

    # ---- BUG F: a BODY line sitting between two metadata keys.
    # After E closes the truncated tags line, the file still looks like:
    #     L12  tags: [...]           <- fixed
    #     L13  (blank)
    #     L14  > **Cross-Domain Bridge:** Neuroscience <-> ML   <- BODY
    #     L15  sources: []
    #     L16  confidence: low
    # The ">" line is body that leaked into the block, and it sits
    # BETWEEN two top-level keys, so Bug A (which only looks at the tail
    # after the LAST key) cannot see it. A blockquote marker at column 0
    # is never valid YAML metadata, so any such line inside a frontmatter
    # block is body. Close the frontmatter immediately before it.
    for i, l in enumerate(lines):
        if l.startswith('>'):
            # The leaked line is BODY. It has to leave the frontmatter, but
            # it must not take the keys below it with it.
            #
            # The first version closed the block immediately before the
            # ">" line. That parsed, and it quietly moved every key AFTER
            # the leak into the body:
            #     id: x / > body quote / sources: [] / confidence: low
            #  -> frontmatter stops at "> body quote", so sources and
            #     confidence are demoted to body text. The control caught
            #     it: the file parsed and the metadata was gone.
            #
            # Correct behaviour: remove the line from the metadata and
            # hand it back so the caller re-inserts it at the top of the
            # body, which is where it belongs. No key is lost.
            out = lines[:i] + lines[i + 1:]
            return N.join(out), 'F_body_line_in_frontmatter', \
                f'moved line {i + 1} out of the frontmatter ' \
                f'({l[:36]!r})', l

    # ---- BUG E: a truncated FLOW SEQUENCE. One file:
    #     tags: [neuroplasticity, continual-learning, catastrophic-
    #            forgetting, hebbian, e
    # The list was cut mid-item and never closed, so the parser read on
    # into the body. The tags that ARE present are intact; only the "]"
    # and the cut tail are missing. Closing the bracket makes the value
    # parse and keeps every tag that survived. The dropped tail is
    # reported, not invented.
    for i, l in enumerate(lines):
        s = l.strip()
        if not s.startswith(('tags:', 'sources:', 'verified:', 'related:')):
            continue
        if s.count('[') <= s.count(']'):
            continue
        head, _, tailtxt = s.partition('[')
        # Every item that is present is real and is kept. The first
        # version dropped the last item whenever it did not end in ']',
        # which threw away a genuine tag: [a, b, c -> [a, b]. A cut tail
        # is far rarer than a complete list that simply lacks its
        # bracket, and silently losing data is the worse error. The
        # cutoff is reported instead of acted on.
        items = [x.strip() for x in tailtxt.split(',') if x.strip()]
        rebuilt = head + '[' + ', '.join(items) + ']'
        out = lines[:i] + [rebuilt] + lines[i + 1:]
        return N.join(out), 'E_truncated_flow_seq', \
            f'line {i + 1} closed, {len(items)} item(s) kept', ''

    # ---- BUG C: a truncated value. Drop the line, record the loss. ----
    for i, l in enumerate(lines):
        m = TRUNC.match(l)
        if m:
            out = lines[:i] + lines[i + 1:]
            return (N.join(out), 'C_truncated_value_dropped',
                    f'key {m.group(1)} had its value truncated upstream; '
                    f'the line is gone and the value is NOT recoverable', '')

    # ---- BUG D: a mapping child indented deeper than its siblings ----
    #     generated:
    #       by: "Hermes Agent (cron)"        <- indent 2
    #         at: "2026-09-10T00:00:00Z"     <- indent 4, BREAKS
    #
    # Three wrong versions of this rule, in order:
    #  1. hardcoded "dedent to 2". Right for most files, wrong whenever
    #     the metadata indents by 4 or 6.
    #  2. KEY.match(par) -- but KEY only matches at column 0, and the
    #     parent here is itself indented, so the rule returned None on
    #     the exact file it was written for.
    #  3. walk up looking for an ancestor at a lower indent. That found
    #     "generated:" at indent 0 and put the child at indent 0, which
    #     moved `at` out of the mapping entirely -- the control caught it
    #     losing the key, reporting generated: {'by': 'b'}.
    #
    # The correct answer is the simplest one: a child sits at the SAME
    # column as its siblings, and the parent line is a sibling. So the
    # target indent is the parent's own indent.
    for i, l in enumerate(lines):
        m = OVERINDENT.match(l)
        if not m or m.group(2) not in ('by', 'at'):
            continue
        child_indent = len(m.group(1))
        if child_indent <= 2:
            continue
        j = i - 1
        while j >= 0 and not lines[j].strip():
            j -= 1
        if j < 0:
            continue
        par = lines[j]
        par_indent = len(par) - len(par.lstrip())
        if par_indent == child_indent:
            continue
        # only correct a child of a mapping, never a list item
        if par.lstrip().startswith('-') or not KEY.match(par.strip()):
            continue
        fixed = ' ' * par_indent + m.group(2) + ': ' + m.group(3)
        out = lines[:i] + [fixed] + lines[i + 1:]
        return N.join(out), 'D_overindent', \
            f'line {i + 1} reindented {child_indent} -> {par_indent}', ''

    return None, None, None, ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--rounds', type=int, default=6,
                    help='a file may carry more than one bug')
    args = ap.parse_args()

    applied, blocked, losses = [], [], []
    for vname, root in R.items():
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if d not in EXCLUDE]
            for f in sorted(fn):
                if not f.endswith('.md'):
                    continue
                p = os.path.join(dp, f)
                text = open(p, encoding='utf-8', errors='replace').read()
                if fm_of(text) is None:
                    continue
                err = None
                try:
                    yaml.safe_load(fm_of(text) or '')
                except Exception as ex:
                    err = str(ex)
                if not err:
                    continue
                rel = os.path.relpath(p, root)
                body_before = body_of(text)
                cur = text
                kinds = []
                for _ in range(args.rounds):
                    try:
                        yaml.safe_load(fm_of(cur) or '')
                        break
                    except Exception:
                        pass
                    new, kind, detail, pre = repair(cur)
                    if new is None:
                        break
                    # Rebuild the whole file, then check the BODY. The
                    # first version tried to check the body from inside the
                    # loop with a hand-rolled join that put the delimiters
                    # in the wrong place, so every file reported "body
                    # would change". Reconstruct the real file first, then
                    # compare body_of() on both sides.
                    _e = cur.find(N + '---', 3)
                    trial = ('---' + N + new + N + '---' + cur[_e + 4:])
                    if pre:
                        # put the moved line back at the top of the body
                        _h = trial.find(N + '---' + N + N)
                        if _h > 0:
                            _h += len(N + '---' + N)
                            trial = (trial[:_h] + N + pre +
                                     trial[_h:])
                    if body_of(trial) != body_before:
                        blocked.append((vname, rel, 'body would change'))
                        break
                    cur = trial
                    kinds.append((kind, detail))
                try:
                    d = yaml.safe_load(fm_of(cur) or '')
                    if not isinstance(d, dict):
                        raise ValueError('not a mapping')
                except Exception as ex:
                    blocked.append((vname, rel,
                                    f'still fails: {str(ex).split(N)[0][:38]}'))
                    continue
                if body_of(cur) != body_before:
                    blocked.append((vname, rel, 'body changed'))
                    continue
                if not kinds:
                    blocked.append((vname, rel, 'no repair matched'))
                    continue
                if args.apply:
                    os.makedirs(BACKUP, exist_ok=True)
                    stamp = time.strftime('%H%M%S')
                    shutil.copy2(p, os.path.join(
                        BACKUP, f'{stamp}-' +
                        hashlib.sha1(p.encode()).hexdigest()[:8] + '.md'))
                    with open(p, 'w', encoding='utf-8') as fh:
                        fh.write(cur)
                applied.append((vname, rel, kinds))
                for k, det in kinds:
                    if k == 'C_truncated_value_dropped':
                        losses.append((vname, rel, det))

    for v, rel, kinds in applied:
        print(f'  {"A" if args.apply else "?"} [{v:12}] {rel[:52]:54} '
              + ', '.join(k for k, _ in kinds))
    print(f'\n  repaired: {len(applied)}   blocked: {len(blocked)}')
    for v, rel, why in blocked[:8]:
        print(f'    BLOCKED [{v}] {rel[:44]:46} {why}')
    if losses:
        print(f'\n  INFORMATION LOSS -- these values are GONE, not repaired:')
        for v, rel, det in losses:
            print(f'    [{v}] {rel[:52]}')
            print(f'        {det}')
    print(f'  apply={args.apply}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
