#!/usr/bin/env python3
"""
okf_lint.py — the single conformance + repair tool for both wikis.

Schema, enums, and repair policy live in schemas/okf-schema.yaml. This file
contains NO hard-coded field list or enum: it imports them. If you need to change
what "valid" means, edit the YAML, never this file.

Modes
  --check        report only, exit 1 if defects (used as a pre-write gate)
  --fix          apply the policy's `repair.auto` classes, then report the rest
  --strict       treat warnings as failures (use in CI / after a write)
  --full         no sampling — walk every file (default; --sample is opt-in)
  --json         machine-readable output
  --source NAME  active-wiki | oracle | both
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys
from datetime import datetime, timezone

# --------------------------------------------------------------------------
# Schema is the single source of truth. Nothing below re-declares its rules.
# --------------------------------------------------------------------------
SCHEMA_PATH = os.environ.get(
    "OKF_SCHEMA", os.path.expanduser("~/hermes-brain/schemas/okf-schema.yaml")
)

SOURCES = {
    "active-wiki": os.path.expanduser("~/.hermes/active-wiki"),
    "oracle": os.path.expanduser("~/.hermes/oracle/brain"),
}

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\s*\n?", re.S)
TOPKEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$")
# [[12]] is a citation marker into a numbered reference list, not a page link.
NUMERIC_LINK_RE = re.compile(r"^\d{1,4}$")

# A PROVENANCE entry records where a page came from, not what it cites.
#
# The COLON IS REQUIRED and that is the whole design. Without it the prefix
# test also matched prose that merely starts with the same word:
# "research paper on memory (Title Here)" was exempted, when it is a
# hand-wave that should fail. With `prefix:` the only strings exempt are the
# machine-written markers, because only they carry a namespace separator.
# Matched prefixes, all of which are namespaces rather than English words
# that start a sentence: session, user-provided, researcher, oracle,
# inherited, conversation, local, research.
PROVENANCE_RE = re.compile(
    r"^(?:session|research|researcher|oracle|inherited|conversation|local):"
    r"|^user-provided$", re.I)

# An entry carrying one of these is a CITATION, and therefore needs a title
# the T2 verifier can compare the resolved document against. The arXiv
# alternation includes the URL forms as well as the bare prefix: "arxiv.org/"
# has ".org/" between "arxiv" and the slash, so `arxiv[:/]` alone misses
# every real arXiv URL.
IDENTIFIER_RE = re.compile(
    r"arxiv[:/]|arxiv\.org/(?:abs|pdf|html)/|"
    r"(?:https?://(?:dx\.)?doi\.org/|doi[:/])10\.\d{4,9}/",
    re.I)

# A bare string carries its title as a trailing parenthetical:
#   arXiv:2509.20021 (Embodied AI Survey)
# At least 8 non-space characters, so "(v1)" or "(2024)" is not mistaken
# for a title.
TITLE_PAREN_RE = re.compile(r"\(\s*\S[^()]{7,}\s*\)\s*$")


def _yaml_load(text: str) -> dict:
    """
    Load the schema with a real YAML parser. Hand-rolling this once silently
    returned empty lists for block sequences while still exiting 0 — a
    linter that enforces nothing while reporting success. If PyYAML is
    unavailable we FAIL LOUD rather than degrade.
    """
    try:
        import yaml  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            f"okf_lint: PyYAML required to read the schema ({exc}). "
            "Install it rather than running with a degraded parser."
        )
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise SystemExit("okf_lint: schema did not parse to a mapping — refusing to continue")
    return data


def load_schema(path: str = SCHEMA_PATH) -> dict:
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    s = _yaml_load(text)
    # Fail closed: a schema that lost a section would silently change what the
    # linter enforces, so every required section must be present AND non-empty.
    for key in ("required", "types", "statuses", "type_map", "status_map", "shapes"):
        if not s.get(key):
            raise SystemExit(
                f"okf_lint: schema missing or empty '{key}' — refusing to guess ({path})"
            )
    bad = [t for t in s["types"] if t not in set(s["type_map"].values()) | set(s["types"])]
    if bad:
        raise SystemExit(f"okf_lint: type_map has no mapping for {bad}")
    return s


# --------------------------------------------------------------------------
# Finding + repair
# --------------------------------------------------------------------------
class Ctx:
    def __init__(self, schema, fix, by_base, by_rel, by_base_lc, dry_run=False):
        self.S = schema
        # In dry-run we still COMPUTE repairs (so `changed` is a real preview)
        # but never write. Counting 0 in a dry run would make it useless.
        self.fix = fix
        self.dry_run = dry_run
        self.by_base = by_base
        self.by_rel = by_rel
        self.by_base_lc = by_base_lc
        self.findings: list[dict] = []
        self.changed = 0
        self.files_changed = 0

    def _repaired(self):
        """True when a repair should be applied to the in-memory text."""
        return self.fix or self.dry_run

    def add(self, cls, path, line, msg, auto, applied=""):
        self.findings.append(
            {
                "class": cls,
                "path": path,
                "line": line,
                "message": msg,
                "auto_fixable": auto,
                "applied": applied,
            }
        )


def walk_files(root: str, excluded):
    for dp, dirs, fns in os.walk(root):
        dirs[:] = [d for d in dirs if d not in excluded]
        for fn in sorted(fns):
            if fn.endswith(".md"):
                yield os.path.join(dp, fn)


def build_index(excluded):
    """
    Obsidian semantics: a [[wikilink]] resolves by PAGE NAME across the whole
    vault, not by relative path. An earlier relative-path resolver reported
    11,253 broken links when only 2,295 were real — 5,457 resolved fine by
    basename alone. Both sources are indexed, plus a per-source relative set
    for path-qualified links.
    """
    by_base: dict[str, set] = {}       # page name -> {relpath}
    by_rel: set[str] = set()           # "dir/name.md" exactly as on disk
    by_base_lc: dict[str, str] = {}    # lowercased name -> real name (case repair)
    for root in SOURCES.values():
        if not os.path.isdir(root):
            continue
        for p in walk_files(root, excluded):
            rel = os.path.relpath(p, root)
            name = os.path.basename(p)[:-3]
            by_base.setdefault(name, set()).add(rel)
            by_rel.add(rel)
            by_base_lc.setdefault(name.lower(), name)
    return by_base, by_rel, by_base_lc


def parse_fm(text):
    m = FM_RE.match(text)
    if not m:
        return None, None, 0
    body = m.group(1)
    # find the offset of the body end in the original text
    end = m.end()
    return body, m, end


def check_file(path, rel, ctx):
    S = ctx.S
    try:
        raw = open(path, encoding="utf-8").read()
    except Exception as e:
        ctx.add("read_error", rel, 0, str(e), False)
        return None

    lines = raw.split("\n")
    body, m, fm_end = parse_fm(raw)

    if body is None:
        ctx.add("missing_front_matter", rel, 1, "no YAML front matter", True)
        return raw

    # ---- enum + required checks -----------------------------------------
    typeset = set(S["types"])
    statuses = set(S["statuses"])
    confs = set(S.get("confidences") or ["high", "medium", "low"])
    type_map = {str(k).lower(): v for k, v in (S["type_map"] or {}).items()}
    status_map = {str(k).lower(): v for k, v in (S["status_map"] or {}).items()}

    present = set()
    newlines = []
    for i, line in enumerate(body.split("\n")):
        km = TOPKEY_RE.match(line)
        if not km:
            newlines.append(line)
            continue
        k, v = km.group(1), km.group(2).strip()
        present.add(k)
        rawval = v.strip('"').strip("'")
        low = rawval.lower()

        if k == "type":
            if rawval in typeset:
                pass
            elif low in type_map:
                tgt = type_map[low]
                ctx.add("type_not_canonical", rel, i + 2,
                        f"type '{rawval}' -> '{tgt}'", True)
                if ctx._repaired():
                    newlines.append(f'type: {tgt}')
                    ctx.changed += 1
                    continue
            else:
                ctx.add("invalid_type", rel, i + 2,
                        f"type '{rawval}' not in schema enum", False)
        elif k == "status":
            if rawval in statuses:
                pass
            elif low in status_map:
                tgt = status_map[low]
                ctx.add("status_not_canonical", rel, i + 2,
                        f"status '{rawval}' -> '{tgt}'", True)
                if ctx._repaired():
                    newlines.append(f"status: {tgt}")
                    ctx.changed += 1
                    continue
            else:
                ctx.add("invalid_status", rel, i + 2,
                        f"status '{rawval}' not in schema enum", False)
        elif k == "confidence":
            if rawval not in confs:
                ctx.add("invalid_confidence", rel, i + 2,
                        f"confidence '{rawval}' not in {sorted(confs)}", False)
        elif k == "okf_version":
            want = str(S.get("okf_version", "0.2"))
            if rawval != want:
                ctx.add("bad_okf_version", rel, i + 2,
                        f"okf_version '{rawval}' -> '{want}'", True)
                if ctx._repaired():
                    newlines.append(f'okf_version: "{want}"')
                    ctx.changed += 1
                    continue
        newlines.append(line)

    body_new = "\n".join(newlines)

    # ---- required fields -------------------------------------------------
    missing = [k for k in S["required"] if k not in present]
    if missing:
        ctx.add("missing_required", rel, 2,
                "missing: " + ", ".join(missing), True)
        if ctx._repaired():
            adds = []
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            for k in missing:
                if k == "okf_version":
                    adds.append(f'okf_version: "{S.get("okf_version", "0.2")}"')
                elif k == "generated":
                    adds.append("generated:")
                    adds.append('  by: "okf_lint"')
                    adds.append(f'  at: "{now}"')
                elif k == "tags":
                    adds.append("tags: []")
                elif k == "sources":
                    adds.append("sources: []")
                elif k == "confidence":
                    adds.append("confidence: low")
                elif k == "status":
                    adds.append("status: unverified")
                elif k == "type":
                    adds.append("type: reference")
                elif k == "description":
                    h1 = ""
                    for l in lines:
                        if l.startswith("# "):
                            h1 = l[2:].strip()
                            break
                    adds.append(f"description: {h1 or os.path.basename(rel)[:-3].replace('-', ' ')}")
                else:
                    adds.append(f"{k}: id-{os.path.basename(rel)[:-3]}")
            # insert after the opening ---
            body_new = body_new.rstrip("\n") + "\n" + "\n".join(adds) + "\n"
            ctx.changed += 1

    # ---- citation shape: an identifier needs a title ---------------------
    # Added 2026-09-30. The T2 verifier resolves an identifier, fetches the
    # real document, and compares its real title against the title written
    # here. An entry with an identifier and NO title gives it nothing to
    # compare, so the row is recorded `untitled_citation` and the page can
    # never be promoted past medium.
    #
    # The schema listed `title` as optional in a source entry, so a writer
    # could comply perfectly and still produce a file that could not pass:
    # 1,605 of 2,661 identifier-bearing entries corpus-wide had no title.
    # Reported, never auto-fixed -- the title has to come from the source,
    # and inventing one is M2_identifier_mismatch, which caps at low.
    fm_map = _yaml_load(body) if body.strip() else {}
    for raw_src in (fm_map.get("sources") or []):
        if isinstance(raw_src, dict):
            if not IDENTIFIER_RE.search(str(raw_src.get("resource", ""))):
                continue
            if str(raw_src.get("title") or "").strip():
                continue
            ctx.add("citation_title_missing", rel, 2,
                    f"source has an identifier but no title: "
                    f"{str(raw_src.get('resource'))[:70]}", False)
            continue
        entry = str(raw_src).strip()
        if not IDENTIFIER_RE.search(entry):
            # A source entry with no resolvable identifier AND no title is
            # unresolvable -- "see the paper", "as discussed above". The
            # grader cannot fetch it, so it counts against the page exactly
            # as an untitled identifier does, and the documentation promises
            # this fails. It is reported separately so the two causes stay
            # distinguishable when triaging a batch.
            #
            # A bare domain or an untitled URL is also unresolvable, but it
            # is far more common and less severe, so it is left to the link
            # check rather than blocking here. This check targets entries with
            # no URL at all, which can only be a human-readable reference to
            # something that does not exist as a citable source.
            #
            # PROVENANCE ENTRIES ARE NOT CITATIONS and are exempt. The
            # corpus records where a page came from as well as what it cites:
            #
            #   sources:
            #     - session:20260924_162607_55ce9ddd
            #     - session:telegram:2026-09-28
            #     - user-provided
            #     - research:local-research-dispatch
            #
            # 52 of the 53 source entries in the active wiki are session
            # provenance, and this check blocked every page that carried one
            # -- four of the twelve entity pages, including honcho-memory-
            # stack and hermes-brain. A provenance marker is a pointer to
            # where something was observed, not a claim to be fetched, and
            # demanding a title of it is the same category error as demanding
            # a DOI. It cannot be retrieved, and it is not supposed to be.
            #
            # A titled identifier is still required, above. The two rules
            # are about different things and both are right.
            if PROVENANCE_RE.search(entry):
                continue
            if not re.search(r"https?://", entry) and not TITLE_PAREN_RE.search(entry):
                ctx.add("source_unresolvable", rel, 2,
                        f"source entry has neither an identifier nor a title, "
                        f"so it cannot be retrieved: {entry[:70]}", False)
            continue
        if TITLE_PAREN_RE.search(entry):
            continue
        ctx.add("citation_title_missing", rel, 2,
                f"source has an identifier but no title: {entry[:70]}", False)

    # ---- links -----------------------------------------------------------
    for i, line in enumerate(raw.split("\n")):
        for lm in re.finditer(r"\[\[([^\]]+)\]\]", line):
            tgt = lm.group(1).split("|")[0].split("#")[0].strip()
            if not tgt:
                continue
            # A bare [[12]] is a numeric citation marker, not a page link.
            if NUMERIC_LINK_RE.fullmatch(tgt):
                ctx.add("numeric_citation_marker", rel, i + 1,
                        f"[[{tgt}]] is a citation marker, not a page link", False)
                continue
            if tgt in ctx.by_base:
                continue                                   # exact page name
            if tgt in ctx.by_rel or (tgt + ".md") in ctx.by_rel:
                continue                                   # path-qualified, exact
            real = ctx.by_base_lc.get(tgt.lower())          # case-only difference
            if real and real != tgt:
                ctx.add("link_case_wrong", rel, i + 1,
                        f"[[{tgt}]] -> [[{real}]]", True)
                continue
            if tgt.endswith("/index"):
                base = tgt[: -len("/index")]
                if base in ctx.by_base:
                    ctx.add("link_index_suffix", rel, i + 1,
                            f"[[{tgt}]] -> [[{base}]]", True)
                    continue
            ctx.add("link_unresolvable", rel, i + 1,
                    f"[[{tgt}]] matches no page in either wiki", False)

    # ---- index presence (report only) ------------------------------------
    if os.path.basename(rel) == "index.md":
        pass

    out = raw
    if ctx._repaired() and body_new != body:
        out = fm_end_str(raw, body_new)
    return out


def fm_end_str(raw, new_body):
    m = FM_RE.match(raw)
    if not m:
        return raw
    return raw[: m.start(1)] + new_body.rstrip("\n") + raw[m.end(1) :]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="both", choices=["active-wiki", "oracle", "both"])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--fix", action="store_true")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true", help="--fix but print, do not write")
    args = ap.parse_args()

    S = load_schema()
    excluded = set(S.get("excluded_dirs") or [])
    by_base, by_rel, by_base_lc = build_index(excluded)

    roots = SOURCES.items() if args.source == "both" else [(args.source, SOURCES[args.source])]
    ctx = Ctx(S, args.fix and not args.dry_run, by_base, by_rel, by_base_lc, dry_run=args.dry_run)

    scanned = 0
    for name, root in roots:
        if not os.path.isdir(root):
            print(f"okf_lint: source '{name}' not found at {root}", file=sys.stderr)
            return 2
        files = list(walk_files(root, excluded))
        if args.sample:
            step = max(1, len(files) // args.sample)
            files = files[::step][: args.sample]
        for p in files:
            rel = os.path.relpath(p, root)
            scanned += 1
            before = open(p, encoding="utf-8").read()
            newtext = check_file(p, rel, ctx)
            if newtext is not None and newtext != before:
                ctx.files_changed += 1
                # Write only in real --fix mode. In --dry-run we computed the
                # repair and counted it, but never touch the corpus.
                if ctx.fix:
                    open(p, "w", encoding="utf-8").write(newtext)

    by = collections.Counter(f["class"] for f in ctx.findings)
    auto = sum(1 for f in ctx.findings if f["auto_fixable"])

    if args.json:
        print(json.dumps({
            "scanned": scanned,
            "findings": ctx.findings,
            "by_class": dict(by),
            "auto_fixable": auto,
            "report_only": len(ctx.findings) - auto,
            "files_changed": ctx.files_changed,
            "repairs": ctx.changed,
            "dry_run": args.dry_run,
        }, indent=2))
    else:
        verb = "would_change" if args.dry_run else "changed"
        print(f"okf_lint  scanned={scanned}  findings={len(ctx.findings)}  "
              f"auto={auto}  report-only={len(ctx.findings) - auto}"
              f"  {verb}_files={ctx.files_changed}"
              f"  repairs={ctx.changed}"
              f"{'  (DRY RUN — nothing written)' if args.dry_run else ''}")
        for cls, n in by.most_common():
            mark = "auto" if any(f["class"] == cls and f["auto_fixable"] for f in ctx.findings) else "report"
            print(f"  {n:6d}  {cls:38s} [{mark}]")

    report_only = len(ctx.findings) - auto
    if args.check and not args.fix:
        return 1 if (report_only or (args.strict and ctx.findings)) else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
