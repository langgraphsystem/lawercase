"""Test script for Document Monitor API."""

from __future__ import annotations

from api.routes.document_monitor import router

print("✅ Document Monitor routes loaded successfully")
print(f"Endpoints: {len(router.routes)} routes\n")

for route in router.routes:
    methods = ", ".join(route.methods) if hasattr(route, "methods") else "N/A"
    print(f"  {methods:10} {route.path}")

print("\n✅ All endpoints registered successfully!")
