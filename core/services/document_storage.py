"""
Document storage service for saving uploaded files.

Supports multiple backends:
- Supabase Storage (default)
- Cloudflare R2
- Local filesystem (fallback)
"""

from __future__ import annotations

from datetime import UTC, datetime
import os
from pathlib import Path
from typing import Any
import uuid

import structlog

logger = structlog.get_logger(__name__)


class DocumentStorage:
    """Service for storing document files with metadata."""

    def __init__(
        self,
        backend: str = "supabase",
        bucket_name: str = "intake-documents",
        local_path: str | None = None,
    ):
        """Initialize document storage.

        Args:
            backend: Storage backend - 'supabase', 'r2', or 'local'
            bucket_name: Name of storage bucket
            local_path: Path for local storage fallback
        """
        self.backend = backend
        self.bucket_name = bucket_name
        self.local_path = local_path or "data/documents"
        self._client = None

    async def _get_supabase_client(self):
        """Get or create Supabase client."""
        if self._client is None:
            try:
                from supabase import create_client

                from config.settings import get_settings

                settings = get_settings()
                self._client = create_client(
                    settings.supabase_url,
                    settings.supabase_service_key or settings.supabase_anon_key,
                )
            except Exception as e:
                logger.warning("document_storage.supabase_init_failed", error=str(e))
                self._client = None
        return self._client

    async def save_document(
        self,
        file_bytes: bytes,
        file_name: str,
        file_type: str,
        user_id: str,
        case_id: str | None = None,
        question_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Save document file to storage.

        Args:
            file_bytes: Raw file content
            file_name: Original filename
            file_type: MIME type
            user_id: User who uploaded
            case_id: Associated case ID
            question_id: Intake question ID if applicable
            metadata: Additional metadata

        Returns:
            Dict with storage_path, storage_url, file_id, etc.
        """
        # Generate unique file ID and path
        file_id = str(uuid.uuid4())
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

        # Sanitize filename
        safe_name = "".join(c for c in file_name if c.isalnum() or c in "._-")
        if not safe_name:
            safe_name = "document"

        # Build storage path: user_id/case_id/timestamp_filename
        path_parts = [user_id]
        if case_id:
            path_parts.append(case_id)
        path_parts.append(f"{timestamp}_{file_id[:8]}_{safe_name}")
        storage_path = "/".join(path_parts)

        # Prepare metadata
        full_metadata = {
            "file_id": file_id,
            "original_name": file_name,
            "file_type": file_type,
            "file_size": len(file_bytes),
            "user_id": user_id,
            "case_id": case_id or "",
            "question_id": question_id or "",
            "uploaded_at": datetime.now(UTC).isoformat(),
        }
        if metadata:
            full_metadata.update(metadata)

        # Try storage backends in order
        result = None

        if self.backend == "supabase":
            result = await self._save_to_supabase(
                file_bytes, storage_path, file_type, full_metadata
            )

        if result is None and self.backend == "r2":
            result = await self._save_to_r2(
                file_bytes, storage_path, file_name, file_type, full_metadata
            )

        if result is None:
            # Fallback to local storage
            result = await self._save_to_local(file_bytes, storage_path, full_metadata)

        if result:
            result["file_id"] = file_id
            result["metadata"] = full_metadata
            logger.info(
                "document_storage.saved",
                file_id=file_id,
                storage_path=storage_path,
                backend=result.get("backend", "unknown"),
            )

        return result or {
            "success": False,
            "error": "All storage backends failed",
            "file_id": file_id,
        }

    async def _save_to_supabase(
        self,
        file_bytes: bytes,
        storage_path: str,
        file_type: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Save to Supabase Storage."""
        try:
            client = await self._get_supabase_client()
            if not client:
                return None

            # Upload to Supabase Storage
            response = client.storage.from_(self.bucket_name).upload(
                path=storage_path,
                file=file_bytes,
                file_options={
                    "content-type": file_type,
                    "x-upsert": "true",  # Overwrite if exists
                },
            )

            # Get public URL
            public_url = client.storage.from_(self.bucket_name).get_public_url(storage_path)

            logger.info(
                "document_storage.supabase_upload_success",
                storage_path=storage_path,
            )

            return {
                "success": True,
                "backend": "supabase",
                "storage_path": storage_path,
                "storage_url": public_url,
                "bucket": self.bucket_name,
            }

        except Exception as e:
            logger.warning(
                "document_storage.supabase_upload_failed",
                error=str(e),
                storage_path=storage_path,
            )
            return None

    async def _save_to_r2(
        self,
        file_bytes: bytes,
        storage_path: str,
        file_name: str,
        file_type: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Save to Cloudflare R2."""
        try:
            from core.storage.r2_storage import create_r2_storage

            r2 = create_r2_storage()
            result = await r2.upload_file(
                file_content=file_bytes,
                filename=file_name,
                content_type=file_type,
                folder=storage_path.rsplit("/", 1)[0] if "/" in storage_path else "",
                metadata={k: str(v) for k, v in metadata.items()},
            )

            logger.info(
                "document_storage.r2_upload_success",
                r2_key=result.get("r2_key"),
            )

            return {
                "success": True,
                "backend": "r2",
                "storage_path": result.get("r2_key"),
                "storage_url": result.get("r2_url"),
                "bucket": result.get("bucket"),
            }

        except Exception as e:
            logger.warning(
                "document_storage.r2_upload_failed",
                error=str(e),
                storage_path=storage_path,
            )
            return None

    async def _save_to_local(
        self,
        file_bytes: bytes,
        storage_path: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Save to local filesystem (fallback)."""
        try:
            # Create full path
            full_path = Path(self.local_path) / storage_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            full_path.write_bytes(file_bytes)

            # Write metadata alongside
            meta_path = full_path.with_suffix(full_path.suffix + ".meta.json")
            import json

            meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False))

            logger.info(
                "document_storage.local_save_success",
                path=str(full_path),
            )

            return {
                "success": True,
                "backend": "local",
                "storage_path": str(full_path),
                "storage_url": f"file://{full_path.absolute()}",
            }

        except Exception as e:
            logger.error(
                "document_storage.local_save_failed",
                error=str(e),
                storage_path=storage_path,
            )
            return None

    async def get_document(self, storage_path: str, backend: str = "supabase") -> bytes | None:
        """Retrieve document from storage.

        Args:
            storage_path: Path/key where document is stored
            backend: Which backend to retrieve from

        Returns:
            File bytes or None if not found
        """
        try:
            if backend == "supabase":
                client = await self._get_supabase_client()
                if client:
                    response = client.storage.from_(self.bucket_name).download(storage_path)
                    return response

            elif backend == "r2":
                from core.storage.r2_storage import create_r2_storage

                r2 = create_r2_storage()
                return await r2.download_file(storage_path)

            elif backend == "local":
                full_path = Path(self.local_path) / storage_path
                if full_path.exists():
                    return full_path.read_bytes()

        except Exception as e:
            logger.error(
                "document_storage.get_failed",
                error=str(e),
                storage_path=storage_path,
                backend=backend,
            )

        return None

    async def delete_document(self, storage_path: str, backend: str = "supabase") -> bool:
        """Delete document from storage.

        Args:
            storage_path: Path/key where document is stored
            backend: Which backend to delete from

        Returns:
            True if deleted successfully
        """
        try:
            if backend == "supabase":
                client = await self._get_supabase_client()
                if client:
                    client.storage.from_(self.bucket_name).remove([storage_path])
                    return True

            elif backend == "r2":
                from core.storage.r2_storage import create_r2_storage

                r2 = create_r2_storage()
                await r2.delete_file(storage_path)
                return True

            elif backend == "local":
                full_path = Path(self.local_path) / storage_path
                if full_path.exists():
                    full_path.unlink()
                    # Also remove metadata file
                    meta_path = full_path.with_suffix(full_path.suffix + ".meta.json")
                    if meta_path.exists():
                        meta_path.unlink()
                    return True

        except Exception as e:
            logger.error(
                "document_storage.delete_failed",
                error=str(e),
                storage_path=storage_path,
                backend=backend,
            )

        return False


# Global instance
_document_storage: DocumentStorage | None = None


def get_document_storage() -> DocumentStorage:
    """Get or create global document storage instance."""
    global _document_storage
    if _document_storage is None:
        # Determine backend from environment
        backend = os.environ.get("DOCUMENT_STORAGE_BACKEND", "supabase")
        bucket = os.environ.get("DOCUMENT_STORAGE_BUCKET", "intake-documents")
        _document_storage = DocumentStorage(backend=backend, bucket_name=bucket)
    return _document_storage
