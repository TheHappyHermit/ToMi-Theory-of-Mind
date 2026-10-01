#!/usr/bin/env python3
"""
Repair two source entries that a previous titling run corrupted.

WHAT HAPPENED
  In
  research/frontier-research-ontology-llm-reasoning-failures-large-ontology-model-2026-09-03.md
  two frontmatter sources read, on disk:

      - {'arXiv:2608.22974 (OaK': 'Ontology-as-a-Kernel for LLM Agents)'}
      - {'ACL Findings 2026:687 (ORACLE': 'Ontology-Driven Multi-Hop Reasoning)'}

  That is a Python dict REPR, written into the file as text. An earlier
  pass must have had YAML return the entry as a mapping -- a colon in
  an unquoted scalar does exactly that -- and then serialised the dict
  back into the vault instead of leaving it as a string.

WHY IT MATTERS
  `yaml.safe_load` accepts these lines happily, so the file still loads
  and nothing anywhere reports an error. But `sources[3]` and
  `sources[4]` are dicts, so every consumer that expects a string --
  verify_t2_titles, grade_all, the titler itself -- sees an entry it
  cannot read. The two citations are effectively deleted while the file
  looks healthy.

THE REPAIR
  Rebuild each as a plain quoted string. The title is recoverable: it
  is the dict's value. The identifier is the dict's key up to its
  colon. So the reconstruction is mechanical, and it is asserted rather
  than assumed -- a count of 2, and a check that the result parses as
  a string.

  These 2 lines are the only such damage in the vault: a sweep of all
  113 files with untitled citations found no other `- {` source entry.
"""
import json
import shutil
import sys
from pathlib import Path

import yaml

BRAIN = Path('/home/operator/.hermes/oracle/brain')
PATH = ('research/frontier-research-ontology-llm-reasoning-failures-'
        'large-ontology-model-2026-09-03.md')
BACKUP = Path('/home/operator/.hermes/cache/scratch/vault-repair-backup')
KEYS = ['arXiv:2608.22974', 'ACL Findings 2026:687']


def repair_line(ln):
    """Turn one `- {...}` line back into `- "..."`."""
    body = ln.strip()[2:].strip()
    if not (body.startswith('{') and body.endswith('}')):
        return None
    try:
        parsed = eval(body)                            # noqa: S307
    except Exception:                                 # noqa: BLE001
        return None
    if not isinstance(parsed, dict) or len(parsed) != 1:
        return None
    key, title = next(iter(parsed.items()))
    if title not in body:
        return None
    return '%s- "%s (%s)"' % (ln[:len(ln) - len(ln.lstrip())], key, title)


def main():
    apply = '--apply' in sys.argv
    full = BRAIN / PATH
    text = full.read_text(encoding='utf-8')

    lines = text.split('\n')
    fixed, changed = [], 0
    for ln in lines:
        out = repair_line(ln)
        if out is None:
            fixed.append(ln)
            continue
        fixed.append(out)
        changed += 1
        print('  %s' % ('  - "%s..."' % out.strip()[:88]))

    if changed != len(KEYS):
        print('  ABORT: expected %d repairs, made %d' % (len(KEYS),
                                                         changed))
        return 1

    new_text = '\n'.join(fixed)
    end = new_text.find('\n---', 3)
    meta = yaml.safe_load(new_text[3:end]) or {}
    srcs = meta.get('sources')
    if not isinstance(srcs, list):
        print('  ABORT: sources is not a list after repair')
        return 1
    bad = [i for i, s in enumerate(srcs) if not isinstance(s, str)]
    if bad:
        print('  ABORT: sources%s still not strings' % bad)
        return 1
    for k in KEYS:
        if not any(k in s for s in srcs):
            print('  ABORT: %s vanished from sources' % k)
            return 1

    print('  all sources are strings again (%d entries)' % len(srcs))
    if not apply:
        print('  DRY RUN. Pass --apply to write.')
        return 0

    BACKUP.mkdir(parents=True, exist_ok=True)
    dest = BACKUP / ('corrupt-sources__' + PATH.replace('/', '__'))
    shutil.copy2(full, dest)
    full.write_text(new_text, encoding='utf-8')
    print('  wrote %s' % full)
    print('  backup %s' % dest)
    return 0


if __name__ == '__main__':
    sys.exit(main())
