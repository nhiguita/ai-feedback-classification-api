from app.llm.base import LLMClient
from app.llm.factory import get_llm_client
from app.prompts import build_messages
from app.schemas import FeedbackClassification


def classify_feedback(text: str, llm: LLMClient | None = None) -> FeedbackClassification:
    llm = llm or get_llm_client()
    raw = llm.chat_json(build_messages(text), FeedbackClassification.model_json_schema())
    return FeedbackClassification.model_validate_json(raw)
