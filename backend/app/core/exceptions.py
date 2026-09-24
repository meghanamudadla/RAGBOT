"""
Custom exception classes for clean, consistent HTTP error responses.

WHY CUSTOM EXCEPTIONS:
  Raising domain-specific exceptions (e.g., NotFoundError) in service
  code keeps the service layer framework-agnostic. The global handler
  in main.py converts them to proper HTTP responses in one place.
"""
from fastapi import HTTPException, status


class AppError(Exception):
    """Base application error."""
    def __init__(self, detail: str, status_code: int = 500) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class NotFoundError(AppError):
    def __init__(self, detail: str = "Resource not found") -> None:
        super().__init__(detail, status.HTTP_404_NOT_FOUND)


class ConflictError(AppError):
    def __init__(self, detail: str = "Resource already exists") -> None:
        super().__init__(detail, status.HTTP_409_CONFLICT)


class UnauthorizedError(AppError):
    def __init__(self, detail: str = "Unauthorized") -> None:
        super().__init__(detail, status.HTTP_401_UNAUTHORIZED)


class ForbiddenError(AppError):
    def __init__(self, detail: str = "Forbidden") -> None:
        super().__init__(detail, status.HTTP_403_FORBIDDEN)


class ValidationError(AppError):
    def __init__(self, detail: str = "Validation failed") -> None:
        super().__init__(detail, status.HTTP_422_UNPROCESSABLE_ENTITY)
