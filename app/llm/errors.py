class LLMError(Exception):
    """Base class for provider-agnostic LLM failures."""


class LLMUnavailableError(LLMError):
    """The LLM server is unreachable or rejected the request (e.g. model not pulled)."""


class LLMTimeoutError(LLMError):
    """The LLM did not answer within the configured timeout."""


class LLMInvalidOutputError(LLMError):
    """The LLM answered, but its output does not match the expected schema."""
