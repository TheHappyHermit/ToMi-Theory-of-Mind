#!/usr/bin/env python3
"""
okf_export_json.py — generate the JSON Schema mirror from the canonical YAML.

WHY THIS EXISTS
  The corpus had FOUR divergent definitions of "what a wiki page looks like":
    1. schemas/okf-schema.yaml                 (canonical, new)
    2. schemas/wiki-frontmatter.schema.json (2 identical copies, 6 required
       fields, an `Index` type and a `research_report` type)
    3. research_quality_check.py                 (7 fields, yet another enum)
    4. fill_oracle_gaps.py request payloads      (6 fields, research_report)
  Any tool reading a different one got a different answer. This script makes the
  JSON a DERIVED ARTIFACT so it cannot drift: change the YAML, re-run this, and
  every consumer sees the same standard.

  The JSON is a mirror, never an authority. If they disagree, the YAML is right.

Usage
  okf_export_json.py --check    # exit 1 if the mirror is stale (use in CI)
  okf_export_json.py --write    # regenerate the mirror
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
YAML = os.path.join(REPO, "schemas", "okf-schema.yaml")
MIRRORS = [
    os.path.join(REPO, "schemas", "wiki-frontmatter.schema.json"),
]

spec = importlib.util.spec_from_file_location("okf_lint", os.path.join(HERE, "okf_lint.py"))
L = importlib.util.module_from_spec(spec)
spec.loader.exec_module(L)


def build(s: dict) -> dict:
    props = {}
    shapes = s.get("shapes") or {}

    def prop_for(key):
        sh = (shapes.get(key) or {}).get("type")
        if sh == "enum":
            src = (shapes.get(key) or {}).get("source")
            return {"type": "string", "enum": list(s.get(src) or [])}
        if sh == "list":
            return {"type": "array", "items": {"type": "string"}}
        if sh == "date":
            return {"type": "string", "format": "date"}
        if sh == "mapping":
            return {
                "type": "object",
                "required": list((shapes.get(key) or {}).get("required_subkeys") or []),
                "properties": {
                    "by": {"type": "string"},
                    "at": {"type": "string", "description": "RFC3339 UTC, e.g. 2026-09-26T14:03:00Z"},
                },
            }
        if sh == "kebab-id":
            return {"type": "string", "pattern": (shapes.get(key) or {}).get("pattern", "")}
        return {"type": "string"}

    for key in list(s.get("required") or []) + list(s.get("recommended") or []) + list(s.get("optional") or []):
        props[key] = prop_for(key)
    for key in shapes:
        props.setdefault(key, prop_for(key))

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://hermes-brain.local/schemas/wiki-frontmatter.schema.json",
        "title": "Wiki frontmatter (OKF v0.2) — GENERATED MIRROR",
        "description": (
            "Derived from schemas/okf-schema.yaml by scripts/okf_export_json.py. "
            "DO NOT EDIT BY HAND. The YAML is the single source of truth; if this "
            "file disagrees with it, the YAML is correct."
        ),
        "type": "object",
        "required": list(s.get("required") or []),
        "additionalProperties": True,
        "properties": props,
        "x-canonical-source": "schemas/okf-schema.yaml",
        "x-okf-version": s.get("okf_version"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    s = L.load_schema(YAML)
    doc = json.dumps(build(s), indent=2, sort_keys=False) + "\n"

    stale = []
    for m in MIRRORS:
        cur = open(m, encoding="utf-8").read() if os.path.exists(m) else None
        if cur == doc:
            print(f"  current   {m}")
            continue
        stale.append(m)
        if args.write:
            os.makedirs(os.path.dirname(m), exist_ok=True)
            with open(m, "w", encoding="utf-8") as fh:
                fh.write(doc)
            print(f"  WROTE     {m}")
        else:
            print(f"  STALE     {m}")

    if stale and not args.write:
        print(f"\n{len(stale)} mirror(s) out of date — run: okf_export_json.py --write")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
