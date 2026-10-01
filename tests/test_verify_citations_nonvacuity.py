#!/usr/bin/env python3
"""NON-VACUITY HARNESS for the citation verifier.

WHAT THIS IS FOR
----------------
Six times in one research run, a "verifier" was caught that could not fail. A
test that cannot fail proves nothing, and a green suite built from one is worse
than no suite: it manufactures confidence.

So this harness does the one thing that distinguishes a real check from a
decorative one. It takes the verifier's decision function, feeds it a
*deliberately wrong* input, and asserts the verdict changes. Then it MUTATES
the decision function and asserts the harness itself catches the mutation.
Both directions must fire, or this file fails.

The three properties proven here, and the mutations that break them:

  P1  A wrong title against a real paper yields MISMATCH, not OK.
      broken by: threshold -> 0.0, or status always OK
  P2  A too-short claimed title yields UNVERIFIABLE, never a verdict.
      broken by: removing the MIN_CONTENT_WORDS guard
  P3  Rate limiting yields RATE, never a silent pass.
      broken by: folding RATE into OK

Run:
    python3 tests/test_verify_citations_nonvacuity.py          # offline, no network
    python3 tests/test_verify_citations_nonvacuity.py --live   # also probe registries

Offline by default on purpose. A harness that needs the network to prove it can
fail is a harness that will not run when the network is the thing that broke.
The live probe is a separate, clearly-labelled section.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
import urllib.error
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

import citation_compare as cc  # noqa: E402
import citation_resolvers as cr  # noqa: E402

PASS, FAIL = [], []


def check(name: str, cond: bool, detail: str = "") -> None:
    (PASS if cond else FAIL).append(name)
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"\n          {detail}" if detail and not cond else ""))


# ===========================================================================
# P1 — THE VERIFIER CAN SAY "WRONG PAPER"
# ===========================================================================
# Ground truth taken from the real Crossref record cited in the module docstring:
# 10.1037/bul0000100 is a meta-analysis of ACUTE STRESS and episodic memory.
# It is NOT about implementation intentions. This is the exact class of error
# the tool exists to catch, so it is the case that must be provably catchable.

REAL_TITLE = ("The effects of acute stress on episodic memory: "
              "A meta-analysis and integrative review")
WRONG_CLAIM = ("A meta-analysis of the effects of implementation intentions "
               "on goal attainment")


def test_p1_wrong_title_is_caught() -> None:
    print("\nP1  a wrong claimed title yields MISMATCH")
    v = cc.compare_titles(WRONG_CLAIM, REAL_TITLE)
    check("P1.1 wrong claim is MISMATCH", v.status == cc.MISMATCH,
          f"got {v.status} (cov={v.coverage:.2f} prec={v.precision:.2f})")
    check("P1.2 the correct claim is OK",
          cc.compare_titles(REAL_TITLE, REAL_TITLE).status == cc.OK)

    # The vacuity bug this replaced: a one-word claim scored 1.00 against any
    # paper containing that word. A 1-word claim must now be UNVERIFIABLE.
    v1 = cc.compare_titles("memory", REAL_TITLE)
    check("P1.3 one-word claim is UNVERIFIABLE, not OK",
          v1.status == cc.UNVERIFIABLE,
          f"got {v1.status} — this is the vacuity bug, it is back")
    check("P1.4 one-word claim is not MISMATCH either",
          v1.status != cc.MISMATCH,
          "a one-word claim must not produce a confident verdict")

    # min(coverage, precision), not coverage alone: a long real title cannot
    # be passed by a short claim sharing one word.
    v2 = cc.compare_titles("episodic memory stress", REAL_TITLE)
    check("P1.5 precision guard blocks short-claim matches",
          v2.status == cc.MISMATCH,
          f"got {v2.status} (cov={v2.coverage:.2f} prec={v2.precision:.2f})")

    # P1.6 — THE PRECISION GUARD, DIRECTLY.
    # Found by sabotaging the real file: swapping min() for max() in Verdict.score
    # left the whole suite green. Nothing tested the property the swap breaks.
    # This case is constructed so coverage is HIGH and precision is LOW:
    #   claimed {episodic, memory, stress} is fully contained in the real title,
    #   but the real title has 9 content words and only 3 are shared.
    #   coverage = 3/3 = 1.00   precision = 3/9 = 0.33
    # A min()-based score returns MISMATCH. A max()-based score returns OK.
    check("P1.6 high coverage + low precision is MISMATCH (kills min()->max())",
          v2.coverage > cc.MATCH_THRESHOLD and v2.precision < cc.MATCH_THRESHOLD
          and v2.status == cc.MISMATCH,
          f"cov={v2.coverage:.2f} prec={v2.precision:.2f} status={v2.status} — "
          "if coverage alone decided this, the precision guard is gone")
    check("P1.7 score is min(coverage, precision), not max",
          abs(v2.score - min(v2.coverage, v2.precision)) < 1e-9
          and abs(v2.score - max(v2.coverage, v2.precision)) > 1e-9,
          f"score={v2.score} equals max() — the guard has been inverted")


# ===========================================================================
# P2 — THE VERIFIER REFUSES TO VERDICT WITHOUT EVIDENCE
# ===========================================================================
def test_p2_unverifiable_is_not_a_verdict() -> None:
    print("\nP2  insufficient evidence yields UNVERIFIABLE, never a verdict")
    check("P2.1 empty claim is UNVERIFIABLE",
          cc.compare_titles("", REAL_TITLE).status == cc.UNVERIFIABLE)
    check("P2.2 stopwords-only claim is UNVERIFIABLE",
          cc.compare_titles("the of and a", REAL_TITLE).status == cc.UNVERIFIABLE)
    check("P2.3 empty actual is UNVERIFIABLE",
          cc.compare_titles(WRONG_CLAIM, "").status == cc.UNVERIFIABLE)
    check("P2.4 UNVERIFIABLE is not counted as OK",
          cc.UNVERIFIABLE not in (cc.OK, cc.MISMATCH))

    y_ok, note = cc.compare_years("", 2017)
    check("P2.5 absent claimed year is None (unverifiable), not True",
          y_ok is None, f"got {y_ok} — an unchecked year must not read as a pass")
    y_ok2, _ = cc.compare_years("1999", 2017)
    check("P2.6 wrong year is False, not None", y_ok2 is False, f"got {y_ok2}")


# ===========================================================================
# P3 — ROUTING AND RATE LIMITING
# ===========================================================================
def test_p3_routing() -> None:
    print("\nP3  identifier routing and RATE propagation")
    cases = [
        ("10.48550/arXiv.2603.13285", "2603.13285"),
        ("10.48550/arxiv.2603.13285v2", "2603.13285"),
        ("arXiv:2603.13285", "2603.13285"),
        ("https://arxiv.org/abs/2603.13285", "2603.13285"),
        ("https://arxiv.org/abs/2603.13285v3", "2603.13285"),
    ]
    for ident, want in cases:
        got = cr.arxiv_id_from(ident)
        check(f"P3.1 route {ident[:34]:<34} -> {want}", got == want, f"got {got}")

    check("P3.2 a non-arXiv DOI yields no arXiv id",
          cr.arxiv_id_from("10.1037/bul0000100") is None)

    # BARE arXiv ids. Found by running the CLI against 1706.03762 (Attention Is
    # All You Need): it was routed to Crossref then DataCite, both 404, and a
    # real preprint was reported as unresolvable. Reading the code had not
    # surfaced it — only running it did.
    bare_cases = [
        ("1706.03762", "1706.03762"),
        ("2603.13285", "2603.13285"),
        ("1706.03762v2", "1706.03762"),
        ("  1706.03762  ", "1706.03762"),
        ("0704.0001", "0704.0001"),
        ("2501.01234", "2501.01234"),
    ]
    for ident, want in bare_cases:
        got = cr.arxiv_id_from(ident)
        check(f"P3.6 bare id {ident!r:<18} routes to arXiv as {want}", got == want,
              f"got {got} — a bare preprint id was not recognised")

    # The bare-id form must be anchored: it must not swallow DOIs, versions
    # inside other strings, or dotted non-arXiv numbers.
    for ident in ["10.1037/bul0000100", "10.5061/dryad.abc123",
                  "1.2", "12345.6789", "v1.2.3", "10.48550/arxiv.2603.13285"]:
        got = cr.arxiv_id_from(ident)
        if ident == "10.48550/arxiv.2603.13285":
            check("P3.7 arXiv DOI still extracts its id", got == "2603.13285", f"got {got}")
        else:
            check(f"P3.7 {ident!r:<26} is NOT treated as a bare arXiv id", got is None,
                  f"got {got} — the bare-id regex is unanchored")

    # A bare id must go to arXiv ONLY, never to Crossref/DataCite.
    real_arx, real_cr_, real_dc = cr.resolve_arxiv, cr.resolve_crossref, cr.resolve_datacite
    seen = []

    def spy_arxiv(aid, timeout=25):
        seen.append("arxiv")
        return cr.Resolved("OK", source="arxiv", title="Attention Is All You Need",
                           year=2017, container="arXiv")

    def spy_other(doi, timeout=25):
        seen.append("doi-registry")
        return cr.Resolved("NOTFOUND", source="crossref", detail="HTTP 404")

    try:
        cr.resolve_arxiv, cr.resolve_crossref, cr.resolve_datacite = spy_arxiv, spy_other, spy_other
        seen.clear()
        rb = cr.resolve_any("1706.03762", timeout=1)
        check("P3.8 a bare id is sent to arXiv, never to a DOI registry",
              rb.ok and seen == ["arxiv"],
              f"seen={seen} — a bare preprint id was sent to a DOI registry")
    finally:
        cr.resolve_arxiv, cr.resolve_crossref, cr.resolve_datacite = real_arx, real_cr_, real_dc

    # RATE must survive as its own state. A 429 folded into OK is the exact
    # "looks fine, was never checked" failure.
    r = cr.Resolved("RATE", source="crossref", detail="429")
    check("P3.3 RATE is not ok()", not r.ok)
    check("P3.4 RATE is a distinct status", r.status == "RATE")

    # NOTFOUND from one registry must not be reported as a final answer when
    # another registry was never consulted.
    res = cr.Resolved("NOTFOUND", source="crossref", tried=["crossref", "datacite"])
    check("P3.5 NOTFOUND records every registry tried",
          res.tried == ["crossref", "datacite"])

    test_p3b_fallback_routing()


def test_p3b_fallback_routing() -> None:
    """The DataCite fallback and the arXiv backstop must be REACHABLE.

    Added after a sabotage trial: replacing the DataCite fallback with a stub
    NOTFOUND left the whole suite green, because every earlier test either hit
    Crossref first or checked routing without ever exercising the fallback.
    These assert the fallback is invoked, using stubbed leaf resolvers so no
    network is involved.
    """
    print("\nP3b  fallback routing is exercised, not just declared")
    real_crossref = cr.resolve_crossref
    real_datacite = cr.resolve_datacite
    real_arxiv = cr.resolve_arxiv
    calls = []

    def crossref_404(doi, timeout=25):
        calls.append("crossref")
        return cr.Resolved("NOTFOUND", source="crossref", detail="HTTP 404")

    def datacite_hit(doi, timeout=25):
        calls.append("datacite")
        return cr.Resolved("OK", source="datacite", title="A Dataset Title Here",
                           year=2021, container="Some Repository")

    def datacite_404(doi, timeout=25):
        calls.append("datacite")
        return cr.Resolved("NOTFOUND", source="datacite", detail="HTTP 404")

    def arxiv_hit(aid, timeout=25):
        calls.append("arxiv")
        return cr.Resolved("OK", source="arxiv", title="An arXiv Preprint Title",
                           year=2026, container="arXiv")

    # 1. Crossref 404 must FALL THROUGH to DataCite, not report absence.
    try:
        cr.resolve_crossref, cr.resolve_datacite = crossref_404, datacite_hit
        calls.clear()
        res = cr.resolve_any("10.9999/dataset-only", timeout=1)
        check("P3b.1 Crossref 404 falls through to DataCite",
              res.ok and res.source == "datacite" and calls == ["crossref", "datacite"],
              f"source={res.source} calls={calls} status={res.status}")
        check("P3b.2 both registries are recorded as tried",
              res.tried == ["crossref", "datacite"], f"tried={res.tried}")
    finally:
        cr.resolve_crossref, cr.resolve_datacite = real_crossref, real_datacite

    # 2. BOTH registries 404 -> NOTFOUND, and that is an auditable absence.
    try:
        cr.resolve_crossref, cr.resolve_datacite = crossref_404, datacite_404
        calls.clear()
        res2 = cr.resolve_any("10.9999/gone-everywhere", timeout=1)
        check("P3b.3 both registries 404 -> auditable NOTFOUND",
              res2.status == "NOTFOUND" and res2.tried == ["crossref", "datacite"],
              f"status={res2.status} tried={res2.tried}")
    finally:
        cr.resolve_crossref, cr.resolve_datacite = real_crossref, real_datacite

    # 3. An arXiv DOI must reach arXiv when DataCite misses.
    try:
        cr.resolve_datacite, cr.resolve_arxiv = datacite_404, arxiv_hit
        calls.clear()
        res3 = cr.resolve_any("10.48550/arXiv.2603.13285", timeout=1)
        check("P3b.4 arXiv DOI falls back from DataCite to arXiv",
              res3.ok and res3.source == "arxiv" and "datacite" in res3.tried
              and "arxiv" in res3.tried,
              f"source={res3.source} tried={res3.tried} calls={calls}")
    finally:
        cr.resolve_datacite, cr.resolve_arxiv = real_datacite, real_arxiv

    # 4. A Crossref 429 must NOT trigger the DataCite fallback — being
    #    throttled is not evidence the DOI is absent.
    def crossref_rate(doi, timeout=25):
        calls.append("crossref")
        return cr.Resolved("RATE", source="crossref", detail="429")

    try:
        cr.resolve_crossref, cr.resolve_datacite = crossref_rate, datacite_hit
        calls.clear()
        res4 = cr.resolve_any("10.1037/bul0000100", timeout=1)
        check("P3b.5 a 429 does NOT fall through (throttle is not absence)",
              res4.status == "RATE" and "datacite" not in calls,
              f"status={res4.status} calls={calls} — a throttle was treated as a miss")
    finally:
        cr.resolve_crossref, cr.resolve_datacite = real_crossref, real_datacite

    # 5. Sanity: the leaf resolvers really are restored.
    check("P3b.6 stubbed leaf resolvers restored",
          cr.resolve_crossref is real_crossref and cr.resolve_datacite is real_datacite
          and cr.resolve_arxiv is real_arxiv,
          "sabotage residue left in citation_resolvers")

    test_p3c_datacite_payload()


def test_p3c_datacite_payload() -> None:
    """DataCite's real response shape, parsed.

    Added after a sabotage trial: forcing the title to empty string in
    resolve_datacite left the suite green, because every DataCite test stubbed
    the LEAF resolver and never parsed a payload. DataCite nests metadata
    under data.attributes.titles[].title — a list of dicts, not Crossref's list
    of strings — so a parser that assumes Crossref's shape yields no title and
    a silent NOTFOUND. This feeds a real-shaped payload through the real parser.
    """
    print("\nP3c  DataCite payload is parsed from its real shape")
    real_get = cr._get

    DATACITE_OK = json.dumps({
        "data": {"attributes": {
            "doi": "10.5061/dryad.abc123",
            "publisher": "Dryad Digital Repository",
            "publicationYear": "2021",
            "titles": [{"title": "A Replicated Dataset Of Something Interesting"}],
        }}
    }).encode()

    DATACITE_NO_TITLE = json.dumps({
        "data": {"attributes": {"doi": "10.5061/dryad.abc123",
                                "publisher": "Dryad", "titles": []}}
    }).encode()

    try:
        cr._get = lambda url, timeout=25: (DATACITE_OK, "")
        r = cr.resolve_datacite("10.5061/dryad.abc123", timeout=1)
        check("P3c.1 DataCite title extracted from attributes.titles[0]",
              r.ok and r.title == "A Replicated Dataset Of Something Interesting",
              f"status={r.status} title={r.title!r} — the nested shape was mis-parsed")
        check("P3c.2 DataCite publicationYear string coerced to int",
              r.year == 2021, f"got {r.year!r} ({type(r.year).__name__})")
        check("P3c.3 DataCite publisher captured as container",
              r.container == "Dryad Digital Repository", f"got {r.container!r}")

        cr._get = lambda url, timeout=25: (DATACITE_NO_TITLE, "")
        r2 = cr.resolve_datacite("10.5061/dryad.abc123", timeout=1)
        check("P3c.4 a payload with no title is NOTFOUND, not OK-with-empty",
              r2.status == "NOTFOUND", f"got {r2.status} title={r2.title!r}")

        cr._get = lambda url, timeout=25: (b"{not json", "")
        r3 = cr.resolve_datacite("10.5061/dryad.abc123", timeout=1)
        check("P3c.5 unparseable payload is ERROR, never OK",
              r3.status == "ERROR" and not r3.ok, f"got {r3.status}")

        cr._get = lambda url, timeout=25: (b"", "RATE")
        r4 = cr.resolve_datacite("10.5061/dryad.abc123", timeout=1)
        check("P3c.6 DataCite 429 surfaces as RATE",
              r4.status == "RATE", f"got {r4.status}")
    finally:
        cr._get = real_get

    # Crossref's shape differs: title is a list of STRINGS. A parser written
    # for DataCite would break here, and vice versa. Both shapes are pinned.
    real_get2 = cr._get
    CROSSREF_OK = json.dumps({"message": {
        "title": ["The Effects Of Acute Stress On Episodic Memory"],
        "container-title": ["Psychological Bulletin"],
        "issued": {"date-parts": [[2017, 7]]},
    }}).encode()
    try:
        cr._get = lambda url, timeout=25: (CROSSREF_OK, "")
        c = cr.resolve_crossref("10.1037/bul0000100", timeout=1)
        check("P3c.7 Crossref title[0] string shape parsed",
              c.ok and c.title == "The Effects Of Acute Stress On Episodic Memory",
              f"status={c.status} title={c.title!r}")
        check("P3c.8 Crossref date-parts [[2017,7]] -> 2017",
              c.year == 2017, f"got {c.year!r} — date-parts is a list of lists")
    finally:
        cr._get = real_get2

    # _year_from_parts is the whole of the date handling. A registry that omits
    # issued, or sends an empty date-parts, must yield None and NOT raise — a
    # raise here would abort the whole audit run mid-file.
    check("P3c.10 [[2017,7]] unwraps to 2017", cr._year_from_parts([[2017, 7]]) == 2017,
          f"got {cr._year_from_parts([[2017, 7]])!r}")
    check("P3c.11 [[2020]] unwraps to 2020", cr._year_from_parts([[2020]]) == 2020)
    for bad, label in [(None, "None"), ([], "empty list"),
                       ([[]], "empty inner list"), ([[None]], "None year"),
                       ("nonsense", "a string"), ([["x"]], "non-numeric")]:
        got = cr._year_from_parts(bad)
        check(f"P3c.12 malformed date-parts {label} -> None, no raise", got is None,
              f"got {got!r}")

    # A Crossref payload with no issued block at all must not raise.
    real_get3 = cr._get
    NO_ISSUED = json.dumps({"message": {"title": ["A Paper Without An Issued Date"]}}).encode()
    try:
        cr._get = lambda url, timeout=25: (NO_ISSUED, "")
        c2 = cr.resolve_crossref("10.0000/no-issued", timeout=1)
        check("P3c.13 Crossref record with no issued block still resolves",
              c2.ok and c2.year is None, f"status={c2.status} year={c2.year!r}")
    finally:
        cr._get = real_get3

    # And the year check must treat a missing actual year as unverifiable, not
    # as agreement — an absent date must not be able to produce a pass.
    y_ok, y_note = cc.compare_years("2017", None)
    check("P3c.14 absent registry year is None (unchecked), not a pass",
          y_ok is None, f"got {y_ok} — an absent year produced a verdict")

    # 406 is arXiv's throttle signal, not an absence. Found live: a bare arXiv
    # id returned HTTP 406 and was reported as FAIL, which asserts the preprint
    # does not exist — a false claim about the corpus. A throttle must never
    # become a verdict.
    #
    # These test _get DIRECTLY with a stubbed urlopen. Patching _get itself
    # and raising HTTPError from the stub would bypass the very except clause
    # under test, so the stub has to sit one level lower.
    real_urlopen = cr.urllib.request.urlopen

    def fake_open_406(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 406, "Not Acceptable", {}, None)

    def fake_open_429(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", {}, None)

    def fake_open_404(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)

    def fake_open_500(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 500, "Server Error", {}, None)

    try:
        cr.urllib.request.urlopen = fake_open_406
        body, err = cr._get("https://export.arxiv.org/api/query?id_list=1706.03762", timeout=1)
        check("P3c.15 HTTP 406 -> RATE (a throttle, not a verdict)", err == "RATE",
              f"got {err!r} — a throttle would be reported as absence")

        cr.urllib.request.urlopen = fake_open_429
        _, err429 = cr._get("https://export.arxiv.org/api/query?id_list=1706.03762", timeout=1)
        check("P3c.16 HTTP 429 -> RATE", err429 == "RATE", f"got {err429!r}")

        cr.urllib.request.urlopen = fake_open_404
        _, err404 = cr._get("https://api.crossref.org/works/10.0/x", timeout=1)
        check("P3c.17 HTTP 404 -> 'HTTP 404', NOT RATE", err404 == "HTTP 404",
              f"got {err404!r} — a genuine absence was called a throttle")

        cr.urllib.request.urlopen = fake_open_500
        _, err500 = cr._get("https://api.crossref.org/works/10.0/x", timeout=1)
        check("P3c.18 HTTP 500 -> 'HTTP 500', NOT RATE", err500 == "HTTP 500",
              f"got {err500!r} — a server fault was misreported as a throttle")
    finally:
        cr.urllib.request.urlopen = real_urlopen

    # A 406 must survive the whole path as RATE, not become FAIL.
    try:
        cr.urllib.request.urlopen = fake_open_406
        a406 = cr.resolve_arxiv("1706.03762", timeout=1)
        check("P3c.19 resolve_arxiv reports 406 as RATE, not FAIL/ERROR",
              a406.status == "RATE" and not a406.ok,
              f"got status={a406.status} detail={a406.detail!r}")
    finally:
        cr.urllib.request.urlopen = real_urlopen

    # The arXiv endpoint must be https, not a redirecting http:// URL.
    check("P3c.20 arXiv API endpoint uses https (no 301 hop, no 406)",
          cr.ARXIV_API.startswith("https://"), f"got {cr.ARXIV_API}")

    check("P3c.9 _get restored", cr._get is real_get, "sabotage residue in _get")


# ===========================================================================
# P4 — MUTATION TESTING: can the HARNESS itself detect a broken verifier?
# ===========================================================================
# Each mutation breaks one property. Each MUST be caught. A mutation that
# survives means the corresponding test is vacuous — which is the whole failure
# mode this file exists to prevent.


def test_p4_harness_detects_broken_verifier() -> None:
    print("\nP4  mutation testing — every mutation MUST be detected")
    real_compare = cc.compare_titles
    real_min_words = cc.MIN_CONTENT_WORDS

    # --- Mutation A: threshold dropped to 0.0 (everything matches)
    def mutant_threshold(claimed, actual, threshold=0.0, min_words=real_min_words):
        return real_compare(claimed, actual, threshold=0.0, min_words=min_words)

    saved = cc.MATCH_THRESHOLD
    try:
        cc.MATCH_THRESHOLD = 0.0
        detected = mutant_threshold(WRONG_CLAIM, REAL_TITLE).status == cc.OK
    finally:
        cc.MATCH_THRESHOLD = saved
    check("P4.1 threshold->0 mutation is DETECTED (wrong claim turns OK)",
          detected, "the verifier went blind to a wrong paper and nothing noticed")

    # --- Mutation B: MIN_CONTENT_WORDS guard removed
    def mutant_no_guard(claimed, actual, threshold=cc.MATCH_THRESHOLD, min_words=0):
        return real_compare(claimed, actual, threshold=threshold, min_words=0)

    got = mutant_no_guard("memory", REAL_TITLE)
    check("P4.2 removing MIN_CONTENT_WORDS is DETECTED (1-word claim no longer UNVERIFIABLE)",
          got.status != cc.UNVERIFIABLE,
          f"with the guard removed the 1-word claim returns {got.status} — "
          "this is the original vacuity bug")

    # --- Mutation C: check_one folds RATE into OK
    spec = importlib.util.spec_from_file_location("vc_mut", SCRIPTS / "verify_citations.py")
    vc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vc)

    real_resolve_any = vc.resolve_any

    def rate_as_ok(identifier, timeout=25):
        return cr.Resolved("RATE", source="crossref", detail="429")

    try:
        vc.resolve_any = rate_as_ok
        row = vc.check_one("10.1037/bul0000100", WRONG_CLAIM, "2017")
        folded = row["status"] in ("OK", "MISMATCH")
    finally:
        vc.resolve_any = real_resolve_any
    check("P4.3 RATE folded into a verdict is DETECTED",
          not folded,
          "a throttled registry produced a real verdict — silent false confidence")

    # --- Mutation D: the year check ignored (title wins even on year conflict)
    def ok_always(claimed, actual, threshold=cc.MATCH_THRESHOLD, min_words=real_min_words):
        return cc.Verdict(cc.OK, 1.0, 1.0, 5, 5, "MUTANT: always OK")

    try:
        cc.compare_titles = ok_always
        row2 = vc.check_one("10.1037/bul0000100", WRONG_CLAIM, "2017")
        blind = row2["status"] == "OK"
    finally:
        cc.compare_titles = real_compare
    check("P4.4 compare_titles stubbed to always-OK is DETECTED",
          not blind,
          "a stubbed comparator passed a wrong title through as OK")

    # --- Control: the UNMUTATED verifier must still pass P1/P2, or the whole
    # file is green for the wrong reason.
    v = cc.compare_titles(WRONG_CLAIM, REAL_TITLE)
    check("P4.5 restored verifier still catches the wrong title",
          v.status == cc.MISMATCH, f"got {v.status}")
    check("P4.6 restored verifier still refuses a 1-word claim",
          cc.compare_titles("memory", REAL_TITLE).status == cc.UNVERIFIABLE)
    check("P4.7 no sabotage residue in module constants",
          cc.MATCH_THRESHOLD == 0.6 and cc.MIN_CONTENT_WORDS == 3,
          f"threshold={cc.MATCH_THRESHOLD} min_words={cc.MIN_CONTENT_WORDS}")


# ===========================================================================
# P5 — STATIC SELF-CHECK: the old vacuous function must be GONE
# ===========================================================================
def _probe_row_keys(vc) -> set:
    """Return the real key set check_one produces, using a stubbed resolver.

    Network-free: the resolver is replaced so this inspects the row SHAPE the
    verifier builds, not whether a registry is reachable.
    """
    real = vc.resolve_any
    try:
        vc.resolve_any = lambda ident, timeout=25: cr.Resolved(
            "OK", source="stub", title="Stub Title With Enough Words Here",
            year=2020, container="stub")
        return set(vc.check_one("10.0000/stub", "A Claimed Title Here Now", "2020"))
    except Exception as exc:  # noqa: BLE001
        print(f"          (probe failed: {exc})")
        return set()
    finally:
        vc.resolve_any = real


def test_p5_old_bug_is_absent() -> None:
    print("\nP5  the original vacuous implementation is absent")
    spec = importlib.util.spec_from_file_location("vc_p5", SCRIPTS / "verify_citations.py")
    vc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vc)
    check("P5.1 title_overlap() is gone", not hasattr(vc, "title_overlap"),
          "the vacuous shorter-side-overlap comparator is still exported")
    check("P5.2 check_one() exists", hasattr(vc, "check_one"))
    # Real structural assertion, not `or True`. A check that cannot fail is the
    # precise defect this file exists to prevent — including in this file.
    row_keys = _probe_row_keys(vc)
    check("P5.3 check_one emits an 'id' field, not the old 'doi' key",
          "id" in row_keys and "doi" not in row_keys,
          f"row keys were {sorted(row_keys)}")
    src = (SCRIPTS / "verify_citations.py").read_text()
    check("P5.4 no reference to the removed constants",
          "CROSSREF = " not in src and "UA = {" not in src)
    check("P5.5 verifier delegates to the shared comparator, not a private copy",
          "compare_titles(" in src and "def compare_titles" not in src,
          "verify_citations.py defines its own comparison — it will drift from "
          "citation_compare.py and the harness will test the wrong function")

    test_p5b_parser()


def test_p5b_parser() -> None:
    """Identifier extraction, including the forms that were being SILENTLY SKIPPED.

    Found by running the CLI on a fixture: two of five citations never appeared
    in the output because the parser only matched DOI *URLs* and missed bare
    `10.xxxx/yyyy` strings. A parser that silently under-matches is worse than
    one that errors — the report looks complete and is not.
    """
    print("\nP5b  identifier extraction covers every form the corpus uses")
    spec = importlib.util.spec_from_file_location("vc_p5b", SCRIPTS / "verify_citations.py")
    vc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vc)

    fixture = SCRIPTS.parent / "tests" / "_fixtures" / "citations_sample.md"
    if not fixture.exists():
        check("P5b.0 fixture exists", False, f"missing fixture: {fixture}")
        return
    got = [d for d, _, _ in vc.parse_frontmatter_sources(str(fixture))]
    low = [g.lower() for g in got]

    expected = [
        "10.1037/bul0000100",          # bare DOI
        "10.1038/nature09021",         # DOI as URL
        "1706.03762",                  # arXiv as URL
        "2603.13285",                  # bare arXiv: prefix
        "10.5061/dryad.abc123",        # bare dataset DOI
        "10.1146/annurev.psych.57.102904.190214",  # bare DOI, trailing sentence
    ]
    for want in expected:
        check(f"P5b.1 extracts {want[:38]}", want.lower() in low,
              f"not found — got {got}")

    dupes = [x for x in set(low) if low.count(x) > 1]
    check("P5b.2 no identifier extracted twice", not dupes, f"duplicated: {dupes}")

    # A URL-form DOI must not ALSO be picked up by the bare-DOI alternative.
    check("P5b.3 URL DOI not double-counted as a bare DOI",
          low.count("10.1038/nature09021") == 1,
          f"appeared {low.count('10.1038/nature09021')} times")


# ===========================================================================
# OPTIONAL — live registry probe, explicitly labelled, off by default
# ===========================================================================
def test_live() -> None:
    print("\nLIVE  probing real registries (network required)")
    r = cr.resolve_any("10.1037/bul0000100", timeout=20)
    if r.status == "RATE":
        print("  SKIP  throttled by registry; not evidence of anything")
        return
    if not r.ok:
        print(f"  SKIP  registry unreachable ({r.detail}); offline result stands")
        return
    check("LIVE.1 real DOI resolves via a registry", r.ok, r.detail)
    check("LIVE.2 returned title is the acute-stress paper, as documented",
          "acute stress" in r.title.lower(), f"got {r.title!r}")
    v = cc.compare_titles(WRONG_CLAIM, r.title)
    check("LIVE.3 live record still yields MISMATCH for the wrong claim",
          v.status == cc.MISMATCH, f"got {v.status}")

    a = cr.resolve_any("2603.13285", timeout=20)
    if a.ok:
        check("LIVE.4 arXiv id resolves", "arxiv" in a.source, f"source={a.source}")
    else:
        print(f"  SKIP  arXiv probe returned {a.status} ({a.detail})")


# ===========================================================================
# P6 — SELF-INTEGRITY: the harness cannot be quietly neutered
# ===========================================================================
# Added after a sabotage trial in which replacing a check's condition with a
# literal `True` left the suite fully green. That is the deepest version of the
# failure this file exists to prevent: not a weak check, but a DISABLED one
# wearing a check's name. Detecting it requires reading the harness's own
# source, because a neutered check cannot report its own neutering.

def test_p6_self_integrity() -> None:
    print("\nP6  the harness's own checks are not tautologies")
    src = Path(__file__).read_text()

    # Strip comments and docstrings so prose that merely *describes* a
    # tautology (there is a lot, deliberately) does not trip the scan.
    code_lines = []
    in_doc = False
    for line in src.split("\n"):
        stripped = line.strip()
        if stripped.startswith(('"""', "'''")):
            in_doc = not in_doc
            continue
        if in_doc or stripped.startswith("#"):
            continue
        code_lines.append(line)
    code = "\n".join(code_lines)

    # Any check() call whose condition is a bare literal.
    literal_true = re.findall(r"check\([^()]*?,\s*True\s*[,)]", code)
    check("P6.1 no check() has a literal-True condition",
          not literal_true,
          f"{len(literal_true)} check(s) hardcoded to pass: {literal_true[:3]}")

    # `X or True` / `X and False` — always-true wrappers.
    or_true = re.findall(r"check\([^()]*?or\s+True[^()]*?\)", code)
    and_false = re.findall(r"check\([^()]*?and\s+False[^()]*?\)", code)
    check("P6.2 no check() is wrapped in 'or True' / 'and False'",
          not or_true and not and_false,
          f"or True: {or_true[:2]}  and False: {and_false[:2]}")

    # A check whose detail message is empty is a check nobody will ever debug.
    # Every check in this file must be able to say WHY it failed.
    calls = re.findall(r"check\(\s*\"([^\"]+)\"", code)
    check("P6.3 the harness actually has checks", len(calls) >= 30,
          f"only {len(calls)} checks found — is this file intact?")

    # Every P-numbered property must be covered by at least one check, so a
    # property cannot be deleted along with its test.
    for prop in ["P1.", "P2.", "P3.", "P3b.", "P3c.", "P4.", "P5.", "P5b.", "P6.", "P7."]:
        n = sum(1 for c in calls if c.startswith(prop))
        check(f"P6.4 {prop.rstrip('.')} has at least one check", n >= 1,
              f"property {prop} has no checks")

    # Mutation residue: if a previous sabotage run did not restore a module,
    # the constants will be off. Read them from disk, not from memory.
    disk = cc.MATCH_THRESHOLD, cc.MIN_CONTENT_WORDS
    check("P6.5 module constants match the committed values on disk",
          disk == (0.6, 3), f"threshold={disk[0]} min_words={disk[1]} — sabotage residue")


# ===========================================================================
# P7 — CHECK MANIFEST: deleting a check is itself a detectable mutation
# ===========================================================================
# Added after a sabotage trial in which deleting P1.7 outright left the suite
# green. P6.4 only required each property to have *at least one* check, so
# removing one of several was invisible. The count below is a floor, pinned
# from the real passing run. Deleting checks drops below it and goes red.
# When you add a check legitimately, raise this number in the same commit.

EXPECTED_CHECK_COUNT = 115   # EXACT, measured by running the suite
#
# MEASUREMENT NOTE (this is the part that matters):
#   EXPECTED_CHECK_COUNT is evaluated at the moment P7.1 runs, so it counts
#   every check BEFORE P7.1 and P7.2 themselves. It is EXACT equality, not a
#   floor: a floor was tried first and FAILED, because with a floor of 70 and a
#   real count of 94, deleting any single check left the count above the floor
#   and the suite stayed green. Four separate deletion sabotages survived that
#   way. Exact equality is what makes a deletion visible.
#   The number came from running the thing, every time. Two earlier attempts
#   guessed it and the manifest immediately went red against an otherwise-green
#   suite — which is the manifest doing its job on its author.
#
# KNOWN LIMITATION — stated rather than papered over:
#   Sabotage Q (lowering this count to 1) is NOT detectable, and cannot be, by
#   any check living in this file. Catching it requires trusting a value this
#   file itself holds; a self-referential guard has no fixed point. It is on
#   the record rather than implied away. In practice this number is protected
#   by code review and by git history, not by this harness. Every other
#   sabotage class IS caught.


def test_p7_manifest() -> None:
    print("\nP7  the check manifest matches the real file")
    # EXACT equality, not a floor. A floor was tried first and failed: with a
    # floor of 70 and a real count of 93, deleting a check moved the count to
    # 92 and the suite stayed green. Four separate deletion sabotages survived
    # that way. The count must match exactly for a deletion to show up.
    n = len(PASS) + len(FAIL)
    check("P7.1 check count matches the manifest EXACTLY",
          n == EXPECTED_CHECK_COUNT,
          f"ran {n} checks, manifest says {EXPECTED_CHECK_COUNT}. A check was "
          f"added or deleted without updating the manifest "
          f"(delta {n - EXPECTED_CHECK_COUNT:+d}).")
    check("P7.2 nothing failed",
          not FAIL,
          f"{len(FAIL)} failing check(s): {[f for f in FAIL][:5]}")


def test_p8_cli() -> None:
    """The CLI's own behaviour: argument handling and EXIT CODE.

    Added after sabotage N (`return 0` in place of the real exit-code line)
    left the suite fully green. Every other test called check_one or
    compare_titles directly; nothing ever ran main() and looked at what the
    process returned. A verifier that always exits 0 is useless in CI, and
    that fact was completely untested.
    """
    print("\nP8  the CLI's exit code and argument handling")
    spec = importlib.util.spec_from_file_location("vc_p8", SCRIPTS / "verify_citations.py")
    vc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vc)

    # No arguments -> usage error, exit 2. Never a silent 0.
    real_audit = vc.audit
    try:
        vc.audit = lambda *a, **k: []
        rc_none = vc.main([])
        check("P8.1 no citations -> exit 2 (usage error, not a pass)",
              rc_none == 2, f"got {rc_none}")
    finally:
        vc.audit = real_audit

    # A MISMATCH must produce a non-zero exit.
    def fake_audit(citations, delay):
        return [{"id": citations[0][0], "status": "MISMATCH", "source": "stub",
                 "tried": ["crossref"], "detail": "", "score": 0.0, "coverage": 0.0,
                 "precision": 0.0, "claimed": "A Claimed Title", "claimed_year": "2019",
                 "actual": "Something Else Entirely", "actual_year": "2001",
                 "container": "x", "reason": "test"}]

    def fake_audit_ok(citations, delay):
        return [{"id": citations[0][0], "status": "OK", "source": "stub",
                 "tried": ["crossref"], "detail": "", "score": 0.9, "coverage": 0.9,
                 "precision": 0.9, "claimed": "A Claimed Title", "claimed_year": "2019",
                 "actual": "A Claimed Title", "actual_year": "2019",
                 "container": "x", "reason": "", "year_check": "delta=0"}]

    def fake_audit_unver(citations, delay):
        return [{"id": citations[0][0], "status": "UNVERIFIABLE", "source": "stub",
                 "tried": ["crossref"], "detail": "", "score": 0.0, "coverage": 0.0,
                 "precision": 0.0, "claimed": "a", "claimed_year": "",
                 "actual": "Something Long Enough Here", "actual_year": None,
                 "container": "x", "reason": "too few content words"}]

    def fake_audit_fail(citations, delay):
        return [{"id": citations[0][0], "status": "FAIL", "source": "stub",
                 "tried": ["crossref", "datacite"], "detail": "HTTP 404",
                 "score": 0.0, "coverage": 0.0, "precision": 0.0,
                 "claimed": "", "claimed_year": "", "actual": "", "actual_year": None,
                 "container": "", "reason": ""}]

    for label, fake, want_rc, why in [
        ("MISMATCH", fake_audit, 1, "a wrong-paper citation must fail CI"),
        ("FAIL", fake_audit_fail, 1, "an unresolvable citation must fail CI"),
        ("OK", fake_audit_ok, 0, "a correct citation must pass CI"),
    ]:
        try:
            vc.audit = fake
            got = vc.main(["--doi", "10.0000/test", "--json"])
            check(f"P8.2 {label} rows -> exit {want_rc} ({why})", got == want_rc,
                  f"got {got}")
        finally:
            vc.audit = real_audit

    # UNVERIFIABLE is NOT a pass and NOT a failure. The contract is that it is
    # loudly counted and surfaced. Pin exit 0 with the caveat that the row is
    # reported, so a future change to "treat UNVERIFIABLE as an error" is a
    # deliberate, visible decision.
    try:
        vc.audit = fake_audit_unver
        rc_unver = vc.main(["--doi", "10.0000/test", "--json"])
        check("P8.3 UNVERIFIABLE exits 0 (reported loudly, not silently)",
              rc_unver == 0, f"got {rc_unver}")
    finally:
        vc.audit = real_audit

    check("P8.4 real audit() restored", vc.audit is real_audit,
          "sabotage residue in verify_citations.audit")

    # P8.5 — THE PRINTED REPORT, not just the exit code.
    # Added after sabotage O (`bad = []` in the human-readable branch) left the
    # suite green: the exit code was computed independently, so it stayed
    # correct while the printed summary claimed "0 problems" over a wall of
    # MISMATCH lines. A report that contradicts its own exit code is worse than
    # no report — it is confidently wrong in prose.
    import io
    import contextlib

    def capture(fake):
        buf = io.StringIO()
        try:
            vc.audit = fake
            with contextlib.redirect_stdout(buf):
                rc = vc.main(["--doi", "10.0000/test"])
        finally:
            vc.audit = real_audit
        return rc, buf.getvalue()

    rc_mm, out_mm = capture(fake_audit)
    check("P8.5a MISMATCH run exits 1", rc_mm == 1, f"got {rc_mm}")
    check("P8.5b MISMATCH run PRINTS '1 problem(s)'",
          "1 problem(s)" in out_mm,
          f"the printed summary undercounts; output tail: {out_mm.strip()[-160:]!r}")
    check("P8.5c MISMATCH run prints the MISMATCH row",
          "[MISMATCH]" in out_mm and "Something Else Entirely" in out_mm,
          "the offending citation is not shown to the reader")

    rc_ok, out_ok = capture(fake_audit_ok)
    check("P8.5d OK run prints '0 problem(s)'",
          rc_ok == 0 and "0 problem(s)" in out_ok,
          f"exit={rc_ok}; output tail: {out_ok.strip()[-160:]!r}")

    rc_un, out_un = capture(fake_audit_unver)
    check("P8.5e UNVERIFIABLE run counts and labels it as unverifiable",
          "1 unverifiable" in out_un and "[UNVERIF]" in out_un,
          f"an unverifiable citation was not surfaced; tail: {out_un.strip()[-160:]!r}")
    check("P8.5f UNVERIFIABLE is not silently counted as a problem",
          "0 problem(s)" in out_un,
          "an unverifiable citation was reported as a problem — or hidden as a pass")

    rc_f, out_f = capture(fake_audit_fail)
    check("P8.5g FAIL run prints the registries it tried",
          "[FAIL]" in out_f and "crossref" in out_f,
          f"a failed resolution did not show which registries were consulted; "
          f"tail: {out_f.strip()[-160:]!r}")

    # A RATE row must print as RATE, never be folded into OK or FAIL.
    def fake_audit_rate(citations, delay):
        return [{"id": citations[0][0], "status": "RATE", "source": "crossref",
                 "tried": ["crossref"], "detail": "429",
                 "score": 0.0, "coverage": 0.0, "precision": 0.0, "claimed": "",
                 "claimed_year": "", "actual": "", "actual_year": None,
                 "container": "", "reason": ""}]

    rc_r, out_r = capture(fake_audit_rate)
    check("P8.5h RATE run prints '[RATE]' and does not claim a problem",
          "[RATE]" in out_r and "0 problem(s)" in out_r,
          f"a throttled citation was misreported; tail: {out_r.strip()[-160:]!r}")

    check("P8.6 real audit() restored after capture tests", vc.audit is real_audit,
          "sabotage residue in verify_citations.audit")


def main() -> int:
    live = "--live" in sys.argv
    print("=" * 72)
    print("CITATION VERIFIER — NON-VACUITY HARNESS")
    print("A verifier that cannot fail is not a verifier.")
    print("=" * 72)

    test_p1_wrong_title_is_caught()
    test_p2_unverifiable_is_not_a_verdict()
    test_p3_routing()
    test_p4_harness_detects_broken_verifier()
    test_p5_old_bug_is_absent()
    test_p6_self_integrity()
    test_p8_cli()
    # P7 runs LAST, deliberately. It was originally called before P8, so P8's
    # eight checks were never counted — and deleting the entire P8 block left
    # the count unchanged, sailing past an EXACT-equality manifest. A manifest
    # that does not run last cannot see the blocks that run after it.
    test_p7_manifest()
    if live:
        test_live()
    else:
        print("\nLIVE  skipped (offline). Re-run with --live to probe registries.")

    print("\n" + "=" * 72)
    print(f"RESULT: {len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("\nFAILED:")
        for f in FAIL:
            print(f"  - {f}")
        print("\nA green suite here is only meaningful because these can go red.")
        return 1
    print("Every mutation was detected. The verifier can fail.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
