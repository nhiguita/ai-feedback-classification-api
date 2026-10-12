from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
URL = "/api/v1/feedback/analyze"


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_returns_classifier_result():
    fake = {"sentiment": "negative", "intent": "report_issue", "category": "technical_issue", "priority": "high"}
    with patch("app.services.classifier.classify_feedback", return_value=fake) as mock:
        response = client.post(URL, json={"text": "The application crashes when I upload reports."})
    assert response.status_code == 200
    assert response.json() == fake
    mock.assert_called_once_with("The application crashes when I upload reports.")


def test_analyze_returns_501_while_classifier_is_stub():
    response = client.post(URL, json={"text": "Nice app"})
    assert response.status_code == 501


def test_analyze_rejects_missing_text():
    response = client.post(URL, json={})
    assert response.status_code == 422
