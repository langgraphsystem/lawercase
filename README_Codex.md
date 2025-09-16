# mega_agent_pro — Codex Handoff Package
Generated: 2025-09-16T08:15:39.465708Z

This package contains **specifications, tasks, configs, and examples** for an AI code generator (Codex-like)
to produce a production-ready implementation of the *mega_agent_pro* multi-agent system.

## Contents
- `codex_spec.json` — authoritative, machine-readable spec of every key file, public API, commands, and dependencies.
- `requirements.txt` — pinned core dependencies to bootstrap environment.
- `pyproject.toml` — base project metadata and tool config.
- `.env.example` — environment variables the project expects.
- `samples/telegram_commands.md` — examples of Telegram commands and expected behaviors.
- `samples/prompts/*` — seed prompts for RAG/KAG flows and writing.
- `tests_checklist.md` — acceptance criteria and test coverage blueprint.

**Note**: This handoff emphasizes:
- Pydantic v2 (`model_validate`, `model_dump`)
- LangGraph / LangGraph Plus patterns (StateGraph, conditional routers, fan-out/fan-in, checkpointers, interrupts)
- Centralized auditing (`memory_manager.log_audit`), role-based access, tenacity retries
- RAG models (OpenAI, Anthropic, DeepSeek, Gemini, Mistral, HF), **Gemini embeddings** and hybrid retrieval
- File ingestion and parsers (PDF/DOCX/HTML/MD/TXT/Images w/ OCR)

The code generator should implement **interfaces first**, then fill adapters per provider incrementally.
