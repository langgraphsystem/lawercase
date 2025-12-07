"""Memory Reflection Policy - Extract and score salient facts from events.

This module provides:
- Heuristic compression for fast event processing
- LLM-based fact extraction for production use
- Salience scoring based on event type and content
- Entity extraction for improved searchability
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from dataclasses import dataclass
from typing import Any

from ..models import AuditEvent, MemoryRecord


@dataclass
class ExtractedFact:
    """A fact extracted from an event."""

    text: str
    fact_type: str  # "preference", "entity", "milestone", "action", "context"
    salience: float  # 0.0 - 1.0
    confidence: float  # 0.0 - 1.0
    entities: list[str]
    tags: list[str]


# Salience weights by action type
ACTION_SALIENCE = {
    # High salience (0.9+)
    "case_create": 0.95,
    "document_generate": 0.92,
    "preference_set": 0.90,
    "milestone_reached": 0.90,
    # Medium-high salience (0.7-0.9)
    "handle_command": 0.80,
    "node_complete": 0.75,
    "decision_made": 0.78,
    "question_answered": 0.72,
    # Medium salience (0.5-0.7)
    "context_update": 0.60,
    "search_performed": 0.55,
    "retrieval_complete": 0.52,
    # Low salience (< 0.5)
    "log_message": 0.30,
    "debug": 0.10,
}

# Entity extraction patterns
ENTITY_PATTERNS = {
    "person": r"\b([A-Z][a-z]+ [A-Z][a-z]+)\b",
    "date": r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})\b",
    "case_id": r"\b(case_[a-zA-Z0-9_]+)\b",
    "email": r"\b([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\b",
    "money": r"\$[\d,]+(?:\.\d{2})?",
}


def compress_event(event: AuditEvent) -> str:
    """Compress an event to a concise one-liner for storage.

    Args:
        event: AuditEvent to compress

    Returns:
        Compressed string representation
    """
    user = f"u={event.user_id}" if event.user_id else "u=?"
    act = event.action
    src = event.source
    detail = event.payload.get("summary") or event.payload.get("text") or ""
    if detail:
        detail = str(detail)[:200]
    return f"[{src}] {act} {user} {detail}".strip()


def extract_entities(text: str) -> dict[str, list[str]]:
    """Extract named entities from text using patterns.

    Args:
        text: Text to extract entities from

    Returns:
        Dict of entity type -> list of entities
    """
    entities: dict[str, list[str]] = {}
    for entity_type, pattern in ENTITY_PATTERNS.items():
        matches = re.findall(pattern, text)
        if matches:
            entities[entity_type] = list(set(matches))
    return entities


def calculate_salience(event: AuditEvent, extracted_entities: dict[str, list[str]]) -> float:
    """Calculate salience score based on event type and content.

    Args:
        event: The audit event
        extracted_entities: Entities extracted from event

    Returns:
        Salience score between 0.0 and 1.0
    """
    # Base salience from action type
    base_salience = ACTION_SALIENCE.get(event.action, 0.5)

    # Boost for tags
    tags = event.tags or []
    if "preference" in tags:
        base_salience = min(1.0, base_salience + 0.15)
    if "important" in tags:
        base_salience = min(1.0, base_salience + 0.10)
    if "user_explicit" in tags:
        base_salience = min(1.0, base_salience + 0.20)

    # Boost for entity density
    entity_count = sum(len(v) for v in extracted_entities.values())
    if entity_count > 0:
        base_salience = min(1.0, base_salience + 0.05 * min(entity_count, 3))

    return round(base_salience, 2)


def select_salient_facts(event: AuditEvent) -> list[MemoryRecord]:
    """Extract salient facts from an event using heuristics.

    This is the fast path for development. In production with LLM enabled,
    use `aselect_salient_facts_llm` for better extraction.

    Args:
        event: AuditEvent to process

    Returns:
        List of MemoryRecord objects representing extracted facts
    """
    text = compress_event(event)
    entities = extract_entities(text)
    salience = calculate_salience(event, entities)

    # Determine fact type
    fact_type = "action"
    tags = list(event.tags or [])

    if event.action in {"handle_command", "node_complete"}:
        tags.append("milestone")
        fact_type = "milestone"
    if "preference" in tags:
        fact_type = "preference"
    if any(entities.get(k) for k in ["person", "case_id"]):
        tags.append("entity")
        fact_type = "entity"

    # Add entity tags
    for entity_type, entity_list in entities.items():
        for entity in entity_list[:3]:  # Limit to 3 per type
            tags.append(f"{entity_type}:{entity}")

    rec = MemoryRecord(
        user_id=event.user_id,
        type="semantic",
        text=text,
        salience=salience,
        confidence=0.6 if fact_type == "action" else 0.75,
        source=event.source,
        tags=tags,
        metadata={
            "fact_type": fact_type,
            "entities": entities,
            "event_id": event.event_id,
            "action": event.action,
        },
    )
    return [rec]


# LLM-based extraction prompt
EXTRACTION_PROMPT = """Analyze this event and extract key facts for long-term memory storage.

Event:
- Source: {source}
- Action: {action}
- User: {user_id}
- Content: {content}
- Tags: {tags}

Extract:
1. **Key Facts**: Important information worth remembering (1-3 facts)
2. **Preferences**: Any user preferences expressed
3. **Entities**: People, cases, dates, organizations mentioned
4. **Importance**: Rate 0.0-1.0 how important this is to remember

Respond in JSON format:
{{
    "facts": [
        {{"text": "...", "type": "fact|preference|entity", "importance": 0.8}}
    ],
    "entities": {{"person": [...], "case": [...], "date": [...]}},
    "should_remember": true/false
}}"""


async def aselect_salient_facts_llm(
    event: AuditEvent,
    *,
    llm_client: Any | None = None,
) -> list[MemoryRecord]:
    """Extract salient facts using LLM for better understanding.

    Args:
        event: AuditEvent to process
        llm_client: Optional LLM client (uses OpenAI if not provided)

    Returns:
        List of MemoryRecord objects with LLM-extracted facts
    """
    # Fall back to heuristics if LLM not available
    if llm_client is None:
        try:
            from core.llm_interface.openai_client import OpenAIClient

            llm_client = OpenAIClient(
                model=os.getenv("OPENAI_DEFAULT_MODEL", "gpt-5.1"),
                temperature=0.1,  # Low temp for factual extraction
                max_tokens=500,
            )
        except ImportError:
            return select_salient_facts(event)

    # Build prompt
    content = event.payload.get("summary") or event.payload.get("text") or json.dumps(event.payload)
    prompt = EXTRACTION_PROMPT.format(
        source=event.source,
        action=event.action,
        user_id=event.user_id or "unknown",
        content=str(content)[:1000],
        tags=", ".join(event.tags or []),
    )

    try:
        result = await llm_client.acomplete(prompt=prompt)
        response_text = result.get("output", "")

        # Parse JSON response
        json_match = re.search(r"\{[\s\S]*\}", response_text)
        if not json_match:
            return select_salient_facts(event)

        parsed = json.loads(json_match.group())

        # Check if worth remembering
        if not parsed.get("should_remember", True):
            return []

        # Convert to MemoryRecords
        records: list[MemoryRecord] = []
        for fact in parsed.get("facts", []):
            fact_text = fact.get("text", "")
            if not fact_text:
                continue

            fact_type = fact.get("type", "fact")
            importance = float(fact.get("importance", 0.7))

            # Generate stable ID (md5 used for ID generation, not security)
            fact_hash = hashlib.md5(
                f"{event.event_id}:{fact_text}".encode(),
                usedforsecurity=False,
            ).hexdigest()[:12]

            tags = [fact_type]
            entities = parsed.get("entities", {})
            for entity_type, entity_list in entities.items():
                for entity in entity_list[:3]:
                    tags.append(f"{entity_type}:{entity}")

            rec = MemoryRecord(
                id=f"mem_{fact_hash}",
                user_id=event.user_id,
                type="semantic",
                text=fact_text,
                salience=importance,
                confidence=0.85,  # Higher confidence for LLM extraction
                source=event.source,
                tags=tags,
                metadata={
                    "fact_type": fact_type,
                    "entities": entities,
                    "event_id": event.event_id,
                    "extraction": "llm",
                    "model": "gpt-5.1",
                },
            )
            records.append(rec)

        return records if records else select_salient_facts(event)

    except (json.JSONDecodeError, KeyError, TypeError):
        # Fall back to heuristics on parse error
        return select_salient_facts(event)


class ReflectionPolicy:
    """Configurable reflection policy for memory extraction.

    Supports both heuristic (fast) and LLM-based (accurate) extraction.
    """

    def __init__(
        self,
        *,
        use_llm: bool = False,
        llm_client: Any | None = None,
        min_salience: float = 0.3,
    ) -> None:
        """Initialize reflection policy.

        Args:
            use_llm: Whether to use LLM for extraction
            llm_client: Custom LLM client
            min_salience: Minimum salience to store a fact
        """
        self.use_llm = use_llm
        self.llm_client = llm_client
        self.min_salience = min_salience

    async def extract(self, event: AuditEvent) -> list[MemoryRecord]:
        """Extract facts from event using configured method.

        Args:
            event: AuditEvent to process

        Returns:
            List of MemoryRecord objects
        """
        if self.use_llm:
            records = await aselect_salient_facts_llm(event, llm_client=self.llm_client)
        else:
            records = select_salient_facts(event)

        # Filter by minimum salience
        return [r for r in records if r.salience >= self.min_salience]

    async def extract_batch(self, events: list[AuditEvent]) -> list[MemoryRecord]:
        """Extract facts from multiple events.

        Args:
            events: List of AuditEvents to process

        Returns:
            Flattened list of MemoryRecord objects
        """
        if self.use_llm:
            # Process in parallel for LLM
            tasks = [self.extract(e) for e in events]
            results = await asyncio.gather(*tasks)
            return [r for batch in results for r in batch]
        # Sequential for heuristics (fast enough)
        all_records: list[MemoryRecord] = []
        for event in events:
            all_records.extend(await self.extract(event))
        return all_records
