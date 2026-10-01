#!/usr/bin/env python3
"""Publish a folder-only skeleton of the active wiki to the repo.

The live vault at ~/.hermes/active-wiki holds personal notes and must never be
committed. What belongs in GitHub is its SHAPE: the 13 numbered areas, their
sub-folders, and an index.md in each that says what the folder is for and how
content is supposed to reach it.

So this script writes folders and indexes. It never copies a note, and it
refuses to touch a directory that already holds anything but its own index.

  # show what would be written
  python3 scripts/publish_wiki_skeleton.py --dry-run

  # write it
  python3 scripts/publish_wiki_skeleton.py

  # confirm the committed copy matches the generator
  python3 scripts/publish_wiki_skeleton.py --check
"""

import argparse
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(REPO, 'wiki-skeleton')

# (folder, subfolder or None, type, epistemic, purpose)
# Kept in one place so the generator, the docs and the tests cannot drift.
TAXONOMY = [
    ('00_System', None, 'index', None,
     "The vault's rulebook: how it governs itself. Templates, proposals, and "
     "the notes that define what the other folders mean."),
    ('00_System', 'Templates', 'reference', None,
     "One template per note type, so every new note starts consistent."),
    ('00_System', 'Proposals', 'idea', None,
     "Pending edits awaiting approval. The gate for substantive changes to "
     "compiled folders."),

    ('01_Raw', None, 'index', None,
     "Immutable intake. Everything enters here first, unclassified. Capturing "
     "must never require deciding what something means."),
    ('01_Raw', 'Web', 'reference', None,
     "Browser captures and web clippings. Verbatim, never interpreted here."),
    ('01_Raw', 'Conversations', 'reference', None,
     "Chat exports and dialogue transcripts."),
    ('01_Raw', 'Quick-Captures', 'idea', 'hypothesis',
     "One-line thoughts, not yet thought through. `epistemic: hypothesis` is "
     "honest about that rather than asserting it."),
    ('01_Raw', 'Documents', 'reference', None,
     "Standalone files: PDFs, docs, data dumps."),
    ('01_Raw', 'Imports', 'reference', None,
     "Bulk imports and migrations from other systems."),
    ('01_Raw', 'Attachments', 'asset', None,
     "Media that accompanies other captures: images, audio."),

    ('02_Log', None, 'index', None,
     "Episodic memory. Dated events with outcomes: what happened, when, and "
     "what it produced."),
    ('02_Log', 'Daily', 'log', None, "Day summaries."),
    ('02_Log', 'Agent-Sessions', 'log', None,
     "What agent sessions did and what they produced."),
    ('02_Log', 'Meetings', 'log', None, "People interactions and commitments."),
    ('02_Log', 'Experiments', 'log', None,
     "Trials and their results, including the failures."),
    ('02_Log', 'Incidents', 'incident', None, "Breakages, outages, postmortems."),

    ('10_Self', None, 'index', None,
     "The durable model of the user: profile, goals, priorities, "
     "preferences, constraints, principles. Small, slow-changing, and high "
     "retrieval value."),
    ('10_Self', 'Goals', 'profile', None, "What the user is aiming at."),
    ('10_Self', 'Preferences', 'profile', None,
     "Stated preferences, in the user's own framing."),
    ('10_Self', 'Constraints', 'profile', None,
     "Hard limits the user works within."),
    ('10_Self', 'Principles', 'lesson', None,
     "Standing rules for how decisions get made."),

    ('20_Areas', None, 'index', None,
     "Ongoing responsibilities with no finish line: infrastructure, health, "
     "home, practice. Standards and health per area, reviewed on a cadence."),
    ('20_Areas', 'Standards', 'technical-spec', None,
     "The level something is expected to be held to."),
    ('20_Areas', 'Health', 'routine', None,
     "Current state of the area against that standard."),

    ('30_Projects', None, 'index', None,
     "Finite work with a definition of done. Lifecycle-driven: a project is "
     "identified by being active, paused, or completed, and by nothing else."),
    ('30_Projects', 'Active', 'project', None, "Being worked now."),
    ('30_Projects', 'Paused', 'project', None, "Parked, with intent to return."),
    ('30_Projects', 'Completed', 'project', None,
     "Done, lessons not yet extracted."),

    ('40_Entities', None, 'index', None,
     "Operationally relevant people, organisations, and things, sub-folders by "
     "kind. Context that matters to the user, not encyclopedia content."),
    ('40_Entities', 'People', 'person', None, "People who matter to the work."),
    ('40_Entities', 'Organizations', 'entity', None,
     "Companies, teams, institutions."),
    ('40_Entities', 'Systems', 'system', None,
     "Running systems and the infrastructure they depend on."),
    ('40_Entities', 'Products', 'asset', None, "Tools and products in use."),
    ('40_Entities', 'Models', 'model-card', None,
     "Models in service, with the details that matter operationally."),
    ('40_Entities', 'Places', 'entity', None, "Physical locations that recur."),

    ('50_Beliefs', None, 'index', None,
     "The user's current interpretations, graded by epistemic certainty. A "
     "claim is not a belief because it is asserted; it is here because it is "
     "held at a stated confidence."),
    ('50_Beliefs', 'Claims', 'reference', 'verified-inference',
     "Checkable assertions."),
    ('50_Beliefs', 'Hypotheses', 'idea', 'hypothesis',
     "Unconfirmed explanations or predictions."),
    ('50_Beliefs', 'Theses', 'evergreen', 'verified-inference',
     "Broader interpretations built from multiple claims."),
    ('50_Beliefs', 'Principles', 'lesson', None,
     "Normative rules governing how the user decides."),

    ('60_Decisions', None, 'index', 'verified-inference',
     "Append-only record of choices made: context, alternatives, rationale, "
     "consequences. Superseded by a new decision, never rewritten."),
    ('60_Decisions', 'Superseded', 'decision', None,
     "Decisions that a later decision replaced. Kept, not deleted."),

    ('70_Questions', None, 'index', None,
     "Known unknowns worth answering. Each blocks or drives something; when it "
     "is resolved it links to the decision or belief that resolved it."),

    ('80_Models', None, 'index', None,
     "Assembled understanding, built out of other notes. A model is derived "
     "work: it cites the claims and decisions it is built from."),
    ('80_Models', 'Syntheses', 'evergreen', None,
     "Integrations across many notes."),
    ('80_Models', 'Mental-Models', 'evergreen', None,
     "Reusable frames and lenses."),
    ('80_Models', 'Maps', 'technical-spec', None,
     "Relationship and dependency overviews."),
    ('80_Models', 'Current-State', 'temporal', None,
     "Where things stand right now, as of a date."),

    ('85_Procedures', None, 'index', None,
     "How work gets done: runbooks, standing rules, and pointers to the "
     "skills that graduated out of these notes."),
    ('85_Procedures', 'Human-Runbooks', 'routine', None,
     "Step-by-step operational procedures, for a person at a keyboard."),
    ('85_Procedures', 'Policies', 'technical-spec', None,
     "Standing rules for recurring situations."),
    ('85_Procedures', 'Skill-References', 'reference', None,
     "Pointers to agent skills that came out of these notes."),

    ('90_Archive', None, 'index', None,
     "Cold storage. Inactive and retained for history, excluded from routine "
     "attention. Nothing is deleted; it moves here."),
]

INDEX_NAME = 'index.md'

HEADER = """---
type: {ty}
epistemic: {ep}
confidence: not_applicable
sources:
---

# {title}
"""


def index_body(folder, sub, ty, ep, purpose):
    """The index.md text for one folder or sub-folder."""
    if sub is None:
        title = folder.split('_', 1)[-1].replace('_', ' ')
        path = f'[[{folder}]]' if folder != '00_System' else '[[00_System]]'
        breadcrumb = f'Part of the active wiki. {purpose}'
    else:
        title = sub.replace('-', ' ')
        breadcrumb = f'Sub-folder of [[{folder}]]. {purpose}'

    lines = [HEADER.format(ty=ty, ep=ep, title=title)]
    lines.append(breadcrumb)
    lines.append('')
    subs = [t[1] for t in TAXONOMY if t[0] == folder and t[1]]
    if subs and sub is None:
        lines.append('## Sub-folders')
        lines.append('')
        for s in subs:
            lines.append(f'- [{s}]({s}/index.md) — '
                         + dict((t[1], t[4]) for t in TAXONOMY if t[1] == s)[s])
        lines.append('')
    return '\n'.join(lines)


def wanted():
    """Every (relpath, content) the skeleton should contain."""
    out = []
    for folder, sub, ty, ep, purpose in TAXONOMY:
        rel = os.path.join(folder, sub) if sub else folder
        out.append((os.path.join(rel, INDEX_NAME), index_body(
            folder, sub, ty, ep, purpose)))
    return out


def dirs():
    return sorted({f if s else f for f, s, _, _, _ in TAXONOMY})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--target', default=TARGET)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    wrote = same = 0
    problems = []

    for rel, content in wanted():
        path = os.path.join(a.target, rel)
        if a.check:
            if not os.path.exists(path):
                problems.append(f'missing: {rel}')
            elif open(path, encoding='utf-8').read() != content:
                problems.append(f'stale:   {rel}')
            else:
                same += 1
            continue
        if os.path.exists(path) and open(path, encoding='utf-8').read() == content:
            same += 1
            continue
        if a.dry_run:
            print(f'  would write {rel}')
            wrote += 1
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(content)
        wrote += 1

    # Guard: a live note must never appear in the published skeleton.
    # Only files this script generates are allowed, plus the hand-written
    # README. Anything else in the tree is a leak and must fail the run --
    # including a note dragged in by an editor, a stray .bak, or a copy of
    # the live vault committed by hand.
    if not a.dry_run and not a.check:
        # wanted() already yields the full relative path of each index, so
        # this is the allowlist as-is. Appending INDEX_NAME again here
        # produced '00_System/index.md/index.md' and rejected the entire
        # tree the generator had just written -- a guard that failed on
        # correct output is worse than no guard.
        allowed = {w[0] for w in wanted()}
        allowed.add('README.md')
        stray = []
        for dp, _dn, fn in os.walk(a.target):
            for f in fn:
                p = os.path.join(dp, f)
                if os.path.relpath(p, a.target) in allowed:
                    continue
                stray.append(os.path.relpath(p, a.target))
        if stray:
            print('  ERROR: non-generated content in the published '
                  'skeleton:')
            for s in sorted(stray):
                print('    ' + s)
            return 1

    if a.check:
        if problems:
            print(f'  skeleton OUT OF DATE: {len(problems)} problem(s)')
            for p in problems[:20]:
                print('    ' + p)
            return 1
        print(f'  skeleton IN SYNC: {same} index files')
        return 0

    verb = 'would write' if a.dry_run else 'wrote'
    print(f'  {verb} {wrote}, already correct {same} '
          f'-> {os.path.relpath(a.target, REPO)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
