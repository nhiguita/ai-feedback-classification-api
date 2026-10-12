import json
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from app.llm.ollama_client import OllamaClient
from app.schemas import Category, FeedbackClassification, Intent, Priority, Sentiment
from app.services.classifier import classify_feedback

VALID = {"sentiment": "negative", "intent": "report_issue", "category": "technical_issue", "priority": "high"}


def fake_llm(content: str) -> MagicMock:
    llm = MagicMock()
    llm.chat_json.return_value = content
    return llm


def test_classify_feedback_parses_llm_json():
    llm = fake_llm(json.dumps(VALID))
    result = classify_feedback("The application crashes when I upload reports.", llm=llm)
    assert result == FeedbackClassification(
        sentiment=Sentiment.NEGATIVE, intent=Intent.REPORT_ISSUE, category=Category.TECHNICAL_ISSUE, priority=Priority.HIGH
    )


def test_classify_feedback_sends_prompt_and_schema():
    llm = fake_llm(json.dumps(VALID))
    classify_feedback("Login is broken.", llm=llm)
    messages, schema = llm.chat_json.call_args.args
    assert messages[0]["role"] == "system"
    assert "Login is broken." in messages[-1]["content"]
    assert schema == FeedbackClassification.model_json_schema()


def test_classify_feedback_uses_default_client_when_none_given():
    llm = fake_llm(json.dumps(VALID))
    with patch("app.services.classifier.get_llm_client", return_value=llm):
        classify_feedback("Nice app")
    llm.chat_json.assert_called_once()


def test_classify_feedback_rejects_invalid_llm_output():
    llm = fake_llm(json.dumps({**VALID, "priority": "urgent"}))
    with pytest.raises(ValidationError):
        classify_feedback("Something", llm=llm)


def test_ollama_client_calls_chat_with_structured_output():
    with patch("app.llm.ollama_client.ollama.Client") as client_cls:
        client_cls.return_value.chat.return_value.message.content = json.dumps(VALID)
        client = OllamaClient(host="http://ollama:11434", model="qwen3:4b", timeout=5)
        schema = FeedbackClassification.model_json_schema()
        content = client.chat_json([{"role": "user", "content": "hi"}], schema)

    assert content == json.dumps(VALID)
    client_cls.assert_called_once_with(host="http://ollama:11434", timeout=5)
    kwargs = client_cls.return_value.chat.call_args.kwargs
    assert kwargs["model"] == "qwen3:4b"
    assert kwargs["format"] == schema
    assert kwargs["think"] is False
    assert kwargs["options"] == {"temperature": 0}
