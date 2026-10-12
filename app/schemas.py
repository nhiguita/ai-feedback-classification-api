from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

MAX_TEXT_LENGTH = 2000


class Sentiment(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"


class Intent(StrEnum):
    REPORT_ISSUE = "report_issue"
    REQUEST_FEATURE = "request_feature"
    ASK_QUESTION = "ask_question"
    GIVE_PRAISE = "give_praise"
    COMPLAIN = "complain"
    OTHER = "other"


class Category(StrEnum):
    TECHNICAL_ISSUE = "technical_issue"
    PERFORMANCE = "performance"
    USABILITY = "usability"
    FEATURE_REQUEST = "feature_request"
    ACCOUNT_ACCESS = "account_access"
    DATA_QUALITY = "data_quality"
    GENERAL = "general"


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={"examples": [{"text": "The application crashes when I upload reports."}]},
    )

    text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH, description="Feedback text to classify.")


class FeedbackClassification(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "sentiment": "negative",
                    "intent": "report_issue",
                    "category": "technical_issue",
                    "priority": "high",
                }
            ]
        },
    )

    sentiment: Sentiment
    intent: Intent
    category: Category
    priority: Priority
