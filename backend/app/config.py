"""Application configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv(override=True)


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_llm_model() -> str:
    return get_required_env("LLM_MODEL")


def get_groq_api_key() -> str:
    return get_required_env("GROQ_API_KEY")
