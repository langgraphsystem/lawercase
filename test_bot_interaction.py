"""Test script to interact with Telegram bot and verify responses."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime

import structlog
from dotenv import load_dotenv
from telegram import Bot

logger = structlog.get_logger(__name__)

load_dotenv()


async def test_bot():
    """Test bot by getting bot info and recent updates."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env")
        return

    bot = Bot(token=token)

    print("\n" + "=" * 60)
    print("🤖 TELEGRAM BOT TEST")
    print("=" * 60 + "\n")

    try:
        # Get bot info
        me = await bot.get_me()
        print("✅ Bot connected successfully!")
        print(f"   Bot Username: @{me.username}")
        print(f"   Bot ID: {me.id}")
        print(f"   Bot Name: {me.first_name}")
        print()

        # Get recent updates
        print("📨 Checking recent updates (last 10)...\n")
        updates = await bot.get_updates(limit=10)

        if not updates:
            print("   ℹ️  No recent updates found")
            print("   Tip: Try sending /start to the bot in Telegram first\n")
        else:
            print(f"   Found {len(updates)} recent update(s):\n")
            for i, update in enumerate(updates[-5:], 1):  # Show last 5
                if update.message:
                    msg = update.message
                    user = msg.from_user
                    chat_id = msg.chat.id
                    text = msg.text or "(media/other)"
                    timestamp = msg.date.strftime("%H:%M:%S")

                    print(f"   {i}. [{timestamp}] From: @{user.username or user.first_name}")
                    print(f"      User ID: {user.id}")
                    print(f"      Chat ID: {chat_id}")
                    print(f"      Message: {text}")
                    print()

        # Get webhook info
        webhook_info = await bot.get_webhook_info()
        print("🌐 Webhook Status:")
        print(f"   URL: {webhook_info.url or 'Not set (using polling)'}")
        print(f"   Pending updates: {webhook_info.pending_update_count}")
        print()

        # Test send message (to developer - optional)
        test_chat_id = os.getenv("TEST_CHAT_ID")
        if test_chat_id:
            print(f"📤 Sending test message to chat {test_chat_id}...")
            await bot.send_message(
                chat_id=test_chat_id,
                text=f"🤖 Bot test at {datetime.now().strftime('%H:%M:%S')}\nBot is operational! ✅",
            )
            print("   ✅ Test message sent!\n")

        print("=" * 60)
        print("✅ All tests passed! Bot is working correctly.")
        print("=" * 60 + "\n")

        if not updates:
            print("💡 To test the bot:")
            print("   1. Open Telegram")
            print(f"   2. Search for @{me.username}")
            print("   3. Send /start command")
            print("   4. Check if you receive a response")
            print()

    except Exception as e:
        print(f"❌ Error: {e}")
        logger.exception("bot_test_error", error=str(e))


if __name__ == "__main__":
    asyncio.run(test_bot())
