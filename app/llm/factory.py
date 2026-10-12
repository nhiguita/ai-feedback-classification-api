from functools import lru_cache

from app.config import get_settings
from app.llm.base import LLMClient
from app.llm.ollama_client import OllamaClient


@lru_cache
def get_llm_client() -> LLMClient:
    settings = get_settings()
    return OllamaClient(
        host=settings.ollama_host,
        model=settings.ollama_model,
        timeout=settings.llm_timeout_seconds,
    )
