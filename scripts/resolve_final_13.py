"""Resolve the last 13 non-matching rows, one decision per row.

Each was read individually against the file's own subject line and
the resolver's authoritative title. The 13 split into five kinds, and
the kind decides the repair:

  BARE            the source entry is a URL with no title text at all
                  ("- \\"https://doi.org/10.1126/science.1069590\\"").
                  Four of the five DOI repairs made earlier left their
                  entry bare, because replacing the identifier does not
                  add a title. The fix is to write the authoritative
                  title into the entry.

  ABBREVIATION    the vault names the paper in shortened form --
                  "PICCO Framework: Five-Element Prompt Taxonomy" for
                  "The PICCO Framework for Large Language Model
                  Prompting: A Taxonomy and Reference Architecture for
                  Prompt Engineering". Same paper, so write the real
                  title.

  ACRONYM+INITIALS "Indyk & Motwani 1998 LSH" for "Approximate nearest
                  neighbors". An author-and-year label, not a title.

  GLUED TAG       "schema-minerpro" for a title whose Crossref form is
                  "<scp>schema-miner</scp> pro: ...". Scored 0.75 as
                  written and 1.0 with the space restored; verified
                  directly rather than assumed.

  IN-TEXT NAME    two rows where the sources entry carries a nickname
                  and the real title is already in the file's numbered
                  reference list.

doi:10.1142/10269 is handled separately. It resolves to "Real Options
in Energy and Commodity Markets", a finance paper with no relationship
to neuromorphic computing, so titling it would be worse than leaving
it: the entry is excluded pending a decision about what the file
actually meant to cite.
"""
import json
import re
import shutil
import sys
from pathlib import Path

BRAIN = Path('/home/operator/.hermes/oracle/brain')
BACKUP = Path('/home/operator/.hermes/cache/scratch/pre-final13-backup')
EVIDENCE = Path('/home/operator/hermes-brain/docs/audit/'
                't2-final-13.json')

# (path, identifier, kind, title)
DECISIONS = [
    ('Consolidation/Adaptive-Forgetting.md',
     '10.1038/35066572', 'bare',
     'Suppressing unwanted memories by executive control'),
    ('Executive-Control/Dual-Process-Theories.md',
     '10.1016/j.neuron.2011.02.027', 'bare',
     "Model-Based Influences on Humans' Choices and Striatal "
     'Prediction Errors'),
    ('Neuroplasticity/Skill-Myelination-Hardware-Acceleration-Paths.md',
     '10.1073/pnas.1916646117', 'bare',
     'Activity-dependent myelination: A glial mechanism of '
     'oscillatory self-organization in late adult life'),
    ('Neuroscience/Corollary-Discharge-Efference-Copy-Agency.md',
     '10.1126/science.1069590', 'bare',
     'A Pathway in Primate Brain for Internal Monitoring of Movements'),
    ('research/batch210-the-evidence-check-verifies-existence-not-support.md',
     '10.1037/0278-7393.19.4.851', 'bare',
     'The cue-familiarity heuristic in metacognition'),
    ('research/frontier-research-ontology-worlddb-goi-alignment-2026-09-03.md',
     '10.1177/22104968261431521', 'glued_tag',
     'schema-miner pro: Agentic AI for Ontology Grounding Over '
     'Heterogeneous Enterprise Data'),
    ('research/frontier-research-taxonomy-2027-supplement-v2.md',
     '2602.19320', 'abbreviation',
     'Anatomy of Agentic Memory: Taxonomy and Empirical Analysis of '
     'Evaluation and System Limitations'),
    ('research/frontier-research-taxonomy-2027-supplement-v2.md',
     '2604.14197', 'abbreviation',
     'The PICCO Framework for Large Language Model Prompting: A '
     'Taxonomy and Reference Architecture for Prompt Engineering'),
    ('research/frontier-research-taxonomy-2027-supplement.md',
     '2606.05339', 'abbreviation',
     'A Taxonomy of Runtime Faults in Model Context Protocol Servers'),
    ('research/memory-write-deduplication-amplification-control.md',
     '10.1145/276698.276876', 'acronym_initials',
     'Approximate nearest neighbors'),
]

# The two rows whose real title is already in the file's reference list.
IN_TEXT = [
    ('domains/ai-cognition/missing-brain-systems-deep-dive.md',
     '2509.20021', 'Embodied AI: From LLMs to World Models'),
    ('domains/ai-cognition/missing-brain-systems-deep-dive.md',
     '2604.14228', "Dive into Claude Code: The Design Space of Today's "
     'and Future AI Agent Systems'),
]

# Known-unrelated, deliberately not titled.
EXCLUDED = [{
    'path': 'AI-Architecture/Neuromorphic-Computing.md',
    'identifier': 'doi:10.1142/10269',
    'resolves_to': 'Real Options in Energy and Commodity Markets',
    'decision': 'not titled',
    'reason': 'a finance paper with no relationship to neuromorphic '
              'computing; titling it would make the file assert a '
              'source it does not mean. Needs a human decision about '
              'what the file intended to cite.'}]


def entry_text(old, title):
    """Rewrite one frontmatter source line so it carries a title.

    Keeps the entry's own URL and its own quoting, and appends the
    title in the established "URL (Title)" form. A bare entry has no
    parenthesised title yet, so the form is appended; an entry that
    already has one has it replaced.
    """
    s = old.strip()
    lead = old[:len(old) - len(old.lstrip())]
    assert s.startswith('- '), 'not a source entry: %r' % s[:60]
    body = s[2:].strip()
    quote = ''
    if body[:1] in '"\'' and body[-1:] == body[:1]:
        quote = body[0]
        body = body[1:-1]
    cut = body.find(' (')
    url = body
    if cut == -1:
        # No parenthesised title. The entry may instead use a dash
        # separator -- "arXiv:2602.19320 — Anatomy of Agentic
        # Memory: 4-Structure Taxonomy" -- in which case everything
        # after the first dash is the abbreviated title being
        # replaced. Treat that as the cut point instead of taking the
        # whole line as a URL, which is what made the first version of
        # this function report "rewrite produced no change" on the
        # three taxonomy rows.
        for dash in ('—', '–', '-'):
            m = re.search(r'\s*%s\s+' % re.escape(dash), body)
            if m:
                cut = m.start()
                break
        url = body if cut == -1 else body[:cut]
        if cut != -1:
            new = '%s- %s%s (%s)%s' % (lead, quote, url.strip(), title,
                                       quote)
            return new
    else:
        url = body[:cut]
    new = '%s- %s%s (%s)%s' % (lead, quote, url, title, quote)
    return new


def main():
    apply = '--apply' in sys.argv
    planned, problems = [], []

    for rel, ident, kind, title in DECISIONS:
        full = BRAIN / rel
        text = full.read_text(encoding='utf-8')
        end = text.find('\n---', 3)
        fm = text[:end] if end != -1 else text
        hits = [ln for ln in fm.split('\n') if ident in ln
                and ln.strip().startswith('- ')]
        if len(hits) != 1:
            problems.append({'path': rel, 'identifier': ident,
                             'reason': 'expected 1 frontmatter entry, '
                                       'found %d' % len(hits)})
            print('  SKIP %-32s %d entries' % (ident[-32:], len(hits)))
            continue
        old = hits[0]
        new = entry_text(old, title)
        if old == new:
            problems.append({'path': rel, 'identifier': ident,
                             'reason': 'rewrite produced no change'})
            print('  NOOP %-32s' % ident[-32:])
            continue
        planned.append({'path': rel, 'identifier': ident, 'kind': kind,
                        'title': title, 'old': old, 'new': new})
        print('  %-16s %-30s -> %s' % (kind, ident[-30:], title[:52]))

    print()
    print('  to write: %d   left for a human: %d' % (len(planned),
                                                     len(EXCLUDED)))
    for p in problems:
        print('  PROBLEM %s %s' % (p['identifier'], p['reason']))
    if not apply:
        print('  DRY RUN. Pass --apply to write.')
        return 0

    by_file = {}
    for p in planned:
        by_file.setdefault(p['path'], []).append(p)
    written = 0
    for rel, items in by_file.items():
        full = BRAIN / rel
        text = full.read_text(encoding='utf-8')
        out = text
        for p in items:
            if p['old'] not in out:
                raise SystemExit('stale review for %s: %r'
                                 % (p['identifier'], p['old'][:70]))
            out = out.replace(p['old'], p['new'], 1)
        if out != text:
            dst = BACKUP / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(full, dst)
            full.write_text(out, encoding='utf-8')
            written += 1
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(
        {'rewritten': planned, 'in_text_titles_already_present': IN_TEXT,
         'excluded': EXCLUDED, 'problems': problems}, indent=1) + '\n',
        encoding='utf-8')
    print('  files written: %d' % written)
    return 0


if __name__ == '__main__':
    sys.exit(main())
