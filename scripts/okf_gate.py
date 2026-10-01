#!/usr/bin/env python3
"""
okf_gate.py — the pre-write gate every wiki writer must pass.

A page is not "written" until it satisfies the schema. This wraps okf_lint for
single-file use and returns a non-zero exit on failure, so a cron, a skill, or a
hook can block a bad write instead of reporting it after the fact.

Usage
  okf_gate.py FILE...            check each file, exit 1 on any report-only defect
  okf_gate.py --fix FILE...      repair what is auto-fixable, then check
  okf_gate.py --quiet FILE...    exit code only
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("okf_lint", os.path.join(HERE, "okf_lint.py"))
L = importlib.util.module_from_spec(spec)
spec.loader.exec_module(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--fix", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    S = L.load_schema()
    excluded = set(S.get("excluded_dirs") or [])
    by_base, by_rel, by_base_lc = L.build_index(excluded)
    ctx = L.Ctx(S, args.fix, by_base, by_rel, by_base_lc)

    failed = 0
    for f in args.files:
        if not os.path.exists(f):
            print(f"GATE FAIL  {f}: file does not exist")
            failed += 1
            continue
        # Expand a directory into the .md files under it.
        #
        # Passing a folder used to fail with "Is a directory", which is the
        # least useful possible outcome: the obvious way to invoke this on
        # a wiki folder is the way that does not work, and the obvious
        # workaround is a shell glob, which puts a 2,400-path command line
        # in reach of ARG_MAX. Walking it here also means the paths actually
        # checked are the ones under the folder the user named.
        if os.path.isdir(f):
            found = []
            for root, dirs, files in os.walk(f):
                dirs[:] = [d for d in dirs
                           if d not in excluded and d != "__pycache__"]
                for name in sorted(files):
                    if name.endswith(".md"):
                        found.append(os.path.join(root, name))
            if not found:
                if not args.quiet:
                    print(f"GATE PASS  {f}/  (no .md files)")
                continue
            for sub in sorted(found):
                rel = os.path.relpath(sub, os.path.dirname(f.rstrip("/")))
                out = L.check_file(sub, rel, ctx)
                mine = [x for x in ctx.findings if x["path"] == rel]
                if args.fix and out is not None and \
                        out != open(sub, encoding="utf-8").read():
                    open(sub, "w", encoding="utf-8").write(out)
                report = [x for x in mine if not x["auto_fixable"]]
                if report:
                    failed += 1
                    if not args.quiet:
                        print(f"GATE FAIL  {sub}")
                        for r in report:
                            print(f"    line {r['line']:>4}  "
                                  f"{r['class']}: {r['message']}")
                elif not args.quiet:
                    print(f"GATE PASS  {sub}")
            continue
        rel = os.path.basename(f)
        out = L.check_file(f, rel, ctx)
        mine = [x for x in ctx.findings if x["path"] == rel]
        if args.fix and out is not None and out != open(f, encoding="utf-8").read():
            open(f, "w", encoding="utf-8").write(out)
        report = [x for x in mine if not x["auto_fixable"]]
        if report:
            failed += 1
            if not args.quiet:
                print(f"GATE FAIL  {f}")
                for r in report:
                    print(f"    line {r['line']:>4}  {r['class']}: {r['message']}")
        elif not args.quiet:
            fixed = [x for x in mine if x["auto_fixable"]]
            print(f"GATE PASS  {f}" + (f"  ({len(fixed)} auto-repaired)" if fixed and args.fix else ""))

    if not args.quiet:
        print(f"\n{len(args.files)} file(s), {failed} blocked by report-only defects")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
