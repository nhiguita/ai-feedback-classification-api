import logging
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.llm.base import LLMClient
from app.llm.errors import LLMInvalidOutputError
from app.llm.factory import get_llm_client
from app.priority.facts import FeedbackAnalysis
from app.priority.rules import decide_priority
from app.prompts import build_messages
from app.schemas import FeedbackClassification

logger = logging.getLogger(__name__)

# Structured output makes invalid JSON rare; one retry covers occasional glitches
# without doubling latency for every failure mode.
MAX_ATTEMPTS = 2

T = TypeVar("T", bound=BaseModel)


def request_validated(llm: LLMClient, messages: list[dict[str, str]], output_model: type[T]) -> T:
    """Ask the LLM for JSON matching output_model, retrying once if validation fails."""
    schema = output_model.model_json_schema()
    for attempt in range(1, MAX_ATTEMPTS + 1):
        raw = llm.chat_json(messages, schema)
        try:
            return output_model.model_validate_json(raw)
        except ValidationError as exc:
            logger.warning("Invalid LLM output (attempt %d/%d): %s", attempt, MAX_ATTEMPTS, exc)
            last_error = exc

    raise LLMInvalidOutputError(f"LLM output failed validation after {MAX_ATTEMPTS} attempts") from last_error


def analyze_feedback(text: str, llm: LLMClient | None = None) -> FeedbackAnalysis:
    return request_validated(llm or get_llm_client(), build_messages(text), FeedbackAnalysis)


def classify_feedback(text: str, llm: LLMClient | None = None) -> FeedbackClassification:
    analysis = analyze_feedback(text, llm)
    decision = decide_priority(analysis.facts)
    logger.info("Priority %s from facts %s", decision.priority.value, decision.reasons or "none")
    return FeedbackClassification(
        sentiment=analysis.sentiment,
        intent=analysis.intent,
        category=analysis.category,
        priority=decision.priority,
    )
