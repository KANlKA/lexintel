"""
Contradiction detection for LexIntel reasoning engine.

Detects logical conflicts between events extracted from legal documents.
Checks for location conflicts, time conflicts, and action impossibilities.
"""

import logging
from itertools import combinations
from typing import Any

logger = logging.getLogger(__name__)

# Actors too generic to meaningfully compare across events
_SKIP_ACTORS = {
    "unknown", "court", "the court", "the law", "judge",
    "courts", "justice", "the indictment", "the principle",
    "the legislature", "the constitution",
}


def _normalize(value: str | None) -> str | None:
    """Lowercase and strip a string, return None if empty/null/unknown."""
    if not value:
        return None
    v = value.lower().strip()
    if v in ("null", "unknown", "n/a", "none", ""):
        return None
    return v


def _times_conflict(t1: str, t2: str) -> bool:
    """
    Return True if two time strings appear to describe the same moment.
    Only matches when both are specific enough (not "unknown").
    """
    t1n = _normalize(t1)
    t2n = _normalize(t2)
    if not t1n or not t2n:
        return False
    # Remove filler words for comparison
    for filler in ("around ", "approximately ", "about ", "near "):
        t1n = t1n.replace(filler, "")
        t2n = t2n.replace(filler, "")
    return t1n == t2n


def _locations_conflict(l1: str, l2: str) -> bool:
    """Return True if two locations are both specific and different."""
    l1n = _normalize(l1)
    l2n = _normalize(l2)
    if not l1n or not l2n:
        return False
    return l1n != l2n


def detect_contradictions(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Detect contradictions between all pairs of events.

    Currently detects:
      1. Location conflict — same actor, same time, different location
      2. Action conflict   — same actor, same time, mutually exclusive actions

    Args:
        events: Flat list of event dicts.

    Returns:
        List of contradiction dicts with fields:
          event1_id, event2_id, type, description, severity,
          event1_summary, event2_summary
    """
    contradictions: list[dict[str, Any]] = []

    for e1, e2 in combinations(events, 2):
        actor1 = _normalize(e1.get("actor", ""))
        actor2 = _normalize(e2.get("actor", ""))

        # Only compare events with the same non-generic actor
        if not actor1 or not actor2:
            continue
        if actor1 != actor2:
            continue
        if actor1 in _SKIP_ACTORS:
            continue

        time1 = e1.get("time")
        time2 = e2.get("time")
        loc1 = e1.get("location")
        loc2 = e2.get("location")

        # ── Rule 1: Location conflict ────────────────────────────────────
        if _times_conflict(time1, time2) and _locations_conflict(loc1, loc2):
            contradictions.append({
                "event1_id": e1["event_id"],
                "event2_id": e2["event_id"],
                "type": "location_conflict",
                "description": (
                    f"'{e1['actor']}' cannot be at '{loc1}' and '{loc2}' "
                    f"at the same time ({time1})."
                ),
                "severity": "critical",
                "event1_summary": f"{e1['actor']} → {e1['action']} @ {loc1}",
                "event2_summary": f"{e2['actor']} → {e2['action']} @ {loc2}",
            })

        # ── Rule 2: Action conflict (same actor, same time, different doc) ─
        # If same actor has two events at same time from different source docs,
        # flag as a potential inconsistency worth reviewing.
        elif (
            _times_conflict(time1, time2)
            and e1.get("source_document") != e2.get("source_document")
            and _normalize(e1.get("action")) != _normalize(e2.get("action"))
        ):
            contradictions.append({
                "event1_id": e1["event_id"],
                "event2_id": e2["event_id"],
                "type": "cross_document_conflict",
                "description": (
                    f"'{e1['actor']}' described differently across documents "
                    f"at the same time ({time1}): "
                    f"'{e1['action']}' vs '{e2['action']}'."
                ),
                "severity": "moderate",
                "event1_summary": f"{e1['source_document']}: {e1['action']}",
                "event2_summary": f"{e2['source_document']}: {e2['action']}",
            })

    logger.info("[Contradictions] Detected %d contradictions.", len(contradictions))
    return contradictions