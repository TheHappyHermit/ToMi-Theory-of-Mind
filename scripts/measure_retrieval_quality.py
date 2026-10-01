#!/usr/bin/env python3
"""Does the knowledge graph actually improve retrieval? A baseline measurement.

Why this exists
---------------
The graph layer has been described in the architecture document as part of
retrieval, and it has been verified to *run*: a two-hop walk was checked by hand
and the query path returns connected documents with the path that reached them.

What has never existed is a number. Nothing in this repository has measured
whether adding the graph makes retrieval better than not adding it. That is the
gap this script closes -- or, if the graph does not help, exposes.

What it measures
----------------
Four retrieval strategies over the same corpus and the same queries:

  1. `keyword`  -- plain token overlap. The floor every other result must beat.
  2. `graph`    -- the graph layer alone (seeds + personalised PageRank).
  3. `fused`    -- reciprocal rank fusion of 1 and 2, which is what
                   `brain_query.py --graph` actually does.
  4. `oracle`   -- a deliberately unattainable upper bound, computed by checking
                   whether a relevant document is present in the corpus at all.
                   Reported to show how much of any gap is a coverage problem
                   rather than a ranking problem.

The metric is **recall@k**: of the documents a human marked relevant, how many
appear in the top k. Precision is reported too, but recall is the honest target
for a retrieval layer whose job is not to hide anything.

The judgement set
----------------
A small, hand-checked set of query/relevant-document pairs, stored in this file
rather than in the user's vault. Two reasons: the set must be versioned with the
code that consumes it, and a benchmark derived from the live corpus drifts
whenever the corpus is rebuilt.

If the corpus is not present, this exits 2 and says so. **A benchmark that cannot
measure anything must not report success** -- that is the same rule the dependency
health checker follows.

Interpreting the result
----------------------
A positive result means the graph surfaced relevant documents that keyword search
missed. A negative result is *also* useful and should not be hidden: it would mean
the graph layer is an index that costs build time and returns nothing a keyword
search would not have found, which is an argument for demoting it to optional.

Run:
    HERMES_HOME=<vault root> python3 scripts/measure_retrieval_quality.py
    python3 scripts/measure_retrieval_quality.py --json
    python3 scripts/measure_retrieval_quality.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
import retrieval_labels as rl
from typing import Dict, List, Optional, Sequence, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

import graph_retrieval as gr  # noqa: E402

RRF_K = 60

# --- The judgement set -------------------------------------------------------
# (query, [relevant document path fragments]). Fragments are matched as
# Relevance labels are content hashes built by retrieval_labels.py, judged on
# document text. The filename-fragment judgement set this replaced is gone: it
# was matched by substring against the path, which made the labels and the
# keyword arm share a matching rule and turned the "oracle" arm into a
# tautology. See that module for the full argument.

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "of", "and", "or", "in",
    "on", "at", "for", "to", "with", "how", "does", "do", "it", "its", "this",
    "that", "i", "we", "you", "by", "from", "as", "but", "not",
}


# --- Corpus ------------------------------------------------------------------
def iter_documents(vault: Path) -> List[Path]:
    out: List[Path] = []
    if not vault.exists():
        return out
    for p in vault.rglob("*.md"):
        # Only consider dot-prefixed components RELATIVE to the vault root.
        # Checking the absolute path would reject an entire corpus living under
        # ~/.something, and the benchmark would report zero documents while
        # looking like it had run.
        rel = p.relative_to(vault)
        if any(part.startswith(".") for part in rel.parts):
            continue
        out.append(p)
    return out


def tokenize(text: str) -> List[str]:
    words = re.findall(r"[a-z0-9']+", (text or "").lower())
    return [w for w in words if len(w) > 2 and w not in STOPWORDS]


def build_keyword_index(docs: Sequence[Path], max_bytes: int = 200_000) -> Dict[str, Set[int]]:
    """Inverted index: token -> set of document indices.

    Indexes the document BODY, not just its path. The previous version indexed
    only the file path, so a document could be scored as a "hit" purely because
    of what it was called, and a document that discussed a topic thoroughly in
    its text was invisible unless its title happened to contain the keyword.
    That made the keyword arm a filename-matching arm, and made the filename-based
    relevance labels look like a real recall ceiling.

    The path is still indexed, because a title is a legitimate signal — it is
    just not the only one. Documents are truncated at `max_bytes` so a handful of
    very large files cannot dominate the index or the runtime.
    """
    index: Dict[str, Set[int]] = defaultdict(set)
    for i, doc in enumerate(docs):
        toks = set(tokenize(str(doc)))
        try:
            with open(doc, encoding="utf-8", errors="ignore") as f:
                toks |= set(tokenize(f.read(max_bytes)))
        except OSError:
            # Unreadable file: fall back to path-only tokens for this document
            # rather than dropping it from the index entirely.
            pass
        for tok in toks:
            index[tok].add(i)
    return index


def keyword_search(
    query: str, docs: Sequence[Path], index: Dict[str, Set[int]], top_k: int
) -> List[int]:
    """Rank documents by how many distinct query terms appear in them.

    Scores whole-document term matches, counting each term once. Deliberately
    simple and deterministic.

    This is a genuine floor, not a filename-matching stub: it reads the body via
    build_keyword_index. It is still weaker than BM25 (no term frequency
    saturation, no length normalisation, no stemming), so treat it as a lower
    bound and not as evidence that a richer retriever cannot do better.
    """
    terms = set(tokenize(query))
    if not terms:
        return []
    scores: Dict[int, int] = defaultdict(int)
    for term in terms:
        for doc_i in index.get(term, ()):
            scores[doc_i] += 1
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], str(docs[kv[0]])))
    return [i for i, _ in ranked[:top_k]]


# --- Graph layer -------------------------------------------------------------
def graph_search(query: str, top_k: int, depth: int) -> List[str]:
    """Query the graph layer. Returns document-path fragments, not indices."""
    res = gr.multi_hop_search(query, top_k=top_k, depth=depth)
    files = []
    for r in res.get("results", []):
        f = r.get("file") or r.get("source_file") or ""
        if f:
            files.append(str(f))
    return files


def fuse(keyword_files: Sequence[str], graph_files: Sequence[str], top_k: int) -> List[str]:
    """Reciprocal rank fusion -- mirrors what brain_query.py --graph does.

    The two arms return DIFFERENT identifier shapes: the keyword arm yields
    absolute paths, the graph arm yields paths relative to the sub-vault (e.g.
    "research/findings.md"). Fused on raw strings they can never match, so every
    slot looked like "found by one arm only" even when both arms had retrieved
    the same document. Normalise to a comparable key before scoring.
    """
    def key(path: str) -> str:
        """Reduce either arm's path to a vault-relative comparable form.

        Keyword arm: absolute ("/.../oracle/brain/research/x.md")
        Graph arm:   sub-vault relative ("research/x.md")
        """
        p = str(path)
        if p.startswith("/"):
            try:
                p = os.path.relpath(p, str(gr.ORACLE_BRAIN))
            except ValueError:
                pass
        return os.path.normpath(p).lower()

    scores: Dict[str, float] = defaultdict(float)
    seen: Dict[str, str] = {}
    for rank, f in enumerate(keyword_files, start=1):
        k = key(f)
        seen.setdefault(k, str(f))
        scores[k] += 1.0 / (RRF_K + rank)
    for rank, f in enumerate(graph_files, start=1):
        k = key(f)
        seen.setdefault(k, str(f))
        scores[k] += 1.0 / (RRF_K + rank)
    return [seen[k] for k, _ in sorted(scores.items(), key=lambda kv: -kv[1])[:top_k]]


# --- Corpus selection --------------------------------------------------------
def resolve_corpus_root() -> Path:
    """The vault the graph was built over, with a graph present.

    Selection order:
      1. ORACLE_BRAIN_PATH / ACTIVE_WIKI_PATH, whichever holds a graph.
      2. Otherwise the first of the two that exists.

    A candidate without a graph is rejected with a message rather than used
    silently. The failure this prevents is quiet and total: the graph arm
    returns paths relative to the vault it indexed, so pointing the benchmark
    at a different tree makes every one of those paths unresolvable and the
    graph arm scores 0.000 forever while looking like a real result.

    On this machine ~/.hermes/oracle/brain exists and has 378 files, but no
    graph -- the graph is at ~/.hermes/oracle/brain. Choosing by
    "directory exists" picks the wrong one.
    """
    candidates = [gr.ORACLE_BRAIN, gr.ACTIVE_WIKI]
    with_graph = [c for c in candidates if (c / "graphify-out" / "graph.json").exists()]
    if with_graph:
        return with_graph[0]

    existing = [c for c in candidates if c.exists()]
    if existing:
        chosen = existing[0]
        print(
            f"[benchmark] WARNING: no graph.json under any known vault "
            f"({', '.join(str(c) for c in candidates)}).\n"
            f"[benchmark]          measuring {chosen} anyway -- the graph arm will "
            f"score 0.000, which means 'not pointed at these files', not 'the "
            f"graph found nothing'.",
            file=sys.stderr,
        )
        return chosen
    return candidates[0]


# --- Scoring -----------------------------------------------------------------
# Labels are content hashes from retrieval_labels.py. There is deliberately no
# is_relevant() here: the substring test this replaces matched on the PATH, so
# the labels and the keyword arm shared a matching rule, "oracle" was not an
# independent ceiling, and a body-aware retriever could be marked wrong for
# retrieving a document that discusses the topic but is not titled with the
# keyword. A hash of the document's bytes cannot be satisfied by its name.

# A perfect exhaustive keyword system must not score well. If it does, the
# labels are reachable by matching rather than by reading, which is the
# original defect wearing a new hat. Set by control_full_context() below.
MULTI_HOP_GATE_MAX_RECALL = 0.20


def _hashes(paths: Sequence) -> set:
    """Content hashes for a set of returned paths.

    Paths from different arms arrive in different shapes: the keyword arm yields
    absolute paths, the graph arm yields sub-vault-relative ones. Both are
    resolved against the corpus directory so the same document hashes the same
    way whichever arm found it.
    """
    out = set()
    for p in paths:
        try:
            candidate = Path(p)
            if not candidate.exists():
                candidate = docs_dir / str(p)
            if candidate.exists():
                out.add(rl.doc_hash(candidate))
        except (OSError, ValueError):
            continue
    return out


# Set by evaluate(); the corpus the arms are searching.
docs_dir: Path = Path(".")


def evaluate(
    docs: Sequence[Path],
    index: Dict[str, Set[int]],
    strategy: str,
    top_k: int,
    depth: int = 2,
    labels: Dict[str, frozenset] = None,
) -> Dict[str, object]:
    """Run one strategy over the whole judgement set, scored by content hash."""
    global docs_dir
    docs_dir = Path(docs[0]).parent if docs else Path(".")
    if labels is None:
        labels = rl.build_labels(docs)

    per_query = []
    hits = 0
    total_relevant = 0

    for query, relevant in labels.items():
        if strategy == "keyword":
            returned = [str(docs[i]) for i in
                        keyword_search(query, docs, index, top_k)]
        elif strategy == "graph":
            returned = graph_search(query, top_k, depth)
        elif strategy == "fused":
            kw = [str(docs[i]) for i in keyword_search(query, docs, index, top_k)]
            returned = fuse(kw, graph_search(query, top_k, depth), top_k)
        elif strategy == "oracle":
            # Perfect knowledge of the labels. Still an upper bound, not a
            # measurement: it cannot say whether a label is right.
            wanted = set(relevant)
            returned = [str(d) for d in docs if rl.doc_hash(d) in wanted][:top_k]
        else:
            raise ValueError(f"unknown strategy: {strategy}")

        returned_hashes = _hashes(returned)
        matched = returned_hashes & set(relevant)
        hits += len(matched)
        total_relevant += len(relevant)
        per_query.append({
            "query": query,
            "returned": len(returned),
            "matched": len(matched),
            "relevant_total": len(relevant),
        })

    return {
        "strategy": strategy,
        "k": top_k,
        "recall": round(hits / total_relevant, 4) if total_relevant else 0.0,
        "matched": hits,
        "relevant_total": total_relevant,
        "per_query": per_query,
        "label_caveat": rl.LABELS_ARE_PROXY,
    }


def control_full_context(
    docs: Sequence[Path],
    labels: Dict[str, frozenset],
    top_k: int = 10,
) -> Dict[str, object]:
    """Control arm A: the whole corpus in context, no retrieval at all.

    The upper bound. Anything a retriever scores against it, the retriever is
    choosing from a set that already contains the answer, so this is what
    perfect selection would achieve. Without this arm a recall number cannot be
    read as anything other than a number.
    """
    return {
        "arm": "full_context",
        "description": "every document in context, perfect selection, no retrieval",
        "k": top_k,
        "per_query": {q: min(top_k, len(v)) for q, v in labels.items()},
        "recall": 1.0,
        "note": "an upper bound by construction, not a measurement",
    }


def control_body_bm25(
    docs: Sequence[Path],
    index: Dict[str, Set[int]],
    labels: Dict[str, frozenset],
    top_k: int = 10,
) -> Dict[str, object]:
    """Control arm B: real BM25 over document bodies.

    The floor that matters. A graph arm that cannot beat plain BM25 is not
    earning its maintenance cost, and that is the comparison the graph question
    turns on. Uses ranklib's BM25Okapi if available and falls back to the
    in-repo term-count index, reporting which one ran.
    """
    try:
        from rank_bm25 import BM25Okapi  # type: ignore
        engine = "rank_bm25.BM25Okapi"
    except ImportError:
        BM25Okapi = None
        engine = "in-repo term-count index (rank_bm25 not installed)"

    corpus_tokens = []
    for d in docs:
        try:
            corpus_tokens.append(tokenize(d.read_text(
                encoding="utf-8", errors="ignore")[:200_000]))
        except OSError:
            corpus_tokens.append([])

    if BM25Okapi is not None and any(corpus_tokens):
        bm25 = BM25Okapi(corpus_tokens)
    else:
        bm25 = None

    global docs_dir
    docs_dir = Path(docs[0]).parent if docs else Path(".")

    per_query = {}
    hits = 0
    total = 0
    for query, relevant in labels.items():
        terms = tokenize(query)
        if not terms:
            continue
        if bm25 is not None:
            scores = bm25.get_scores(terms)
            ranked = sorted(range(len(docs)), key=lambda i: -scores[i])[:top_k]
        else:
            ranked = keyword_search(query, docs, index, top_k)
        got = {rl.doc_hash(docs[i]) for i in ranked} & set(relevant)
        hits += len(got)
        total += len(relevant)
        per_query[query] = len(got)

    return {
        "arm": "body_bm25",
        "description": f"BM25 over document bodies ({engine})",
        "engine": engine,
        "k": top_k,
        "recall": round(hits / total, 4) if total else 0.0,
        "per_query": per_query,
    }


def check_multi_hop_gate(result: Dict[str, object]) -> Tuple[bool, str]:
    """A perfect exhaustive keyword system must not score well.

    If it does, the labels are reachable by matching rather than by reading, and
    the benchmark is measuring the labels rather than the retriever. That is
    the original defect, so it is checked explicitly rather than assumed.
    """
    if result.get("strategy") != "oracle":
        return True, "not the oracle arm; gate applies to the oracle only"
    recall = float(result.get("recall", 0.0))
    if recall <= MULTI_HOP_GATE_MAX_RECALL:
        return True, (f"oracle recall {recall:.4f} is within "
                      f"{MULTI_HOP_GATE_MAX_RECALL}")
    return False, (f"oracle recall {recall:.4f} exceeds "
                   f"{MULTI_HOP_GATE_MAX_RECALL}: the labels are reachable by "
                   "matching, not by reading. Every other number here is void.")


# --- Self-test ---------------------------------------------------------------
def self_test() -> int:
    """Check the metric on a corpus and queries whose answer we constructed.

    A benchmark that cannot detect a known difference is not a benchmark.
    """
    import tempfile

    failures = []

    # Build a tiny corpus where the right answer is unambiguous.
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "alpha").mkdir()
        (root / "beta").mkdir()
        (root / "alpha" / "hippocampus.md").write_text("x")
        (root / "beta" / "unrelated.md").write_text("x")
        docs = iter_documents(root)
        idx = build_keyword_index(docs)
        got = keyword_search("hippocampus", docs, idx, 10)
        if len(got) != 1 or "hippocampus" not in str(docs[got[0]]):
            failures.append(f"keyword_search missed the planted doc: {got}")
        # A query matching nothing must return nothing, not everything.
        if keyword_search("zzzznotpresent", docs, idx, 10):
            failures.append("keyword_search returned results for an absent term")

    # Relevance is judged on CONTENT. A document whose NAME contains the topic
    # but whose text does not discuss it must not be labelled relevant -- that
    # is the defect this replaced, and it is what made the old "oracle" ceiling
    # circular.
    with tempfile.TemporaryDirectory() as tmp:
        r = Path(tmp)
        # The body must actually discuss the query's subject. An earlier
        # version of this fixture was about retrieval-induced forgetting while
        # the query asked about the thalamus, and the labeller was right to
        # reject it.
        on_topic = r / "thalamic-notes.md"
        on_topic.write_text(
            "the thalamus gates sensory input before it reaches the cortex. "
            "thalamic gating filters attention, and thalamic nuclei carry "
            "sensory signals. " * 12)
        misnamed = r / "thalamus-gating.md"
        misnamed.write_text("a shopping list and some weather notes.\n" * 40)
        q = "thalamus gating sensory attention"
        if not rl.judge_by_content(on_topic, q):
            failures.append("judge_by_content missed an on-topic document")
        if rl.judge_by_content(misnamed, q):
            failures.append(
                "judge_by_content labelled a document relevant by its FILENAME "
                "alone -- the substring defect, still present")
        # Renaming must not change relevance. Identity is content, not name.
        renamed = r / "zzz-unrelated-name.md"
        renamed.write_text(on_topic.read_text())
        if rl.doc_hash(renamed) != rl.doc_hash(on_topic):
            failures.append(
                "doc_hash depends on the filename, so renaming a document would "
                "change its label")

    # A perfect exhaustive system must not score well against these labels.
    gate_ok, gate_why = check_multi_hop_gate({"strategy": "oracle", "recall": 0.5})
    if gate_ok:
        failures.append(f"multi-hop gate did not fire: {gate_why}")
    gate_ok, _ = check_multi_hop_gate({"strategy": "oracle", "recall": 0.1})
    if not gate_ok:
        failures.append("multi-hop gate fired on a passing result")

    # RRF must rank a document found by both strategies above one found by one.
    fused = fuse(["a", "b", "c"], ["x", "b", "y"], top_k=10)
    if not fused or fused[0] != "b":
        failures.append(f"RRF did not promote the document found by both: {fused[:3]}")

    for f in failures:
        print(f"  FAIL: {f}", file=sys.stderr)
    if failures:
        print(f"self-test: {len(failures)} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (planted answer found, absent terms ignored, RRF promotes agreement, labels judged on content not filename, hash survives rename, multi-hop gate fires)")
    return 0


# --- Main --------------------------------------------------------------------
def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Measure retrieval quality with and without the graph")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    ap.add_argument("--k", type=int, default=10, help="cutoff (default 10)")
    ap.add_argument("--depth", type=int, default=2, help="graph hops (default 2)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(list(argv) if argv is not None else sys.argv[1:])

    if args.self_test:
        return self_test()

    # Measure the vault the graph was actually built over.
    #
    # This used to be gr._hermes_home(strict=True), which resolves to the Hermes
    # install directory rather than to a vault. On this machine that walked
    # 20,603 markdown files, of which 19,847 were profiles, agent source, cache
    # and cron output -- not knowledge documents at all. It also meant the
    # graph arm scored a guaranteed 0.000: the graph returns paths relative to
    # the oracle vault, and none of them exist under the install directory, so
    # nothing could ever match. A retrieval benchmark comparing two corpora
    # measures nothing.
    #
    # The corpus must be the one the graph indexes. That is ORACLE_BRAIN_PATH,
    # falling back to the active wiki, and it is validated below: if the chosen
    # root has no graph, the graph arm is reported as unmeasurable rather than
    # as a score of zero, because "the graph found nothing" and "the graph was
    # never pointed at these files" are different findings.
    vault = resolve_corpus_root()
    docs = iter_documents(vault)
    if not docs:
        print(
            f"No markdown corpus found under {vault}.\n"
            "This benchmark measures the graph against real documents; without a\n"
            "corpus there is nothing to measure, so it will not report a result.\n"
            f"Set ORACLE_BRAIN_PATH to the vault the graph was built over and re-run.",
            file=sys.stderr,
        )
        return 2

    graphs, notes = gr.load_graphs()
    index = build_keyword_index(docs)

    # Labels are built once, over the whole corpus, and shared by every arm.
    # Pooling each arm's own results would make the labels a function of the
    # arm being measured.
    labels = rl.build_labels(docs)

    strategies = ["keyword", "graph", "fused", "oracle"]
    results = [evaluate(docs, index, s, args.k, args.depth, labels=labels)
               for s in strategies]

    # Mandatory control arms. Without these every number above is
    # uninterpretable, so they are not optional flags.
    controls = {
        "full_context": control_full_context(docs, labels, args.k),
        "body_bm25": control_body_bm25(docs, index, labels, args.k),
    }

    # If a perfect exhaustive keyword system scores well, the labels are
    # reachable by matching rather than by reading, and nothing else here means
    # anything. Checked explicitly rather than assumed.
    gate_results = {r["strategy"]: check_multi_hop_gate(r) for r in results
                    if r["strategy"] == "oracle"}
    gate_ok, gate_why = next(iter(gate_results.values()), (True, "no oracle arm"))

    payload = {
        "vault": str(vault),
        "documents": len(docs),
        "graphs_loaded": sorted(graphs),
        "graph_notes": notes,
        "queries": len(labels),
        "k": args.k,
        "results": results,
        "controls": controls,
        "multi_hop_gate": {"passed": gate_ok, "detail": gate_why},
        "label_caveat": rl.LABELS_ARE_PROXY,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"Corpus: {len(docs)} markdown files under {vault}")
    print(f"Graphs loaded: {', '.join(sorted(graphs)) or 'none'}")
    for n in notes:
        print(f"  note: {n}")
    print(f"\n{len(labels)} queries, recall@{args.k}, graph depth {args.depth}\n")
    print("CONTROL ARMS (mandatory -- a number without them is uninterpretable)")
    print(f"  {'full_context':<14}{controls['full_context']['recall']:>8.3f}  "
          f"{controls['full_context']['note']}")
    print(f"  {'body_bm25':<14}{controls['body_bm25']['recall']:>8.3f}  "
          f"engine: {controls['body_bm25']['engine']}")
    print()
    print(f"{'strategy':<12}{'recall@k':>10}{'matched':>12}")
    print("-" * 34)
    for r in results:
        print(f"{r['strategy']:<12}{r['recall']:>10.3f}"
              f"{str(r['matched']) + '/' + str(r['relevant_total']):>12}")
    print()
    print(f"multi-hop gate: {'PASS' if gate_ok else 'FAIL'} -- {gate_why}")
    print(f"labels: {rl.LABELS_ARE_PROXY}")

    kw = next(r for r in results if r["strategy"] == "keyword")
    fu = next(r for r in results if r["strategy"] == "fused")
    gr_ = next(r for r in results if r["strategy"] == "graph")
    orc = next(r for r in results if r["strategy"] == "oracle")

    print()

    delta = float(fu["recall"]) - float(kw["recall"])  # type: ignore[arg-type]
    if delta > 0:
        print(f"FUSED BEATS KEYWORD by {delta:+.3f} recall@{args.k}.")
        print("The graph layer found relevant documents keyword search missed.")
    elif delta < 0:
        # Diagnose the mechanism rather than asserting a cause. Fusion spends part
        # of the top-k budget on graph results, which displaces keyword hits that
        # were scoring. Report the composition so the cause is visible.
        kw_only = graph_only = both = 0
        for query, relevant in labels.items():
            idxs = keyword_search(query, docs, index, args.k)
            kwf = [str(docs[i]) for i in idxs]
            gff = graph_search(query, args.k, args.depth)
            fused_f = fuse(kwf, gff, args.k)
            for f in fused_f:
                if f in kwf and f in gff:
                    both += 1
                elif f in kwf:
                    kw_only += 1
                elif f in gff:
                    graph_only += 1
        total_slots = max(1, len(labels) * args.k)
        print(f"FUSED IS WORSE THAN KEYWORD by {delta:+.3f} recall@{args.k}.")
        print(f"Fused top-{args.k} composition across all queries:")
        print(f"  from keyword only : {kw_only:>4}  ({100*kw_only/total_slots:.0f}% of slots)")
        print(f"  from graph only   : {graph_only:>4}  ({100*graph_only/total_slots:.0f}% of slots)")
        print(f"  found by both     : {both:>4}")
        print()
        print("Mechanism: reciprocal rank fusion gives the two strategies separate")
        print("rank ranges, so each occupies roughly half the top-k budget. When the")
        print("graph's half does not contain relevant documents, it displaces keyword")
        print("hits that did. This is a budget-allocation problem, not a fusion-weight")
        print("problem -- weighting the keyword side higher would trade away the")
        print("graph's multi-hop reach instead.")
        print()
        print("Do not enable --graph by default until the graph's own recall rises.")
    else:
        print(f"FUSED TIES KEYWORD at {kw['recall']:.3f} recall@{args.k} on this set.")
        print("The graph layer returned nothing keyword search had not already found.")

    print(f"\nGraph alone: {gr_['recall']:.3f} recall@{args.k} "
          f"({gr_['matched']}/{gr_['relevant_total']} relevant documents found).")
    if gr_["recall"] == 0:
        # A zero here has two very different causes, and conflating them is how
        # a path bug came to be read as a graph-quality finding. Check which one
        # it is before saying anything about the graph.
        graph_path = gr.GRAPH_SOURCES.get("oracle-brain") or next(
            iter(gr.GRAPH_SOURCES.values()))
        corpus_has_graph = (vault / "graphify-out" / "graph.json").exists()
        if not corpus_has_graph:
            print(f"  -> ZERO, but the corpus has no graph: {vault}")
            print("     The graph arm was measured against files the graph does")
            print("     not index. This is a path problem, not a graph-quality result.")
            print("     Set ORACLE_BRAIN_PATH to the vault the graph was built over.")
        elif not graph_path.exists():
            print(f"  -> ZERO, and the graph file is missing: {graph_path}")
            print("     The graph was never loaded. Run the ingestion job, or check")
            print("     GRAPH_OUT_ORACLE_BRAIN.")
        else:
            print("  -> The graph loaded and matched nothing on this set. That is a")
            print("     real result. It may be misconfigured, or the corpus may be too")
            print("     small for multi-hop to pay off. Run")
            print("     scripts/verify_graph_integrity.py before concluding it is useless.")

    print("\nThis is a small hand-checked set, not a benchmark. It can show a clear")
    print("difference; it cannot establish one. Treat a small delta as inconclusive.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
