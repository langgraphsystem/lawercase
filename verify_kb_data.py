"""Verify knowledge base data in Supabase via REST API."""

from __future__ import annotations

import os

from dotenv import load_dotenv
import requests

load_dotenv()


def verify_knowledge_base():
    """Check if knowledge base records exist in Supabase using REST API."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        print("❌ SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not found")
        return

    # Use mega_agent schema
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept-Profile": "mega_agent",  # Specify schema
    }

    # Count total records
    count_url = f"{url}/rest/v1/semantic_memory?select=record_id"
    resp = requests.get(count_url, headers={**headers, "Prefer": "count=exact"}, timeout=30)

    if resp.status_code != 200:
        print(f"❌ Ошибка при подсчёте: {resp.status_code} - {resp.text[:200]}")
        return

    total_count = resp.headers.get("content-range", "0/0").split("/")[-1]
    print(f"📊 Всего записей в semantic_memory: {total_count}")

    # Get records with knowledge_base tag
    kb_url = f"{url}/rest/v1/semantic_memory?select=record_id,tags,source,text&tags=cs.{{knowledge_base}}"
    resp = requests.get(kb_url, headers=headers, timeout=30)
    if resp.status_code == 200:
        kb_records = resp.json()
        print(f"📚 Записей с тегом 'knowledge_base': {len(kb_records)}")

        if kb_records:
            # Collect unique tags
            all_tags = set()
            sources = set()
            for record in kb_records[:50]:
                for tag in record.get("tags", []):
                    all_tags.add(tag)
                if record.get("source"):
                    sources.add(record["source"][:50])

            print("\n🏷️ Уникальные теги в knowledge_base:")
            for tag in sorted(all_tags):
                print(f"   • {tag}")

            if sources:
                print("\n📄 Источники:")
                for source in list(sources)[:5]:
                    print(f"   • {source}")

            # Preview
            print("\n📝 Примеры записей:")
            for i, record in enumerate(kb_records[:3], 1):
                text = record.get("text", "")[:150]
                source = record.get("source", "unknown")[:30]
                print(f"   {i}. [{source}] {text}...")

            if len(kb_records) >= 100:
                print(
                    f"\n✅ База знаний содержит {len(kb_records)} записей - данные успешно сохранены!"
                )
            else:
                print(f"\n⚠️ В базе знаний {len(kb_records)} записей")
        else:
            print("❌ Записей с тегом knowledge_base не найдено")
    else:
        print(f"❌ Ошибка API: {resp.status_code} - {resp.text[:200]}")


if __name__ == "__main__":
    verify_knowledge_base()
