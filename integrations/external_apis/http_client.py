from __future__ import annotations

"""HTTP client stub for upcoming tool integrations.

Provides async placeholder to be replaced with real implementation.
"""

from typing import Any


class HttpClient:
    """Placeholder async HTTP client."""

    async def get(self, url: str, **kwargs: Any) -> dict[str, Any]:
        return {"url": url, "status": "stub", "kwargs": kwargs}
