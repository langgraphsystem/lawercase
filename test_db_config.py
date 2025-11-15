"""Test to debug DatabaseManager initialization."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

print("\n" + "=" * 60)
print("🔍 DEBUGGING DATABASE CONFIGURATION")
print("=" * 60 + "\n")

# Check environment variables
print("Environment variables:")
print(f"  POSTGRES_DSN: {os.getenv('POSTGRES_DSN', 'NOT SET')[:50]}...")
print(f"  DATABASE_URL: {os.getenv('DATABASE_URL', 'NOT SET')[:50]}...")
print()

# Try to create StorageConfig
print("Attempting to create StorageConfig...")
try:
    from core.storage.config import StorageConfig

    config = StorageConfig()
    print("✅ StorageConfig created successfully!")
    print(f"  postgres_dsn: {str(config.postgres_dsn)[:50]}...")
    print(f"  pinecone_api_key: {config.pinecone_api_key}")
    print(f"  voyage_api_key: {config.voyage_api_key}")
    print(f"  r2_account_id: {config.r2_account_id}")
except Exception as e:
    print("❌ Failed to create StorageConfig:")
    print(f"   Error: {e}")
    import traceback

    traceback.print_exc()
    print()

# Try to get DatabaseManager
print("\nAttempting to get DatabaseManager...")
try:
    from core.storage.connection import get_db_manager

    db_manager = get_db_manager()
    print("✅ DatabaseManager created successfully!")
    print(f"  Engine: {db_manager._engine}")
except Exception as e:
    print("❌ Failed to get DatabaseManager:")
    print(f"   Error: {e}")
    import traceback

    traceback.print_exc()
