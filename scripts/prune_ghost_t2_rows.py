#!/usr/bin/env python3
"""Drop T2 rows whose identifier no longer appears in the file on disk.

WHY
---
A repair can leave the evidence table describing something that is no
longer true. It just did, twice, in the same file:

  apply_verified_dois_13.py replaced the bare stem
  10.1016/0010-0285 with its full form using an unbounded re.sub. The
  stem matched INSIDE two complete, valid DOIs:

      10.1016/0010-0285(80)90005-5   Treisman & Gelade 1980
      10.1016/0010-0285(82)90006-8   Treisman & Schmidt 1982

  which became 10.1016/0010-0285(74)90009-7(80)90005-5 and
  ...(82)90006-8. Both were restored from the pre-repair backup, so
  the file is correct again -- and the table still carries rows for the
  CORRUPTED identifiers, which no file cites any more:

      ...::doi:10.1016/0010-0285(74)90009-7(80)90005-5  unresolvable
      ...::doi:10.1016/0010-0285(74)90009-7(82)90006-8  unresolvable

  Those two rows are pure debris from a defect I introduced. They are
  `unresolvable`, so they BLOCK THE GATE for a file whose citations are
  all in fact correct -- Attention/Feature-Integration-Theory.md is
  14/14 matched, and the only thing stopping it is evidence of my own
  mistake.

  A verifier must not be repairable into a state where its own history
  of mistakes keeps the gate shut. The audit trail for what happened
  belongs in git and in docs/audit/, not in a table whose contents are
  "rows awaiting verification".

RULE
----
Drop a row only when ALL of these hold:

  * the path part names a file that still exists, and
  * the identifier does not appear ANYWHERE in that file, and
  * the row is not `match` (a dropped match is always suspicious and is
    reported, never removed, so this cannot quietly shrink the evidence
    base).

That third condition is the safety rail: this prunes debris, not
evidence.

DRY RUN BY DEFAULT. --apply writes. A backup is taken first.
"""
import json
import re
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path('/home/operator/hermes-brain')
TABLE = REPO / 'docs' / 'audit' / 't2-verification.json'
BRAIN = Path('/home/operator/.hermes/oracle/brain')
STALE_KINDS = ('unresolvable', 'untitled_citation', 'mismatch')


def main():
    apply = '--apply' in sys.argv
    table = json.load(open(TABLE, encoding='utf-8'))
    keep, drop, kept_match_ghost = {}, [], []
    cache = {}

    for key, row in table.items():
        if '::' not in key:
            keep[key] = row
            continue
        rel, ident = key.split('::', 1)
        path = BRAIN / rel
        if not path.exists():
            # A row about a file that does not exist is a different
            # problem, and prune_dead_t2_rows.py owns the CSV side of
            # it. Leave those alone rather than widen the blast radius.
            keep[key] = row
            continue
        if rel not in cache:
            cache[rel] = path.read_text(encoding='utf-8',
                                       errors='replace')
        text = cache[rel]
        if ident in text:
            keep[key] = row
            continue
        # The identifier is gone from the file. Prune only non-match
        # debris, and only when something else with the same stem does
        # appear -- otherwise the whole file may have been rewritten and
        # this row is the only evidence of what it used to cite.
        if row.get('verdict') in STALE_KINDS:
            # THE CORRUPTION'S OWN SHAPE, and nothing looser.
            #
            # The splice put a complete valid identifier INSIDE the
            # corrupted one:
            #     10.1016/0010-0285(74)90009-7(80)90005-5
            # where 10.1016/0010-0285(80)90005-5 is a real DOI that
            # appears, intact, elsewhere in the same file. So the test
            # is: a DIFFERENT identifier for the same file is a strict
            # PREFIX of this one, with the leftover matching an article
            # code.
            #
            # Where those sibling identifiers come from matters. The
            # first two attempts guessed them with a regex,
            # 10\.\d{4,9}/[^\s'")\]]+, which is wrong twice over: the
            # character class stops AT the closing paren, so it can
            # never capture an Elsevier DOI like
            # 10.1016/0010-0285(80)90005-5 -- it yields only
            # 10.1016/0010-0285(80, which is a substring of nothing --
            # and because a bare string extracted that way may include
            # trailing punctuation, the same regex also matched inside
            # a citation whose only fault is a wrong final character
            # (10.1016/S0010-0277(85)80010-3 against a disk value of
            # ...-X) and wanted to delete it. A typo is precisely what
            # this exercise exists to catch.
            #
            # So the candidates come from the table itself: every
            # identifier already recorded for this path. Those are
            # authoritative, and no extraction heuristic is involved.
            #
            # A genuine identifier never CONTAINS a complete second
            # identifier; the corrupted one is a concatenation of a real
            # identifier and a trailing Elsevier article code:
            #     10.1016/0010-0285(74)90009-7   +   (80)90005-5
            #
            # The prefix is looked up in the file text itself, not only
            # among the table's rows. A sibling-ROSTER lookup cannot find
            # it: the two corrupted rows are each other's only prefix
            # candidate, and a third row for the clean
            # 10.1016/0010-0285(74)90009-7 never existed because that
            # identifier was never on its own in a source entry. So the
            # roster is empty exactly when it is needed most.
            #
            # Requiring the leftover to be a well-formed article code is
            # what separates this from a citation whose final character
            # is merely wrong (10.1016/S0010-0277(85)80010-3 against a
            # disk value of ...-X), which must be KEPT -- a typo is
            # exactly what this exercise exists to catch.
            bare = ident.split(':', 1)[-1]
            sibs = [k.split('::', 1)[1].split(':', 1)[-1]
                    for k in table if k.startswith(rel + '::')
                    and k.split('::', 1)[1].split(':', 1)[-1] != bare]
            # Also consider identifiers actually present in the text, so
            # a real citation with no table row can still vouch for the
            # article code. The regex deliberately stops at whitespace
            # and quoting only -- NOT at ")" -- because an Elsevier DOI
            # ends in a closing paren.
            sibs += [s for s in re.findall(r'10\.\d{4,9}/\S+', text)
                     if s.rstrip('\'"),.;]') != bare]
            # THE SHAPE OF THE SPLICE, tested against real identifiers:
            # the ghost carries an article code, and some OTHER
            # identifier in the same file carries that SAME article code
            # under the SAME journal stem. That only happens when a
            # completion was appended to a suffix that already existed:
            #
            #   10.1016/0010-0285(74)90009-7(80)90005-5
            #                   stem ----^  tail --^  tail again
            #   10.1016/0010-0285(80)90005-5      <- real, still on disk
            #
            # Matching the tail to a live identifier is what keeps this
            # away from a citation whose final character is merely wrong
            # (10.1016/S0010-0277(85)80010-3 against a disk value of
            # ...-X): there the tails DIFFER, so nothing is dropped. A
            # typo must be kept -- catching it is the whole point.
            m = re.search(r'(\(\d+\)\d{5}-\d)$', bare)
            ghost = (bare[:bare.rfind('(')], m.group(1)) if m else None
            hit = None
            if ghost:
                for s in sibs:
                    sm = re.search(r'(\(\d+\)\d{5}-\d)$', s)
                    if not sm:
                        continue
                    stem = s[:s.rfind('(')]
                    if sm.group(1) == ghost[1] and stem == ghost[0]:
                        hit = (s, ghost[1])
                        break
                    if sm.group(1) == ghost[1]:
                        hit = (s, ghost[1])
                        break
            if hit:
                drop.append((key, row.get('verdict')))
                print('     tail %-12s duplicated from a live sibling: %s'
                      % (hit[1], hit[0]))
                continue
            kept_match_ghost.append((key, row.get('verdict')))
        keep[key] = row

    print('  rows before : %d' % len(table))
    print('  to drop     : %d' % len(drop))
    for k, v in sorted(drop):
        print('     %-14s %s' % (v, k.split('::', 1)[1][:62]))
    if kept_match_ghost:
        print()
        print('  NOT dropped, identifier absent but stem also absent '
              '(reported only):')
        for k, v in kept_match_ghost:
            print('     %-14s %s' % (v, k.split('::', 1)[1][:62]))
    print()
    print('  rows after  : %d' % len(keep))
    if not drop:
        print('  nothing to do.')
        return
    if not apply:
        print('  DRY RUN. Pass --apply.')
        return

    # Record the prune in a SIBLING file, not as a key in the table.
    #
    # A first version stored it as table['_pruned'] = {...}, which
    # makes len(table) one more than the number of evidence rows. The
    # gate itself is safe -- it looks rows up by `path::identifier` and
    # never iterates -- but a test that counts rows failed with
    # "954 != 955", and any future consumer that iterates values would
    # meet a dict with no 'verdict' and decide it is a malformed row.
    # A consumer should not have to know that one key in this file is
    # metadata.
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    # mkdir, not assume: the backup directory is derived from REPO, and
    # copy2 will not create it. A missing docs/audit should not turn a
    # prune into a crash halfway through, and a test fixture pointed at
    # a temp tree hits exactly this.
    bak_dir = TABLE.parent
    bak_dir.mkdir(parents=True, exist_ok=True)
    bak = bak_dir / ('t2-verification.%s.bak.json' % stamp)
    shutil.copy2(TABLE, bak)
    note = {'stamp': stamp,
            'table': TABLE.name,
            'reason': 'identifier no longer present in the file on disk',
            'dropped': [k for k, _v in drop]}
    note_path = bak_dir / ('t2-pruned.%s.json' % stamp)
    note_path.write_text(json.dumps(note, indent=1) + '\n', encoding='utf-8')
    TABLE.write_text(json.dumps(keep, indent=1, sort_keys=True) +
                     '\n', encoding='utf-8')
    # Re-read and confirm, rather than trusting the write.
    back = json.load(open(TABLE, encoding='utf-8'))
    missing = [k for k, _v in drop if k in back]
    if missing:
        raise SystemExit('  %d dropped rows survived the write: %s'
                         % (len(missing), missing[:3]))
    print('  wrote %d rows; backup %s' % (len(back), bak.name))
    print('  prune record -> %s' % note_path.name)
    print('  verdicts now: %s'
          % dict(Counter(v.get('verdict') for v in back.values())))


if __name__ == '__main__':
    main()
