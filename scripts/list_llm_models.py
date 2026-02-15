from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any
import warnings

import httpx

# Some environments emit a FutureWarning on import; keep output clean.
warnings.filterwarnings("ignore", category=FutureWarning)


def _print_section(title: str) -> None:
    print()
    print("=" * len(title))
    print(title)
    print("=" * len(title))


def _list_openai_models() -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"ok": False, "error": "OPENAI_API_KEY not set"}

    url = "https://api.openai.com/v1/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        with httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
            resp = client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        return {"ok": False, "error": str(exc)}
    if resp.status_code >= 400:
        return {"ok": False, "status_code": resp.status_code, "error": resp.text}
    data = resp.json().get("data", [])
    ids = sorted([m.get("id") for m in data if isinstance(m, dict) and m.get("id")])
    return {"ok": True, "models": ids}


def _list_anthropic_models() -> dict[str, Any]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {"ok": False, "error": "ANTHROPIC_API_KEY not set"}

    url = "https://api.anthropic.com/v1/models"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    try:
        with httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
            resp = client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        return {"ok": False, "error": str(exc)}
    if resp.status_code >= 400:
        return {"ok": False, "status_code": resp.status_code, "error": resp.text}
    data = resp.json().get("data", [])
    ids = sorted([m.get("id") for m in data if isinstance(m, dict) and m.get("id")])
    return {"ok": True, "models": ids}


def _list_gemini_models_rest() -> dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return {"ok": False, "error": "GEMINI_API_KEY/GOOGLE_API_KEY not set"}

    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        with httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
            resp = client.get(url)
    except httpx.HTTPError as exc:
        return {"ok": False, "error": str(exc)}
    if resp.status_code >= 400:
        return {"ok": False, "status_code": resp.status_code, "error": resp.text}

    models = resp.json().get("models", [])
    names = []
    for model in models:
        if not isinstance(model, dict):
            continue
        name = model.get("name")
        if isinstance(name, str) and name.startswith("models/"):
            names.append(name.removeprefix("models/"))
        elif isinstance(name, str):
            names.append(name)
    return {"ok": True, "models": sorted(set(names))}


def _list_gemini_models() -> dict[str, Any]:
    # Prefer python SDK if available, otherwise use REST.
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=FutureWarning)
            import google.generativeai as genai
    except Exception:
        return _list_gemini_models_rest()

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return {"ok": False, "error": "GEMINI_API_KEY/GOOGLE_API_KEY not set"}

    genai.configure(api_key=api_key)
    names = []
    for model in genai.list_models():
        name = getattr(model, "name", None)
        if isinstance(name, str) and name.startswith("models/"):
            names.append(name.removeprefix("models/"))
        elif isinstance(name, str):
            names.append(name)
    return {"ok": True, "models": sorted(set(names))}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="List available LLM models from providers.")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args(argv)

    results = {
        "openai": _list_openai_models(),
        "anthropic": _list_anthropic_models(),
        "google_gemini": _list_gemini_models(),
    }

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    for provider, payload in results.items():
        _print_section(provider)
        if not payload.get("ok"):
            print(payload.get("error") or payload)
            continue
        models = payload.get("models") or []
        for model_id in models:
            print(model_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
