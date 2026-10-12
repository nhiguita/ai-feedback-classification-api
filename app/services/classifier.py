class ClassifierNotImplementedError(Exception):
    """Raised until the LLM-backed classifier is wired in."""


def classify_feedback(text: str) -> dict:
    # Placeholder: the Ollama/Qwen3 integration is added in a later step.
    raise ClassifierNotImplementedError("Feedback classifier is not implemented yet.")
