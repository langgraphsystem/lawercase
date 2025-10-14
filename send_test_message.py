"""Send a test message directly via Telegram API."""

from __future__ import annotations

import asyncio

import httpx

BOT_TOKEN = "7472625853:AAGPl30wtI9g57VqYIAO4H2WyXnrZgk4scA"  # pragma: allowlist secret  # nosec
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


async def get_chat_id():
    """Get updates to find chat_id."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/getUpdates", params={"limit": 10})
        data = response.json()

        if data.get("ok") and data.get("result"):
            updates = data["result"]
            print(f"Found {len(updates)} updates:\n")

            for update in updates:
                message = update.get("message", {})
                chat = message.get("chat", {})
                user = message.get("from", {})
                text = message.get("text", "")

                print(f"Update ID: {update.get('update_id')}")
                print(f"Chat ID: {chat.get('id')}")
                print(f"User: {user.get('first_name')} (@{user.get('username')})")
                print(f"Message: {text}")
                print("-" * 50)

            return updates[-1].get("message", {}).get("chat", {}).get("id")
        else:
            print("No updates found or error:", data)
            return None


async def send_message(chat_id: int, text: str):
    """Send a message to a specific chat."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
        )
        data = response.json()

        if data.get("ok"):
            print(f"✅ Message sent successfully to chat {chat_id}")
            return True
        else:
            print(f"❌ Failed to send message: {data.get('description')}")
            return False


async def main():
    print("=" * 60)
    print("Telegram Bot - Message Test")
    print("=" * 60)

    # Get chat ID from recent updates
    print("\n1. Getting recent updates to find chat_id...")
    chat_id = await get_chat_id()

    if chat_id:
        print(f"\n2. Sending test message to chat {chat_id}...")
        test_message = """
🤖 **Test Message from Bot**

This is an automated test to verify bot functionality.

Bot is running: ✅
API connection: ✅
Message sending: ✅

Try sending: /start
        """
        await send_message(chat_id, test_message)
    else:
        print("\n❌ No chat_id found. Please send any message to the bot first.")
        print("   1. Open Telegram")
        print("   2. Find @lawercasebot")
        print("   3. Send /start")
        print("   4. Run this script again")


if __name__ == "__main__":
    asyncio.run(main())
