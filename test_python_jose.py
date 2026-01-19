#!/usr/bin/env python3
"""Test script to verify python-jose installation and JWT functionality."""

from __future__ import annotations

import sys


def test_jose_import():
    """Test if jose module can be imported."""
    print("=" * 60)
    print("Testing python-jose Import")
    print("=" * 60)

    try:
        from jose import jwt

        print("✓ jose.jwt imported successfully")
        print(f"  JWT module: {jwt}")
        print("  ✅ python-jose is installed correctly")
        return True

    except ModuleNotFoundError as e:
        print(f"  ❌ FAILED: {e}")
        print("  python-jose is not installed or missing dependencies")
        print("  Required: python-jose[cryptography]>=3.3.0")
        return False
    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        print("  Likely missing cryptography dependencies")
        print("  Required system packages: libssl-dev, libffi-dev")
        return False


def test_jwt_encode_decode():
    """Test JWT encoding and decoding."""
    print("\n" + "=" * 60)
    print("Testing JWT Encode/Decode")
    print("=" * 60)

    try:
        from jose import jwt

        # Test data
        secret_key = "test-secret-key-for-testing-only"  # pragma: allowlist secret  # nosec B105
        algorithm = "HS256"
        payload = {
            "sub": "test-user",
            "roles": ["admin"],
            "exp": 9999999999,  # Far future
        }

        # Encode
        token = jwt.encode(payload, secret_key, algorithm=algorithm)
        print("✓ JWT token encoded successfully")
        print(f"  Token (first 50 chars): {token[:50]}...")

        # Decode
        decoded = jwt.decode(token, secret_key, algorithms=[algorithm])
        print("✓ JWT token decoded successfully")
        print(f"  Decoded payload: {decoded}")

        # Verify payload
        if decoded.get("sub") == "test-user" and "admin" in decoded.get("roles", []):
            print("  ✅ JWT encode/decode works correctly")
            return True

        print("  ❌ Decoded payload doesn't match")
        return False

    except Exception as e:
        print(f"  ❌ JWT operations failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_cryptography_backend():
    """Test cryptography backend availability."""
    print("\n" + "=" * 60)
    print("Testing Cryptography Backend")
    print("=" * 60)

    try:
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import hashes

        backend = default_backend()
        print("✓ cryptography backend loaded successfully")
        print(f"  Backend: {backend}")

        # Test basic hash
        digest = hashes.Hash(hashes.SHA256(), backend=backend)
        digest.update(b"test")
        result = digest.finalize()
        print(f"✓ SHA256 hash test passed (length: {len(result)} bytes)")
        print("  ✅ cryptography library works correctly")
        return True

    except ImportError as e:
        print(f"  ❌ cryptography import failed: {e}")
        return False
    except Exception as e:
        print(f"  ❌ cryptography test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("\n🧪 python-jose Test Suite\n")

    results = {
        "jose Import": test_jose_import(),
        "JWT Encode/Decode": test_jwt_encode_decode(),
        "Cryptography Backend": test_cryptography_backend(),
    }

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n🎉 All tests passed! python-jose is working correctly.\n")
        return 0

    print("\n⚠️  Some tests failed. Check the logs above.\n")
    print("Common fixes:")
    print("  1. Install python-jose[cryptography]: pip install 'python-jose[cryptography]>=3.3.0'")
    print("  2. Install system dependencies: apt-get install libssl-dev libffi-dev")
    print("  3. Rebuild with updated Dockerfile\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
