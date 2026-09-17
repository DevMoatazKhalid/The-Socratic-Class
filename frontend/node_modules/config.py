"""
Centralized AI and LLM configuration module.

Handles environment loading, provider-specific settings, role-to-model
mappings, temperature overrides, timeout/retries, and validation.
Never exposes raw API keys in errors or string representations.
"""
from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Automatically load .env from project root if present
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"
if _ENV_PATH.is_file():
    load_dotenv(dotenv_path=_ENV_PATH)
else:
    load_dotenv()


class ModelRole(str, Enum):
    """Logical roles a model plays across the AI Coach architecture."""

    COACH = "COACH"              # student-facing tutoring / response generation
    REASONING = "REASONING"      # diagnosis / misconception analysis
    LIGHTWEIGHT = "LIGHTWEIGHT"  # intervention routing, validation, cheap tasks
    VERIFICATION = "VERIFICATION"  # evaluating learning-verification answers


SUPPORTED_PROVIDERS = (
    "openai",
    "openai_compatible",
    "nvidia",
    "nvidia_nim",
    "anthropic",
)

PROVIDERS_REQUIRING_BASE_URL = (
    "openai_compatible",
    "nvidia",
    "nvidia_nim",
)

_DEFAULT_MODELS: dict[ModelRole, str] = {
    ModelRole.COACH: "gpt-4o-mini",
    ModelRole.REASONING: "gpt-4o-mini",
    ModelRole.LIGHTWEIGHT: "gpt-4o-mini",
    ModelRole.VERIFICATION: "gpt-4o-mini",
}

_PROVIDER_DEFAULT_FALLBACKS: dict[str, str] = {
    "openai": "gpt-4o-mini",
    "openai_compatible": "gpt-4o-mini",
    "nvidia": "meta/llama-3.1-8b-instruct",
    "nvidia_nim": "meta/llama-3.1-8b-instruct",
    "anthropic": "claude-3-5-haiku-20241022",
}


class AIConfigError(ValueError):
    """Raised when AI configuration is invalid or missing required values."""
    pass


def _get_clean_env(name: str) -> Optional[str]:
    """Retrieve environment variable, stripped, or None if empty/unset."""
    val = os.getenv(name)
    if val is None:
        return None
    val = val.strip()
    return val if val else None


def _mask_secret(secret: Optional[str]) -> str:
    """Safely indicate whether a secret is configured without printing its value."""
    if not secret:
        return "[NOT SET]"
    return "[CONFIGURED]"


class ModelConfig:
    """Reads role -> provider/model/temperature/timeouts from environment and validates.

    Env vars:
        AI_PROVIDER                "openai" | "openai_compatible" | "nvidia" | "nvidia_nim" | "anthropic"
        AI_API_KEY                 shared API key
        AI_BASE_URL                base URL (required for openai_compatible, nvidia, nvidia_nim)
        AI_MODEL_DEFAULT           fallback model name across all roles
        AI_MODEL_<ROLE>            role-specific model override (e.g. AI_MODEL_COACH)
        AI_TEMPERATURE_DEFAULT     fallback temperature across roles
        AI_TEMPERATURE_<ROLE>      role-specific temperature override (e.g. AI_TEMPERATURE_REASONING)
        AI_TIMEOUT                 request timeout in seconds
        AI_MAX_RETRIES             maximum request retries
    """

    def __init__(self, role: ModelRole = ModelRole.COACH):
        self.role = role
        raw_provider = _get_clean_env("AI_PROVIDER") or "openai"
        self.provider = raw_provider.lower()
        self.api_key = _get_clean_env("AI_API_KEY")
        self.base_url = _get_clean_env("AI_BASE_URL")

        # Model resolution: AI_MODEL_<ROLE> -> AI_MODEL_DEFAULT -> provider default -> role default
        provider_fallback = _PROVIDER_DEFAULT_FALLBACKS.get(self.provider, _DEFAULT_MODELS[role])
        default_model = _get_clean_env("AI_MODEL_DEFAULT") or provider_fallback
        self.model = _get_clean_env(f"AI_MODEL_{role.value}") or default_model

        # Temperature resolution: AI_TEMPERATURE_<ROLE> -> AI_TEMPERATURE_DEFAULT -> role default
        default_temp = "0.2" if role == ModelRole.REASONING else "0.5"
        raw_temp = _get_clean_env(f"AI_TEMPERATURE_{role.value}") or _get_clean_env("AI_TEMPERATURE_DEFAULT") or default_temp
        try:
            self.temperature = float(raw_temp)
        except (ValueError, TypeError) as exc:
            raise AIConfigError(
                f"AI configuration error:\nInvalid temperature value '{raw_temp}'. Must be a valid float."
            ) from exc

        # Timeout & retries
        raw_timeout = _get_clean_env("AI_TIMEOUT")
        if raw_timeout is not None:
            try:
                self.timeout = float(raw_timeout)
            except ValueError as exc:
                raise AIConfigError(
                    f"AI configuration error:\nInvalid AI_TIMEOUT value '{raw_timeout}'. Must be a number."
                ) from exc
        else:
            self.timeout = 60.0

        raw_retries = _get_clean_env("AI_MAX_RETRIES")
        if raw_retries is not None:
            try:
                self.max_retries = int(raw_retries)
            except ValueError as exc:
                raise AIConfigError(
                    f"AI configuration error:\nInvalid AI_MAX_RETRIES value '{raw_retries}'. Must be an integer."
                ) from exc
        else:
            self.max_retries = 2

    def validate(self) -> None:
        """Validate the configuration for active execution.

        Raises clean AIConfigError if mandatory variables are missing.
        Never formats secrets into error messages.
        """
        if self.provider not in SUPPORTED_PROVIDERS:
            supported = ", ".join(SUPPORTED_PROVIDERS)
            raise AIConfigError(
                f"AI configuration error:\nUnknown AI_PROVIDER '{self.provider}'. Supported: {supported}."
            )

        if not self.api_key:
            raise AIConfigError(
                f"AI configuration error:\nAI_API_KEY is required when AI_PROVIDER={self.provider}"
            )

        if self.provider in PROVIDERS_REQUIRING_BASE_URL and not self.base_url:
            raise AIConfigError(
                f"AI configuration error:\nAI_BASE_URL is required when AI_PROVIDER={self.provider}"
            )

    def __repr__(self) -> str:
        return (
            f"ModelConfig(role={self.role.value}, provider='{self.provider}', "
            f"model='{self.model}', temperature={self.temperature}, "
            f"api_key={_mask_secret(self.api_key)}, base_url={self.base_url!r}, "
            f"timeout={self.timeout}, max_retries={self.max_retries})"
        )

    def __str__(self) -> str:
        return (
            f"Role: {self.role.value} | Provider: {self.provider} | Model: {self.model} | "
            f"API Key: {_mask_secret(self.api_key)} | Base URL: {self.base_url or '[None]'}"
        )


def validate_ai_config(role: ModelRole = ModelRole.COACH) -> ModelConfig:
    """Convenience helper to inspect and validate configuration for a role.

    Returns the valid ModelConfig or raises AIConfigError.
    """
    config = ModelConfig(role)
    config.validate()
    return config
