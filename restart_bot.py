"""Script to properly restart Telegram bot and clear pending updates."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys

import psutil
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()


def kill_bot_processes():
    """Kill all running telegram bot processes."""
    print("🔍 Searching for running bot processes...")
    killed = 0
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = proc.info.get("cmdline") or []
            cmdline_str = " ".join(cmdline)
            if "telegram_interface.bot" in cmdline_str and "python" in proc.info["name"].lower():
                print(f"   ⚠️  Found process PID {proc.info['pid']}: {cmdline_str[:80]}")
                proc.kill()
                killed += 1
                print(f"   ✅ Killed PID {proc.info['pid']}")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if killed == 0:
        print("   ✅ No running bot processes found")
    else:
        print(f"   ✅ Killed {killed} process(es)")
    print()


async def clear_pending_updates():
    """Clear all pending updates from Telegram."""
    print("🧹 Clearing pending updates...")
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("   ❌ TELEGRAM_BOT_TOKEN not found")
        return False

    bot = Bot(token=token)
    try:
        # Get pending update count
        updates = await bot.get_updates()
        count = len(updates)

        if count == 0:
            print("   ✅ No pending updates")
        else:
            print(f"   Found {count} pending update(s)")
            # Mark all as read by getting updates with offset
            if updates:
                last_update_id = updates[-1].update_id
                await bot.get_updates(offset=last_update_id + 1, timeout=1)
                print(f"   ✅ Cleared {count} pending update(s)")
        print()
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        print()
        return False


def start_bot():
    """Start the Telegram bot."""
    print("🚀 Starting Telegram bot...")
    try:
        # Start bot as subprocess
        process = subprocess.Popen(  # nosec B603 - Controlled input from sys.executable
            [sys.executable, "-m", "telegram_interface.bot"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        print(f"   ✅ Bot started with PID {process.pid}")
        print("   📝 Showing startup logs...\n")
        print("   " + "=" * 60)

        # Show first few lines of output
        for i, line in enumerate(process.stdout):
            if i < 10:
                print(f"   {line.rstrip()}")
            elif "Application started" in line:
                print(f"   {line.rstrip()}")
                break

        print("   " + "=" * 60)
        print()
        print("✅ Bot is running!")
        print(f"   PID: {process.pid}")
        print(f"   To stop: kill {process.pid}")
        print("   Or use: python restart_bot.py --stop")
        print()
        print("💡 Now try sending /start to @lawercasebot in Telegram")
        print()

        # Keep process running
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\n⚠️  Stopping bot...")
            process.terminate()
            process.wait(timeout=5)
            print("✅ Bot stopped")

    except Exception as e:
        print(f"   ❌ Error starting bot: {e}")


def main():
    """Main entry point."""
    print("\n" + "=" * 70)
    print("🤖 TELEGRAM BOT RESTART UTILITY")
    print("=" * 70 + "\n")

    # Check for --stop flag
    if "--stop" in sys.argv:
        kill_bot_processes()
        return

    # Step 1: Kill existing processes
    kill_bot_processes()

    # Step 2: Clear pending updates
    success = asyncio.run(clear_pending_updates())
    if not success:
        print("❌ Failed to clear updates. Exiting.")
        return

    # Step 3: Start bot
    start_bot()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
