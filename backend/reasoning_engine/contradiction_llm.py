"""
LLM-based contradiction detection for LexIntel.

Uses Groq Llama 3.1 to judge whether event pairs describe mutually
inconsistent facts. This is research Approach C in evaluate.py.
"""

import json
import logging
import os
import re
from itertools import combinations
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from groq import Groq

from reasoning_engine.contradiction_detector import detect_contradictions

logger = logging.getLogger(__name__)

GROQ_MODEL = "llama-3.1-8b-instant"

_SKIP_ACTORS = {
    "unknown", "unknown actor", "court", "the court", "the law", "judge",
    "courts", "justice", "the indictment", "the legislature",
}


def _get_groq_client() -> Groq:
    """Initialize and return Groq client using GROQ_API_KEY."""
    load_dotenv()
    base = Path(__file__).resolve().parent.parent
    load_dotenv(base / ".env")
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set. Add it to .env or environment.")
    return Groq(api_key=api_key)


def _normalize(value: str | None) -> str:
    if not value:
        return ""
    return value.lower().strip()


def _event_summary(event: dict[str, Any]) -> str:
    return (
        f"ID: {event.get('event_id')}\n"
        f"Actor: {event.get('actor') or 'Unknown'}\n"
        f"Action: {event.get('action') or 'Unknown'}\n"
        f"Time: {event.get('time') or 'Unknown'}\n"
        f"Location: {event.get('location') or 'Unknown'}\n"
        f"Source: {event.get('source_document') or 'Unknown'}"
    )


def _parse_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()

    obj_match = re.search(r"\{[\s\S]*\}", text)
    if not obj_match:
        raise ValueError("No JSON object found in LLM response.")

    return json.loads(obj_match.group(0))


def _candidate_pairs(
    events: list[dict[str, Any]],
    max_pairs: int,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []

    for e1, e2 in combinations(events, 2):
        actor1 = _normalize(e1.get("actor"))
        actor2 = _normalize(e2.get("actor"))

        if not actor1 or not actor2:
            continue
        if actor1 in _SKIP_ACTORS or actor2 in _SKIP_ACTORS:
            continue

        same_actor = actor1 == actor2
        same_time = bool(e1.get("time") and e1.get("time") == e2.get("time"))
        same_location = bool(
            e1.get("location") and e1.get("location") == e2.get("location")
        )

        if same_actor or same_time or same_location:
            pairs.append((e1, e2))

        if len(pairs) >= max_pairs:
            break

    return pairs


def _fallback_detect(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Use the deterministic detector when Groq is unavailable."""
    fallback = detect_contradictions(events)
    for item in fallback:
        item["approach"] = "llm_fallback"
    return fallback


def detect_contradictions_llm(
    events: list[dict[str, Any]],
    max_pairs: int = 30,
) -> list[dict[str, Any]]:
    """
    Detect contradictions by asking an LLM to judge likely candidate pairs.

    Args:
        events: Flat list of event dicts from the pipeline.
        max_pairs: Maximum event pairs to ask the LLM to review.

    Returns:
        List of contradiction dicts with approach='llm'.
    """
    if not events:
        return []

    pairs = _candidate_pairs(events, max_pairs)
    if not pairs:
        return []

    try:
        client = _get_groq_client()
    except ValueError as exc:
        logger.warning("[LLM] Groq client init failed, using rule fallback: %s", exc)
        return _fallback_detect(events)

    contradictions: list[dict[str, Any]] = []

    for e1, e2 in pairs:
        prompt = f"""
Decide whether these two legal case events are a direct factual contradiction.

Event 1:
{_event_summary(e1)}

Event 2:
{_event_summary(e2)}

Return only JSON with this exact shape:
{{
  "contradiction": true,
  "type": "time_conflict | location_conflict | action_conflict | role_conflict | none",
  "severity": "low | moderate | critical",
  "reason": "short explanation"
}}

Mark contradiction true only if both events cannot be true at the same time.
Different procedural steps, legal rules, citations, or sequential events are not contradictions.
"""

        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a careful legal-event contradiction judge. "
                            "Return only valid JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
            )
        except Exception as exc:
            logger.warning("[LLM] Groq API failure, using rule fallback: %s", exc)
            return _fallback_detect(events)

        content = response.choices[0].message.content
        if not content:
            continue

        try:
            result = _parse_json_object(content)
        except (ValueError, json.JSONDecodeError) as exc:
            logger.warning("[LLM] Could not parse response: %s", exc)
            continue

        if not result.get("contradiction"):
            continue

        contradictions.append({
            "event1_id": e1["event_id"],
            "event2_id": e2["event_id"],
            "type": result.get("type") or "llm_conflict",
            "description": result.get("reason") or "LLM judged the events contradictory.",
            "severity": result.get("severity") or "moderate",
            "event1_summary": f"{e1.get('source_document')}: {e1.get('action')}",
            "event2_summary": f"{e2.get('source_document')}: {e2.get('action')}",
            "approach": "llm",
        })

    logger.info("[LLM] Detected %d contradictions.", len(contradictions))
    return contradictions
