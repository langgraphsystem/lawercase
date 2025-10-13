"""Immutable audit trail system."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Types of audit events."""

    # Authentication events
    LOGIN = "auth.login"
    LOGOUT = "auth.logout"
    LOGIN_FAILED = "auth.login_failed"

    # Authorization events
    ACCESS_GRANTED = "authz.access_granted"
    ACCESS_DENIED = "authz.access_denied"

    # Data operations
    DATA_CREATE = "data.create"
    DATA_READ = "data.read"
    DATA_UPDATE = "data.update"
    DATA_DELETE = "data.delete"
    DATA_EXPORT = "data.export"

    # Agent operations
    AGENT_EXECUTE = "agent.execute"
    AGENT_ERROR = "agent.error"

    # System events
    SYSTEM_START = "system.start"
    SYSTEM_STOP = "system.stop"
    CONFIG_CHANGE = "system.config_change"

    # Security events
    SECURITY_ALERT = "security.alert"
    INJECTION_DETECTED = "security.injection_detected"
    ANOMALY_DETECTED = "security.anomaly"


@dataclass
class AuditEvent:
    """Immutable audit event."""

    event_id: str
    event_type: AuditEventType
    timestamp: datetime
    user_id: str | None
    resource_type: str
    resource_id: str | None
    action: str
    result: str  # success, failure, error
    details: dict[str, Any] = field(default_factory=dict)
    ip_address: str | None = None
    user_agent: str | None = None
    previous_hash: str = ""  # Hash of previous event for chain integrity
    current_hash: str = ""  # Hash of this event

    def calculate_hash(self) -> str:
        """Calculate hash for this event.

        Returns:
            SHA256 hash of event data
        """
        # Create deterministic string representation
        data = {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "action": self.action,
            "result": self.result,
            "details": self.details,
            "previous_hash": self.previous_hash,
        }

        # Sort keys for consistency
        data_str = json.dumps(data, sort_keys=True)

        # Calculate SHA256
        return hashlib.sha256(data_str.encode()).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "action": self.action,
            "result": self.result,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "previous_hash": self.previous_hash,
            "current_hash": self.current_hash,
        }


class AuditTrail:
    """Manages immutable audit trail with blockchain-like integrity."""

    def __init__(self, storage_path: Path | None = None) -> None:
        """Initialize audit trail.

        Args:
            storage_path: Path to store audit logs (None for in-memory only)
        """
        self.storage_path = storage_path
        self.events: list[AuditEvent] = []
        self.last_hash = ""

        if storage_path:
            storage_path.parent.mkdir(parents=True, exist_ok=True)
            self._load_existing_events()

        logger.info(f"AuditTrail initialized (storage: {'file' if storage_path else 'memory'})")

    def _load_existing_events(self) -> None:
        """Load existing audit events from storage."""
        if not self.storage_path or not self.storage_path.exists():
            return

        try:
            with self.storage_path.open("r", encoding="utf-8") as f:
                for line in f:
                    event_data = json.loads(line.strip())
                    event = self._dict_to_event(event_data)
                    self.events.append(event)
                    self.last_hash = event.current_hash

            logger.info(f"Loaded {len(self.events)} audit events from storage")

            # Verify chain integrity
            if not self.verify_chain():
                logger.error("Audit trail integrity verification failed!")

        except Exception as e:
            logger.error(f"Failed to load audit events: {e}")

    def _dict_to_event(self, data: dict[str, Any]) -> AuditEvent:
        """Convert dictionary to AuditEvent.

        Args:
            data: Event data dictionary

        Returns:
            AuditEvent instance
        """
        return AuditEvent(
            event_id=data["event_id"],
            event_type=AuditEventType(data["event_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            user_id=data.get("user_id"),
            resource_type=data["resource_type"],
            resource_id=data.get("resource_id"),
            action=data["action"],
            result=data["result"],
            details=data.get("details", {}),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            previous_hash=data.get("previous_hash", ""),
            current_hash=data.get("current_hash", ""),
        )

    def log_event(
        self,
        event_type: AuditEventType,
        user_id: str | None,
        resource_type: str,
        resource_id: str | None,
        action: str,
        result: str,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditEvent:
        """Log an audit event.

        Args:
            event_type: Type of event
            user_id: User ID (if applicable)
            resource_type: Type of resource affected
            resource_id: ID of resource (if applicable)
            action: Action performed
            result: Result of action
            details: Additional details
            ip_address: IP address of request
            user_agent: User agent string

        Returns:
            Created audit event
        """
        # Generate event ID
        event_id = hashlib.sha256(
            f"{datetime.utcnow().isoformat()}{user_id}{action}".encode()
        ).hexdigest()[:16]

        # Create event
        event = AuditEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            result=result,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            previous_hash=self.last_hash,
        )

        # Calculate hash for integrity
        event.current_hash = event.calculate_hash()

        # Add to chain
        self.events.append(event)
        self.last_hash = event.current_hash

        # Persist to storage
        if self.storage_path:
            self._append_to_storage(event)

        logger.debug(
            f"Audit event logged: {event_type} by {user_id} on {resource_type}/{resource_id}"
        )

        return event

    def _append_to_storage(self, event: AuditEvent) -> None:
        """Append event to persistent storage.

        Args:
            event: Event to append
        """
        try:
            with self.storage_path.open("a", encoding="utf-8") as f:  # type: ignore[union-attr]
                f.write(json.dumps(event.to_dict()) + "\n")
        except Exception as e:
            logger.error(f"Failed to persist audit event: {e}")

    def verify_chain(self) -> bool:
        """Verify integrity of entire audit chain.

        Returns:
            True if chain is valid
        """
        if not self.events:
            return True

        for i, event in enumerate(self.events):
            # Verify hash
            expected_hash = event.calculate_hash()
            if event.current_hash != expected_hash:
                logger.error(
                    f"Hash mismatch at event {i} ({event.event_id}): "
                    f"expected {expected_hash}, got {event.current_hash}"
                )
                return False

            # Verify chain link
            if i > 0:
                previous_event = self.events[i - 1]
                if event.previous_hash != previous_event.current_hash:
                    logger.error(
                        f"Chain break at event {i} ({event.event_id}): previous_hash doesn't match"
                    )
                    return False

        logger.info(f"Audit chain verified: {len(self.events)} events")
        return True

    def query_events(
        self,
        event_type: AuditEventType | None = None,
        user_id: str | None = None,
        resource_type: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """Query audit events.

        Args:
            event_type: Filter by event type
            user_id: Filter by user ID
            resource_type: Filter by resource type
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum number of events to return

        Returns:
            List of matching events
        """
        results = []

        for event in reversed(self.events):  # Most recent first
            # Apply filters
            if event_type and event.event_type != event_type:
                continue
            if user_id and event.user_id != user_id:
                continue
            if resource_type and event.resource_type != resource_type:
                continue
            if start_time and event.timestamp < start_time:
                continue
            if end_time and event.timestamp > end_time:
                continue

            results.append(event)

            if len(results) >= limit:
                break

        logger.debug(f"Query returned {len(results)} events")
        return results

    def get_user_activity(self, user_id: str, limit: int = 50) -> list[AuditEvent]:
        """Get recent activity for user.

        Args:
            user_id: User ID
            limit: Maximum events to return

        Returns:
            List of user's audit events
        """
        return self.query_events(user_id=user_id, limit=limit)

    def get_security_events(self, hours: int = 24) -> list[AuditEvent]:
        """Get recent security-related events.

        Args:
            hours: Number of hours to look back

        Returns:
            List of security events
        """
        from datetime import timedelta

        start_time = datetime.utcnow() - timedelta(hours=hours)

        security_types = [
            AuditEventType.ACCESS_DENIED,
            AuditEventType.LOGIN_FAILED,
            AuditEventType.SECURITY_ALERT,
            AuditEventType.INJECTION_DETECTED,
            AuditEventType.ANOMALY_DETECTED,
        ]

        results = []
        for event_type in security_types:
            results.extend(
                self.query_events(event_type=event_type, start_time=start_time, limit=100)
            )

        # Sort by timestamp (most recent first)
        results.sort(key=lambda e: e.timestamp, reverse=True)

        return results


# Global instance
_audit_trail: AuditTrail | None = None


def get_audit_trail(storage_path: Path | None = None) -> AuditTrail:
    """Get or create global audit trail.

    Args:
        storage_path: Storage path (only used for new instance)

    Returns:
        Global AuditTrail instance
    """
    global _audit_trail
    if _audit_trail is None:
        _audit_trail = AuditTrail(storage_path=storage_path)
    return _audit_trail
