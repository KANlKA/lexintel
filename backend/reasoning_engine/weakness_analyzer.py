"""
Weakness analyzer for LexIntel reasoning engine.

Scores each event for how legally vulnerable or attackable it is,
based on missing information, low confidence, and contradictions.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _append_reason(reasons: list[str], reason: str) -> None:
    """Preserve reason order while avoiding duplicate reason text."""
    if reason not in reasons:
        reasons.append(reason)


def score_weakness(
    event: dict[str, Any],
    contradictions: list[dict[str, Any]],
    all_events: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Calculate a weakness score for a single event.

    Scoring rules:
      +0.40  — event is involved in a critical contradiction
      +0.25  — event is involved in a moderate contradiction
      +0.20  — missing time
      +0.10  — missing location
      +0.25  — confidence < 0.7
      +0.10  — confidence between 0.7 and 0.79
      +0.15  — only one event from this source document (single-source dependency)

    Score is clamped to [0.0, 1.0].

    Args:
        event: Single event dict.
        contradictions: All detected contradictions.
        all_events: All events (used to check single-source dependency).

    Returns:
        Dict with event_id, weakness_score (0-1), severity label, and reasons list.
    """
    score = 0.0
    reasons: list[str] = []
    eid = event["event_id"]

    # Check contradiction involvement
    for c in contradictions:
        if eid in (c["event1_id"], c["event2_id"]):
            if c["severity"] == "critical":
                score += 0.40
                _append_reason(reasons, f"critical contradiction: {c['type']}")
            elif c["severity"] == "moderate":
                score += 0.25
                _append_reason(reasons, f"moderate contradiction: {c['type']}")

    # Missing time
    time_val = event.get("time")
    if not time_val or str(time_val).lower() in ("null", "unknown", "none", ""):
        score += 0.20
        _append_reason(reasons, "missing time")

    # Missing location
    loc_val = event.get("location")
    if not loc_val or str(loc_val).lower() in ("null", "unknown", "none", ""):
        score += 0.10
        _append_reason(reasons, "missing location")

    # Low confidence
    confidence = event.get("confidence", 1.0)
    if confidence < 0.7:
        score += 0.25
        _append_reason(reasons, f"low extraction confidence ({confidence:.2f})")
    elif confidence < 0.8:
        score += 0.10
        _append_reason(reasons, f"moderate extraction confidence ({confidence:.2f})")

    # Single-source dependency
    source = event.get("source_document")
    source_count = sum(1 for e in all_events if e.get("source_document") == source)
    if source_count == 1:
        score += 0.15
        _append_reason(reasons, "only event from this source document")

    score = round(min(score, 1.0), 3)

    if score >= 0.6:
        severity = "high"
    elif score >= 0.3:
        severity = "medium"
    else:
        severity = "low"

    return {
        "event_id": eid,
        "actor": event.get("actor"),
        "action": event.get("action"),
        "weakness_score": score,
        "severity": severity,
        "reasons": reasons,
        "source_document": event.get("source_document"),
    }


def analyze_weaknesses(
    events: list[dict[str, Any]],
    contradictions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Score all events for weakness and return sorted results.

    Args:
        events: All extracted events.
        contradictions: All detected contradictions.

    Returns:
        List of weakness dicts sorted by weakness_score descending.
    """
    results = [score_weakness(e, contradictions, events) for e in events]
    results.sort(key=lambda x: x["weakness_score"], reverse=True)
    logger.info(
        "[Weakness] Scored %d events. High: %d, Medium: %d, Low: %d",
        len(results),
        sum(1 for r in results if r["severity"] == "high"),
        sum(1 for r in results if r["severity"] == "medium"),
        sum(1 for r in results if r["severity"] == "low"),
    )
    return results
