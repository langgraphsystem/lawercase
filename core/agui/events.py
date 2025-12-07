"""
AG-UI Event Types - Standard events for agent-user interaction.

Based on AG-UI Protocol specification:
https://docs.ag-ui.com/
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class EventType(str, Enum):
    """AG-UI standard event types."""

    # Lifecycle events
    RUN_STARTED = "RUN_STARTED"
    RUN_FINISHED = "RUN_FINISHED"
    RUN_ERROR = "RUN_ERROR"

    # Text message events (streaming)
    TEXT_MESSAGE_START = "TEXT_MESSAGE_START"
    TEXT_MESSAGE_CONTENT = "TEXT_MESSAGE_CONTENT"
    TEXT_MESSAGE_END = "TEXT_MESSAGE_END"

    # Tool call events
    TOOL_CALL_START = "TOOL_CALL_START"
    TOOL_CALL_ARGS = "TOOL_CALL_ARGS"
    TOOL_CALL_END = "TOOL_CALL_END"

    # State synchronization
    STATE_SNAPSHOT = "STATE_SNAPSHOT"
    STATE_DELTA = "STATE_DELTA"

    # Human-in-the-loop
    STEP_STARTED = "STEP_STARTED"
    STEP_FINISHED = "STEP_FINISHED"

    # Custom events for EB-1A workflow
    AGENT_HANDOFF = "AGENT_HANDOFF"
    VALIDATION_REQUIRED = "VALIDATION_REQUIRED"
    VALIDATION_RESULT = "VALIDATION_RESULT"
    DOCUMENT_GENERATED = "DOCUMENT_GENERATED"
    INTAKE_QUESTION = "INTAKE_QUESTION"
    INTAKE_ANSWER = "INTAKE_ANSWER"


class AGUIEvent(BaseModel):
    """Single AG-UI event for streaming to frontend."""

    model_config = ConfigDict(use_enum_values=True)

    type: EventType = Field(..., description="Event type")
    timestamp: float = Field(default_factory=time.time, description="Unix timestamp")
    event_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique event ID")

    # Content fields (used based on event type)
    message_id: str | None = Field(default=None, description="Message ID for text events")
    content: str | None = Field(default=None, description="Text content")
    delta: str | None = Field(default=None, description="Incremental text delta")
    role: str = Field(default="assistant", description="Message role")

    # Tool call fields
    tool_call_id: str | None = Field(default=None, description="Tool call ID")
    tool_name: str | None = Field(default=None, description="Tool name")
    tool_args: dict[str, Any] | None = Field(default=None, description="Tool arguments")
    tool_result: Any | None = Field(default=None, description="Tool result")

    # State fields
    state: dict[str, Any] | None = Field(default=None, description="Full state snapshot")
    state_delta: dict[str, Any] | None = Field(default=None, description="State delta/patch")

    # Agent coordination
    agent_name: str | None = Field(default=None, description="Current agent name")
    next_agent: str | None = Field(default=None, description="Next agent in handoff")

    # Workflow specific
    step_name: str | None = Field(default=None, description="Current workflow step")
    case_id: str | None = Field(default=None, description="Case ID")

    # Error handling
    error: str | None = Field(default=None, description="Error message")
    error_code: str | None = Field(default=None, description="Error code")

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def to_sse(self) -> str:
        """Convert to Server-Sent Events format."""
        import json

        # Manually build dict to avoid Pydantic serialization issues
        data: dict[str, Any] = {
            "type": str(self.type),
            "timestamp": self.timestamp,
            "event_id": self.event_id,
        }

        # Add optional fields only if they have values
        optional_fields = [
            "message_id",
            "content",
            "delta",
            "role",
            "tool_call_id",
            "tool_name",
            "tool_args",
            "tool_result",
            "state",
            "state_delta",
            "agent_name",
            "next_agent",
            "step_name",
            "case_id",
            "error",
            "error_code",
        ]
        for field in optional_fields:
            val = getattr(self, field, None)
            if val is not None:
                # Ensure value is JSON-serializable
                if callable(val):
                    data[field] = str(val)
                else:
                    data[field] = val

        # Handle metadata separately
        if self.metadata:
            data["metadata"] = {k: str(v) if callable(v) else v for k, v in self.metadata.items()}

        json_str = json.dumps(data, default=str)
        return f"event: {self.type}\ndata: {json_str}\n\n"

    def to_json(self) -> str:
        """Convert to JSON string."""
        import json

        # Use the same safe serialization as to_sse
        data = {"type": str(self.type), "timestamp": self.timestamp, "event_id": self.event_id}
        for field in self.model_fields:
            if field not in data:
                val = getattr(self, field, None)
                if val is not None:
                    data[field] = str(val) if callable(val) else val
        return json.dumps(data, default=str)

    # Factory methods for common events
    @classmethod
    def run_started(cls, case_id: str | None = None, **kwargs) -> AGUIEvent:
        return cls(type=EventType.RUN_STARTED, case_id=case_id, **kwargs)

    @classmethod
    def run_finished(cls, case_id: str | None = None, **kwargs) -> AGUIEvent:
        return cls(type=EventType.RUN_FINISHED, case_id=case_id, **kwargs)

    @classmethod
    def run_error(cls, error: str, error_code: str | None = None, **kwargs) -> AGUIEvent:
        return cls(type=EventType.RUN_ERROR, error=error, error_code=error_code, **kwargs)

    @classmethod
    def text_message_start(cls, message_id: str | None = None, **kwargs) -> AGUIEvent:
        msg_id = message_id or str(uuid4())
        return cls(type=EventType.TEXT_MESSAGE_START, message_id=msg_id, **kwargs)

    @classmethod
    def text_message_content(cls, content: str, message_id: str, **kwargs) -> AGUIEvent:
        return cls(
            type=EventType.TEXT_MESSAGE_CONTENT,
            message_id=message_id,
            delta=content,
            **kwargs,
        )

    @classmethod
    def text_message_end(cls, message_id: str, **kwargs) -> AGUIEvent:
        return cls(type=EventType.TEXT_MESSAGE_END, message_id=message_id, **kwargs)

    @classmethod
    def tool_call_start(
        cls, tool_name: str, tool_call_id: str | None = None, **kwargs
    ) -> AGUIEvent:
        return cls(
            type=EventType.TOOL_CALL_START,
            tool_name=tool_name,
            tool_call_id=tool_call_id or str(uuid4()),
            **kwargs,
        )

    @classmethod
    def tool_call_end(cls, tool_call_id: str, result: Any = None, **kwargs) -> AGUIEvent:
        return cls(
            type=EventType.TOOL_CALL_END,
            tool_call_id=tool_call_id,
            tool_result=result,
            **kwargs,
        )

    @classmethod
    def state_snapshot(cls, state: dict[str, Any], **kwargs) -> AGUIEvent:
        return cls(type=EventType.STATE_SNAPSHOT, state=state, **kwargs)

    @classmethod
    def state_delta(cls, delta: dict[str, Any], **kwargs) -> AGUIEvent:
        return cls(type=EventType.STATE_DELTA, state_delta=delta, **kwargs)

    @classmethod
    def agent_handoff(cls, from_agent: str, to_agent: str, **kwargs) -> AGUIEvent:
        return cls(
            type=EventType.AGENT_HANDOFF,
            agent_name=from_agent,
            next_agent=to_agent,
            **kwargs,
        )

    @classmethod
    def step_started(cls, step_name: str, agent_name: str | None = None, **kwargs) -> AGUIEvent:
        return cls(
            type=EventType.STEP_STARTED,
            step_name=step_name,
            agent_name=agent_name,
            **kwargs,
        )

    @classmethod
    def step_finished(cls, step_name: str, **kwargs) -> AGUIEvent:
        return cls(type=EventType.STEP_FINISHED, step_name=step_name, **kwargs)

    # EB-1A specific events
    @classmethod
    def validation_required(
        cls, case_id: str, validation_type: str, data: dict[str, Any], **kwargs
    ) -> AGUIEvent:
        return cls(
            type=EventType.VALIDATION_REQUIRED,
            case_id=case_id,
            metadata={"validation_type": validation_type, "data": data},
            **kwargs,
        )

    @classmethod
    def validation_result(
        cls, case_id: str, approved: bool, feedback: str | None = None, **kwargs
    ) -> AGUIEvent:
        return cls(
            type=EventType.VALIDATION_RESULT,
            case_id=case_id,
            metadata={"approved": approved, "feedback": feedback},
            **kwargs,
        )

    @classmethod
    def document_generated(
        cls, case_id: str, document_type: str, document_id: str, **kwargs
    ) -> AGUIEvent:
        return cls(
            type=EventType.DOCUMENT_GENERATED,
            case_id=case_id,
            metadata={"document_type": document_type, "document_id": document_id},
            **kwargs,
        )

    @classmethod
    def intake_question(
        cls, case_id: str, block_id: str, question_id: str, question_text: str, **kwargs
    ) -> AGUIEvent:
        return cls(
            type=EventType.INTAKE_QUESTION,
            case_id=case_id,
            content=question_text,
            metadata={"block_id": block_id, "question_id": question_id},
            **kwargs,
        )

    @classmethod
    def intake_answer(cls, case_id: str, question_id: str, answer: str, **kwargs) -> AGUIEvent:
        return cls(
            type=EventType.INTAKE_ANSWER,
            case_id=case_id,
            content=answer,
            metadata={"question_id": question_id},
            **kwargs,
        )
