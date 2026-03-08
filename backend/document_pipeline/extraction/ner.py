"""
Named Entity Recognition (NER) for LexIntel document pipeline.

Identifies legal entities such as parties, dates, locations, and times
in legal document text using spaCy.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

# Labels to extract: PERSON -> persons, GPE -> locations, DATE -> dates, TIME -> times
_LABEL_MAP = {
    "PERSON": "persons",
    "GPE": "locations",
    "DATE": "dates",
    "TIME": "times",
}


def _get_nlp():
    """
    Lazy-load spaCy model to avoid loading on import.

    Returns None when spaCy/model is unavailable (e.g., unsupported Python runtime).
    """
    if not hasattr(_get_nlp, "_nlp"):
        try:
            import spacy

            _get_nlp._nlp = spacy.load("en_core_web_sm")
        except Exception as exc:
            print(f"[NER] spaCy unavailable, skipping entity extraction: {exc}")
            _get_nlp._nlp = None
    return _get_nlp._nlp


def extract_entities(text: str) -> dict[str, list[str]]:
    """
    Extract named entities from text using spaCy.

    Extracts PERSON, GPE (locations), DATE, and TIME. Returns a dict
    with keys "persons", "locations", "dates", "times". Duplicates
    are removed. Empty lists returned when none found.

    Args:
        text: Document or section text.

    Returns:
        Dict with "persons", "locations", "dates", "times" keys.
    """
    result: dict[str, list[str]] = {
        "persons": [],
        "locations": [],
        "dates": [],
        "times": [],
    }

    if not text or not text.strip():
        return result

    nlp = _get_nlp()
    if nlp is None:
        return result

    doc = nlp(text)

    # Use sets to deduplicate, then convert to list
    collected: dict[str, set[str]] = {
        "persons": set(),
        "locations": set(),
        "dates": set(),
        "times": set(),
    }

    for ent in doc.ents:
        if ent.label_ in _LABEL_MAP:
            key = _LABEL_MAP[ent.label_]
            collected[key].add(ent.text.strip())

    for key in result:
        result[key] = sorted(collected[key])

    return result


class EntityType(str, Enum):
    """Legal entity types for NER."""

    PARTY = "PARTY"
    DATE = "DATE"
    AMOUNT = "AMOUNT"
    JURISDICTION = "JURISDICTION"
    STATUTE = "STATUTE"
    LOCATION = "LOCATION"
    ORGANIZATION = "ORGANIZATION"


@dataclass
class Entity:
    """A named entity extracted from text."""

    text: str
    entity_type: EntityType
    start_char: int
    end_char: int
    confidence: float = 1.0


def extract_entities_dict(text: str) -> list[dict[str, Any]]:
    """
    Extract entities and return as flat list of dicts for serialization.

    Args:
        text: Document or section text.

    Returns:
        List of entity dicts with 'text' and 'type' keys.
    """
    entities = extract_entities(text)
    result: list[dict[str, Any]] = []
    type_map = {"persons": "PERSON", "locations": "GPE", "dates": "DATE", "times": "TIME"}
    for key, texts in entities.items():
        for t in texts:
            result.append({"text": t, "type": type_map[key]})
    return result
