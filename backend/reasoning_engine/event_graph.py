import networkx as nx
from document_pipeline.models.event_model import Event

class EventGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def build(self, events: list[dict]) -> None:
        for e in events:
            self.graph.add_node(e["event_id"], **e)
        # Connect events from same document in order
        by_doc = {}
        for e in events:
            by_doc.setdefault(e["source_document"], []).append(e)
        for doc_events in by_doc.values():
            for i in range(len(doc_events) - 1):
                self.graph.add_edge(
                    doc_events[i]["event_id"],
                    doc_events[i+1]["event_id"],
                    relation="precedes"
                )

    def get_events_for_actor(self, actor: str) -> list[dict]:
        return [
            data for _, data in self.graph.nodes(data=True)
            if data.get("actor", "").lower() == actor.lower()
        ]