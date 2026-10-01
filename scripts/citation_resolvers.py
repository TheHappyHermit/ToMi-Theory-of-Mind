#!/usr/bin/env python3
"""Network resolvers for citation verification.

Three independent sources, tried in order, because no single registry covers
the corpus:

  1. Crossref  — the DOI registry for most publishers. Best metadata.
  2. DataCite  — covers datasets, preprints, and government/institutional
     repositories. Crossref 404s on a large fraction of these.
  3. arXiv     — the corpus is preprint-heavy. arXiv identifiers appear as
     `arXiv:2603.13285`, as `https://arxiv.org/abs/2603.13285`, and as
     DataCite DOIs (`10.48550/arXiv.2603.13285`).

Every resolver returns a `Resolved` with a `source` field so a caller can
report WHERE a title came from. A title obtained from the same registry the
citation was minted from is weaker evidence than an independent one, and the
caller needs to be able to see that.

Network discipline
------------------
A 429 is reported, never swallowed. A resolver that returns "fine" when it was
actually throttled is exactly the failure this whole toolchain exists to
prevent — so `RATE` is a distinct, loud state, not an error code that gets
folded into "could not check".
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional

CROSSREF = "https://api.crossref.org/works/"
DATACITE = "https://api.datacite.org/dois/"
# HTTPS, not HTTP. The http:// endpoint 301-redirects to https://, and arXiv's
# Varnish front end answers some redirected requests with 406. Going straight
# to https removes the hop. Found by reading the response headers off a live
# request, not by reading the code.
ARXIV_API = "https://export.arxiv.org/api/query?id_list="

UA = {"User-Agent": "hermes-brain/1.0 (https://github.com/TheHappyHermit/ToMi-Theory-of-Mind)"}

# arXiv DOIs are registered with DataCite, not Crossref. Recognising them lets
# the caller route to the right registry on the first try instead of eating a
# Crossref 404 first.
ARXIV_DOI_RE = re.compile(r"^10\.48550/arxiv\.(\d{4}\.\d{4,5})(v\d+)?$", re.I)
ARXIV_ID_RE = re.compile(r"(?:arxiv\.org/abs/|arxiv:)(\d{4}\.\d{4,5})(v\d+)?", re.I)
# A BARE arXiv id, e.g. "1706.03762" or "2603.13285v2". Anchored so it cannot
# match a DOI, a version string, or an arbitrary number containing a dot.
# Without this, a bare id was routed to Crossref and DataCite — both of which
# 404 — and a real preprint was reported as unresolvable. Found by running the
# CLI against Attention Is All You Need (1706.03762), not by reading the code.
ARXIV_BARE_RE = re.compile(r"^(\d{4}\.\d{4,5})(v\d+)?$")

ATOM = "{http://www.w3.org/2005/Atom}"


@dataclass
class Resolved:
    """Outcome of a resolution attempt.

    status: OK | RATE | NOTFOUND | ERROR
    source: crossref | datacite | arxiv | '' — which registry answered.
    """

    status: str
    source: str = ""
    title: str = ""
    year: Optional[int] = None
    container: str = ""
    detail: str = ""
    tried: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status == "OK"


def _get(url: str, timeout: int = 25) -> tuple:
    """Return (body_bytes, error). error is '' | 'RATE' | 'HTTP n' | message."""
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read(), ""
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            return b"", "RATE"
        # arXiv's Varnish front end answers 406 when it wants a client to slow
        # down. It is a throttle wearing a different status code, and treating
        # it as an error would report "this preprint does not exist" — a false
        # statement about the corpus. Map it to RATE and say so.
        if exc.code == 406:
            return b"", "RATE"
        if exc.code == 404:
            return b"", "HTTP 404"
        return b"", f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001 - report, never fabricate
        return b"", str(exc)[:80]


def _year_from_parts(parts) -> Optional[int]:
    try:
        return int(parts[0][0])
    except (TypeError, IndexError, ValueError):
        return None


def resolve_crossref(doi: str, timeout: int = 25) -> Resolved:
    """Resolve a DOI against Crossref."""
    url = CROSSREF + urllib.parse.quote(doi, safe="")
    body, err = _get(url, timeout)
    if err:
        return Resolved("RATE" if err == "RATE" else ("NOTFOUND" if err == "HTTP 404" else "ERROR"),
                        source="crossref", detail=err)
    try:
        msg = json.loads(body.decode()).get("message", {})
    except Exception as exc:  # noqa: BLE001
        return Resolved("ERROR", source="crossref", detail=f"unparseable: {str(exc)[:60]}")
    if not msg:
        return Resolved("NOTFOUND", source="crossref", detail="empty message")
    return Resolved(
        "OK",
        source="crossref",
        title=(msg.get("title") or ["?"])[0],
        year=_year_from_parts(msg.get("issued", {}).get("date-parts") or [[None]]),
        container=(msg.get("container-title") or [""])[0],
    )


def resolve_datacite(doi: str, timeout: int = 25) -> Resolved:
    """Resolve a DOI against DataCite.

    DataCite nests the real metadata under attributes.titles[].title, which is
    a list of dicts rather than Crossref's list of strings. Getting this wrong
    is how a resolver silently returns an empty title and the comparison
    downstream passes vacuously.
    """
    url = DATACITE + urllib.parse.quote(doi, safe="")
    body, err = _get(url, timeout)
    if err:
        return Resolved("RATE" if err == "RATE" else ("NOTFOUND" if err == "HTTP 404" else "ERROR"),
                        source="datacite", detail=err)
    try:
        attrs = json.loads(body.decode())["data"]["attributes"]
    except Exception as exc:  # noqa: BLE001
        return Resolved("ERROR", source="datacite", detail=f"unparseable: {str(exc)[:60]}")

    titles = attrs.get("titles") or []
    title = ""
    for t in titles:
        if isinstance(t, dict) and t.get("title"):
            title = t["title"]
            break
    if not title:
        return Resolved("NOTFOUND", source="datacite", detail="no title in attributes")

    publisher = attrs.get("publisher") or ""
    # DataCite publicationYear is a string, and may be absent.
    try:
        year = int(attrs.get("publicationYear"))
    except (TypeError, ValueError):
        year = None
    return Resolved("OK", source="datacite", title=title, year=year, container=publisher)


def resolve_arxiv(arxiv_id: str, timeout: int = 25) -> Resolved:
    """Resolve a bare arXiv identifier via the export API.

    Uses id_list rather than the query syntax so a malformed id produces a
    zero-entry feed instead of a syntax error page.
    """
    url = ARXIV_API + urllib.parse.quote(arxiv_id, safe="") + "&max_results=1"
    body, err = _get(url, timeout)
    if err:
        return Resolved("RATE" if err == "RATE" else ("NOTFOUND" if err == "HTTP 404" else "ERROR"),
                        source="arxiv", detail=err)
    try:
        root = ET.fromstring(body.decode())
    except Exception as exc:  # noqa: BLE001
        return Resolved("ERROR", source="arxiv", detail=f"unparseable: {str(exc)[:60]}")

    entry = root.find(f"{ATOM}entry")
    if entry is None:
        return Resolved("NOTFOUND", source="arxiv", detail="no entry in feed")

    title_el = entry.find(f"{ATOM}title")
    title = re.sub(r"\s+", " ", title_el.text).strip() if title_el is not None and title_el.text else ""
    if not title:
        # arXiv returns a stub entry titled "Error" for unknown ids.
        return Resolved("NOTFOUND", source="arxiv", detail="entry has no title")

    year = None
    published = entry.find(f"{ATOM}published")
    if published is not None and published.text:
        try:
            year = int(published.text[:4])
        except ValueError:
            year = None

    return Resolved("OK", source="arxiv", title=title, year=year, container="arXiv")


def arxiv_id_from(identifier: str) -> Optional[str]:
    """Extract a bare arXiv id from a DOI, URL, 'arXiv:NNNN.NNNNN', or a bare id.

    Order matters: the anchored forms are tried before the bare-id form so a
    DOI is never mistaken for an arXiv id.
    """
    if not identifier:
        return None
    s = identifier.strip()
    m = ARXIV_DOI_RE.match(s)
    if m:
        return m.group(1)
    m = ARXIV_ID_RE.search(s)
    if m:
        return m.group(1)
    m = ARXIV_BARE_RE.match(s)
    if m:
        return m.group(1)
    return None


def resolve_any(identifier: str, timeout: int = 25) -> Resolved:
    """Resolve any citation identifier, trying the right registries in order.

    Routing is deliberate, not a blind loop:
      - a bare arXiv id  -> arXiv only
      - an arXiv DOI      -> DataCite (where it is registered), arXiv as backstop
      - any other DOI     -> Crossref, then DataCite as fallback

    `tried` records every registry consulted, so a NOTFOUND verdict is
    auditable: it means "absent from all of these", not "we asked once and
    gave up".
    """
    identifier = (identifier or "").strip()
    if not identifier:
        return Resolved("NOTFOUND", detail="empty identifier")

    tried = []
    bare = arxiv_id_from(identifier)
    is_doi = identifier.lower().startswith("10.")

    if bare and not is_doi:
        # A bare or arXiv-prefixed id is not a DOI at all. Crossref and
        # DataCite both 404 on it, so routing it there first would report a
        # real preprint as unresolvable.
        tried.append("arxiv")
        return _tag(resolve_arxiv(bare, timeout), tried)

    if bare:  # 10.48550/arXiv.NNNN — DataCite owns it
        tried.append("datacite")
        r = resolve_datacite(identifier, timeout)
        if r.ok:
            return _tag(r, tried)
        tried.append("arxiv")
        return _tag(resolve_arxiv(bare, timeout), tried)

    tried.append("crossref")
    r = resolve_crossref(identifier, timeout)
    if r.ok:
        return _tag(r, tried)
    if r.status == "RATE":
        return _tag(r, tried)
    # Crossref 404s on datasets, preprints and government repositories. Fall
    # through rather than reporting a false absence.
    tried.append("datacite")
    return _tag(resolve_datacite(identifier, timeout), tried)


def _tag(r: Resolved, tried: list) -> Resolved:
    r.tried = tried
    return r


def polite_sleep(seconds: float) -> None:
    if seconds > 0:
        time.sleep(seconds)
