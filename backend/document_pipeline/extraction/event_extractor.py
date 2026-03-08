"""
Event extractor for LexIntel document pipeline.

Extracts structured legal events from document text using Groq Llama 3.1
and converts them into Event objects.
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


def _load_prompt() -> str:
    """Load the event extraction prompt template from prompts/event_prompt.txt."""
    base = Path(__file__).resolve().parent.parent
    prompt_path = base / "prompts" / "event_prompt.txt"
    if not prompt_path.exists():
        msg = f"Prompt file not found: {prompt_path}"
        raise FileNotFoundError(msg)
    return prompt_path.read_text(encoding="utf-8")


def _get_groq_client() -> Groq:
    """Initialize and return Groq client using GROQ_API_KEY from environment."""
    load_dotenv()
    base = Path(__file__).resolve().parent.parent.parent
    load_dotenv(base / ".env")
    load_dotenv(base / "backend" / ".env")
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        msg = "GROQ_API_KEY not set. Add it to .env or environment."
        raise ValueError(msg)
    return Groq(api_key=api_key)


def _extract_json_array(text: str) -> list[dict[str, Any]]:
    """
    Parse JSON array from LLM response. Handles markdown code blocks and
    extra text after the JSON array.
    """
    text = text.strip()
    # Remove markdown code blocks if present
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()
    # Extract the first JSON array from the response (handles extra text after)
    array_match = re.search(r"\[[\s\S]*\]", text)
    if not array_match:
        raise ValueError("No JSON array found in LLM response")
    json_str = array_match.group(0)
    try:
        parsed = json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.warning("Invalid JSON from LLM: %s", e)
        raise ValueError(f"Invalid JSON response: {e}") from e
    if not isinstance(parsed, list):
        parsed = [parsed] if isinstance(parsed, dict) else []
    return parsed


def _raw_to_event(
    raw: dict[str, Any],
    source_document: str,
    confidence: float = DEFAULT_CONFIDENCE,  # FIX: now actually used as base
) -> Event | None:
    """
    Convert a raw JSON object to an Event. Returns None if required fields missing.

    Confidence is calculated from the caller-supplied base score, then
    penalised for missing time (-0.05) or missing location (-0.05).
    Previously the base was hardcoded to 0.9 and the parameter ignored — fixed.
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
        if time_val is not None and str(time_val).strip().lower() != "null"
        else None
    )
    location_str = (
        str(location_val).strip()
        if location_val is not None and str(location_val).strip().lower() != "null"
        else None
    )

    # FIX: use the passed-in confidence as base, not hardcoded 0.9
    conf = confidence
    if not time_str:
        conf -= 0.05
    if not location_str:
        conf -= 0.05
    conf = round(max(0.0, min(1.0, conf)), 4)  # clamp to [0, 1]

    return Event.create_with_generated_id(
        actor=actor,
        action=action,
        source_document=source_document,
        time=time_str,
        location=location_str,
        confidence=conf,
    )


def extract_events(
    text: str,
    *,
    prompt_template: str | None = None,
    source_document: str = "document",
    confidence: float = DEFAULT_CONFIDENCE,
) -> list[Event]:
    """
    Extract structured events from legal narrative text using Groq Llama 3.1.

    Sends the text to the LLM, parses the JSON array response, and converts
    each item into an Event. Handles invalid JSON, missing fields, and API errors.

    Args:
        text: Legal document or section text.
        prompt_template: Optional prompt; uses prompts/event_prompt.txt if None.
        source_document: Reference for source_document on each Event.
        confidence: Base confidence score for extracted events (default 0.8).
                    Penalised -0.05 each for missing time or location.

    Returns:
        List of Event objects.
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
        logger.error("Groq client init failed: %s", e)
        raise

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You extract legal events as JSON. Output only valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
        )
    except Exception as e:
        logger.error("Groq API failure: %s", e)
        raise RuntimeError(f"Groq API failed: {e}") from e

    content = response.choices[0].message.content
    if not content:
        return []

    try:
        raw_list = _extract_json_array(content)
    except ValueError as e:
        logger.warning("Could not parse LLM response as JSON: %s", e)
        raise

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