"""
Timeline builder for LexIntel reasoning engine.

Constructs a chronological timeline from extracted events.
Handles fuzzy times, unknown times, and date normalization.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Fuzzy time keywords mapped to sort order (lower = earlier in day)
_FUZZY_TIME_ORDER = {
    "dawn": 5,
    "early morning": 6,
    "morning": 8,
    "mid-morning": 9,
    "noon": 12,
    "midday": 12,
    "afternoon": 14,
    "mid-afternoon": 15,
    "evening": 18,
    "dusk": 19,
    "night": 21,
    "midnight": 24,
    "late night": 25,
}


def _parse_hour(time_str: str) -> float | None:
    """
    Extract a numeric hour (0-25) from a time string for sorting.

    Handles:
      - "7:45 PM" → 19.75
      - "around midnight" → 24
      - "morning" → 8
      - "31st day of March, 1819" → None (date, not time of day)
      - None / "unknown" → None
    """
    if not time_str:
        return None

    s = time_str.lower().strip()

    if s in ("unknown", "null", "n/a", ""):
        return None

    # Check fuzzy keywords
    for keyword, hour in _FUZZY_TIME_ORDER.items():
        if keyword in s:
            return float(hour)

    # Try HH:MM AM/PM pattern
    match = re.search(r"(\d{1,2}):(\d{2})\s*(am|pm)?", s)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        meridiem = match.group(3)
        if meridiem == "pm" and hour != 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
        return hour + minute / 60.0

    # Try plain hour "at 9" or "around 11"
    match = re.search(r"\bat\s+(\d{1,2})\b|\baround\s+(\d{1,2})\b", s)
    if match:
        hour = int(match.group(1) or match.group(2))
        return float(hour)

    return None


def _parse_year(time_str: str) -> int | None:
    """Extract a 4-digit year from a time string for cross-day sorting."""
    if not time_str:
        return None
    match = re.search(r"\b(1[0-9]{3}|20[0-9]{2})\b", time_str)
    if match:
        return int(match.group(1))
    return None


def build_timeline(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Sort events into a chronological timeline.

    Events with parseable times are sorted first (by year, then hour).
    Events with fuzzy/unknown times are appended at the end with
    time_uncertain=True flag.

    Args:
        events: List of event dicts from the pipeline.

    Returns:
        Ordered list of event dicts with added fields:
          - timeline_position (int): 1-based position in timeline
          - time_uncertain (bool): True if time could not be parsed
          - parsed_hour (float | None): extracted hour for reference
    """
    timed: list[tuple[int, float, dict]] = []    # (year, hour, event)
    untimed: list[dict] = []

    for e in events:
        time_str = e.get("time")
        hour = _parse_hour(time_str) if time_str else None
        year = _parse_year(time_str) if time_str else None

        if hour is not None:
            timed.append((year or 9999, hour, e))
        else:
            untimed.append(e)

    # Sort timed events: year first, then hour within same year
    timed.sort(key=lambda x: (x[0], x[1]))

    result: list[dict[str, Any]] = []
    position = 1

    for year, hour, e in timed:
        result.append({
            **e,
            "timeline_position": position,
            "time_uncertain": False,
            "parsed_hour": round(hour, 2),
        })
        position += 1

    for e in untimed:
        result.append({
            **e,
            "timeline_position": position,
            "time_uncertain": True,
            "parsed_hour": None,
        })
        position += 1

    logger.info(
        "[Timeline] %d timed events, %d uncertain events",
        len(timed),
        len(untimed),
    )
    return result