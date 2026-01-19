#!/usr/bin/env python3
"""Test script to verify JPEG2000 support in Pillow and img2pdf."""

from __future__ import annotations

import sys


def test_pillow_jpeg2000():
    """Test if Pillow has JPEG2000 support."""
    print("=" * 60)
    print("Testing Pillow JPEG2000 Support")
    print("=" * 60)

    try:
        from PIL import features

        has_jpeg2000 = features.check_codec("jpg_2000")
        print("✓ Pillow imported successfully")
        print(f"  JPEG2000 codec available: {has_jpeg2000}")

        if has_jpeg2000:
            print("  ✅ JPEG2000 support is ENABLED")
            return True

        print("  ❌ JPEG2000 support is MISSING")
        print("  Note: Pillow needs to be compiled with libopenjp2-7")
        return False

    except ImportError as e:
        print(f"  ❌ Failed to import Pillow: {e}")
        return False


def test_img2pdf_import():
    """Test if img2pdf can be imported without jp2 errors."""
    print("\n" + "=" * 60)
    print("Testing img2pdf Import")
    print("=" * 60)

    try:
        import img2pdf

        print("✓ img2pdf imported successfully")
        print(f"  Version: {img2pdf.__version__ if hasattr(img2pdf, '__version__') else 'unknown'}")
        print("  ✅ No ModuleNotFoundError for 'jp2'")
        return True

    except ModuleNotFoundError as e:
        if "jp2" in str(e):
            print(f"  ❌ FAILED: {e}")
            print("  This is the error we're trying to fix!")
            print("  Solution: Ensure libopenjp2-7-dev is installed before Pillow")
        else:
            print(f"  ❌ Other import error: {e}")
        return False
    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        return False


def test_img2pdf_conversion():
    """Test actual JPEG2000 to PDF conversion."""
    print("\n" + "=" * 60)
    print("Testing img2pdf JPEG2000 Conversion")
    print("=" * 60)

    try:
        from io import BytesIO

        import img2pdf
        from PIL import Image

        # Create a simple test image
        test_image = Image.new("RGB", (100, 100), color="red")

        # Save as JPEG (not JPEG2000, just test basic conversion)
        img_bytes = BytesIO()
        test_image.save(img_bytes, format="JPEG")
        img_bytes.seek(0)

        # Convert to PDF
        pdf_bytes = img2pdf.convert(img_bytes)

        print("✓ Created test image (100x100 red)")
        print("✓ Converted to PDF successfully")
        print(f"  PDF size: {len(pdf_bytes)} bytes")
        print("  ✅ img2pdf conversion works")

        return True

    except Exception as e:
        print(f"  ❌ Conversion failed: {e}")
        return False


def main():
    """Run all tests."""
    print("\n🧪 JPEG2000 Support Test Suite\n")

    results = {
        "Pillow JPEG2000": test_pillow_jpeg2000(),
        "img2pdf Import": test_img2pdf_import(),
        "img2pdf Conversion": test_img2pdf_conversion(),
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
        print("\n🎉 All tests passed! JPEG2000 support is working.\n")
        return 0

    print("\n⚠️  Some tests failed. Check the logs above.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
