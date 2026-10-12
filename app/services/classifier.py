import logging

from pydantic import ValidationError

from app.llm.base import LLMClient
from app.llm.errors import LLMInvalidOutputError
from app.llm.factory import get_llm_client
from app.prompts import build_messages
from app.schemas import FeedbackClassification

logger = logging.getLogger(__name__)

# Structured output makes invalid JSON rare; one retry covers occasional glitches
# without doubling latency for every failure mode.
MAX_ATTEMPTS = 2


def classify_feedback(text: str, llm: LLMClient | None = None) -> FeedbackClassification:
    llm = llm or get_llm_client()
    messages = build_messages(text)
    schema = FeedbackClassification.model_json_schema()

    for attempt in range(1, MAX_ATTEMPTS + 1):
        raw = llm.chat_json(messages, schema)
        try:
            return FeedbackClassification.model_validate_json(raw)
        except ValidationError as exc:
            logger.warning("Invalid LLM output (attempt %d/%d): %s", attempt, MAX_ATTEMPTS, exc)
            last_error = exc

    raise LLMInvalidOutputError(f"LLM output failed validation after {MAX_ATTEMPTS} attempts") from last_error
