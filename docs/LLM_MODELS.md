# LLM Model IDs (OpenAI / Anthropic / Google)

This project supports OpenAI, Anthropic, and Google Gemini providers.

Because model IDs change over time, the recommended way to get an up-to-date list is to query the providers’ official APIs.

## List models (official APIs)

From the repo root:

```bash
python scripts/list_llm_models.py
python scripts/list_llm_models.py --json
```

Required environment variables:

- OpenAI: `OPENAI_API_KEY` (optional override: `OPENAI_MODEL`)
- Anthropic: `ANTHROPIC_API_KEY` (optional override: `ANTHROPIC_MODEL`)
- Gemini: `GEMINI_API_KEY` or `GOOGLE_API_KEY` (optional override: `GEMINI_MODEL` / `GOOGLE_MODEL`)

Notes:

- If a key is missing or invalid, the script prints an error for that provider.
- Network access may be blocked in some sandboxes; run outside the sandbox or with network permissions enabled.

