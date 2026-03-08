"""
Event graph construction for LexIntel reasoning engine.

Builds a directed graph of events where nodes are events and
edges represent temporal/sequential relationships.
"""

import logging
from typing import Any

import networkx as nx

logger = logging.getLogger(__name__)


class EventGraph:
    """
    Directed graph of legal case events.

    Nodes = individual events (with all event fields as attributes).
    Edges = relationships between events (temporal, causal).
    """

    def __init__(self):
        self.graph = nx.DiGraph()

    def build(self, events: list[dict[str, Any]]) -> None:
        """
        Build graph from a flat list of event dicts.

        Events from the same source document are connected in sequence
        with a 'precedes' edge. Events from different documents with
        the same actor get a 'same_actor' edge.

        Args:
            events: List of event dicts from the pipeline.
        """
        self.graph.clear()

        # Add all events as nodes
        for e in events:
            self.graph.add_node(e["event_id"], **e)

        # Connect events from same document sequentially
        by_doc: dict[str, list[dict]] = {}
        for e in events:
            by_doc.setdefault(e["source_document"], []).append(e)

        for doc_events in by_doc.values():
            for i in range(len(doc_events) - 1):
                self.graph.add_edge(
                    doc_events[i]["event_id"],
                    doc_events[i + 1]["event_id"],
                    relation="precedes",
                )

        # Connect events with same actor across documents
        by_actor: dict[str, list[dict]] = {}
        for e in events:
            actor = e.get("actor", "").lower().strip()
            if actor and actor not in ("unknown", "court", "the law", "the court"):
                by_actor.setdefault(actor, []).append(e)

        for actor_events in by_actor.values():
            if len(actor_events) > 1:
                for i in range(len(actor_events) - 1):
                    src = actor_events[i]["event_id"]
                    dst = actor_events[i + 1]["event_id"]
                    if not self.graph.has_edge(src, dst):
                        self.graph.add_edge(src, dst, relation="same_actor")

        logger.info(
            "[EventGraph] Built graph: %d nodes, %d edges",
            self.graph.number_of_nodes(),
            self.graph.number_of_edges(),
        )

    def get_events_for_actor(self, actor: str) -> list[dict[str, Any]]:
        """Return all events involving a specific actor (case-insensitive)."""
        return [
            data
            for _, data in self.graph.nodes(data=True)
            if data.get("actor", "").lower() == actor.lower()
        ]

    def get_events_for_document(self, source_document: str) -> list[dict[str, Any]]:
        """Return all events from a specific source document."""
        return [
            data
            for _, data in self.graph.nodes(data=True)
            if data.get("source_document") == source_document
        ]

    def get_all_events(self) -> list[dict[str, Any]]:
        """Return all event nodes as a list of dicts."""
        return [data for _, data in self.graph.nodes(data=True)]

    def summary(self) -> dict[str, int]:
        return {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
        }