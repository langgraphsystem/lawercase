"""I/O helpers for EB-1A pipeline."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_bytes(path: Path) -> bytes:
    return path.read_bytes()


def write_bytes(path: Path, data: bytes) -> Path:
    ensure_directory(path.parent)
    path.write_bytes(data)
    logger.debug("io.write_bytes", path=str(path), size=len(data))
    return path


def read_text(path: Path, encoding: str = "utf-8") -> str:
    return path.read_text(encoding=encoding)


@contextmanager
def temp_directory(base: Path) -> Iterator[Path]:
    ensure_directory(base)
    with os.scandir(base) as _:
        yield base
