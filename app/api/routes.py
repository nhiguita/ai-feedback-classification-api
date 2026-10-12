from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.services import classifier

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    # Minimal request body; full input/output schemas are defined in the next step.
    text: str


@router.post("/analyze")
def analyze_feedback(request: FeedbackRequest) -> dict:
    try:
        return classifier.classify_feedback(request.text)
    except classifier.ClassifierNotImplementedError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)) from exc
