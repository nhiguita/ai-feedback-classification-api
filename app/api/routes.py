from fastapi import APIRouter, HTTPException, status

from app.schemas import FeedbackClassification, FeedbackRequest
from app.services import classifier

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("/analyze", response_model=FeedbackClassification)
def analyze_feedback(request: FeedbackRequest) -> FeedbackClassification:
    try:
        return classifier.classify_feedback(request.text)
    except classifier.ClassifierNotImplementedError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)) from exc
