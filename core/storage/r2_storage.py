"""Cloudflare R2 storage client for document management.

Official Documentation:
https://developers.cloudflare.com/r2/api/s3/api/
https://developers.cloudflare.com/r2/api/s3/tokens/
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import TYPE_CHECKING, Any, BinaryIO
from uuid import uuid4

if TYPE_CHECKING:
    from pydantic import SecretStr

try:
    import boto3
    from botocore.client import Config

    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


class R2Storage:
    """
    Cloudflare R2 storage client (S3-compatible API).

    Features:
    - S3-compatible API for easy integration
    - No egress fees
    - Automatic presigned URL generation
    - Metadata storage with files

    Docs: https://developers.cloudflare.com/r2/
    """

    def __init__(
        self,
        account_id: str | None = None,
        access_key_id: SecretStr | None = None,
        secret_access_key: SecretStr | None = None,
        bucket_name: str | None = None,
    ):
        if not BOTO3_AVAILABLE:
            raise ImportError("boto3 is required for R2. Install with: pip install boto3")

        # Import config here to avoid circular imports
        from .config import get_storage_config

        config = get_storage_config()

        self.account_id = account_id or config.r2_account_id
        self.access_key_id = access_key_id or config.r2_access_key_id
        self.secret_access_key = secret_access_key or config.r2_secret_access_key
        self.bucket_name = bucket_name or config.r2_bucket_name
        self.endpoint = config.r2_endpoint
        self.public_url = config.r2_public_url

        # Initialize S3-compatible client for R2
        # https://developers.cloudflare.com/r2/api/s3/tokens/
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key_id.get_secret_value(),
            aws_secret_access_key=self.secret_access_key.get_secret_value(),
            config=Config(signature_version="s3v4"),
            region_name="auto",  # R2 uses "auto" region
        )

    async def upload_file(
        self,
        file_content: bytes | BinaryIO,
        filename: str,
        content_type: str,
        folder: str = "",
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Upload file to R2.

        Args:
            file_content: File bytes or file-like object
            filename: Original filename
            content_type: MIME type (e.g., "application/pdf")
            folder: Optional folder/prefix for organization
            metadata: Additional metadata to store with file

        Returns:
            Dict with r2_key, r2_url, file_size, bucket

        Example:
            >>> storage = R2Storage()
            >>> with open("doc.pdf", "rb") as f:
            ...     result = await storage.upload_file(
            ...         f, "document.pdf", "application/pdf", folder="cases/123"
            ...     )
            >>> print(result["r2_key"])
            cases/123/550e8400-e29b-41d4-a716-446655440000.pdf
        """
        # Generate unique key with UUID
        file_id = str(uuid4())
        file_extension = filename.split(".")[-1] if "." in filename else ""
        r2_key = f"{folder}/{file_id}.{file_extension}" if folder else f"{file_id}.{file_extension}"

        # Prepare file content
        if isinstance(file_content, bytes):
            file_obj = io.BytesIO(file_content)
            file_size = len(file_content)
        else:
            # File-like object
            file_obj = file_content
            file_obj.seek(0, 2)  # Seek to end
            file_size = file_obj.tell()
            file_obj.seek(0)  # Reset to beginning

        # Prepare S3 metadata
        s3_metadata = {
            "original-filename": filename,
            "uploaded-at": datetime.utcnow().isoformat(),
            "file-id": file_id,
        }

        if metadata:
            # Convert all values to strings (S3 metadata requirement)
            s3_metadata.update({k: str(v) for k, v in metadata.items()})

        # Upload to R2
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.put_object
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=r2_key,
            Body=file_obj,
            ContentType=content_type,
            Metadata=s3_metadata,
        )

        # Generate URL
        r2_url = self._get_url(r2_key)

        return {
            "r2_key": r2_key,
            "r2_url": r2_url,
            "file_size": file_size,
            "bucket": self.bucket_name,
            "file_id": file_id,
        }

    async def download_file(self, r2_key: str) -> bytes:
        """
        Download file from R2.

        Args:
            r2_key: File key in R2

        Returns:
            File content as bytes

        Example:
            >>> storage = R2Storage()
            >>> content = await storage.download_file("cases/123/doc.pdf")
            >>> len(content)
            52348
        """
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=r2_key)
        return response["Body"].read()

    async def get_metadata(self, r2_key: str) -> dict[str, Any]:
        """
        Get file metadata without downloading content.

        Args:
            r2_key: File key in R2

        Returns:
            Dict with metadata, size, content_type, etc.

        Example:
            >>> storage = R2Storage()
            >>> meta = await storage.get_metadata("cases/123/doc.pdf")
            >>> print(meta["content_type"])
            application/pdf
        """
        response = self.s3_client.head_object(Bucket=self.bucket_name, Key=r2_key)
        return {
            "content_type": response.get("ContentType"),
            "content_length": response.get("ContentLength"),
            "last_modified": response.get("LastModified"),
            "metadata": response.get("Metadata", {}),
            "etag": response.get("ETag"),
        }

    async def delete_file(self, r2_key: str) -> None:
        """
        Delete file from R2.

        Args:
            r2_key: File key in R2

        Example:
            >>> storage = R2Storage()
            >>> await storage.delete_file("cases/123/doc.pdf")
        """
        self.s3_client.delete_object(Bucket=self.bucket_name, Key=r2_key)

    async def delete_files(self, r2_keys: list[str]) -> None:
        """
        Batch delete multiple files from R2.

        Args:
            r2_keys: List of file keys to delete

        Example:
            >>> storage = R2Storage()
            >>> await storage.delete_files(["file1.pdf", "file2.pdf"])
        """
        if not r2_keys:
            return

        # Prepare delete objects structure
        objects = [{"Key": key} for key in r2_keys]

        self.s3_client.delete_objects(
            Bucket=self.bucket_name, Delete={"Objects": objects, "Quiet": True}
        )

    async def generate_presigned_url(
        self,
        r2_key: str,
        expiration: int = 3600,
        force_download: bool = False,
        download_filename: str | None = None,
    ) -> str:
        """
        Generate presigned URL for temporary file access.

        Args:
            r2_key: File key in R2
            expiration: URL expiration in seconds (default 1 hour)
            force_download: Force browser to download instead of display
            download_filename: Custom filename for download

        Returns:
            Presigned URL

        Example:
            >>> storage = R2Storage()
            >>> url = await storage.generate_presigned_url(
            ...     "doc.pdf", expiration=3600, force_download=True
            ... )
            >>> print(url)
            https://...?X-Amz-Signature=...
        """
        params: dict[str, Any] = {
            "Bucket": self.bucket_name,
            "Key": r2_key,
        }

        # Force download with custom filename
        if force_download:
            disposition = "attachment"
            if download_filename:
                disposition += f'; filename="{download_filename}"'
            params["ResponseContentDisposition"] = disposition

        url = self.s3_client.generate_presigned_url(
            "get_object", Params=params, ExpiresIn=expiration
        )

        return url

    async def list_files(self, prefix: str = "", max_keys: int = 1000) -> list[dict[str, Any]]:
        """
        List files in R2 bucket.

        Args:
            prefix: Filter by key prefix (e.g., "cases/123/")
            max_keys: Maximum number of results

        Returns:
            List of file info dicts

        Example:
            >>> storage = R2Storage()
            >>> files = await storage.list_files(prefix="cases/123/")
            >>> len(files)
            5
        """
        response = self.s3_client.list_objects_v2(
            Bucket=self.bucket_name, Prefix=prefix, MaxKeys=max_keys
        )

        files = []
        for obj in response.get("Contents", []):
            files.append(
                {
                    "key": obj["Key"],
                    "size": obj["Size"],
                    "last_modified": obj["LastModified"],
                    "etag": obj["ETag"],
                    "url": self._get_url(obj["Key"]),
                }
            )

        return files

    async def copy_file(self, source_key: str, dest_key: str) -> None:
        """
        Copy file within R2 bucket.

        Args:
            source_key: Source file key
            dest_key: Destination file key

        Example:
            >>> storage = R2Storage()
            >>> await storage.copy_file("doc.pdf", "archive/doc.pdf")
        """
        copy_source = {"Bucket": self.bucket_name, "Key": source_key}
        self.s3_client.copy_object(CopySource=copy_source, Bucket=self.bucket_name, Key=dest_key)

    def _get_url(self, r2_key: str) -> str:
        """Generate URL for file (public URL if configured, else endpoint URL)."""
        if self.public_url:
            return f"{self.public_url}/{r2_key}"
        return f"{self.endpoint}/{self.bucket_name}/{r2_key}"

    async def health_check(self) -> bool:
        """
        Check R2 connectivity.

        Returns:
            True if connected, False otherwise

        Example:
            >>> storage = R2Storage()
            >>> await storage.health_check()
            True
        """
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            return True
        except Exception:
            return False


def create_r2_storage() -> R2Storage:
    """
    Factory function to create R2 storage client with config from environment.

    Returns:
        Configured R2Storage instance

    Example:
        >>> storage = create_r2_storage()
        >>> storage.bucket_name
        'mega-agent-documents'
    """
    return R2Storage()
