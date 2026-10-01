#!/usr/bin/env python3
"""Verify that a citation's DOI actually resolves to the paper it claims to be.

Why this exists
---------------
Spot-checking DOIs in the Oracle vault's `Prospective-Memory/Implementation-Intentions.md`
found four bad citations out of six checked:

  - `10.1037/bul0000100` was cited as a meta-analysis of implementation intentions.
    It actually resolves to *"The effects of acute stress on episodic memory: A
    meta-analysis and integrative review"* (Psychological Bulletin, 2017) --
    a different topic entirely.
  - `10.1038/nature09021` was cited in the forgetting dossier; it resolves to
    *"The folding cooperativity of a protein is controlled by its chain length"*
    (Nature, 2010).
  - `10.1016/j.jrp.2008.12.003` was cited as Webb & Sheeran on boosting goal
    striving; it resolves to a paper on narrative ego integrity.
  - `10.1037/0033-295X.106.4.593` and `10.1146/annurev.psych.57.102904.190214`
    return 404 from Crossref (either malformed or the DOI is wrong).

A DOI that resolves to the *wrong paper* is worse than no DOI, because it looks
verified and sends a reader to confident nonsense. This script catches that class
of error, which a human skimming a reference list will not.

What it checks
--------------
  1. The DOI resolves (Crossref `/works/{doi}`).
  2. The resolved title's words overlap substantially with the title the vault
     claims. Overlap, not equality, because titles get reformatted and
     subtitles move around.
  3. Optionally, the year is within a small tolerance.

Exit codes: 0 all good, 1 mismatches found, 2 usage/network error.
Rate limited: registries allow a burst then throttle. The script sleeps between
calls; on 429 it reports the fact rather than pretending the citation is fine.

Design note — the non-vacuity problem
-------------------------------------
The first version of this script compared titles by
`|shorter INTERSECT longer| / |shorter|` and called >= 0.6 a match. That is
vacuous: a one-word claimed title scores 1.00 against any real paper
containing that word, and an empty claimed title scores 0.00, which the
caller read as MISMATCH — a confident wrong verdict rather than "cannot
compare". Both directions produced a number that looked like evidence.

The comparison now lives in `citation_compare.py` and returns three states
(OK / MISMATCH / UNVERIFIABLE), scores on min(coverage, precision), and
refuses to emit a verdict below MIN_CONTENT_WORDS. Resolution lives in
`citation_resolvers.py` and tries Crossref, then DataCite, then arXiv.

Crucially, `tests/test_verify_citations_nonvacuity.py` MUTATES these
functions and asserts the mutations are detected. A verifier that cannot fail
is not a verifier, and the only way to know whether this one can fail is to try.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import List, Optional, Tuple

sys.path.insert(0, __file__.rsplit("/", 1)[0])

from citation_compare import (  # noqa: E402
    MATCH_THRESHOLD,
    OK,
    UNVERIFIABLE,
    compare_titles,
    compare_years,
)
from citation_resolvers import Resolved, arxiv_id_from, polite_sleep, resolve_any  # noqa: E402

__all__ = [
    "audit",
    "check_one",
    "parse_frontmatter_sources",
    "arxiv_id_from",
    "resolve_any",
    "compare_titles",
]


def check_one(identifier: str, claimed: str, year: str,
              timeout: int = 25) -> dict:
    """Resolve one identifier and compare it against the claimed title/year."""
    res: Resolved = resolve_any(identifier, timeout=timeout)
    row = {
        "id": identifier,
        "status": res.status,
        "source": res.source,
        "tried": res.tried,
        "detail": res.detail,
    }
    if res.status == "RATE":
        row["status"] = "RATE"
        return row
    if not res.ok:
        row["status"] = "FAIL"
        return row

    verdict = compare_titles(claimed, res.title)
    row.update(
        status=verdict.status,
        score=round(verdict.score, 2),
        coverage=round(verdict.coverage, 2),
        precision=round(verdict.precision, 2),
        claimed=claimed[:90],
        claimed_year=year,
        actual=res.title[:90],
        actual_year=res.year,
        container=res.container[:60],
        reason=verdict.reason,
    )

    # Year is corroboration, never the sole basis for a verdict.
    if verdict.status == OK and year and res.year:
        y_ok, y_note = compare_years(year, res.year)
        row["year_check"] = y_note
        if y_ok is False:
            row["status"] = "MISMATCH"
            row["reason"] = f"title matched but {y_note}"
        elif y_ok is None:
            row["year_check"] = f"UNVERIFIABLE: {y_note}"
    return row


def audit(citations: List[Tuple[str, str, str]], delay: float) -> List[dict]:
    """citations: list of (identifier, claimed_title, claimed_year).

    Sequential with an inter-call delay. Registries throttle aggressively and a
    429 is reported as RATE, never silently converted into a pass.
    """
    out = []
    for i, (ident, claimed, year) in enumerate(citations):
        if i:
            polite_sleep(delay)
        out.append(check_one(ident, claimed, year))
    return out


def parse_frontmatter_sources(path: str) -> List[Tuple[str, str, str]]:
    """Pull (identifier, desc, year) triples out of an OKF-style sources block.

    Recognises three identifier forms, because the corpus uses all three:
      - https://doi.org/10.xxxx/...      (Crossref or DataCite)
      - https://arxiv.org/abs/NNNN.NNNNN (arXiv)
      - arXiv:NNNN.NNNNN                (bare form, no URL)
    """
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return []
    ident_re = re.compile(
        r"https?://(?:dx\.)?doi\.org/([^\s'\"\)\]]+)"
        r"|https?://arxiv\.org/abs/(\d{4}\.\d{4,5})(?:v\d+)?"
        r"|\barXiv:(\d{4}\.\d{4,5})(?:v\d+)?"
        # A BARE DOI, e.g. "10.1037/bul0000100" with no URL around it. The
        # corpus uses this form as often as the URL form; matching only URLs
        # silently skipped half the citations. Anchored on a non-"10" start so
        # it cannot re-match inside a URL already captured above.
        r"|(?<![\w./])(10\.\d{4,9}/[^\s'\"\)\]]+)",
        re.I,
    )
    out = []
    for m in ident_re.finditer(text):
        ident = (m.group(1) or m.group(2) or m.group(3) or m.group(4) or "").rstrip(".,;")
        if not ident:
            continue
        tail = text[m.end():m.end() + 220]
        # claimed title: first quoted chunk after the identifier
        quoted = re.search(r"['\"]([^'\"]{12,})['\"]", tail)
        claimed = quoted.group(1) if quoted else ""
        year = re.search(r"\b(19|20)\d{2}\b", tail)
        out.append((ident, claimed, year.group(0) if year else ""))
    # dedupe, preserve order
    seen, uniq = set(), []
    for d, c, y in out:
        if d.lower() not in seen:
            seen.add(d.lower())
            uniq.append((d, c, y))
    return uniq


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(
        description="Verify vault citations resolve to the paper they claim"
    )
    ap.add_argument("files", nargs="*", help="markdown files to audit")
    ap.add_argument("--doi", action="append", default=[],
                    help="check a bare DOI or arXiv id (repeatable)")
    ap.add_argument("--delay", type=float, default=1.2,
                    help="seconds between registry calls (be polite)")
    ap.add_argument("--threshold", type=float, default=MATCH_THRESHOLD,
                    help="min(coverage, precision) needed for a title match")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    citations: List[Tuple[str, str, str]] = []
    for f in args.files:
        citations.extend(parse_frontmatter_sources(f))
    for d in args.doi:
        citations.append((d, "", ""))

    if not citations:
        print("Nothing to check. Pass markdown files or --doi.", file=sys.stderr)
        return 2

    if args.threshold != MATCH_THRESHOLD:
        import citation_compare
        citation_compare.MATCH_THRESHOLD = args.threshold

    results = audit(citations, args.delay)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        bad = [r for r in results if r["status"] in ("FAIL", "MISMATCH")]
        unver = [r for r in results if r["status"] == UNVERIFIABLE]
        for r in results:
            ident = r["id"]
            if r["status"] == "RATE":
                print(f"  [RATE]       {ident}  (throttled by {r['source']}; retry later)")
            elif r["status"] == "FAIL":
                print(f"  [FAIL]       {ident}  {r['detail']}  tried={r['tried']}")
            elif r["status"] == UNVERIFIABLE:
                print(f"  [UNVERIF]    {ident}  {r['reason']}")
                print(f"      claimed: {r.get('claimed', '')}")
                print(f"      actual:  {r.get('actual', '')}")
            elif r["status"] == "MISMATCH":
                print(f"  [MISMATCH]   {ident}  score={r['score']} "
                      f"(cov={r['coverage']} prec={r['precision']}) via {r['source']}")
                print(f"      claimed: {r['claimed']}  ({r['claimed_year']})")
                print(f"      actual:  {r['actual']}  ({r['actual_year']})")
                print(f"      in:      {r['container']}")
                if r.get("year_check"):
                    print(f"      year:    {r['year_check']}")
            else:
                print(f"  [OK]         {ident}  score={r['score']} via {r['source']}")
                if r.get("year_check"):
                    print(f"      year:    {r['year_check']}")

        rate = sum(1 for r in results if r["status"] == "RATE")
        print(f"\n{len(results)} citation(s) checked · {len(bad)} problem(s) · "
              f"{len(unver)} unverifiable · {rate} rate-limited.")
        if unver:
            print("UNVERIFIABLE is not a pass. A citation with too few content words")
            print("to compare has not been checked — treat it as unchecked, not clean.")
        if bad:
            print("A DOI that resolves to the WRONG paper is worse than a missing DOI:")
            print("it looks verified and leads a reader to confident nonsense.")
    return 1 if any(r["status"] in ("FAIL", "MISMATCH") for r in results) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
