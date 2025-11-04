"""Simple bot starter without external dependencies (no psutil needed)."""

from __future__ import annotations

import asyncio
import os
import sys

from dotenv import load_dotenv
from telegram import Bot

load_dotenv()


async def clear_updates():
    """Clear pending Telegram updates."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN not set in .env")
        return False

    bot = Bot(token=token)
    try:
        updates = await bot.get_updates()
        if updates:
            last_id = updates[-1].update_id
            await bot.get_updates(offset=last_id + 1, timeout=1)
            print(f"✅ Cleared {len(updates)} pending update(s)")
        else:
            print("✅ No pending updates")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("🤖 TELEGRAM BOT - SIMPLE STARTER")
    print("=" * 60 + "\n")

    # Clear pending updates
    print("🧹 Clearing pending updates...")
    success = asyncio.run(clear_updates())
    if not success:
        print("\n⚠️  Continuing anyway...\n")

    # Start bot
    print("🚀 Starting Telegram bot...\n")
    print("   To stop: Press Ctrl+C")
    print("   Bot will run in foreground\n")
    print("=" * 60 + "\n")

    try:
        # Import and run bot
        from telegram_interface.bot import main as bot_main

        bot_main()
    except KeyboardInterrupt:
        print("\n✅ Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
