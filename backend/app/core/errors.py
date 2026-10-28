"""
Standardized Application Exceptions and Error Handlers
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


class ZeroTraceException(Exception):
    """Base exception for ZeroTrace backend"""
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST, details: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class EvidenceValidationError(ZeroTraceException):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422), details=details)


class CryptographicError(ZeroTraceException):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, details=details)


class NotFoundError(ZeroTraceException):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND, details=details)


class ConflictError(ZeroTraceException):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, status_code=status.HTTP_409_CONFLICT, details=details)


class UnauthorizedError(ZeroTraceException):
    def __init__(self, message: str = "Authentication required", details: dict = None):
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED, details=details)


class ForbiddenError(ZeroTraceException):
    def __init__(self, message: str = "Access forbidden", details: dict = None):
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN, details=details)


async def zerotrace_exception_handler(request: Request, exc: ZeroTraceException) -> JSONResponse:
    logger.warning(f"Handled error: {exc.__class__.__name__} - {exc.message} on {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details,
            "path": request.url.path
        }
    )
