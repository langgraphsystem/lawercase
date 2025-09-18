"""S3 client for object storage with presigned URL support."""

from __future__ import annotations

import hashlib
import logging
from typing import Optional

import boto3
from botocore.exceptions import NoCredentialsError

from config.settings import get_settings

logger = logging.getLogger(__name__)


class S3Client:
    """S3 client for uploading/downloading objects with presigned URLs."""

    def __init__(self, settings: Optional[object] = None):
        self.settings = settings or get_settings()
        self._client = None
        self._initialized = False

    def _get_client(self):
        """Get or create S3 client."""
        if not self._client:
            try:
                if self.settings.s3_endpoint:
                    # Custom S3-compatible endpoint
                    self._client = boto3.client(
                        's3',
                        endpoint_url=self.settings.s3_endpoint,
                        region_name=self.settings.s3_region,
                        aws_access_key_id=self.settings.s3_access_key_id,
                        aws_secret_access_key=self.settings.s3_secret_access_key
                    )
                else:
                    # Standard AWS S3
                    self._client = boto3.client(
                        's3',
                        region_name=self.settings.s3_region,
                        aws_access_key_id=self.settings.s3_access_key_id,
                        aws_secret_access_key=self.settings.s3_secret_access_key
                    )
                self._initialized = True
            except (NoCredentialsError, Exception) as e:
                logger.error(f"Failed to initialize S3 client: {e}")
                self._initialized = False

        return self._client

    async def upload_file(self, file_data: bytes, key: str, content_type: str = "application/octet-stream") -> bool:
        """Upload file to S3."""
        try:
            client = self._get_client()
            if not client or not self.settings.s3_bucket:
                return False

            client.put_object(
                Bucket=self.settings.s3_bucket,
                Key=key,
                Body=file_data,
                ContentType=content_type
            )
            logger.info(f"File uploaded to S3: {key}")
            return True

        except Exception as e:
            logger.error(f"Failed to upload file to S3: {e}")
            return False

    async def generate_presigned_download_url(self, key: str, ttl_seconds: Optional[int] = None) -> Optional[str]:
        """Generate presigned download URL."""
        try:
            client = self._get_client()
            if not client or not self.settings.s3_bucket:
                return None

            ttl = ttl_seconds or self.settings.s3_presign_ttl_seconds
            url = client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.settings.s3_bucket, 'Key': key},
                ExpiresIn=ttl
            )
            return url

        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None

    async def generate_presigned_upload_url(self, key: str, content_type: str, ttl_seconds: Optional[int] = None) -> Optional[str]:
        """Generate presigned upload URL."""
        try:
            client = self._get_client()
            if not client or not self.settings.s3_bucket:
                return None

            ttl = ttl_seconds or self.settings.s3_presign_ttl_seconds
            url = client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.settings.s3_bucket,
                    'Key': key,
                    'ContentType': content_type
                },
                ExpiresIn=ttl
            )
            return url

        except Exception as e:
            logger.error(f"Failed to generate presigned upload URL: {e}")
            return None

    @staticmethod
    def calculate_sha256(data: bytes) -> str:
        """Calculate SHA256 hash of data."""
        return hashlib.sha256(data).hexdigest()

    def health_check(self) -> bool:
        """Check S3 connectivity."""
        try:
            client = self._get_client()
            if not client or not self.settings.s3_bucket:
                return False
            client.head_bucket(Bucket=self.settings.s3_bucket)
            return True
        except Exception:
            return False


# Global instance
_s3_client = None


def get_s3_client() -> S3Client:
    """Get global S3 client instance."""
    global _s3_client
    if _s3_client is None:
        _s3_client = S3Client()
    return _s3_client