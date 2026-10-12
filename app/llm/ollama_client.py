from typing import Any

import httpx
import ollama

from app.llm.errors import LLMTimeoutError, LLMUnavailableError


class OllamaClient:
    def __init__(self, host: str, model: str, timeout: float):
        self._client = ollama.Client(host=host, timeout=timeout)
        self._model = model

    def chat_json(self, messages: list[dict[str, str]], schema: dict[str, Any]) -> str:
        # Translate Ollama/httpx exceptions so callers never depend on the provider.
        try:
            response = self._client.chat(
                model=self._model,
                messages=messages,
                format=schema,  # Structured output constrained to the JSON schema.
                think=False,  # Qwen3 reasoning adds latency and is not needed for classification.
                options={"temperature": 0},
            )
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"Ollama did not respond in time: {exc}") from exc
        except (ConnectionError, httpx.TransportError) as exc:
            raise LLMUnavailableError(f"Cannot reach Ollama: {exc}") from exc
        except ollama.ResponseError as exc:
            raise LLMUnavailableError(f"Ollama returned {exc.status_code}: {exc.error}") from exc
        return response.message.content
