#!/usr/bin/env python3
"""
Oracle Knowledge Expansion — Nightly Cron Script

This script runs as a no-agent cron job to identify knowledge EXPANSION
opportunities for the Oracle long-term wiki. It analyzes what's already in
the Oracle wiki and uses the Researcher to actively learn about related
topics, adjacent domains, and deeper context that would enrich the knowledge
base.

This is NOT about stale pages (Oracle knowledge like "what Einstein said"
doesn't change in 90 days). It's about actively expanding the knowledge
space around existing Oracle content.

Active Wiki content eventually decants down to Oracle, so we don't need
to cross-reference Active Wiki — we focus purely on expanding Oracle's
long-term knowledge.
"""

import os
import sys
import json
import subprocess
import re
from datetime import datetime
from pathlib import Path
from collections import Counter

HERMES_HOME = os.path.expanduser("~/.hermes")
ORACLE_WIKI = os.path.join(HERMES_HOME, "oracle", "brain")
EXCHANGE_DIR = os.path.join(HERMES_HOME, "exchange", "research")
GAP_LOG = os.path.join(HERMES_HOME, "logs", "oracle-expansion.log")

def log(msg):
    """Log to both stdout and log file."""
    timestamp = datetime.now().isoformat()
    line = f"[{timestamp}] {msg}"
    print(line)
    os.makedirs(os.path.dirname(GAP_LOG), exist_ok=True)
    with open(GAP_LOG, "a") as f:
        f.write(line + "\n")

# Markdown section headings, not knowledge topics.
STOP_PHRASES = {
    "related pages", "see also", "table of contents", "further reading",
    "references", "external links", "notes", "overview", "introduction",
    "conclusion", "background", "main page", "index page", "quick start",
    "getting started", "open ontologies", "capture notes", "use cases",
    "why it matters", "open questions", "core mechanisms", "basic usage",
}
# A trailing generic noun marks scaffolding, whatever the subject: "Puget Sound
# Example", "Seattle Relevance", "Example Output". Matching the suffix keeps
# this general instead of enumerating one subject at a time.
STOP_SUFFIXES = {
    "example", "examples", "relevance", "notes", "output", "usage",
    "steps", "questions", "mechanisms", "pages", "ontologies", "figures",
}
STOP_WORDS = {
    "the", "this", "that", "these", "those", "there", "then", "than",
    "however", "therefore", "thus", "also", "when", "where", "which",
    "while", "with", "from", "into", "about", "after", "before",
    "between", "during", "under", "over", "each", "some", "more",
    "most", "such", "both", "same", "other", "another", "because",
}
# Body markup that is data, not topic prose.
BODY_NOISE = (
    re.compile(r"```.*?```", re.S),          # fenced code
    re.compile(r"^\s*\|.*$", re.M),          # table rows
    re.compile(r"\]\([^)]*\)"),              # link targets
    re.compile(r"`[^`]*`"),                  # inline code
)
# Horizontal whitespace only: \s+ would weld line-wrapped text into nonsense
# topics such as 'False\nAccept' and 'Named\nDefault'.
CONCEPT = re.compile(r"\b[A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+)*\b")


def _is_usable_topic(c):
    """True if a Title Case run is plausibly a knowledge topic."""
    c_norm = c.strip().lower()
    if not c_norm or "\n" in c:
        return False
    if c_norm in STOP_PHRASES:
        return False
    words = c_norm.split()
    if len(words) < 2:
        return False
    if words[-1] in STOP_SUFFIXES:
        return False
    # Reject only when EVERY word is filler. Rejecting on ANY stop word
    # silently dropped legitimate topics: "The Hippocampus supports ..."
    # lost its subject because of the leading article.
    return not all(w in STOP_WORDS or len(w) <= 2 for w in words)


def extract_oracle_topics():
    """Extract key topics, concepts, and themes from Oracle wiki pages."""
    topics = []
    for md_file in Path(ORACLE_WIKI).rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")

            if content.startswith("---"):
                fm = content.split("---", 2)[1]
                for line in fm.split("\n"):
                    if line.startswith(("tags:", "title:")):
                        # tags may be inline [a, b] or a YAML block list
                        raw = line.split(":", 1)[1].strip().strip("[]")
                        topics.extend(
                            t.strip().strip("\"'") for t in raw.split(",")
                            if t.strip().strip("\"'") and t.strip().lower() not in STOP_PHRASES
                        )

            body = content.split("---", 2)[-1] if content.startswith("---") else content
            for pattern in BODY_NOISE:
                body = pattern.sub(" ", body)
            topics.extend(
                c for c in CONCEPT.findall(body)
                if len(c) > 5 and _is_usable_topic(c)
            )
        except Exception as e:
            log(f"Error reading {md_file}: {e}")

    topic_counts = Counter(topics)
    return [t for t, _ in topic_counts.most_common(50)], topic_counts

def existing_page_slugs():
    """Normalized stems of every page actually on disk in the Oracle wiki.

    Normalization strips case and every non-alphanumeric character so that
    'Active-Inference', 'active inference' and 'active_inference' all collapse
    to the same key.
    """
    slugs = set()
    for md_file in Path(ORACLE_WIKI).rglob("*.md"):
        slugs.add(re.sub(r"[^a-z0-9]+", "", md_file.stem.lower()))
    return slugs


def normalize(text):
    return re.sub(r"[^a-z0-9]+", "", str(text).lower())


def topic_is_covered(topic, slugs):
    """True if a single existing page plausibly covers this anchor topic.

    All significant words of the ANCHOR must appear in the SAME slug. Requiring
    one slug (not a union across the vault) is what makes this meaningful: with
    a 3000-page wiki, generic template words like 'historical' or 'context'
    always match something, so matching on the full direction string suppressed
    genuinely new work. Matching the anchor also matches the vault's own
    convention: pages are named after the topic, not the expansion direction.
    """
    words = [w for w in re.split(r"[-\s]+", str(topic).lower()) if len(w) > 3]
    if not words:
        return False
    norm = [normalize(w) for w in words]
    return any(all(nw in s for nw in norm) for s in slugs)


def pending_directions():
    """Directions already queued as pending (not yet archived) requests.

    The request schema stores the expansion direction in the 'topic' field.
    """
    out = set()
    if not os.path.isdir(EXCHANGE_DIR):
        return out
    for f in os.listdir(EXCHANGE_DIR):
        if not f.endswith(".json"):
            continue
        try:
            with open(os.path.join(EXCHANGE_DIR, f)) as fh:
                out.add(json.load(fh).get("topic", ""))
        except Exception:
            continue
    return {d for d in out if d}


def identify_expansion_directions(topics, topic_counts):
    """Identify directions to expand knowledge based on existing topics.

    Skips any direction already covered by a page on disk, already queued as
    a pending request, or already consumed into the archive. Without these
    guards this generator re-emitted the same 5 directions every night forever.
    """
    expansions = []

    # Common expansion patterns
    expansion_templates = [
        ("historical context of {topic}", "Historical background and evolution"),
        ("modern applications of {topic}", "Current real-world applications and use cases"),
        ("critiques and limitations of {topic}", "Known criticisms, failures, and boundary conditions"),
        ("related frameworks to {topic}", "Alternative or complementary frameworks and methodologies"),
        ("key figures in {topic}", "Influential people, their contributions, and intellectual lineage"),
        ("open problems in {topic}", "Unsolved questions and active research areas"),
        ("case studies of {topic}", "Detailed real-world examples and lessons learned"),
        ("prerequisites for {topic}", "Foundational knowledge needed to understand this deeply"),
    ]

    slugs = existing_page_slugs()
    queued = pending_directions()
    seen_this_run = set()
    skipped_topics = 0
    skipped_queued = 0

    # Walk topics by decreasing frequency, not just the first 15: the most
    # frequent topics are the ones most likely to already be saturated.
    ranked = sorted(topics, key=lambda t: (-topic_counts.get(t, 0), t))

    for topic in ranked:
        if len(expansions) >= 20:
            break
        # Anchor-level dedup: if the vault already has a page for this topic,
        # skip the whole family of expansion directions for it.
        if topic_is_covered(topic, slugs):
            skipped_topics += 1
            continue
        for template, description in expansion_templates:
            if len(expansions) >= 20:
                break
            direction = template.format(topic=topic)
            if direction in seen_this_run:
                continue
            seen_this_run.add(direction)
            if direction in queued:
                skipped_queued += 1
                continue
            expansions.append({
                "topic": topic,
                "direction": direction,
                "description": description,
                "priority": "high" if topic_counts.get(topic, 0) > 2 else "normal"
            })

    log(f"Dedup: skipped {skipped_topics} already-covered topics, "
        f"{skipped_queued} already-queued directions")
    return expansions[:20]  # Return top 20 expansion opportunities

def create_research_request(topic, direction, description, priority="normal"):
    """Create a research request package for the Researcher profile."""
    os.makedirs(EXCHANGE_DIR, exist_ok=True)
    
    request = {
        "id": f"oracle-expand-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{abs(hash(direction)) % 10000:04d}",
        "topic": direction,
        "context": f"Oracle knowledge expansion: {description} for '{topic}'. This expands long-term knowledge around existing Oracle content.",
        "priority": priority,
        "created_at": datetime.now().isoformat(),
        "source": "oracle-knowledge-expansion",
        "target_profile": "oracle-researcher",
        "deliver_to": "exchange/research",
        "requirements": {
            "verify_citations": True,
            "synthesize": True,
            "target_wiki": "oracle",
            "max_pages": 3,
            "focus": "long-term knowledge, not current events",
            "frontmatter_schema": "/home/operator/schemas/okf-schema.yaml",
            "schema_authority": "DO NOT hard-code fields or types here. Load them from frontmatter_schema, or run okf_gate.py --fix on the written page.",
            "type": "research-report"
        },
        "metadata": {
            "seed_topic": topic,
            "expansion_type": "knowledge_expansion",
            "oracle_anchor": topic
        }
    }
    
    req_file = os.path.join(EXCHANGE_DIR, f"{request['id']}.json")
    with open(req_file, "w") as f:
        json.dump(request, f, indent=2)
    
    log(f"Created research request: {req_file} — {direction}")
    return req_file

def main():
    log("=== Oracle Knowledge Expansion Started ===")
    
    # 1. Extract existing Oracle topics
    topics, topic_counts = extract_oracle_topics()
    log(f"Extracted {len(topics)} key topics from Oracle wiki")
    
    if not topics:
        log("No topics found in Oracle wiki — skipping expansion")
        print(json.dumps({"timestamp": datetime.now().isoformat(), "requests_created": 0, "reason": "empty_oracle"}))
        return
    
    # 2. Identify expansion directions
    expansions = identify_expansion_directions(topics, topic_counts)
    log(f"Identified {len(expansions)} knowledge expansion directions")
    
    # 3. Create research requests (max 5 per night)
    requests_created = 0
    for exp in expansions:
        if requests_created >= 5:
            break
        create_research_request(
            exp["topic"],
            exp["direction"],
            exp["description"],
            exp["priority"]
        )
        requests_created += 1
    
    # 4. Summary
    log(f"=== Oracle Knowledge Expansion Complete: {requests_created} research requests created ===")
    
    summary = {
        "timestamp": datetime.now().isoformat(),
        "oracle_topics_analyzed": len(topics),
        "expansion_directions_identified": len(expansions),
        "research_requests_created": requests_created,
        "top_seed_topics": topics[:10]
    }
    print(json.dumps(summary))

if __name__ == "__main__":
    main()