"""Agent Filesystem - Virtual filesystem for agent context management.

Provides:
- Virtual file system for agent scratchpads
- Context isolation between subagents
- Persistent and ephemeral storage
- File-based context sharing
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
import json
from pathlib import Path
import tempfile
from typing import Any
from uuid import uuid4

import structlog

logger = structlog.get_logger(__name__)


class FileType(str, Enum):
    """Types of files in agent filesystem."""

    CONTEXT = "context"
    FINDING = "finding"
    REPORT = "report"
    PLAN = "plan"
    SCRATCHPAD = "scratchpad"
    CACHE = "cache"
    CHECKPOINT = "checkpoint"


class StorageType(str, Enum):
    """Storage persistence types."""

    MEMORY = "memory"  # In-memory only
    TEMPORARY = "temporary"  # Temp files, cleaned on exit
    PERSISTENT = "persistent"  # Persisted to disk


@dataclass
class AgentFile:
    """A file in the agent filesystem."""

    file_id: str
    name: str
    path: str
    file_type: FileType
    content: str | bytes | dict[str, Any]
    storage_type: StorageType = StorageType.MEMORY
    owner_id: str | None = None
    size_bytes: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.content, str):
            self.size_bytes = len(self.content.encode("utf-8"))
        elif isinstance(self.content, bytes):
            self.size_bytes = len(self.content)
        elif isinstance(self.content, dict):
            self.size_bytes = len(json.dumps(self.content).encode("utf-8"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_id": self.file_id,
            "name": self.name,
            "path": self.path,
            "file_type": self.file_type.value,
            "storage_type": self.storage_type.value,
            "owner_id": self.owner_id,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
        }


@dataclass
class AgentDirectory:
    """A directory in the agent filesystem."""

    dir_id: str
    name: str
    path: str
    owner_id: str | None = None
    files: dict[str, AgentFile] = field(default_factory=dict)
    subdirs: dict[str, AgentDirectory] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dir_id": self.dir_id,
            "name": self.name,
            "path": self.path,
            "owner_id": self.owner_id,
            "file_count": len(self.files),
            "subdir_count": len(self.subdirs),
            "created_at": self.created_at.isoformat(),
        }


class AgentFilesystem:
    """Virtual filesystem for agent context management.

    Features:
    - Isolated agent workspaces
    - Virtual file operations
    - Context sharing between agents
    - Checkpointing and recovery

    Usage:
        >>> fs = AgentFilesystem()
        >>> workspace = await fs.create_workspace("agent_001")
        >>> await fs.write_file(
        ...     workspace,
        ...     "findings.json",
        ...     {"key": "value"},
        ...     FileType.FINDING
        ... )
        >>> content = await fs.read_file(workspace, "findings.json")
    """

    def __init__(
        self,
        base_path: str | Path | None = None,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        max_workspace_size: int = 100 * 1024 * 1024,  # 100MB
    ):
        """Initialize agent filesystem.

        Args:
            base_path: Base path for persistent storage
            max_file_size: Maximum file size in bytes
            max_workspace_size: Maximum workspace size in bytes
        """
        self.base_path = Path(base_path) if base_path else Path(tempfile.gettempdir()) / "agent_fs"
        self.max_file_size = max_file_size
        self.max_workspace_size = max_workspace_size

        # In-memory filesystem root
        self._root = AgentDirectory(
            dir_id="root",
            name="/",
            path="/",
        )

        # Workspace registry
        self._workspaces: dict[str, AgentDirectory] = {}

        # File locks for concurrent access
        self._locks: dict[str, asyncio.Lock] = {}

        # Stats
        self._stats = {
            "total_files": 0,
            "total_size": 0,
            "operations": 0,
        }

        self.logger = logger.bind(component="AgentFilesystem")

    async def create_workspace(
        self,
        agent_id: str,
        storage_type: StorageType = StorageType.MEMORY,
    ) -> str:
        """Create a workspace for an agent.

        Args:
            agent_id: ID of the agent
            storage_type: Storage persistence type

        Returns:
            Workspace path
        """
        workspace_path = f"/workspaces/{agent_id}"

        if workspace_path in self._workspaces:
            return workspace_path

        workspace = AgentDirectory(
            dir_id=f"ws_{agent_id}",
            name=agent_id,
            path=workspace_path,
            owner_id=agent_id,
        )

        self._workspaces[workspace_path] = workspace

        # Create physical directory for persistent storage
        if storage_type == StorageType.PERSISTENT:
            physical_path = self.base_path / "workspaces" / agent_id
            physical_path.mkdir(parents=True, exist_ok=True)

        self.logger.info(
            "filesystem.workspace_created",
            agent_id=agent_id,
            path=workspace_path,
            storage_type=storage_type.value,
        )

        return workspace_path

    async def write_file(
        self,
        workspace: str,
        filename: str,
        content: str | bytes | dict[str, Any],
        file_type: FileType = FileType.SCRATCHPAD,
        storage_type: StorageType = StorageType.MEMORY,
        metadata: dict[str, Any] | None = None,
    ) -> AgentFile:
        """Write a file to the agent filesystem.

        Args:
            workspace: Workspace path
            filename: Name of file
            content: File content
            file_type: Type of file
            storage_type: Storage persistence
            metadata: Additional metadata

        Returns:
            Created AgentFile
        """
        ws = self._workspaces.get(workspace)
        if not ws:
            raise FileNotFoundError(f"Workspace not found: {workspace}")

        file_path = f"{workspace}/{filename}"

        # Check size limits
        if isinstance(content, str):
            size = len(content.encode("utf-8"))
        elif isinstance(content, bytes):
            size = len(content)
        else:
            size = len(json.dumps(content).encode("utf-8"))

        if size > self.max_file_size:
            raise ValueError(f"File size {size} exceeds limit {self.max_file_size}")

        # Get or create lock
        if file_path not in self._locks:
            self._locks[file_path] = asyncio.Lock()

        async with self._locks[file_path]:
            # Create file
            agent_file = AgentFile(
                file_id=f"file_{uuid4().hex[:8]}",
                name=filename,
                path=file_path,
                file_type=file_type,
                content=content,
                storage_type=storage_type,
                owner_id=ws.owner_id,
                metadata=metadata or {},
            )

            # Add to workspace
            ws.files[filename] = agent_file

            # Persist if needed
            if storage_type == StorageType.PERSISTENT:
                await self._persist_file(agent_file)

            self._stats["total_files"] += 1
            self._stats["total_size"] += agent_file.size_bytes
            self._stats["operations"] += 1

        self.logger.debug(
            "filesystem.file_written",
            path=file_path,
            size=agent_file.size_bytes,
            type=file_type.value,
        )

        return agent_file

    async def read_file(
        self,
        workspace: str,
        filename: str,
    ) -> str | bytes | dict[str, Any]:
        """Read a file from the agent filesystem.

        Args:
            workspace: Workspace path
            filename: Name of file

        Returns:
            File content
        """
        ws = self._workspaces.get(workspace)
        if not ws:
            raise FileNotFoundError(f"Workspace not found: {workspace}")

        agent_file = ws.files.get(filename)
        if not agent_file:
            # Try to load from persistent storage
            agent_file = await self._load_file(workspace, filename)
            if not agent_file:
                raise FileNotFoundError(f"File not found: {filename}")

        self._stats["operations"] += 1
        return agent_file.content

    async def delete_file(
        self,
        workspace: str,
        filename: str,
    ) -> bool:
        """Delete a file from the agent filesystem.

        Args:
            workspace: Workspace path
            filename: Name of file

        Returns:
            True if deleted, False if not found
        """
        ws = self._workspaces.get(workspace)
        if not ws:
            return False

        file_path = f"{workspace}/{filename}"

        if file_path in self._locks:
            async with self._locks[file_path]:
                if filename in ws.files:
                    agent_file = ws.files.pop(filename)
                    self._stats["total_files"] -= 1
                    self._stats["total_size"] -= agent_file.size_bytes

                    # Delete from persistent storage
                    if agent_file.storage_type == StorageType.PERSISTENT:
                        await self._delete_persistent_file(agent_file)

                    self.logger.debug("filesystem.file_deleted", path=file_path)
                    return True

        return False

    async def list_files(
        self,
        workspace: str,
        file_type: FileType | None = None,
    ) -> list[AgentFile]:
        """List files in a workspace.

        Args:
            workspace: Workspace path
            file_type: Optional filter by file type

        Returns:
            List of AgentFile objects
        """
        ws = self._workspaces.get(workspace)
        if not ws:
            return []

        files = list(ws.files.values())

        if file_type:
            files = [f for f in files if f.file_type == file_type]

        return files

    async def copy_file(
        self,
        source_workspace: str,
        source_filename: str,
        dest_workspace: str,
        dest_filename: str | None = None,
    ) -> AgentFile:
        """Copy a file between workspaces.

        Args:
            source_workspace: Source workspace path
            source_filename: Source filename
            dest_workspace: Destination workspace path
            dest_filename: Destination filename (defaults to source)

        Returns:
            Copied AgentFile
        """
        content = await self.read_file(source_workspace, source_filename)

        source_ws = self._workspaces.get(source_workspace)
        source_file = source_ws.files.get(source_filename) if source_ws else None

        return await self.write_file(
            workspace=dest_workspace,
            filename=dest_filename or source_filename,
            content=content,
            file_type=source_file.file_type if source_file else FileType.SCRATCHPAD,
            storage_type=source_file.storage_type if source_file else StorageType.MEMORY,
        )

    async def create_checkpoint(
        self,
        workspace: str,
        checkpoint_name: str,
    ) -> AgentFile:
        """Create a checkpoint of workspace state.

        Args:
            workspace: Workspace path
            checkpoint_name: Name for checkpoint

        Returns:
            Checkpoint file
        """
        ws = self._workspaces.get(workspace)
        if not ws:
            raise FileNotFoundError(f"Workspace not found: {workspace}")

        # Serialize workspace state
        checkpoint_data = {
            "checkpoint_name": checkpoint_name,
            "workspace": workspace,
            "created_at": datetime.now(UTC).isoformat(),
            "files": {
                name: {
                    "file_id": f.file_id,
                    "name": f.name,
                    "file_type": f.file_type.value,
                    "content": (
                        f.content
                        if isinstance(f.content, str | dict)
                        else f.content.decode("utf-8")
                    ),
                    "metadata": f.metadata,
                }
                for name, f in ws.files.items()
            },
        }

        return await self.write_file(
            workspace=workspace,
            filename=f"checkpoint_{checkpoint_name}.json",
            content=checkpoint_data,
            file_type=FileType.CHECKPOINT,
            storage_type=StorageType.PERSISTENT,
        )

    async def restore_checkpoint(
        self,
        workspace: str,
        checkpoint_name: str,
    ) -> bool:
        """Restore workspace from checkpoint.

        Args:
            workspace: Workspace path
            checkpoint_name: Name of checkpoint

        Returns:
            True if restored successfully
        """
        try:
            checkpoint = await self.read_file(
                workspace,
                f"checkpoint_{checkpoint_name}.json",
            )

            if not isinstance(checkpoint, dict):
                return False

            ws = self._workspaces.get(workspace)
            if not ws:
                return False

            # Restore files
            for name, file_data in checkpoint.get("files", {}).items():
                if name.startswith("checkpoint_"):
                    continue  # Skip checkpoint files

                await self.write_file(
                    workspace=workspace,
                    filename=name,
                    content=file_data["content"],
                    file_type=FileType(file_data["file_type"]),
                    metadata=file_data.get("metadata", {}),
                )

            self.logger.info(
                "filesystem.checkpoint_restored",
                workspace=workspace,
                checkpoint=checkpoint_name,
            )

            return True

        except FileNotFoundError:
            return False

    async def delete_workspace(self, workspace: str) -> bool:
        """Delete a workspace and all its files.

        Args:
            workspace: Workspace path

        Returns:
            True if deleted
        """
        ws = self._workspaces.get(workspace)
        if not ws:
            return False

        # Delete all files
        for filename in list(ws.files.keys()):
            await self.delete_file(workspace, filename)

        # Remove workspace
        del self._workspaces[workspace]

        self.logger.info("filesystem.workspace_deleted", workspace=workspace)
        return True

    async def _persist_file(self, agent_file: AgentFile) -> None:
        """Persist file to disk."""
        # Extract workspace from path
        parts = agent_file.path.split("/")
        if len(parts) >= 3:
            workspace_name = parts[2]
            physical_path = self.base_path / "workspaces" / workspace_name / agent_file.name

            physical_path.parent.mkdir(parents=True, exist_ok=True)

            if isinstance(agent_file.content, dict):
                content = json.dumps(agent_file.content, indent=2)
                physical_path.write_text(content, encoding="utf-8")
            elif isinstance(agent_file.content, bytes):
                physical_path.write_bytes(agent_file.content)
            else:
                physical_path.write_text(agent_file.content, encoding="utf-8")

    async def _load_file(
        self,
        workspace: str,
        filename: str,
    ) -> AgentFile | None:
        """Load file from persistent storage."""
        parts = workspace.split("/")
        if len(parts) >= 3:
            workspace_name = parts[2]
            physical_path = self.base_path / "workspaces" / workspace_name / filename

            if physical_path.exists():
                content = physical_path.read_text(encoding="utf-8")

                # Try to parse as JSON
                try:
                    content = json.loads(content)
                except json.JSONDecodeError:
                    pass

                return AgentFile(
                    file_id=f"file_{uuid4().hex[:8]}",
                    name=filename,
                    path=f"{workspace}/{filename}",
                    file_type=FileType.SCRATCHPAD,
                    content=content,
                    storage_type=StorageType.PERSISTENT,
                )

        return None

    async def _delete_persistent_file(self, agent_file: AgentFile) -> None:
        """Delete file from persistent storage."""
        parts = agent_file.path.split("/")
        if len(parts) >= 3:
            workspace_name = parts[2]
            physical_path = self.base_path / "workspaces" / workspace_name / agent_file.name

            if physical_path.exists():
                physical_path.unlink()

    def get_stats(self) -> dict[str, Any]:
        """Get filesystem statistics."""
        return {
            **self._stats,
            "workspace_count": len(self._workspaces),
        }


def create_agent_filesystem(
    base_path: str | Path | None = None,
) -> AgentFilesystem:
    """Create an agent filesystem with default configuration."""
    return AgentFilesystem(base_path=base_path)


__all__ = [
    "AgentDirectory",
    "AgentFile",
    "AgentFilesystem",
    "FileType",
    "StorageType",
    "create_agent_filesystem",
]
