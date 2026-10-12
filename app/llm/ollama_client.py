from typing import Any

import ollama


class OllamaClient:
    def __init__(self, host: str, model: str, timeout: float):
        self._client = ollama.Client(host=host, timeout=timeout)
        self._model = model

    def chat_json(self, messages: list[dict[str, str]], schema: dict[str, Any]) -> str:
        response = self._client.chat(
            model=self._model,
            messages=messages,
            format=schema,  # Structured output constrained to the JSON schema.
            think=False,  # Qwen3 reasoning adds latency and is not needed for classification.
            options={"temperature": 0},
        )
        return response.message.content
