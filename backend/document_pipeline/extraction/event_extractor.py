"""
Event extractor for LexIntel document pipeline.

Extracts structured legal events from document text using Groq Llama 3.1
and converts them into Event objects.

Robustness: malformed LLM JSON responses are logged and skipped rather
than crashing the entire pipeline.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from groq import Groq

from document_pipeline.models.event_model import Event

logger = logging.getLogger(__name__)

GROQ_MODEL = "llama-3.1-8b-instant"
DEFAULT_CONFIDENCE = 0.8
_FALLBACK_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_TIME_PATTERN = re.compile(
    r"\b("
    r"\d{1,2}:\d{2}\s?(?:AM|PM|am|pm)?|"
    r"\d{4}|"
    r"morning|afternoon|evening|night|midnight|noon|dawn|dusk"
    r")\b"
)
_LOCATION_PATTERN = re.compile(
    r"\b(?:at|in|near|outside|inside)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,3})"
)
_ACTOR_PATTERN = re.compile(
    r"^(?:The\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}|[A-Z][a-z]+\s+(?:court|judge|defendant|plaintiff|witness|officer))\b"
)


def _load_prompt() -> str:
    """Load the event extraction prompt template from prompts/event_prompt.txt."""
    base = Path(__file__).resolve().parent.parent
    prompt_path = base / "prompts" / "event_prompt.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def _get_groq_client() -> Groq:
    """Initialize and return Groq client using GROQ_API_KEY from environment."""
    load_dotenv()
    base = Path(__file__).resolve().parent.parent.parent
    load_dotenv(base / ".env")
    load_dotenv(base / "backend" / ".env")
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set. Add it to .env or environment.")
    return Groq(api_key=api_key)


def _repair_json(text: str) -> str:
    """
    Attempt basic repairs on malformed JSON arrays from LLMs.

    Common LLM mistakes we fix:
      - Trailing commas before ] or }
      - Single quotes instead of double quotes
      - Truncated arrays (add closing bracket)
    """
    # Remove trailing commas before closing brackets/braces
    text = re.sub(r",\s*([}\]])", r"\1", text)

    # Replace smart quotes with straight quotes
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2018", "'").replace("\u2019", "'")

    # If array opened but not closed, close it
    open_count = text.count("[")
    close_count = text.count("]")
    if open_count > close_count:
        # Find last complete object and close after it
        last_brace = text.rfind("}")
        if last_brace != -1:
            text = text[: last_brace + 1] + "]"

    return text


def _extract_json_array(text: str) -> list[dict[str, Any]]:
    """
    Parse JSON array from LLM response with repair fallback.

    Strategy:
      1. Strip markdown code blocks
      2. Try direct parse
      3. Try repair then parse
      4. Try extracting individual objects if array fails
    """
    text = text.strip()

    # Strip markdown code fences
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()

    # Extract the JSON array portion
    array_match = re.search(r"\[[\s\S]*\]", text)
    if not array_match:
        # Maybe it's a single object — wrap it
        obj_match = re.search(r"\{[\s\S]*\}", text)
        if obj_match:
            try:
                obj = json.loads(obj_match.group(0))
                return [obj] if isinstance(obj, dict) else []
            except json.JSONDecodeError:
                pass
        raise ValueError("No JSON array or object found in LLM response")

    json_str = array_match.group(0)

    # Attempt 1: direct parse
    try:
        parsed = json.loads(json_str)
        if isinstance(parsed, list):
            return parsed
        return [parsed] if isinstance(parsed, dict) else []
    except json.JSONDecodeError:
        pass

    # Attempt 2: repair then parse
    repaired = _repair_json(json_str)
    try:
        parsed = json.loads(repaired)
        if isinstance(parsed, list):
            logger.debug("JSON repaired successfully.")
            return parsed
        return [parsed] if isinstance(parsed, dict) else []
    except json.JSONDecodeError:
        pass

    # Attempt 3: extract individual objects from broken array
    objects: list[dict] = []
    for obj_match in re.finditer(r"\{[^{}]*\}", json_str):
        try:
            obj = json.loads(obj_match.group(0))
            if isinstance(obj, dict):
                objects.append(obj)
        except json.JSONDecodeError:
            continue

    if objects:
        logger.warning(
            "Array parse failed — recovered %d individual objects.", len(objects)
        )
        return objects

    raise ValueError(f"Could not parse JSON from LLM response after repair attempts.")


def _raw_to_event(
    raw: dict[str, Any],
    source_document: str,
    confidence: float = DEFAULT_CONFIDENCE,
) -> Event | None:
    """
    Convert a raw JSON object to an Event.
    Returns None if required fields are missing.
    """
    actor = raw.get("actor")
    action = raw.get("action")
    if not actor or not action:
        return None

    actor = str(actor).strip()
    action = str(action).strip()
    if not actor or not action:
        return None

    time_val = raw.get("time")
    location_val = raw.get("location")

    time_str = (
        str(time_val).strip()
        if time_val is not None and str(time_val).strip().lower() not in ("null", "none", "")
        else None
    )
    location_str = (
        str(location_val).strip()
        if location_val is not None and str(location_val).strip().lower() not in ("null", "none", "")
        else None
    )

    # Use caller-supplied confidence as base, penalise for missing fields
    conf = confidence
    if not time_str:
        conf -= 0.05
    if not location_str:
        conf -= 0.05
    conf = round(max(0.0, min(1.0, conf)), 4)

    return Event.create_with_generated_id(
        actor=actor,
        action=action,
        source_document=source_document,
        time=time_str,
        location=location_str,
        confidence=conf,
    )


def _fallback_extract_events(text: str, source_document: str) -> list[Event]:
    """
    Deterministic offline fallback when Groq is unavailable.

    Uses shallow sentence heuristics to emit minimally useful events so the
    reasoning API can still build timelines, contradictions, and weaknesses
    during local development.
    """
    events: list[Event] = []
    seen_actions: set[str] = set()

    for sentence in _FALLBACK_SENTENCE_SPLIT.split(text):
        normalized = " ".join(sentence.split())
        if len(normalized) < 40:
            continue

        actor_match = _ACTOR_PATTERN.search(normalized)
        actor = actor_match.group(1).strip() if actor_match else "Unknown actor"

        lowered = normalized.lower()
        if lowered.startswith("opinion ") or lowered.startswith("page "):
            continue

        action = normalized[:220]
        if action in seen_actions:
            continue
        seen_actions.add(action)

        time_match = _TIME_PATTERN.search(normalized)
        location_match = _LOCATION_PATTERN.search(normalized)

        event = Event.create_with_generated_id(
            actor=actor,
            action=action,
            source_document=source_document,
            time=time_match.group(1) if time_match else None,
            location=location_match.group(1) if location_match else None,
            confidence=0.55,
        )
        events.append(event)

        if len(events) >= 8:
            break

    return events


def extract_events(
    text: str,
    *,
    prompt_template: str | None = None,
    source_document: str = "document",
    confidence: float = DEFAULT_CONFIDENCE,
) -> list[Event]:
    """
    Extract structured events from legal narrative text using Groq Llama 3.1.

    Malformed LLM responses are logged and return an empty list rather
    than raising — this keeps the pipeline running across all cases.

    Args:
        text: Legal document or section text.
        prompt_template: Optional prompt; loads event_prompt.txt if None.
        source_document: Source reference for each Event.
        confidence: Base confidence score (default 0.8).

    Returns:
        List of Event objects. Empty list on LLM/parse failure.
    """
    if not text or not text.strip():
        return []

    MAX_INPUT_CHARS = 6000
    text = text[:MAX_INPUT_CHARS]

    if prompt_template is None:
        prompt_template = _load_prompt()

    prompt = prompt_template.replace("{document_text}", text.strip())

    try:
        client = _get_groq_client()
    except ValueError as e:
        logger.warning("Groq client init failed, using fallback extraction: %s", e)
        return _fallback_extract_events(text, source_document)

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You extract legal events as JSON. "
                        "Output ONLY a valid JSON array. "
                        "No explanation, no markdown, no extra text. "
                        "Every string value must use double quotes. "
                        "Use null (not 'null') for missing fields."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,   # lower temperature = more consistent JSON
        )
    except Exception as e:
        logger.warning("Groq API failure, using fallback extraction: %s", e)
        return _fallback_extract_events(text, source_document)

    content = response.choices[0].message.content
    if not content:
        logger.warning("Empty response from Groq for document: %s", source_document)
        return []

    try:
        raw_list = _extract_json_array(content)
    except ValueError as e:
        logger.warning(
            "Falling back for document '%s' — could not parse LLM response: %s",
            source_document,
            e,
        )
        return _fallback_extract_events(text, source_document)

    events: list[Event] = []
    for raw in raw_list:
        if not isinstance(raw, dict):
            continue
        event = _raw_to_event(raw, source_document, confidence)
        if event:
            events.append(event)

    return events


def extract_events_from_sections(
    sections: list[dict[str, Any]],
    *,
    prompt_template: str | None = None,
    source_document: str = "document",
    confidence: float = DEFAULT_CONFIDENCE,
) -> list[Event]:
    """
    Extract events from pre-split document sections.

    Args:
        sections: List of section dicts with 'content' or 'text' key.
        prompt_template: Optional prompt template.
        source_document: Source document reference.
        confidence: Base confidence score.

    Returns:
        Combined list of Event objects.
    """
    events: list[Event] = []
    for sec in sections:
        content = sec.get("content") or sec.get("text", "")
        if content and str(content).strip():
            events.extend(
                extract_events(
                    str(content),
                    prompt_template=prompt_template,
                    source_document=source_document,
                    confidence=confidence,
                )
            )
    return events
