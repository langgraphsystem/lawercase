"""Asynchronous task worker for MegaAgent background jobs."""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from typing import Any

import structlog
import typer

from core.memory.memory_manager_v2 import create_dev_memory_manager

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class WorkerConfig:
    """Runtime configuration for the worker loop."""

    health_check_interval: float = 30.0
    shutdown_grace_period: float = 5.0


async def _health_check_task(config: WorkerConfig) -> None:
    """Periodically run a memory health-check to ensure dependencies stay responsive."""
    memory = create_dev_memory_manager()
    while True:
        status = await memory.health_check()
        logger.info("worker.health_check", status=status)
        await asyncio.sleep(config.health_check_interval)


async def run_worker(config: WorkerConfig) -> None:
    """Main worker loop that runs background tasks."""
    logger.info("worker.start", config=config)
    task = asyncio.create_task(_health_check_task(config))
    try:
        await task
    except asyncio.CancelledError:
        logger.info("worker.stop_requested")
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.wait_for(task, timeout=config.shutdown_grace_period)
        logger.info("worker.stopped")


async def run_once() -> dict[str, Any]:
    """Execute a single health-check cycle – used by smoke tests."""
    memory = create_dev_memory_manager()
    status = await memory.health_check()
    logger.info("worker.smoke", status=status)
    return status


worker_cli = typer.Typer(help="Background worker entrypoint for MegaAgent Pro.")


@worker_cli.command()
def start(
    health_check_interval: float = typer.Option(
        30.0, min=5.0, help="Interval between health checks."
    ),
) -> None:
    """Start the asynchronous worker."""
    config = WorkerConfig(health_check_interval=health_check_interval)
    try:
        asyncio.run(run_worker(config))
    except KeyboardInterrupt:  # pragma: no cover - interactive exit
        logger.warning("worker.interrupted")


@worker_cli.command()
def smoke() -> None:
    """Run a single health-check iteration and exit with non-zero status on failure."""
    status = asyncio.run(run_once())
    if not all(status.values()):
        raise typer.Exit(code=1)


if __name__ == "__main__":
    worker_cli()
