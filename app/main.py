import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.llm.errors import LLMError, LLMInvalidOutputError, LLMTimeoutError, LLMUnavailableError

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Feedback Classification API",
    description="Classifies user feedback by sentiment, intent, category and priority using a local LLM.",
    version="0.1.0",
)

app.include_router(router, prefix="/api/v1")

# Generic client-facing messages; details stay in the server logs.
LLM_ERROR_RESPONSES: dict[type[LLMError], tuple[int, str]] = {
    LLMUnavailableError: (503, "The language model service is unavailable. Try again later."),
    LLMTimeoutError: (504, "The language model did not respond in time."),
    LLMInvalidOutputError: (502, "The language model returned an invalid classification."),
}


@app.exception_handler(LLMError)
def handle_llm_error(request: Request, exc: LLMError) -> JSONResponse:
    status_code, detail = LLM_ERROR_RESPONSES.get(type(exc), (502, "Language model error."))
    logger.error("LLM error on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=status_code, content={"detail": detail})


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
