"""Storage configuration for PostgreSQL, Pinecone, Voyage AI, and Cloudflare R2."""

from __future__ import annotations

from pydantic import Field, PostgresDsn, SecretStr
from pydantic_settings import BaseSettings


class StorageConfig(BaseSettings):
    """Unified storage configuration for all storage backends."""

    # PostgreSQL
    postgres_dsn: PostgresDsn = Field(..., description="PostgreSQL connection string (asyncpg)")
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Max overflow connections")
    pool_timeout: int = Field(default=30, description="Pool timeout in seconds")
    pool_recycle: int = Field(default=3600, description="Recycle connections after N seconds")
    echo_sql: bool = Field(default=False, description="Echo SQL queries for debugging")

    # Supabase Configuration
    supabase_url: str | None = Field(default=None, description="Supabase project URL")
    supabase_service_role_key: SecretStr | None = Field(
        default=None, description="Supabase service role key"
    )
    supabase_vector_url: str | None = Field(
        default=None, description="Supabase Vector API URL for embeddings"
    )
    supabase_embedding_model: str = Field(
        default="text-embedding-3-large", description="Embedding model to use"
    )

    # Vector Store Configuration
    vector_namespace: str = Field(
        default="default", description="Default namespace for vector storage (multi-tenancy)"
    )
    embedding_dimension: int = Field(
        default=2000, description="Embedding vector dimension (max for pgvector HNSW index: 2000)"
    )

    # Pinecone Vector Store (optional)
    pinecone_api_key: SecretStr | None = Field(default=None, description="Pinecone API key")
    pinecone_environment: str = Field(
        default="us-east-1-aws", description="Pinecone environment/region"
    )
    pinecone_index_name: str = Field(
        default="mega-agent-semantic", description="Pinecone index name"
    )
    pinecone_namespace: str = Field(
        default="default", description="Default Pinecone namespace for multi-tenancy"
    )

    # Voyage AI Embeddings (optional)
    voyage_api_key: SecretStr | None = Field(default=None, description="Voyage AI API key")
    voyage_model: str = Field(default="voyage-3-large", description="Voyage embedding model name")
    voyage_dimension: int = Field(default=2048, description="Embedding vector dimension")
    voyage_input_type_default: str = Field(
        default="document", description="Default input type: 'document' or 'query'"
    )

    # Cloudflare R2 Storage (optional)
    r2_account_id: str | None = Field(default=None, description="Cloudflare account ID")
    r2_access_key_id: SecretStr | None = Field(
        default=None, description="R2 access key ID (S3-compatible)"
    )
    r2_secret_access_key: SecretStr | None = Field(
        default=None, description="R2 secret access key (S3-compatible)"
    )
    r2_bucket_name: str = Field(
        default="mega-agent-documents", description="R2 bucket name for document storage"
    )
    r2_endpoint: str | None = Field(
        default=None, description="R2 endpoint URL (https://<account-id>.r2.cloudflarestorage.com)"
    )
    r2_public_url: str | None = Field(
        default=None, description="R2 public URL (custom domain if configured)"
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",  # Ignore extra fields in .env (like OPENAI_API_KEY, TELEGRAM_*, etc.)
    }


# Global singleton instance
_storage_config: StorageConfig | None = None


def get_storage_config() -> StorageConfig:
    """Get global storage configuration instance."""
    global _storage_config
    if _storage_config is None:
        _storage_config = StorageConfig()
    return _storage_config


def validate_memory_config() -> list[str]:
    """
    Validate memory system configuration.

    Returns:
        List of error messages. Empty list means all valid.
    """
    import os

    errors = []
    config = get_storage_config()

    # Check database connection
    if not config.postgres_dsn:
        errors.append("POSTGRES_DSN not set - database connection required")

    # Check embeddings endpoint
    if not config.supabase_vector_url:
        errors.append(
            "SUPABASE_VECTOR_URL not set - required for semantic memory embeddings "
            "(e.g., https://api.openai.com/v1/embeddings)"
        )

    # Check API keys (either Supabase service role key or OpenAI API key)
    has_supabase_key = config.supabase_service_role_key is not None
    has_openai_key = os.getenv("OPENAI_API_KEY") is not None

    if not has_supabase_key and not has_openai_key:
        errors.append(
            "Neither SUPABASE_SERVICE_ROLE_KEY nor OPENAI_API_KEY set - "
            "at least one API key required for embeddings"
        )

    # Check embedding dimensions match model
    # NOTE: Using 2000 dimensions (max for pgvector HNSW index)
    # OpenAI text-embedding-3-large supports variable dimensions via API parameter
    expected_dims = {
        "text-embedding-3-large": 2000,  # Max for pgvector HNSW (API param: dimensions=2000)
        "text-embedding-3-small": 1536,  # Default dimension for text-embedding-3-small
        "text-embedding-ada-002": 1536,  # Default dimension for ada-002
    }
    model = config.supabase_embedding_model
    if model in expected_dims and config.embedding_dimension != expected_dims[model]:
        errors.append(
            f"EMBEDDING_DIMENSION mismatch: {config.embedding_dimension} "
            f"!= {expected_dims[model]} for model {model}"
        )

    return errors
