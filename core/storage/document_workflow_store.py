"""
Storage layer for document generation workflow states.

Provides persistence for document monitor workflow states using in-memory
storage (development) with option to use Redis (production).
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import json
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class DocumentWorkflowStore:
    """
    Storage for document generation workflow states.

    In development: Uses in-memory dict
    In production: Can use Redis for persistence
    """

    def __init__(self, use_redis: bool = False, redis_client: Any | None = None):
        """
        Initialize workflow store.

        Args:
            use_redis: Whether to use Redis for persistence
            redis_client: Redis client instance (if use_redis=True)
        """
        self.use_redis = use_redis
        self.redis = redis_client
        self._memory_store: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def save_state(self, thread_id: str, state: dict[str, Any]) -> None:
        """
        Save workflow state.

        Args:
            thread_id: Workflow thread ID
            state: Complete workflow state dictionary
        """
        async with self._lock:
            try:
                # Add updated timestamp
                state["_updated_at"] = datetime.now().isoformat()

                if self.use_redis and self.redis:
                    # Save to Redis with 24-hour TTL
                    key = f"document_workflow:{thread_id}"
                    await self.redis.setex(
                        key,
                        86400,  # 24 hours
                        json.dumps(state),
                    )
                    logger.info("document_workflow_saved_redis", thread_id=thread_id)
                else:
                    # Save to memory
                    self._memory_store[thread_id] = state
                    logger.debug("document_workflow_saved_memory", thread_id=thread_id)

            except Exception as e:
                logger.error("document_workflow_save_error", thread_id=thread_id, error=str(e))
                raise

    async def load_state(self, thread_id: str) -> dict[str, Any] | None:
        """
        Load workflow state.

        Args:
            thread_id: Workflow thread ID

        Returns:
            Workflow state dict or None if not found
        """
        async with self._lock:
            try:
                if self.use_redis and self.redis:
                    key = f"document_workflow:{thread_id}"
                    data = await self.redis.get(key)
                    if data:
                        state = json.loads(data)
                        logger.debug("document_workflow_loaded_redis", thread_id=thread_id)
                        return state
                    logger.debug("document_workflow_not_found_redis", thread_id=thread_id)
                    return None
                state = self._memory_store.get(thread_id)
                if state:
                    logger.debug("document_workflow_loaded_memory", thread_id=thread_id)
                else:
                    logger.debug("document_workflow_not_found_memory", thread_id=thread_id)
                return state

            except Exception as e:
                logger.error("document_workflow_load_error", thread_id=thread_id, error=str(e))
                return None

    async def update_section(
        self, thread_id: str, section_id: str, updates: dict[str, Any]
    ) -> bool:
        """
        Update a specific section in workflow state.

        Args:
            thread_id: Workflow thread ID
            section_id: Section identifier
            updates: Fields to update in section

        Returns:
            True if successful, False otherwise
        """
        state = await self.load_state(thread_id)
        if not state:
            logger.warning("section_update_no_state", thread_id=thread_id, section_id=section_id)
            return False

        sections = state.get("sections", [])
        for section in sections:
            if section.get("id") == section_id or section.get("section_id") == section_id:
                section.update(updates)
                section["updated_at"] = datetime.now().isoformat()
                await self.save_state(thread_id, state)
                logger.info(
                    "section_updated",
                    thread_id=thread_id,
                    section_id=section_id,
                    updates=list(updates.keys()),
                )
                return True

        logger.warning("section_not_found", thread_id=thread_id, section_id=section_id)
        return False

    async def add_log(self, thread_id: str, log_entry: dict[str, Any]) -> bool:
        """
        Add log entry to workflow state.

        Args:
            thread_id: Workflow thread ID
            log_entry: Log entry dictionary

        Returns:
            True if successful, False otherwise
        """
        state = await self.load_state(thread_id)
        if not state:
            logger.warning("add_log_no_state", thread_id=thread_id)
            return False

        if "logs" not in state:
            state["logs"] = []

        # Add timestamp if not present
        if "timestamp" not in log_entry:
            log_entry["timestamp"] = datetime.now().isoformat()

        state["logs"].append(log_entry)

        # Keep only last 100 logs
        if len(state["logs"]) > 100:
            state["logs"] = state["logs"][-100:]

        await self.save_state(thread_id, state)
        logger.debug("log_added", thread_id=thread_id, level=log_entry.get("level"))
        return True

    async def add_exhibit(self, thread_id: str, exhibit_data: dict[str, Any]) -> bool:
        """
        Add exhibit to workflow state.

        Args:
            thread_id: Workflow thread ID
            exhibit_data: Exhibit metadata dictionary

        Returns:
            True if successful, False otherwise
        """
        state = await self.load_state(thread_id)
        if not state:
            logger.warning("add_exhibit_no_state", thread_id=thread_id)
            return False

        if "exhibits" not in state:
            state["exhibits"] = []

        # Add timestamp if not present
        if "uploaded_at" not in exhibit_data:
            exhibit_data["uploaded_at"] = datetime.now().isoformat()

        state["exhibits"].append(exhibit_data)
        await self.save_state(thread_id, state)

        logger.info(
            "exhibit_added",
            thread_id=thread_id,
            exhibit_id=exhibit_data.get("exhibit_id"),
            filename=exhibit_data.get("filename"),
        )
        return True

    async def update_workflow_status(
        self, thread_id: str, status: str, error_message: str | None = None
    ) -> bool:
        """
        Update overall workflow status.

        Args:
            thread_id: Workflow thread ID
            status: New status ("idle", "generating", "paused", "completed", "error")
            error_message: Error message if status is "error"

        Returns:
            True if successful, False otherwise
        """
        state = await self.load_state(thread_id)
        if not state:
            logger.warning("update_status_no_state", thread_id=thread_id)
            return False

        old_status = state.get("status")
        state["status"] = status

        if error_message:
            state["error_message"] = error_message

        await self.save_state(thread_id, state)

        logger.info(
            "workflow_status_updated", thread_id=thread_id, old_status=old_status, new_status=status
        )
        return True

    async def delete_state(self, thread_id: str) -> bool:
        """
        Delete workflow state.

        Args:
            thread_id: Workflow thread ID

        Returns:
            True if successful, False otherwise
        """
        async with self._lock:
            try:
                if self.use_redis and self.redis:
                    key = f"document_workflow:{thread_id}"
                    await self.redis.delete(key)
                elif thread_id in self._memory_store:
                    del self._memory_store[thread_id]

                logger.info("document_workflow_deleted", thread_id=thread_id)
                return True

            except Exception as e:
                logger.error("document_workflow_delete_error", thread_id=thread_id, error=str(e))
                return False

    async def list_active_workflows(self) -> list[str]:
        """
        List all active workflow thread IDs.

        Returns:
            List of thread IDs
        """
        if self.use_redis and self.redis:
            keys = await self.redis.keys("document_workflow:*")
            return [key.decode().split(":", 1)[1] for key in keys]
        return list(self._memory_store.keys())


# Singleton instance
_store: DocumentWorkflowStore | None = None


def get_document_workflow_store(
    use_redis: bool = False, redis_client: Any | None = None
) -> DocumentWorkflowStore:
    """
    Get singleton document workflow store instance.

    Args:
        use_redis: Whether to use Redis
        redis_client: Redis client instance

    Returns:
        DocumentWorkflowStore instance
    """
    global _store
    if _store is None:
        _store = DocumentWorkflowStore(use_redis=use_redis, redis_client=redis_client)
    return _store
