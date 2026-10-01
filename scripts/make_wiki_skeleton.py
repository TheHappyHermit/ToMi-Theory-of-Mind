#!/usr/bin/env python3
"""Create the active wiki's numbered folder skeleton, with an index per folder.

Why a generator rather than 40 hand-written index files
------------------------------------------------------
`verify_okf_index.py` requires an `index.md` in EVERY directory, so a 13-folder
taxonomy with sub-folders is ~40 index files. Hand-writing them guarantees
drift: a sub-folder added later gets no index, and the daily cron job reports
it as a failure nobody can reproduce by hand.

This script is the single place the taxonomy lives. Re-running it is idempotent:
existing files are never overwritten without `--force`, and a folder that gains
content is not reset back to an empty stub.

Design rules, all deliberate:

  * `type:` uses ONLY the 29 types already in schemas/okf-schema.yaml. The
    numbered folders are an organisation decision; `type:` is a classification
    decision. Nothing here requires a schema change. 19 of 29 types are used;
    the other 10 (paper, preprint, journal, conference, research-report, trip,
    purchase, code, comparison, presentation) are research-vault types the
    working layer has no use for.

  * An empty folder is a PROMISE, not a placeholder. Its index says what will
    go there and which field decides. That is what makes an empty folder
    useful rather than noise -- otherwise nobody can route to it.

  * The belief split is `epistemic:`, which the schema already defines, not
    four invented types. `hypothesis` and `prediction` already exist there.

  * Lifecycle is `status:`, not a directory. `30_Projects/Active|Paused|
    Completed` would be machine-uncheckable; `status: active|blocked|
    completed` is in the enum already and the linter reads it. The same
    applies to 90_Archive (`status: archived`).

Usage:
    python3 scripts/make_wiki_skeleton.py --dry-run
    python3 scripts/make_wiki_skeleton.py
    python3 scripts/make_wiki_skeleton.py --vault ~/.hermes/active-wiki
"""
import argparse
import datetime
import os
import sys

# (folder, sub-folder or None, type, epistemic, one-line purpose)
TAXONOMY = [
    ("00_System", None, "index", "fact",
     "How the vault governs itself: ontology, routing rules, write policy, "
     "templates, and proposals awaiting approval."),
    ("00_System", "Templates", "reference", "fact",
     "One template per note type, so a new note starts schema-valid."),
    ("00_System", "Proposals", "idea", "hypothesis",
     "Pending substantive edits awaiting approval. The curator proposes here "
     "and never applies its own proposals."),

    ("01_Raw", None, "index", "fact",
     "Immutable intake. Everything enters here unclassified; capturing never "
     "requires deciding what something means."),
    ("01_Raw", "Web", "reference", "observation",
     "Browser captures and web clippings. Verbatim, never interpreted here."),
    ("01_Raw", "Conversations", "reference", "observation",
     "Chat exports and dialogue transcripts."),
    ("01_Raw", "Quick-Captures", "idea", "hypothesis",
     "One-line thoughts, not yet thought through. `epistemic: hypothesis` is "
     "honest about that rather than implying a settled claim."),
    ("01_Raw", "Documents", "reference", "observation",
     "Standalone files: PDFs, docs, data dumps."),
    ("01_Raw", "Imports", "reference", "observation",
     "Bulk imports and migrations from other systems."),
    ("01_Raw", "Attachments", "asset", "observation",
     "Media accompanying other captures: images, audio."),

    ("02_Log", None, "index", "fact",
     "Episodic memory. Dated events with outcomes: what happened, when, result."),
    ("02_Log", "Daily", "log", "observation", "Day summaries."),
    ("02_Log", "Agent-Sessions", "log", "observation",
     "What agent sessions did and produced."),
    ("02_Log", "Meetings", "log", "observation",
     "People interactions and commitments made."),
    ("02_Log", "Experiments", "log", "observation",
     "Trials and their results, including the failures."),
    ("02_Log", "Incidents", "incident", "observation",
     "Breakages, outages, and postmortems."),

    ("10_Self", None, "index", "fact",
     "The durable model of the operator: profile, goals, priorities, preferences, "
     "constraints, principles. Small, slow-changing, high retrieval value."),
    ("10_Self", "Goals", "project", "decision",
     "What he is trying to achieve. `type: project` because a goal has an "
     "endpoint; `epistemic: decision` because it was decided, not discovered."),
    ("10_Self", "Preferences", "profile", "explicit-preference",
     "Stated likes, dislikes and standing choices."),
    ("10_Self", "Constraints", "technical-spec", "fact",
     "Hard limits: hardware, budget, schedule, rules he is bound by."),
    ("10_Self", "Principles", "lesson", "explicit-preference",
     "Normative rules for how he decides. `lesson`, not `fact`: a principle is "
     "not a weaker truth, it is a different kind of object."),

    ("20_Areas", None, "index", "fact",
     "Ongoing responsibilities with no finish line: infrastructure, health, "
     "home, practice. Standards and health per area, reviewed on a cadence."),
    ("20_Areas", "Standards", "technical-spec", "fact",
     "The standard each area is held to."),
    ("20_Areas", "Health", "routine", "fact",
     "Current state and review cadence per area."),

    ("30_Projects", None, "index", "fact",
     "Finite work with a definition of done. Lifecycle is `status:`, not a "
     "directory: `active` / `blocked` / `completed` / `cancelled`."),
    ("30_Projects", "Active", "project", "decision", "Being worked now."),
    ("30_Projects", "Paused", "project", "decision", "Parked, intent to return."),
    ("30_Projects", "Completed", "project", "decision",
     "Done, lessons not yet extracted. `supersedes`/`superseded_by` link the "
     "decision that ended it."),

    ("40_Entities", None, "index", "fact",
     "Operationally relevant people, orgs and things. Context that matters to "
     "the operator, not encyclopedia content."),
    ("40_Entities", "People", "person", "fact", "Individuals."),
    ("40_Entities", "Organizations", "entity", "fact", "Companies, teams, groups."),
    ("40_Entities", "Systems", "system", "fact",
     "Running systems and the infrastructure behind them."),
    ("40_Entities", "Products", "asset", "observation",
     "Tools, models and hardware he uses."),
    ("40_Entities", "Models", "model-card", "fact",
     "LLMs and model families, with their provenance."),
    ("40_Entities", "Places", "entity", "fact", "Physical locations."),

    ("50_Beliefs", None, "index", "fact",
     "Current interpretations held with a confidence. The four sub-folders "
     "differ by `epistemic:`, not by `type:` -- the schema's epistemic enum "
     "already separates them."),
    ("50_Beliefs", "Claims", "reference", "verified-inference",
     "Checkable assertions with a resolvable source."),
    ("50_Beliefs", "Hypotheses", "idea", "hypothesis",
     "Unconfirmed explanations or predictions. `epistemic: hypothesis` is the "
     "schema doing the work, not the folder name."),
    ("50_Beliefs", "Theses", "evergreen", "verified-inference",
     "Broader interpretations built from multiple claims."),
    ("50_Beliefs", "Principles", "lesson", "explicit-preference",
     "Normative rules governing how decisions get made."),

    ("60_Decisions", None, "index", "fact",
     "Append-only record of choices made: context, alternatives, rationale, "
     "consequences. Superseded by a new decision, never rewritten."),
    ("60_Decisions", "Superseded", "decision", "decision",
     "Kept for history. `status: superseded` plus `superseded_by` is the "
     "machine-readable form of 'this no longer holds'."),

    ("70_Questions", None, "index", "fact",
     "Known unknowns worth answering. Each blocks or drives something; when "
     "resolved it links to the resulting decision or belief."),

    ("80_Models", None, "index", "fact",
     "Assembled understanding, built from other notes."),
    ("80_Models", "Syntheses", "evergreen", "verified-inference",
     "Integrations across many notes."),
    ("80_Models", "Mental-Models", "evergreen", "verified-inference",
     "Reusable frames and lenses."),
    ("80_Models", "Maps", "reference", "verified-inference",
     "Relationship and dependency overviews."),
    ("80_Models", "Current-State", "temporal", "observation",
     "'Where things stand right now' summaries. `temporal` because it ages."),

    ("85_Procedures", None, "index", "fact",
     "How work gets done. Each entry should graduate to a skill once it is "
     "stable; the skill is then the canonical form."),
    ("85_Procedures", "Human-Runbooks", "routine", "fact",
     "Step-by-step operational procedures a person follows by hand."),
    ("85_Procedures", "Policies", "technical-spec", "fact",
     "Standing rules for recurring situations."),
    ("85_Procedures", "Skill-References", "reference", "fact",
     "Pointers to agent skills that graduated from these notes."),

    ("90_Archive", None, "index", "fact",
     "Cold storage. Inactive, retained for history, excluded from routine "
     "attention. `status: archived` marks a note; this folder keeps retired "
     "material out of the working set."),
]

TPL = """---
okf_version: "0.2"
id: {id}
title: "{title}"
description: "{desc}"
status: active
type: {ty}
epistemic: {ep}
created: {date}
updated: {date}
tags: [{tags}]
sources: ["session:telegram:2026-09-30"]
confidence: not_applicable
---

# {title}

{desc}

{body}
"""


def build(vault, dry_run=False, force=False):
    today = datetime.date.today().isoformat()
    made, kept = [], []
    for folder, sub, ty, ep, purpose in TAXONOMY:
        d = os.path.join(vault, folder, sub) if sub else os.path.join(vault, folder)
        rel = os.path.relpath(d, vault)
        if sub:
            os.makedirs(os.path.dirname(d), exist_ok=True)
        os.makedirs(d, exist_ok=True)
        idx = os.path.join(d, "index.md")
        if os.path.exists(idx) and not force:
            kept.append(rel)
            continue
        if dry_run:
            made.append(rel)
            continue
        slug = rel.replace("/", "-").replace("_", "-").lower()
        body = ("This folder is empty. That is deliberate: it exists so material "
                "has somewhere correct to go the first time it appears.\n\n"
                "- **Folder purpose:** %s\n"
                "- **Note `type:`** `%s`\n"
                "- **`epistemic:`** `%s`\n\n"
                "Every note in the vault is validated by "
                "`scripts/okf_gate.py` against `schemas/okf-schema.yaml`. "
                "The numbered folders are an organisation decision; `type:` is "
                "a classification decision and uses only types the schema "
                "already defines." % (purpose, ty, ep))
        if not sub:
            body += ("\n## Sub-folders\n\n"
                     + "".join("- [[%s/%s/index]] — %s\n" % (folder, s, p)
                               for f2, s, t2, e2, p in TAXONOMY
                               if f2 == folder and s))
        with open(idx, "w", encoding="utf-8") as fh:
            fh.write(TPL.format(
                id=slug, title="%s — Index" % (rel.split("/")[-1]),
                desc=purpose, ty=ty, ep=ep, date=today,
                tags=", ".join(rel.lower().split("/")),
                body=body))
        made.append(rel)
    return made, kept


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=os.path.expanduser("~/.hermes/active-wiki"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="overwrite existing index.md files")
    a = ap.parse_args()
    if not os.path.isdir(a.vault):
        sys.exit("no such vault: %s" % a.vault)
    made, kept = build(a.vault, a.dry_run, a.force)
    verb = "would create" if a.dry_run else "created"
    print("%s %d index file(s); %d already present" % (verb, len(made), len(kept)))
    for m in made:
        print("  + %s/index.md" % m)
    if kept:
        print("kept existing (use --force to overwrite): %s" % ", ".join(kept))


if __name__ == "__main__":
    main()
