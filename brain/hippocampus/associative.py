#!/usr/bin/env python3
"""
brain.hippocampus.associative — HippoRAG-Style Associative Memory & Personalized PageRank.

Implements neurobiologically-inspired associative memory:
Instead of isolated vector similarity, memory is organized as an associative graph
of concepts, entities, and episodic episodes. Retrieval uses Personalized PageRank (PPR)
with random walks with restart to uncover multi-hop associative connections.

Persistence: The graph loads from and persists to the Postgres `edges` table,
so restarts do not lose the graph.
"""

import os
import logging
from collections import defaultdict
from typing import Dict, Any, List, Tuple, Set, Optional

logger = logging.getLogger(__name__)

# Try pg8000 first, fall back to psycopg2
try:
    import pg8000
except ImportError:
    try:
        import psycopg2 as pg8000
    except ImportError:
        pg8000 = None


class HippoAssociativeGraph:
    """
    Associative Memory Graph with Personalized PageRank (PPR) retrieval.

    Persists to the Postgres `edges` table via the `edges` table created in
    scripts/brain_schema.sql (subject, relation, object, source_file, heading).
    """

    def __init__(self, damping_factor: float = 0.85, max_iterations: int = 20,
                 pg_conn=None, pg_host=None, pg_port=None, pg_user=None,
                 pg_password=None, pg_db=None, persist: bool = True):
        self.damping_factor = damping_factor
        self.max_iterations = max_iterations
        # Adjacency list: node -> Dict[neighbor, weight]
        self.adjacency: Dict[str, Dict[str, float]] = defaultdict(dict)
        self.nodes: Set[str] = set()
        self._pg = pg_conn
        # Persistence is opt-out. It was previously wired but unreachable:
        # brain/hermes_brain.py constructed this with only damping_factor, so
        # _pg_config stayed None, _get_pg_conn() returned None, and the graph
        # silently ran in-memory only -- losing every edge on restart while
        # still reporting success. Config now defaults from the environment so
        # the controller does not have to know the details.
        self.persist = persist
        self._pg_config = None
        if pg_conn is None and persist:
            self._pg_config = {
                "host": pg_host or os.environ.get("POSTGRES_HOST", "localhost"),
                "port": int(pg_port or os.environ.get("POSTGRES_PORT", "5433")),
                "user": pg_user or os.environ.get("POSTGRES_USER", "brain"),
                "password": pg_password or os.environ.get("POSTGRES_PASSWORD", "brain"),
                "database": pg_db or os.environ.get("POSTGRES_DB", "brain"),
            }
        # Auto-load from Postgres if available
        self._load_from_postgres()

    def _get_pg_conn(self):
        """Get or create a Postgres connection."""
        if self._pg:
            return self._pg
        if self._pg_config and pg8000:
            try:
                return pg8000.connect(**self._pg_config)
            except Exception as e:
                logger.warning(f"Postgres connection failed: {e}")
        return None

    def _load_from_postgres(self):
        """Load edges from Postgres into the in-memory adjacency list."""
        conn = self._get_pg_conn()
        if conn is None:
            return
        own_conn = self._pg is None
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT subject, relation, object
                FROM edges
                WHERE superseded_by IS NULL
            """)
            count = 0
            for row in cur.fetchall():
                subject, relation, object_ = row[0], row[1], row[2]
                weight = 1.0
                self.add_edge(subject, object_, weight=weight, bidirectional=False,
                              relation=relation, persist=False)
                count += 1
            logger.info(f"Loaded {count} edges from Postgres")
        except Exception as e:
            logger.warning(f"Failed to load edges from Postgres: {e}")
        finally:
            if own_conn:
                conn.close()

    def _persist_edge(self, source: str, target: str, relation: str,
                      source_file: str = "associative_graph", heading: str = ""):
        """Persist an edge to Postgres. No-op when persistence is disabled."""
        if not self.persist:
            return
        conn = self._get_pg_conn()
        if conn is None:
            return
        own_conn = self._pg is None
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO edges (subject, relation, object, source_file, heading)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (subject, relation, object)
                WHERE superseded_by IS NULL
                DO NOTHING
            """, (source, relation, target, source_file, heading))
            conn.commit()
        except Exception as e:
            logger.warning(f"Failed to persist edge to Postgres: {e}")
        finally:
            if own_conn:
                conn.close()

    def add_edge(self, source: str, target: str, weight: float = 1.0,
                 bidirectional: bool = True, relation: str = "associated",
                 source_file: str = "associative_graph", heading: str = "",
                 persist: bool = True):
        """Add an edge to the graph. Optionally persist to Postgres."""
        self.nodes.add(source)
        self.nodes.add(target)
        self.adjacency[source][target] = weight
        if bidirectional:
            self.adjacency[target][source] = weight
        if persist:
            self._persist_edge(source, target, relation, source_file, heading)

    def add_episode(self, episode_id: str, concepts: List[str],
                    persist: bool = True):
        """Connect an episodic memory node to all constituent concept/entity nodes."""
        self.nodes.add(episode_id)
        for concept in concepts:
            self.add_edge(episode_id, concept, weight=1.0, bidirectional=True,
                          relation="episode_contains", persist=persist)

    def personalized_pagerank(self, seed_nodes: List[str]) -> Dict[str, float]:
        """
        Compute Personalized PageRank starting from seed nodes.
        Returns:
            Dict[node_name, rank_score]
        """
        if not self.nodes:
            return {}

        valid_seeds = [s for s in seed_nodes if s in self.nodes]
        if not valid_seeds:
            return {node: 1.0 / len(self.nodes) for node in self.nodes}

        # Teleport vector
        teleport = {node: 0.0 for node in self.nodes}
        seed_weight = 1.0 / len(valid_seeds)
        for s in valid_seeds:
            teleport[s] = seed_weight

        # Initialize ranks
        ranks = teleport.copy()

        for _ in range(self.max_iterations):
            new_ranks = {node: (1.0 - self.damping_factor) * teleport[node] for node in self.nodes}

            for node in self.nodes:
                neighbors = self.adjacency.get(node, {})
                if not neighbors:
                    # Dangling node distribute to all teleport
                    for t_node, t_val in teleport.items():
                        new_ranks[t_node] += self.damping_factor * ranks[node] * t_val
                    continue

                total_out_weight = sum(neighbors.values())
                if total_out_weight == 0:
                    continue

                for neighbor, weight in neighbors.items():
                    share = (weight / total_out_weight) * ranks[node]
                    new_ranks[neighbor] += self.damping_factor * share

            ranks = new_ranks

        # Normalize ranks
        total = sum(ranks.values()) or 1.0
        return {node: round(score / total, 4) for node, score in ranks.items()}

    def retrieve_relevant(self, seed_nodes: List[str], top_k: int = 5) -> List[Tuple[str, float]]:
        """Retrieve top-k most associatively relevant nodes given query seeds."""
        scores = self.personalized_pagerank(seed_nodes)
        # Filter out the seeds themselves to discover novel associative hops
        ranked = [(node, score) for node, score in scores.items() if node not in seed_nodes]
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked[:top_k]
