from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(
    title="AI Feedback Classification API",
    description="Classifies user feedback by sentiment, intent, category and priority using a local LLM.",
    version="0.1.0",
)

app.include_router(router, prefix="/api/v1")


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
