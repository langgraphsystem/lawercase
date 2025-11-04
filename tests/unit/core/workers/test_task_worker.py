from __future__ import annotations

import pytest

from core.workers.task_worker import run_once


@pytest.mark.asyncio
async def test_worker_run_once_returns_health_status() -> None:
    status = await run_once()
    assert status == {"semantic": True, "episodic": True, "working": True}
