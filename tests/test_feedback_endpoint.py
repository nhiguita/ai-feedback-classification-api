from unittest.mock import patch

from fastapi.testclient import TestClient

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
