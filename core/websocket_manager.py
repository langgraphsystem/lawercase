"""
WebSocket Manager for real-time workflow updates.

Provides instant notifications to connected clients about document generation progress.
Replaces polling with push-based updates for better performance and UX.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import WebSocket

logger = structlog.get_logger(__name__)

# Active WebSocket connections: thread_id -> list of WebSocket connections
active_connections: dict[str, list[WebSocket]] = {}


class ConnectionManager:
    """Manages WebSocket connections for workflow updates."""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, thread_id: str) -> None:
        """Accept and register a new WebSocket connection.

        Args:
            websocket: WebSocket connection
            thread_id: Workflow thread ID to subscribe to
        """
        await websocket.accept()

        if thread_id not in self.active_connections:
            self.active_connections[thread_id] = []

        self.active_connections[thread_id].append(websocket)

        logger.info(
            "websocket_connected",
            thread_id=thread_id,
            total_connections=len(self.active_connections[thread_id]),
        )

    def disconnect(self, websocket: WebSocket, thread_id: str) -> None:
        """Unregister a WebSocket connection.

        Args:
            websocket: WebSocket connection to remove
            thread_id: Workflow thread ID
        """
        if thread_id in self.active_connections:
            if websocket in self.active_connections[thread_id]:
                self.active_connections[thread_id].remove(websocket)

            # Cleanup empty thread entries
            if not self.active_connections[thread_id]:
                del self.active_connections[thread_id]

        logger.info(
            "websocket_disconnected",
            thread_id=thread_id,
            remaining_connections=len(self.active_connections.get(thread_id, [])),
        )

    async def send_personal_message(self, message: dict[str, Any], websocket: WebSocket) -> None:
        """Send message to a specific WebSocket connection.

        Args:
            message: Message data (will be JSON serialized)
            websocket: Target WebSocket connection
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error("websocket_send_error", error=str(e))

    async def broadcast(self, thread_id: str, message: dict[str, Any]) -> None:
        """Broadcast message to all connections subscribed to a thread.

        Args:
            thread_id: Workflow thread ID
            message: Message data (will be JSON serialized)
        """
        if thread_id not in self.active_connections:
            logger.debug("websocket_broadcast_no_connections", thread_id=thread_id)
            return

        connections = self.active_connections[thread_id].copy()
        disconnected = []

        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning("websocket_broadcast_failed", thread_id=thread_id, error=str(e))
                disconnected.append(connection)

        # Cleanup disconnected clients
        for connection in disconnected:
            self.disconnect(connection, thread_id)

        logger.debug(
            "websocket_broadcast_sent",
            thread_id=thread_id,
            recipients=len(connections) - len(disconnected),
            failed=len(disconnected),
        )

    async def broadcast_to_all(self, message: dict[str, Any]) -> None:
        """Broadcast message to all active connections.

        Args:
            message: Message data (will be JSON serialized)
        """
        total_sent = 0
        for thread_id in list(self.active_connections.keys()):
            await self.broadcast(thread_id, message)
            total_sent += len(self.active_connections.get(thread_id, []))

        logger.info("websocket_broadcast_all", total_recipients=total_sent)

    def get_connection_count(self, thread_id: str | None = None) -> int:
        """Get number of active connections.

        Args:
            thread_id: Optional thread ID to get count for specific thread

        Returns:
            Number of active connections
        """
        if thread_id:
            return len(self.active_connections.get(thread_id, []))
        return sum(len(conns) for conns in self.active_connections.values())


# Global connection manager instance
manager = ConnectionManager()


# ═══════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS FOR WORKFLOW UPDATES
# ═══════════════════════════════════════════════════════════════════════════


async def broadcast_workflow_update(thread_id: str, update: dict[str, Any]) -> None:
    """Broadcast workflow update to all connected clients.

    Args:
        thread_id: Workflow thread ID
        update: Update data (section status, progress, etc.)
    """
    message = {
        "type": "workflow_update",
        "thread_id": thread_id,
        "timestamp": update.get("timestamp") or "",
        "data": update,
    }

    await manager.broadcast(thread_id, message)


async def broadcast_section_update(
    thread_id: str, section_id: str, status: str, **kwargs: Any
) -> None:
    """Broadcast section-specific update.

    Args:
        thread_id: Workflow thread ID
        section_id: Section ID
        status: Section status (pending, in_progress, completed, error)
        **kwargs: Additional section data (tokens_used, error_message, etc.)
    """
    update = {
        "section_id": section_id,
        "status": status,
        **kwargs,
    }

    await broadcast_workflow_update(thread_id, update)


async def broadcast_log_entry(
    thread_id: str, level: str, message: str, agent: str | None = None
) -> None:
    """Broadcast new log entry to connected clients.

    Args:
        thread_id: Workflow thread ID
        level: Log level (info, success, error, warning)
        message: Log message
        agent: Agent name (optional)
    """
    from datetime import datetime

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "message": message,
        "agent": agent,
    }

    message_data = {
        "type": "log_entry",
        "thread_id": thread_id,
        "log": log_entry,
    }

    await manager.broadcast(thread_id, message_data)


async def broadcast_status_change(thread_id: str, status: str, **kwargs: Any) -> None:
    """Broadcast overall workflow status change.

    Args:
        thread_id: Workflow thread ID
        status: New status (generating, paused, completed, error)
        **kwargs: Additional status data
    """
    message = {
        "type": "status_change",
        "thread_id": thread_id,
        "status": status,
        **kwargs,
    }

    await manager.broadcast(thread_id, message)


async def broadcast_progress_update(
    thread_id: str, completed: int, total: int, percentage: float
) -> None:
    """Broadcast progress update.

    Args:
        thread_id: Workflow thread ID
        completed: Number of completed sections
        total: Total number of sections
        percentage: Progress percentage (0-100)
    """
    message = {
        "type": "progress_update",
        "thread_id": thread_id,
        "completed": completed,
        "total": total,
        "percentage": percentage,
    }

    await manager.broadcast(thread_id, message)


async def broadcast_error(thread_id: str, error_message: str, **kwargs: Any) -> None:
    """Broadcast error to connected clients.

    Args:
        thread_id: Workflow thread ID
        error_message: Error message
        **kwargs: Additional error context
    """
    message = {
        "type": "error",
        "thread_id": thread_id,
        "error_message": error_message,
        **kwargs,
    }

    await manager.broadcast(thread_id, message)


# ═══════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════

__all__ = [
    "ConnectionManager",
    "broadcast_error",
    "broadcast_log_entry",
    "broadcast_progress_update",
    "broadcast_section_update",
    "broadcast_status_change",
    "broadcast_workflow_update",
    "manager",
]
