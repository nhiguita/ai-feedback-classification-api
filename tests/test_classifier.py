import json
from unittest.mock import MagicMock, patch

import httpx
import ollama
import pytest

from app.llm.errors import LLMInvalidOutputError, LLMTimeoutError, LLMUnavailableError
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


def test_classify_feedback_retries_once_after_invalid_output():
    llm = MagicMock()
    llm.chat_json.side_effect = ["not json", json.dumps(VALID)]
    result = classify_feedback("Something", llm=llm)
    assert result.priority == Priority.HIGH
    assert llm.chat_json.call_count == 2


@pytest.mark.parametrize(
    "bad_output",
    ["not json", json.dumps({**VALID, "priority": "urgent"}), json.dumps({**VALID, "extra": "x"}), "{}"],
)
def test_classify_feedback_raises_after_two_invalid_outputs(bad_output):
    llm = fake_llm(bad_output)
    with pytest.raises(LLMInvalidOutputError):
        classify_feedback("Something", llm=llm)
    assert llm.chat_json.call_count == 2


def test_classify_feedback_does_not_retry_transport_errors():
    llm = MagicMock()
    llm.chat_json.side_effect = LLMUnavailableError("down")
    with pytest.raises(LLMUnavailableError):
        classify_feedback("Something", llm=llm)
    llm.chat_json.assert_called_once()


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


@pytest.mark.parametrize(
    ("raised", "expected"),
    [
        (ConnectionError("Failed to connect to Ollama"), LLMUnavailableError),
        (httpx.ConnectError("refused"), LLMUnavailableError),
        (ollama.ResponseError("model 'qwen3:4b' not found", 404), LLMUnavailableError),
        (httpx.ReadTimeout("timed out"), LLMTimeoutError),
    ],
)
def test_ollama_client_maps_provider_errors(raised, expected):
    with patch("app.llm.ollama_client.ollama.Client") as client_cls:
        client_cls.return_value.chat.side_effect = raised
        client = OllamaClient(host="http://ollama:11434", model="qwen3:4b", timeout=5)
        with pytest.raises(expected):
            client.chat_json([{"role": "user", "content": "hi"}], {})
