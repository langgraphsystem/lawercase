"""Simple test to verify OpenAI API connection and available models."""

from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv

from core.llm_interface.openai_client import OpenAIClient

load_dotenv()


async def test_basic_connection():
    """Test basic OpenAI API connection with available models."""
    print("\n" + "=" * 70)
    print("🔍 OpenAI API Connection Test")
    print("=" * 70)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not found in .env")
        return

    print(f"✅ API Key found: {api_key[:10]}...{api_key[-4:]}")
    print(f"📏 Key length: {len(api_key)} characters")
    print()

    # Test different models to see which ones work
    models_to_test = [
        ("GPT-5 (Primary)", "gpt-5"),
        ("GPT-5-mini (Balanced)", "gpt-5-mini"),
        ("GPT-5-nano (Economy)", "gpt-5-nano"),
        ("O3-mini (Reasoning)", "o3-mini"),
    ]

    test_prompt = "Say 'Hello' in one word."

    results = []

    for model_name, model_id in models_to_test:
        print(f"\n{'─'*70}")
        print(f"Testing: {model_name} ({model_id})")
        print(f"{'─'*70}")

        try:
            client = OpenAIClient(
                model=model_id, api_key=api_key, temperature=0.5, max_completion_tokens=10
            )

            result = await client.acomplete(test_prompt)

            if "error" in result:
                error_msg = result["error"]
                if "invalid_api_key" in str(error_msg):
                    print("❌ Invalid API key")
                    status = "INVALID_KEY"
                elif "model_not_found" in str(error_msg) or "does not exist" in str(error_msg):
                    print(f"⚠️  Model not available: {error_msg}")
                    status = "MODEL_NOT_FOUND"
                elif "insufficient_quota" in str(error_msg):
                    print("💰 Insufficient quota/credits")
                    status = "NO_CREDITS"
                else:
                    print(f"❌ Error: {error_msg}")
                    status = "ERROR"
            else:
                print("✅ Success!")
                print(f"   Response: {result['output']}")
                print(f"   Tokens: {result['usage']['total_tokens']}")
                status = "SUCCESS"

            results.append((model_name, model_id, status))

        except Exception as e:
            print(f"❌ Exception: {e}")
            results.append((model_name, model_id, "EXCEPTION"))

    # Summary
    print(f"\n{'='*70}")
    print("📊 Summary")
    print(f"{'='*70}")

    for model_name, model_id, status in results:
        emoji = {
            "SUCCESS": "✅",
            "INVALID_KEY": "🔑",
            "MODEL_NOT_FOUND": "❌",
            "NO_CREDITS": "💰",
            "ERROR": "❌",
            "EXCEPTION": "⚠️",
        }.get(status, "❓")

        print(f"{emoji} {model_name:30} {model_id:20} {status}")

    print()

    # Recommendations
    working_models = [m for m, _, s in results if s == "SUCCESS"]

    if working_models:
        print("✅ Working models found!")
        print("\n💡 You can use these models:")
        for model in working_models:
            print(f"   - {model}")
    else:
        print("❌ No working models found.")
        print("\n🔧 Troubleshooting:")
        print("   1. Check your API key at: https://platform.openai.com/api-keys")
        print("   2. Verify you have credits: https://platform.openai.com/usage")
        print("   3. Check API key permissions (should have access to Chat Completions)")
        print("   4. Try regenerating your API key if it's old")

    print()


if __name__ == "__main__":
    asyncio.run(test_basic_connection())
