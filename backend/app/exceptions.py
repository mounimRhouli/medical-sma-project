"""
Custom exception classes for the medical multi-agent system.
Provides structured error handling with error codes and user-friendly messages.
"""


class SMABaseError(Exception):
    """Base exception for the SMA clinical system."""

    def __init__(self, message: str, error_code: str = "SMA_ERROR", detail: str = ""):
        self.message = message
        self.error_code = error_code
        self.detail = detail
        super().__init__(self.message)

    def to_dict(self) -> dict:
        return {
            "error": True,
            "error_code": self.error_code,
            "message": self.message,
            "detail": self.detail,
        }


class ConsultationNotFoundError(SMABaseError):
    """Raised when a consultation thread_id does not exist."""

    def __init__(self, thread_id: str):
        super().__init__(
            message=f"Aucune consultation trouvée pour le thread_id : {thread_id}",
            error_code="CONSULTATION_NOT_FOUND",
            detail=thread_id,
        )


class ConsultationAlreadyExistsError(SMABaseError):
    """Raised when trying to create a consultation that already exists."""

    def __init__(self, thread_id: str):
        super().__init__(
            message=f"Une consultation existe déjà pour le thread_id : {thread_id}",
            error_code="CONSULTATION_EXISTS",
            detail=thread_id,
        )


class ReportNotReadyError(SMABaseError):
    """Raised when the final report is not yet generated."""

    def __init__(self, thread_id: str):
        super().__init__(
            message="Le rapport final n'est pas encore généré pour cette consultation.",
            error_code="REPORT_NOT_READY",
            detail=thread_id,
        )


class LLMError(SMABaseError):
    """Raised when an LLM call fails."""

    def __init__(self, operation: str, original_error: str):
        super().__init__(
            message=f"Erreur LLM lors de {operation}.",
            error_code="LLM_ERROR",
            detail=original_error,
        )


class MCPServerError(SMABaseError):
    """Raised when the MCP server is unavailable or returns an error."""

    def __init__(self, detail: str = ""):
        super().__init__(
            message="Le serveur MCP n'est pas disponible.",
            error_code="MCP_UNAVAILABLE",
            detail=detail,
        )


class GraphExecutionError(SMABaseError):
    """Raised when the LangGraph workflow encounters an error."""

    def __init__(self, step: str, original_error: str):
        super().__init__(
            message=f"Erreur d'exécution du graphe lors de : {step}",
            error_code="GRAPH_EXECUTION_ERROR",
            detail=original_error,
        )


class ValidationError(SMABaseError):
    """Raised for input validation failures beyond Pydantic."""

    def __init__(self, field: str, reason: str):
        super().__init__(
            message=f"Validation échouée pour '{field}' : {reason}",
            error_code="VALIDATION_ERROR",
            detail=f"{field}: {reason}",
        )


class DatabaseError(SMABaseError):
    """Raised when a database operation fails."""

    def __init__(self, operation: str, original_error: str):
        super().__init__(
            message=f"Erreur base de données lors de : {operation}",
            error_code="DATABASE_ERROR",
            detail=original_error,
        )
