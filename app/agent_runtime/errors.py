from __future__ import annotations


class AgentCoreError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int = 400, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.retryable = retryable


def internal_error() -> AgentCoreError:
    return AgentCoreError("INTERNAL_ERROR", "The Agent request could not be completed.", 500)
