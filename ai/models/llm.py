"""
Model/provider abstraction.

Nothing in ai/agents or ai/prompts should import a concrete LangChain chat
model class directly. Everything goes through `get_llm(role)` /
`get_structured_llm(role, schema)`.

Configuration is entirely through environment variables so the Coach can be
pointed at OpenAI-compatible endpoints (including NVIDIA NIM), Anthropic, or
a local server without code changes.
"""
from __future__ import annotations

import os
from enum import Enum
from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel


class ModelRole(str, Enum):
    """Logical role a model plays. Each role can be configured independently
    so, e.g., a cheap model can handle routing while a stronger model handles
    diagnosis. See section 6 of docs/AI_SPEC.md."""

    COACH = "COACH"              # student-facing tutoring / response generation
    REASONING = "REASONING"      # diagnosis / misconception analysis
    LIGHTWEIGHT = "LIGHTWEIGHT"  # intervention routing, validation, cheap tasks
    VERIFICATION = "VERIFICATION"  # evaluating learning-verification answers


_DEFAULT_MODELS = {
    ModelRole.COACH: "gpt-4o-mini",
    ModelRole.REASONING: "gpt-4o-mini",
    ModelRole.LIGHTWEIGHT: "gpt-4o-mini",
    ModelRole.VERIFICATION: "gpt-4o-mini",
}


class ModelConfig:
    """Reads role -> provider/model/temperature config from the environment.

    Env vars:
        AI_PROVIDER                "openai" | "openai_compatible" | "nvidia" | "anthropic"
        AI_API_KEY                 shared API key (role-specific override not needed for MVP)
        AI_BASE_URL                required for openai_compatible / NVIDIA NIM endpoints
        AI_MODEL_<ROLE>            e.g. AI_MODEL_REASONING, falls back to AI_MODEL_DEFAULT
        AI_TEMPERATURE_<ROLE>      e.g. AI_TEMPERATURE_REASONING, falls back to AI_TEMPERATURE_DEFAULT
    """

    def __init__(self, role: ModelRole):
        self.role = role
        self.provider = os.getenv("AI_PROVIDER", "openai").lower()
        self.api_key = os.getenv("AI_API_KEY")
        self.base_url = os.getenv("AI_BASE_URL")
        self.model = os.getenv(f"AI_MODEL_{role.value}") or os.getenv(
            "AI_MODEL_DEFAULT", _DEFAULT_MODELS[role]
        )
        temp_default = "0.2" if role == ModelRole.REASONING else "0.5"
        self.temperature = float(
            os.getenv(f"AI_TEMPERATURE_{role.value}", os.getenv("AI_TEMPERATURE_DEFAULT", temp_default))
        )


def _build_chat_model(config: ModelConfig) -> BaseChatModel:
    if config.provider in ("openai", "openai_compatible", "nvidia", "nvidia_nim"):
        # NVIDIA NIM and most self-hosted providers expose an OpenAI-compatible
        # /v1/chat/completions API, so a single client class covers all of them.
        from langchain_openai import ChatOpenAI

        kwargs = dict(model=config.model, temperature=config.temperature)
        if config.api_key:
            kwargs["api_key"] = config.api_key
        if config.base_url:
            kwargs["base_url"] = config.base_url
        return ChatOpenAI(**kwargs)

    if config.provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        kwargs = dict(model=config.model, temperature=config.temperature)
        if config.api_key:
            kwargs["api_key"] = config.api_key
        return ChatAnthropic(**kwargs)

    raise ValueError(
        f"Unknown AI_PROVIDER '{config.provider}'. Supported: openai, "
        "openai_compatible, nvidia, anthropic."
    )


@lru_cache(maxsize=None)
def get_llm(role: ModelRole = ModelRole.COACH) -> BaseChatModel:
    """Return a cached chat model instance for the given logical role."""
    config = ModelConfig(role)
    return _build_chat_model(config)


def get_structured_llm(role: ModelRole, schema):
    """Convenience: chat model bound to a Pydantic schema via
    `with_structured_output`. Callers should still wrap invocation with
    error handling -- see ai/agents/coach/nodes.py."""
    return get_llm(role).with_structured_output(schema)


def clear_llm_cache() -> None:
    """Test/dev helper to reset cached model instances."""
    get_llm.cache_clear()
