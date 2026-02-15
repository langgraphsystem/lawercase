from __future__ import annotations

from ipaddress import ip_address, ip_network
import os
import re
from typing import Any
from urllib.parse import urlparse

import httpx

from core.tools.tool_registry import ToolMetadata, get_tool_registry


def register_builtin_tools() -> None:
    """Register built-in tools that should always be available."""
    registry = get_tool_registry()

    if any(meta.name == "http.get" for meta in registry.list_tools()):
        return

    _private_nets = [
        ip_network("127.0.0.0/8"),
        ip_network("10.0.0.0/8"),
        ip_network("172.16.0.0/12"),
        ip_network("192.168.0.0/16"),
        ip_network("169.254.0.0/16"),
        ip_network("::1/128"),
        ip_network("fc00::/7"),
        ip_network("fe80::/10"),
    ]

    def _looks_like_ip(host: str) -> bool:
        try:
            ip_address(host)
            return True
        except ValueError:
            return False

    def _is_private_host(host: str) -> bool:
        if not host:
            return True
        host = host.strip().lower()
        if host in {"localhost", "localhost.localdomain"}:
            return True
        if _looks_like_ip(host):
            ip = ip_address(host)
            return any(ip in net for net in _private_nets)
        # Guard obvious internal hostnames without DNS resolution.
        return bool(re.search(r"(^|\\.)local$", host))

    async def _http_get(
        url: str,
        *,
        timeout_s: float = 10.0,
        max_bytes: int = 200_000,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        follow_redirects: bool = True,
    ) -> dict[str, Any]:
        """Perform a constrained HTTP GET request.

        SSRF protection:
        - Only http/https schemes.
        - Blocks localhost/private IPs by default (set HTTP_GET_ALLOW_PRIVATE=true to override).
        """
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("Only http/https URLs are allowed")
        if not parsed.netloc:
            raise ValueError("URL must include a host")

        allow_private = os.getenv("HTTP_GET_ALLOW_PRIVATE", "").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        if not allow_private and _is_private_host(parsed.hostname or ""):
            raise ValueError("Blocked private/localhost URL")

        safe_headers = {"User-Agent": "mega-agent-pro/1.0"}
        if headers:
            for k, v in headers.items():
                if isinstance(k, str) and isinstance(v, str):
                    safe_headers[k] = v

        timeout = httpx.Timeout(timeout_s, connect=min(5.0, timeout_s))
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=follow_redirects) as client:
            resp = await client.get(url, headers=safe_headers, params=params)
            content = b""
            async for chunk in resp.aiter_bytes():
                content += chunk
                if len(content) >= max_bytes:
                    break

        content_type = resp.headers.get("content-type", "")
        try:
            text = content.decode(resp.encoding or "utf-8", errors="replace")
        except Exception:
            text = content.decode("utf-8", errors="replace")

        truncated = len(content) >= max_bytes
        return {
            "url": str(resp.url),
            "status_code": resp.status_code,
            "ok": 200 <= resp.status_code < 300,
            "content_type": content_type,
            "text": text,
            "truncated": truncated,
            "bytes": len(content),
            "headers": {
                "content-type": content_type,
                "content-length": resp.headers.get("content-length"),
            },
        }

    registry.register(
        "http.get",
        _http_get,
        metadata=ToolMetadata(
            name="http.get",
            description="Simplified HTTP GET tool used for smoke tests and development.",
            allowed_roles={"admin", "lawyer"},
            tags={"network", "builtin"},
        ),
    )
