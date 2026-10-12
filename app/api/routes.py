from fastapi import APIRouter

from app.schemas import FeedbackClassification, FeedbackRequest
from app.services import classifier

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("/analyze", response_model=FeedbackClassification)
def analyze_feedback(request: FeedbackRequest) -> FeedbackClassification:
    return classifier.classify_feedback(request.text)
