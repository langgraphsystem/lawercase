"""Test script for Telegram bot functionality."""

from __future__ import annotations

import asyncio

import httpx
import structlog

logger = structlog.get_logger(__name__)

BOT_TOKEN = "7472625853:AAGPl30wtI9g57VqYIAO4H2WyXnrZgk4scA"  # pragma: allowlist secret  # nosec
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


async def test_bot_info():
    """Test getting bot information."""
    print("🤖 Testing bot connection...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/getMe")
        data = response.json()

        if data.get("ok"):
            bot_info = data["result"]
            print("✅ Bot is active!")
            print(f"   Username: @{bot_info.get('username')}")
            print(f"   Name: {bot_info.get('first_name')}")
            print(f"   ID: {bot_info.get('id')}")
            return True
        else:
            print(f"❌ Failed to get bot info: {data.get('description')}")
            return False


async def test_webhook_info():
    """Test webhook configuration."""
    print("\n🔗 Checking webhook...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/getWebhookInfo")
        data = response.json()

        if data.get("ok"):
            webhook = data["result"]
            if webhook.get("url"):
                print(f"   Webhook URL: {webhook['url']}")
            else:
                print("   Webhook: Not configured (using polling)")
            print(f"   Pending updates: {webhook.get('pending_update_count', 0)}")
            return True
        return False


async def test_commands():
    """Test setting bot commands."""
    print("\n📋 Setting bot commands...")

    commands = [
        {"command": "start", "description": "Начать работу с ботом"},
        {"command": "help", "description": "Показать справку"},
        {"command": "ask", "description": "Задать вопрос агенту"},
        {"command": "case_get", "description": "Получить информацию о деле"},
        {"command": "memory_lookup", "description": "Поиск в памяти"},
        {"command": "generate_letter", "description": "Сгенерировать письмо"},
    ]

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/setMyCommands", json={"commands": commands})
        data = response.json()

        if data.get("ok"):
            print("✅ Commands set successfully!")
            for cmd in commands:
                print(f"   /{cmd['command']} - {cmd['description']}")
            return True
        else:
            print(f"❌ Failed to set commands: {data.get('description')}")
            return False


async def get_updates():
    """Get recent updates from bot."""
    print("\n📬 Checking recent updates...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/getUpdates", params={"limit": 5})
        data = response.json()

        if data.get("ok"):
            updates = data["result"]
            if updates:
                print(f"✅ Found {len(updates)} recent updates")
                for update in updates:
                    message = update.get("message", {})
                    text = message.get("text", "")
                    user = message.get("from", {})
                    print(f"   - {user.get('first_name')}: {text}")
            else:
                print("   No recent messages")
            return True
        return False


async def send_test_message(chat_id: int):
    """Send a test message to a chat."""
    print(f"\n💬 Sending test message to chat {chat_id}...")

    test_text = """
🤖 *MegaAgent Pro Bot - Test Message*

Бот успешно настроен и готов к работе!

Доступные команды:
• /start - Начать работу
• /help - Показать справку
• /ask - Задать вопрос

Для проверки работы напишите /start
    """

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/sendMessage",
            json={"chat_id": chat_id, "text": test_text, "parse_mode": "Markdown"},
        )
        data = response.json()

        if data.get("ok"):
            print("✅ Test message sent!")
            return True
        else:
            print(f"❌ Failed to send: {data.get('description')}")
            return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("🧪 Telegram Bot Testing Suite")
    print("=" * 60)

    # Test 1: Bot connection
    if not await test_bot_info():
        print("\n❌ Bot connection failed. Check your token!")
        return

    # Test 2: Webhook info
    await test_webhook_info()

    # Test 3: Set commands
    await test_commands()

    # Test 4: Get updates
    await get_updates()

    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)

    print("\n📝 Next steps:")
    print("1. Start the bot: python -m telegram_interface.bot")
    print("2. Open Telegram and find your bot")
    print("3. Send /start to begin")
    print("4. Test all commands:")
    print("   - /ask Что такое виза H-1B?")
    print("   - /case_get CASE-001")
    print("   - /memory_lookup иммиграция")
    print("   - /generate_letter Запрос документов")


if __name__ == "__main__":
    asyncio.run(main())
