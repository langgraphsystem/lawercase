"""
Document storage service for saving uploaded files.

Supports:
- Supabase Storage (primary/required)
- Cloudflare R2 (optional alternative)

NOTE: Local storage fallback has been removed.
All documents must be saved to cloud storage (Supabase or R2).
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class DocumentStorage:
    """Service for storing document files with metadata."""

    def __init__(
        self,
        backend: str = "supabase",
        bucket_name: str = "intake-documents",
    ):
        """Initialize document storage.

        Args:
            backend: Storage backend - 'supabase' or 'r2'
            bucket_name: Name of storage bucket
        """
        if backend not in ("supabase", "r2"):
            raise ValueError(f"Unsupported backend: {backend}. Use 'supabase' or 'r2'")
        self.backend = backend
        self.bucket_name = bucket_name
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

        # Save to configured backend (no local fallback)
        result = None

        if self.backend == "supabase":
            result = await self._save_to_supabase(
                file_bytes, storage_path, file_type, full_metadata
            )
        elif self.backend == "r2":
            result = await self._save_to_r2(
                file_bytes, storage_path, file_name, file_type, full_metadata
            )

        if result:
            result["file_id"] = file_id
            result["metadata"] = full_metadata
            logger.info(
                "document_storage.saved",
                file_id=file_id,
                storage_path=storage_path,
                backend=result.get("backend", "unknown"),
            )
            return result

        # No fallback - return error
        error_msg = f"Failed to save to {self.backend}. Check configuration and credentials."
        logger.error(
            "document_storage.failed",
            file_id=file_id,
            storage_path=storage_path,
            backend=self.backend,
            error=error_msg,
        )
        return {
            "success": False,
            "error": error_msg,
            "file_id": file_id,
            "backend": self.backend,
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

    async def get_document(self, storage_path: str, backend: str = "supabase") -> bytes | None:
        """Retrieve document from storage.

        Args:
            storage_path: Path/key where document is stored
            backend: Which backend to retrieve from ('supabase' or 'r2')

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

            else:
                logger.warning(
                    "document_storage.unsupported_backend",
                    backend=backend,
                    storage_path=storage_path,
                )

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
            backend: Which backend to delete from ('supabase' or 'r2')

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

            else:
                logger.warning(
                    "document_storage.unsupported_backend",
                    backend=backend,
                    storage_path=storage_path,
                )

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
