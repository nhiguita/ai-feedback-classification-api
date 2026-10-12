from typing import Any, Protocol


class LLMClient(Protocol):
    """Provider-agnostic interface: return the raw JSON text produced by the model."""

    def chat_json(self, messages: list[dict[str, str]], schema: dict[str, Any]) -> str: ...
