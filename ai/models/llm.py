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

from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel

from ai.config import AIConfigError, ModelConfig, ModelRole, SUPPORTED_PROVIDERS, _DEFAULT_MODELS


def _build_chat_model(config: ModelConfig) -> BaseChatModel:
    config.validate()

    if config.provider in ("openai", "openai_compatible", "nvidia", "nvidia_nim"):
        # NVIDIA NIM and most self-hosted providers expose an OpenAI-compatible
        # /v1/chat/completions API, so a single client class covers all of them.
        from langchain_openai import ChatOpenAI

        kwargs = dict(model=config.model, temperature=config.temperature)
        if config.api_key:
            kwargs["api_key"] = config.api_key
        if config.base_url:
            kwargs["base_url"] = config.base_url
        if config.timeout is not None:
            kwargs["timeout"] = config.timeout
        if config.max_retries is not None:
            kwargs["max_retries"] = config.max_retries
        return ChatOpenAI(**kwargs)

    if config.provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        kwargs = dict(model=config.model, temperature=config.temperature)
        if config.api_key:
            kwargs["api_key"] = config.api_key
        if config.base_url:
            kwargs["base_url"] = config.base_url
        if config.timeout is not None:
            kwargs["default_request_timeout"] = config.timeout
        if config.max_retries is not None:
            kwargs["max_retries"] = config.max_retries
        return ChatAnthropic(**kwargs)

    supported = ", ".join(SUPPORTED_PROVIDERS)
    raise AIConfigError(
        f"AI configuration error:\nUnknown AI_PROVIDER '{config.provider}'. Supported: {supported}."
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
