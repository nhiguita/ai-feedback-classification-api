from fastapi import APIRouter

from app.schemas import FeedbackClassification, FeedbackRequest
from app.services import classifier

router = APIRouter(prefix="/feedback", tags=["feedback"])


ERROR_RESPONSES = {
    502: {"description": "The model returned an invalid classification after retrying."},
    503: {"description": "The model service (Ollama) is unreachable or rejected the request."},
    504: {"description": "The model did not respond within the configured timeout."},
}


@router.post("/analyze", response_model=FeedbackClassification, responses=ERROR_RESPONSES)
def analyze_feedback(request: FeedbackRequest) -> FeedbackClassification:
    return classifier.classify_feedback(request.text)
