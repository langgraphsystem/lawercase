from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def check_key(name):
    val = os.getenv(name)
    if val:
        print(f"{name}: Found (starts with {val[:15]}...)")
    else:
        print(f"{name}: NOT FOUND")


print("Checking Environment Variables:")
check_key("OPENAI_API_KEY")
check_key("SUPABASE_URL")
check_key("SUPABASE_SERVICE_ROLE_KEY")
check_key("SUPABASE_VECTOR_URL")
