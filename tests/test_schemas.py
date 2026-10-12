import pytest
from pydantic import ValidationError

from app.schemas import FeedbackClassification, FeedbackRequest, Priority, Sentiment

VALID = {"sentiment": "negative", "intent": "report_issue", "category": "technical_issue", "priority": "high"}


def test_classification_parses_valid_payload():
    result = FeedbackClassification.model_validate(VALID)
    assert result.sentiment is Sentiment.NEGATIVE
    assert result.priority is Priority.HIGH


def test_classification_parses_json_string():
    result = FeedbackClassification.model_validate_json(
        '{"sentiment":"positive","intent":"give_praise","category":"general","priority":"low"}'
    )
    assert result.sentiment is Sentiment.POSITIVE


@pytest.mark.parametrize("field", ["sentiment", "intent", "category", "priority"])
def test_classification_rejects_unknown_label(field):
    with pytest.raises(ValidationError):
        FeedbackClassification.model_validate({**VALID, field: "unknown"})


@pytest.mark.parametrize("field", ["sentiment", "intent", "category", "priority"])
def test_classification_rejects_missing_field(field):
    payload = {k: v for k, v in VALID.items() if k != field}
    with pytest.raises(ValidationError):
        FeedbackClassification.model_validate(payload)


def test_classification_rejects_extra_fields():
    with pytest.raises(ValidationError):
        FeedbackClassification.model_validate({**VALID, "confidence": 0.9})


def test_request_strips_whitespace():
    assert FeedbackRequest(text="  hello  ").text == "hello"


def test_classification_json_schema_lists_enums():
    schema = FeedbackClassification.model_json_schema()
    assert set(schema["required"]) == {"sentiment", "intent", "category", "priority"}
    assert "high" in schema["$defs"]["Priority"]["enum"]
