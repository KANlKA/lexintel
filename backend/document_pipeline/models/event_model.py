"""
Event model for LexIntel document pipeline.

Defines the schema for structured legal events extracted from documents.
"""

import uuid
from typing import Any

from pydantic import BaseModel, Field


def generate_event_id() -> str:
    """Generate a unique event ID (UUID4)."""
    return str(uuid.uuid4())


class Event(BaseModel):
    """Structured representation of a legal event extracted from a document."""

    event_id: str
    actor: str
    action: str
    time: str | None = None
    location: str | None = None
    source_document: str
    confidence: float = Field(..., ge=0.0, le=1.0)

    @classmethod
    def create_with_generated_id(
        cls,
        actor: str,
        action: str,
        source_document: str,
        *,
        time: str | None = None,
        location: str | None = None,
        confidence: float = 1.0,
    ) -> "Event":
        """
        Create an Event with an auto-generated event_id.

        Args:
            actor: Who performed the action.
            action: What was done.
            source_document: Source document reference.
            time: Optional time of the event.
            location: Optional location.
            confidence: Confidence score (0.0–1.0).

        Returns:
            Event instance with generated event_id.
        """
        return cls(
            event_id=generate_event_id(),
            actor=actor,
            action=action,
            time=time,
            location=location,
            source_document=source_document,
            confidence=confidence,
        )

    def model_dump(self) -> dict[str, Any]:
        """Alias for Pydantic's model_dump; use for JSON serialization."""
        return super().model_dump()
