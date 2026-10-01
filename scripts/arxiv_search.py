#!/usr/bin/env python3
"""Search arXiv for recent papers in ontology engineering, memory systems, and AI knowledge topics."""
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import sys

def search_arxiv(query, max_results=20):
    """Search arXiv via their XML API."""
    # arXiv API uses: ti: for title, au: for author, all: for any field
    # Spaces need to be URL-encoded
    url = f'http://export.arxiv.org/api/query?search_query={urllib.parse.quote(query)}&max_results={max_results}&sortBy=submittedDate&sortOrder=descending'
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'HermesAgent/1.0')
    response = urllib.request.urlopen(url, timeout=30)
    xml_data = response.read().decode('utf-8')
    root = ET.fromstring(xml_data)
    ns = {'atom': 'http://www.w3.org/2005/Atom', 'opensearch': 'http://a9.com/-/spec/opensearch/1.1/'}
    total_elem = root.find('opensearch:totalResults', ns)
    total = total_elem.text if total_elem is not None else '0'
    results = []
    for entry in root.findall('atom:entry', ns):
        title_el = entry.find('atom:title', ns)
        summary_el = entry.find('atom:summary', ns)
        published_el = entry.find('atom:published', ns)
        id_el = entry.find('atom:id', ns)
        if any(e is None for e in [title_el, summary_el, published_el, id_el]):
            continue
        title = title_el.text.strip().replace('\n', ' ')
        summary = summary_el.text.strip().replace('\n', ' ')
        published = published_el.text
        id_uri = id_el.text
        if '/abs/' in id_uri:
            arxiv_id = id_uri.split('/abs/')[-1].split('/v')[0]
        else:
            arxiv_id = id_uri.split('/abs/')[-1].split('/v')[0]
        results.append({'title': title, 'summary': summary[:400], 'published': published, 'arxiv_id': arxiv_id})
    return total, results

# arXiv query terms (note: arXiv API uses specific syntax)
queries = [
    'all:ontology AND all:agent',
    'all:hallucination AND all:knowledge',
    'all:memory AND all:LLM',
    'all:neuro-symbolic',
    'all:"knowledge graph" AND all:benchmark',
    'all:alignment AND all:ontology',
    'all:memory AND all:agent',
    'all:ontology AND all:LLM',
]

all_results = []
for q in queries:
    try:
        total, results = search_arxiv(q, max_results=15)
        all_results.extend(results)
        print(f'Query: {q[:50]} -> {total} total, {len(results)} returned', file=sys.stderr)
    except Exception as e:
        print(f'Query failed: {q[:50]} -> {e}', file=sys.stderr)

# Deduplicate by arxiv_id
seen = set()
unique = []
for r in all_results:
    if r['arxiv_id'] not in seen:
        seen.add(r['arxiv_id'])
        unique.append(r)

print(f'\n=== {len(unique)} unique papers found ===')
for r in unique:
    print(f'\n--- {r["arxiv_id"]} ({r["published"]}) ---')
    print(f'Title: {r["title"]}')
    print(f'Summary: {r["summary"][:350]}')
