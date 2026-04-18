"""
Embedding-based contradiction detection for LexIntel.

Uses sentence-transformers to encode event actions as vectors.
Same-actor events from different documents with low cosine similarity
are flagged as potential contradictions.

Research Approach B — semantic embedding.
"""

import logging
from itertools import combinations
from typing import Any

from reasoning_engine.contradiction_detector import detect_contradictions

logger = logging.getLogger(__name__)

_SKIP_ACTORS = {
    "unknown", "court", "the court", "the law", "judge",
    "courts", "justice", "the indictment", "the legislature",
}

# Lazy-load model so import doesn't block startup
_model = None


def _cosine_similarity(vec1, vec2) -> float:
    """Return cosine similarity for two embedding vectors."""
    dot = sum(float(a) * float(b) for a, b in zip(vec1, vec2))
    norm1 = sum(float(a) * float(a) for a in vec1) ** 0.5
    norm2 = sum(float(b) * float(b) for b in vec2) ** 0.5
    if not norm1 or not norm2:
        return 0.0
    return dot / (norm1 * norm2)


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("[Embedding] Loading sentence-transformers model...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("[Embedding] Model loaded.")
    return _model


def detect_contradictions_embedding(
    events: list[dict[str, Any]],
    similarity_threshold: float = 0.35,
) -> list[dict[str, Any]]:
    """
    Detect contradictions using semantic similarity between event actions.

    Two events from the same actor but different source documents
    are flagged as contradictory if their action descriptions have
    cosine similarity below the threshold.

    Lower similarity = more different = more likely a contradiction.

    Args:
        events: Flat list of event dicts from the pipeline.
        similarity_threshold: Cosine similarity below which events
                              are considered contradictory (0-1).

    Returns:
        List of contradiction dicts with approach='embedding'.
    """
    if not events:
        return []

    try:
        model = _get_model()
    except ImportError as exc:
        logger.warning(
            "[Embedding] sentence-transformers unavailable, using rule fallback: %s",
            exc,
        )
        fallback = detect_contradictions(events)
        for item in fallback:
            item["approach"] = "embedding_fallback"
        return fallback

    # Group events by actor
    by_actor: dict[str, list[dict]] = {}
    for e in events:
        actor = e.get("actor", "").lower().strip()
        if not actor or actor in _SKIP_ACTORS:
            continue
        by_actor.setdefault(actor, []).append(e)

    contradictions: list[dict[str, Any]] = []

    for actor, actor_events in by_actor.items():
        if len(actor_events) < 2:
            continue

        # Only compare across different source documents
        cross_doc_pairs = [
            (e1, e2)
            for e1, e2 in combinations(actor_events, 2)
            if e1["source_document"] != e2["source_document"]
        ]

        if not cross_doc_pairs:
            continue

        # Encode all unique actions in one batch (efficient)
        unique_events = list({e["event_id"]: e for e in actor_events}.values())
        actions = [e.get("action", "") for e in unique_events]
        id_to_idx = {e["event_id"]: i for i, e in enumerate(unique_events)}

        embeddings = model.encode(actions, show_progress_bar=False)

        for e1, e2 in cross_doc_pairs:
            idx1 = id_to_idx[e1["event_id"]]
            idx2 = id_to_idx[e2["event_id"]]

            sim = float(_cosine_similarity(embeddings[idx1], embeddings[idx2]))

            if sim < similarity_threshold:
                severity = "critical" if sim < 0.15 else "moderate"
                contradictions.append({
                    "event1_id":     e1["event_id"],
                    "event2_id":     e2["event_id"],
                    "type":          "semantic_conflict",
                    "description": (
                        f"'{e1['actor']}' described differently across documents: "
                        f"'{e1['action']}' vs '{e2['action']}' "
                        f"(semantic similarity: {sim:.2f})"
                    ),
                    "severity":          severity,
                    "similarity_score":  round(sim, 4),
                    "event1_summary":    f"{e1['source_document']}: {e1['action']}",
                    "event2_summary":    f"{e2['source_document']}: {e2['action']}",
                    "approach":          "embedding",
                })

    logger.info(
        "[Embedding] Detected %d semantic contradictions.", len(contradictions)
    )
    return contradictions
