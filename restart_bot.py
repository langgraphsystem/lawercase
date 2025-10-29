"""Supervisor script to run and auto-restart the Telegram bot with logging.

Usage:
  python restart_bot.py --poll-interval 0.0 --max-restarts 0

Features:
- Loads environment from .env if available
- Streams child stdout/stderr to console and to rotating log files
- Auto-restarts on non-zero exit with exponential backoff
- Separate supervisor and bot stream logs
"""

from __future__ import annotations

import argparse
from datetime import datetime
import logging
from logging.handlers import TimedRotatingFileHandler
import os
from pathlib import Path
import queue
import subprocess  # nosec B404
import sys
import threading
import time

LOGGER = logging.getLogger(__name__)


def load_env() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception as exc:  # pragma: no cover - defensive logging
        LOGGER.warning("failed to load .env", exc_info=exc)


def setup_logging(log_dir: Path) -> tuple[logging.Logger, logging.Logger]:
    log_dir.mkdir(parents=True, exist_ok=True)

    supervisor_log = log_dir / "restart_bot.log"
    bot_log = log_dir / "telegram_bot.log"

    # Supervisor logger
    sup_logger = logging.getLogger("restart_bot")
    sup_logger.setLevel(logging.INFO)
    sup_handler = TimedRotatingFileHandler(
        supervisor_log.as_posix(), when="midnight", backupCount=14, encoding="utf-8"
    )
    sup_stream = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    sup_handler.setFormatter(fmt)
    sup_stream.setFormatter(fmt)
    sup_logger.addHandler(sup_handler)
    sup_logger.addHandler(sup_stream)

    # Bot stream logger
    bot_logger = logging.getLogger("bot_stream")
    bot_logger.setLevel(logging.INFO)
    bot_handler = TimedRotatingFileHandler(
        bot_log.as_posix(), when="midnight", backupCount=7, encoding="utf-8"
    )
    bot_handler.setFormatter(fmt)
    bot_logger.addHandler(bot_handler)

    return sup_logger, bot_logger


def enqueue_output(out, q: queue.Queue[str]):
    try:
        for line in iter(out.readline, b""):
            try:
                q.put(line.decode("utf-8", errors="replace"))
            except Exception as exc:  # pragma: no cover - defensive logging
                # Fallback to raw repr
                LOGGER.debug("failed to decode bot output line", exc_info=exc)
                q.put(repr(line))
    finally:
        try:
            out.close()
        except Exception as exc:  # pragma: no cover - defensive logging
            LOGGER.debug("failed to close bot stdout", exc_info=exc)


def run_child(
    cmd: list[str], env: dict[str, str], bot_logger: logging.Logger, sup_logger: logging.Logger
) -> int:
    # Launch child process; command list is fixed and shell disabled.
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        bufsize=1,
        shell=False,
    )  # nosec B603

    q: queue.Queue[str] = queue.Queue()
    t = threading.Thread(target=enqueue_output, args=(proc.stdout, q), daemon=True)  # type: ignore[arg-type]
    t.start()

    # Drain output until process exits
    while True:
        try:
            line = q.get(timeout=0.2)
        except queue.Empty:
            if proc.poll() is not None:
                break
            continue
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        line_s = line.rstrip()
        # Mirror to console and file
        print(f"{ts} | BOT | {line_s}")
        bot_logger.info(line_s)

    # Flush remaining lines
    while True:
        try:
            line = q.get_nowait()
        except queue.Empty:
            break
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        line_s = line.rstrip()
        print(f"{ts} | BOT | {line_s}")
        bot_logger.info(line_s)

    ret = proc.wait()
    sup_logger.info("child exited", extra={})
    return ret


def main() -> int:
    parser = argparse.ArgumentParser(description="Run and auto-restart Telegram bot with logging")
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=0.0,
        help="Polling interval passed to telegram_interface.bot",
    )
    parser.add_argument(
        "--max-restarts",
        type=int,
        default=0,
        help="Maximum number of restarts (0 = unlimited)",
    )
    parser.add_argument(
        "--backoff-initial",
        type=float,
        default=2.0,
        help="Initial backoff seconds before restart",
    )
    parser.add_argument(
        "--backoff-max",
        type=float,
        default=60.0,
        help="Maximum backoff seconds",
    )
    parser.add_argument(
        "--python",
        type=str,
        default=sys.executable,
        help="Python executable to use for child",
    )
    args = parser.parse_args()

    load_env()

    # Ensure token present to avoid restart loop from config error
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        print("ERROR: TELEGRAM_BOT_TOKEN is not set in environment/.env", file=sys.stderr)
        return 2

    logs_dir = Path("logs")
    sup_logger, bot_logger = setup_logging(logs_dir)
    sup_logger.info("restart supervisor starting", extra={})

    restarts = 0
    backoff = max(0.0, args.backoff_initial)

    cmd = [
        args.python,
        "-m",
        "telegram_interface.bot",
        "--poll-interval",
        str(args.poll_interval),
    ]

    # Child inherits current env
    child_env = os.environ.copy()

    try:
        while True:
            rc = run_child(cmd, child_env, bot_logger, sup_logger)
            if rc == 0:
                sup_logger.info("child exited cleanly; not restarting")
                return 0

            restarts += 1
            sup_logger.warning(
                "child crashed; scheduling restart",
            )

            if args.max_restarts and restarts > args.max_restarts:
                sup_logger.error("max restarts reached; exiting")
                return 1

            sup_logger.info("sleeping before restart", extra={})
            time.sleep(backoff)
            backoff = min(args.backoff_max, backoff * 2 if backoff > 0 else 2.0)

    except KeyboardInterrupt:
        sup_logger.info("supervisor interrupted by user")
        return 0
    except Exception as e:
        sup_logger.exception("supervisor fatal error: %s", e)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
