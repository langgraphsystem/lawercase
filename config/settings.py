from __future__ import annotations

import json
from functools import lru_cache
from typing import Dict, List, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProviderBudget(BaseModel):
    """Budget guardrails per LLM provider."""

    name: str
    max_tokens: Optional[int] = Field(default=None, ge=0)
    max_cost_usd: Optional[float] = Field(default=None, ge=0.0)


class RouterSettings(BaseModel):
    """Normalized router configuration."""

    default_provider: str = "openai"
    provider_priority: List[str] = Field(default_factory=lambda: ["openai", "anthropic", "gemini"])
    max_retries: int = 3
    initial_backoff_seconds: float = 0.3
    backoff_multiplier: float = 2.0
    jitter_seconds: float = 0.2
    request_timeout_seconds: float = 30.0


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    router_default_provider: str = Field("openai", alias="LLM_DEFAULT_PROVIDER")
    router_provider_priority: List[str] = Field(default_factory=lambda: ["openai", "anthropic", "gemini"], alias="LLM_PROVIDER_PRIORITY")
    router_max_retries: int = Field(3, alias="LLM_MAX_RETRIES")
    router_initial_backoff: float = Field(0.3, alias="LLM_BACKOFF_INITIAL")
    router_backoff_multiplier: float = Field(2.0, alias="LLM_BACKOFF_MULTIPLIER")
    router_jitter_seconds: float = Field(0.2, alias="LLM_BACKOFF_JITTER")
    router_request_timeout_seconds: float = Field(30.0, alias="LLM_REQUEST_TIMEOUT")

    llm_provider_budgets: Optional[str] = Field(default=None, alias="LLM_PROVIDER_BUDGETS")

    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")

    prometheus_namespace: str = Field("mega_agent_pro", alias="PROMETHEUS_NAMESPACE")

    def router_settings(self) -> RouterSettings:
        return RouterSettings(
            default_provider=self.router_default_provider,
            provider_priority=self.router_provider_priority,
            max_retries=self.router_max_retries,
            initial_backoff_seconds=self.router_initial_backoff,
            backoff_multiplier=self.router_backoff_multiplier,
            jitter_seconds=self.router_jitter_seconds,
            request_timeout_seconds=self.router_request_timeout_seconds,
        )

    def provider_budgets(self) -> Dict[str, ProviderBudget]:
        if not self.llm_provider_budgets:
            return {}
        raw = json.loads(self.llm_provider_budgets)
        budgets: Dict[str, ProviderBudget] = {}
        for provider_name, payload in raw.items():
            payload["name"] = payload.get("name", provider_name)
            budgets[provider_name] = ProviderBudget.model_validate(payload)
        return budgets


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
