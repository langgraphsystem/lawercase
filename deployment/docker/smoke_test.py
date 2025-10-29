"""Simple smoke-test for MegaAgent Docker images.

Usage:
    python deployment/docker/smoke_test.py mega-agent-pro-api:latest
"""

from __future__ import annotations

from collections.abc import Sequence
import subprocess
import sys


def run_command(command: Sequence[str]) -> int:
    process = subprocess.run(
        command, check=False
    )  # nosec B603 - Smoke test script with controlled input
    return process.returncode


def main(image: str) -> int:
    cmd = [
        "docker",
        "run",
        "--rm",
        image,
        "python",
        "-m",
        "core.workers.task_worker",
        "smoke",
    ]
    return run_command(cmd)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python deployment/docker/smoke_test.py <image-name>")
        sys.exit(1)
    exit_code = main(sys.argv[1])
    if exit_code != 0:
        print("Smoke test failed")
    sys.exit(exit_code)
