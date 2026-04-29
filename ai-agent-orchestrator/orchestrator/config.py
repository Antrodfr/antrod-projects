"""Environment-based configuration for LLM providers."""

from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()

MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
DEFAULT_PROVIDER: str = os.getenv("DEFAULT_PROVIDER", "mistral")
DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "mistral-small-latest")

PROVIDER_DEFAULTS: dict[str, str] = {
    "mistral": "mistral-small-latest",
    "openai": "gpt-4o-mini",
}


def get_api_key(provider: str) -> str:
    """Return the API key for the given provider, or raise if missing."""
    key = MISTRAL_API_KEY if provider == "mistral" else OPENAI_API_KEY
    if not key:
        raise ValueError(
            f"No API key found for '{provider}'. "
            f"Set {'MISTRAL_API_KEY' if provider == 'mistral' else 'OPENAI_API_KEY'} in your environment."
        )
    return key
