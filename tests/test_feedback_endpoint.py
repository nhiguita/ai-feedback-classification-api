from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.llm.errors import LLMError, LLMInvalidOutputError, LLMTimeoutError, LLMUnavailableError
from app.main import app
from app.schemas import FeedbackClassification

client = TestClient(app)
URL = "/api/v1/feedback/analyze"
FAKE = {"sentiment": "negative", "intent": "report_issue", "category": "technical_issue", "priority": "high"}


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_returns_classifier_result():
    with patch("app.services.classifier.classify_feedback", return_value=FeedbackClassification(**FAKE)) as mock:
        response = client.post(URL, json={"text": "  The application crashes when I upload reports.  "})
    assert response.status_code == 200
    assert response.json() == FAKE
    mock.assert_called_once_with("The application crashes when I upload reports.")


def test_analyze_rejects_missing_text():
    assert client.post(URL, json={}).status_code == 422


def test_analyze_rejects_blank_text():
    assert client.post(URL, json={"text": "   "}).status_code == 422


def test_analyze_rejects_too_long_text():
    assert client.post(URL, json={"text": "a" * 2001}).status_code == 422


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (LLMUnavailableError("Cannot reach Ollama at http://secret-host:11434"), 503),
        (LLMTimeoutError("timed out"), 504),
        (LLMInvalidOutputError("bad json"), 502),
        (LLMError("unknown"), 502),
    ],
)
def test_analyze_maps_llm_errors_to_http_status(error, status_code):
    with patch("app.services.classifier.classify_feedback", side_effect=error):
        response = client.post(URL, json={"text": "Login is broken."})
    assert response.status_code == status_code
    detail = response.json()["detail"]
    assert isinstance(detail, str)
    assert "secret-host" not in detail  # Internal details are not leaked to clients.


def test_openapi_documents_error_responses():
    responses = client.get("/openapi.json").json()["paths"][URL]["post"]["responses"]
    assert {"502", "503", "504"} <= responses.keys()
