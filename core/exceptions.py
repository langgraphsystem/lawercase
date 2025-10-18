"""Custom exception hierarchy for MegaAgent Pro.

This module provides:
- Structured exception hierarchy
- Error codes and categories
- Context preservation
- User-friendly error messages
- Integration with error handling framework
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional


class ErrorCode(str, Enum):
    """Standard error codes."""

    # General (1000-1999)
    UNKNOWN_ERROR = "ERR_1000"
    VALIDATION_ERROR = "ERR_1001"
    CONFIGURATION_ERROR = "ERR_1002"
    NOT_FOUND = "ERR_1003"
    ALREADY_EXISTS = "ERR_1004"
    PERMISSION_DENIED = "ERR_1005"
    RATE_LIMIT_EXCEEDED = "ERR_1006"

    # Authentication & Authorization (2000-2999)
    AUTH_FAILED = "ERR_2000"
    INVALID_TOKEN = "ERR_2001"
    TOKEN_EXPIRED = "ERR_2002"
    INVALID_CREDENTIALS = "ERR_2003"
    INSUFFICIENT_PERMISSIONS = "ERR_2004"

    # Database (3000-3999)
    DATABASE_ERROR = "ERR_3000"
    CONNECTION_ERROR = "ERR_3001"
    QUERY_ERROR = "ERR_3002"
    CONSTRAINT_VIOLATION = "ERR_3003"
    TRANSACTION_ERROR = "ERR_3004"

    # External Services (4000-4999)
    EXTERNAL_SERVICE_ERROR = "ERR_4000"
    LLM_ERROR = "ERR_4001"
    LLM_TIMEOUT = "ERR_4002"
    LLM_RATE_LIMIT = "ERR_4003"
    API_ERROR = "ERR_4004"
    API_TIMEOUT = "ERR_4005"

    # Agent Operations (5000-5999)
    AGENT_ERROR = "ERR_5000"
    WORKFLOW_ERROR = "ERR_5001"
    VALIDATION_FAILED = "ERR_5002"
    EVIDENCE_ANALYSIS_ERROR = "ERR_5003"
    DOCUMENT_GENERATION_ERROR = "ERR_5004"
    RAG_ERROR = "ERR_5005"

    # File Operations (6000-6999)
    FILE_ERROR = "ERR_6000"
    FILE_NOT_FOUND = "ERR_6001"
    FILE_TOO_LARGE = "ERR_6002"
    INVALID_FILE_TYPE = "ERR_6003"
    FILE_UPLOAD_ERROR = "ERR_6004"
    FILE_PROCESSING_ERROR = "ERR_6005"

    # Memory & Cache (7000-7999)
    MEMORY_ERROR = "ERR_7000"
    CACHE_ERROR = "ERR_7001"
    STORAGE_ERROR = "ERR_7002"
    VECTOR_STORE_ERROR = "ERR_7003"


class ErrorCategory(str, Enum):
    """Error categories for logging and monitoring."""

    SYSTEM = "system"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATABASE = "database"
    EXTERNAL = "external"
    BUSINESS_LOGIC = "business_logic"
    USER_ERROR = "user_error"


class MegaAgentError(Exception):
    """Base exception for all MegaAgent errors.

    Attributes:
        message: Human-readable error message
        code: Machine-readable error code
        category: Error category for classification
        details: Additional context and details
        user_message: User-friendly message (if different from technical)
        recoverable: Whether the error can be recovered from
    """

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        details: Optional[dict[str, Any]] = None,
        user_message: Optional[str] = None,
        recoverable: bool = False,
        cause: Optional[Exception] = None,
    ):
        self.message = message
        self.code = code
        self.category = category
        self.details = details or {}
        self.user_message = user_message or message
        self.recoverable = recoverable
        self.cause = cause

        super().__init__(self.message)

    def __str__(self) -> str:
        """String representation."""
        return f"[{self.code.value}] {self.message}"

    def __repr__(self) -> str:
        """Developer representation."""
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"code={self.code.value}, "
            f"category={self.category.value})"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "error": {
                "message": self.user_message,
                "code": self.code.value,
                "category": self.category.value,
                "details": self.details,
                "recoverable": self.recoverable,
            }
        }


# Validation Errors
class ValidationError(MegaAgentError):
    """Data validation failed."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs: Any,
    ):
        details = kwargs.pop("details", {})
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)

        super().__init__(
            message=message,
            code=ErrorCode.VALIDATION_ERROR,
            category=ErrorCategory.VALIDATION,
            details=details,
            recoverable=True,
            **kwargs,
        )


class ConfigurationError(MegaAgentError):
    """Configuration error."""

    def __init__(self, message: str, **kwargs: Any):
        super().__init__(
            message=message,
            code=ErrorCode.CONFIGURATION_ERROR,
            category=ErrorCategory.SYSTEM,
            recoverable=False,
            **kwargs,
        )


# Authentication & Authorization Errors
class AuthenticationError(MegaAgentError):
    """Authentication failed."""

    def __init__(self, message: str = "Authentication failed", **kwargs: Any):
        super().__init__(
            message=message,
            code=ErrorCode.AUTH_FAILED,
            category=ErrorCategory.AUTHENTICATION,
            user_message="Authentication failed. Please check your credentials.",
            recoverable=True,
            **kwargs,
        )


class InvalidTokenError(AuthenticationError):
    """Token is invalid."""

    def __init__(self, message: str = "Invalid authentication token", **kwargs: Any):
        super().__init__(
            message=message,
            code=ErrorCode.INVALID_TOKEN,
            user_message="Your session is invalid. Please log in again.",
            **kwargs,
        )


class TokenExpiredError(AuthenticationError):
    """Token has expired."""

    def __init__(self, message: str = "Authentication token expired", **kwargs: Any):
        super().__init__(
            message=message,
            code=ErrorCode.TOKEN_EXPIRED,
            user_message="Your session has expired. Please log in again.",
            **kwargs,
        )


class PermissionDeniedError(MegaAgentError):
    """Insufficient permissions."""

    def __init__(
        self,
        message: str = "Permission denied",
        required_permission: Optional[str] = None,
        **kwargs: Any,
    ):
        details = kwargs.pop("details", {})
        if required_permission:
            details["required_permission"] = required_permission

        super().__init__(
            message=message,
            code=ErrorCode.INSUFFICIENT_PERMISSIONS,
            category=ErrorCategory.AUTHORIZATION,
            details=details,
            user_message="You don't have permission to perform this action.",
            recoverable=False,
            **kwargs,
        )


# Database Errors
class DatabaseError(MegaAgentError):
    """Database operation failed."""

    def __init__(self, message: str, **kwargs: Any):
        super().__init__(
            message=message,
            code=ErrorCode.DATABASE_ERROR,
            category=ErrorCategory.DATABASE,
            user_message="A database error occurred. Please try again.",
            recoverable=True,
            **kwargs,
        )


class ConnectionError(DatabaseError):
    """Database connection failed."""

    def __init__(self, message: str = "Database connection failed", **kwargs: Any):
        super().__init__(
            message=message,
            code=ErrorCode.CONNECTION_ERROR,
            user_message="Unable to connect to the database. Please try again later.",
            **kwargs,
        )


# External Service Errors
class ExternalServiceError(MegaAgentError):
    """External service error."""

    def __init__(self, message: str, service_name: Optional[str] = None, **kwargs: Any):
        details = kwargs.pop("details", {})
        if service_name:
            details["service"] = service_name

        super().__init__(
            message=message,
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            category=ErrorCategory.EXTERNAL,
            details=details,
            user_message="An external service is temporarily unavailable.",
            recoverable=True,
            **kwargs,
        )


class LLMError(ExternalServiceError):
    """LLM provider error."""

    def __init__(
        self,
        message: str,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        **kwargs: Any,
    ):
        details = kwargs.pop("details", {})
        if model:
            details["model"] = model
        if provider:
            details["provider"] = provider

        super().__init__(
            message=message,
            service_name="LLM",
            code=ErrorCode.LLM_ERROR,
            user_message="The AI service encountered an error. Please try again.",
            **kwargs,
        )


class LLMTimeoutError(LLMError):
    """LLM request timeout."""

    def __init__(
        self, message: str = "LLM request timed out", timeout: Optional[int] = None, **kwargs: Any
    ):
        details = kwargs.pop("details", {})
        if timeout:
            details["timeout_seconds"] = timeout

        super().__init__(
            message=message,
            code=ErrorCode.LLM_TIMEOUT,
            user_message="The AI service is taking too long. Please try again.",
            **kwargs,
        )


class LLMRateLimitError(LLMError):
    """LLM rate limit exceeded."""

    def __init__(
        self,
        message: str = "LLM rate limit exceeded",
        retry_after: Optional[int] = None,
        **kwargs: Any,
    ):
        details = kwargs.pop("details", {})
        if retry_after:
            details["retry_after_seconds"] = retry_after

        super().__init__(
            message=message,
            code=ErrorCode.LLM_RATE_LIMIT,
            user_message="Too many requests. Please try again in a few moments.",
            **kwargs,
        )


# Agent Errors
class AgentError(MegaAgentError):
    """Agent operation error."""

    def __init__(self, message: str, agent_name: Optional[str] = None, **kwargs: Any):
        details = kwargs.pop("details", {})
        if agent_name:
            details["agent"] = agent_name

        super().__init__(
            message=message,
            code=ErrorCode.AGENT_ERROR,
            category=ErrorCategory.BUSINESS_LOGIC,
            details=details,
            user_message="An error occurred during processing.",
            recoverable=True,
            **kwargs,
        )


class WorkflowError(AgentError):
    """Workflow execution error."""

    def __init__(
        self,
        message: str,
        workflow_name: Optional[str] = None,
        node_name: Optional[str] = None,
        **kwargs: Any,
    ):
        details = kwargs.pop("details", {})
        if workflow_name:
            details["workflow"] = workflow_name
        if node_name:
            details["node"] = node_name

        super().__init__(
            message=message,
            code=ErrorCode.WORKFLOW_ERROR,
            user_message="Workflow execution failed. Please try again.",
            **kwargs,
        )


class EvidenceAnalysisError(AgentError):
    """Evidence analysis failed."""

    def __init__(self, message: str, **kwargs: Any):
        super().__init__(
            message=message,
            agent_name="EvidenceAnalyzer",
            code=ErrorCode.EVIDENCE_ANALYSIS_ERROR,
            user_message="Evidence analysis failed. Please check your evidence.",
            **kwargs,
        )


class DocumentGenerationError(AgentError):
    """Document generation failed."""

    def __init__(self, message: str, **kwargs: Any):
        super().__init__(
            message=message,
            agent_name="DocumentGenerator",
            code=ErrorCode.DOCUMENT_GENERATION_ERROR,
            user_message="Document generation failed. Please try again.",
            **kwargs,
        )


class RAGError(AgentError):
    """RAG pipeline error."""

    def __init__(self, message: str, **kwargs: Any):
        super().__init__(
            message=message,
            agent_name="RAGPipeline",
            code=ErrorCode.RAG_ERROR,
            user_message="Information retrieval failed. Please try again.",
            **kwargs,
        )


# File Errors
class FileError(MegaAgentError):
    """File operation error."""

    def __init__(self, message: str, file_path: Optional[str] = None, **kwargs: Any):
        details = kwargs.pop("details", {})
        if file_path:
            details["file_path"] = file_path

        super().__init__(
            message=message,
            code=ErrorCode.FILE_ERROR,
            category=ErrorCategory.USER_ERROR,
            details=details,
            user_message="File operation failed.",
            recoverable=True,
            **kwargs,
        )


class FileNotFoundError(FileError):
    """File not found."""

    def __init__(self, message: str, file_path: Optional[str] = None, **kwargs: Any):
        super().__init__(
            message=message,
            file_path=file_path,
            code=ErrorCode.FILE_NOT_FOUND,
            user_message="The requested file was not found.",
            **kwargs,
        )


class FileTooLargeError(FileError):
    """File exceeds size limit."""

    def __init__(
        self,
        message: str,
        file_size: Optional[int] = None,
        max_size: Optional[int] = None,
        **kwargs: Any,
    ):
        details = kwargs.pop("details", {})
        if file_size:
            details["file_size_bytes"] = file_size
        if max_size:
            details["max_size_bytes"] = max_size

        super().__init__(
            message=message,
            code=ErrorCode.FILE_TOO_LARGE,
            user_message=(
                f"File is too large. Maximum size is {max_size} bytes."
                if max_size
                else "File is too large."
            ),
            **kwargs,
        )


class InvalidFileTypeError(FileError):
    """Invalid file type."""

    def __init__(
        self,
        message: str,
        file_type: Optional[str] = None,
        allowed_types: Optional[list[str]] = None,
        **kwargs: Any,
    ):
        details = kwargs.pop("details", {})
        if file_type:
            details["file_type"] = file_type
        if allowed_types:
            details["allowed_types"] = allowed_types

        super().__init__(
            message=message,
            code=ErrorCode.INVALID_FILE_TYPE,
            user_message=(
                f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
                if allowed_types
                else "Invalid file type."
            ),
            **kwargs,
        )


# Memory & Cache Errors
class MemoryError(MegaAgentError):
    """Memory operation error."""

    def __init__(self, message: str, **kwargs: Any):
        super().__init__(
            message=message,
            code=ErrorCode.MEMORY_ERROR,
            category=ErrorCategory.SYSTEM,
            user_message="A memory operation failed.",
            recoverable=True,
            **kwargs,
        )


class CacheError(MegaAgentError):
    """Cache operation error."""

    def __init__(self, message: str, **kwargs: Any):
        super().__init__(
            message=message,
            code=ErrorCode.CACHE_ERROR,
            category=ErrorCategory.SYSTEM,
            user_message="A caching error occurred.",
            recoverable=True,
            **kwargs,
        )


class RateLimitExceededError(MegaAgentError):
    """Rate limit exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        limit: Optional[int] = None,
        **kwargs: Any,
    ):
        details = kwargs.pop("details", {})
        if retry_after:
            details["retry_after_seconds"] = retry_after
        if limit:
            details["rate_limit"] = limit

        super().__init__(
            message=message,
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
            category=ErrorCategory.USER_ERROR,
            details=details,
            user_message=(
                f"Rate limit exceeded. Please try again in {retry_after} seconds."
                if retry_after
                else "Rate limit exceeded. Please try again later."
            ),
            recoverable=True,
            **kwargs,
        )


class NotFoundError(MegaAgentError):
    """Resource not found."""

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs: Any,
    ):
        details = kwargs.pop("details", {})
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id

        super().__init__(
            message=message,
            code=ErrorCode.NOT_FOUND,
            category=ErrorCategory.USER_ERROR,
            details=details,
            user_message=f"{resource_type} not found" if resource_type else "Resource not found",
            recoverable=False,
            **kwargs,
        )


class AlreadyExistsError(MegaAgentError):
    """Resource already exists."""

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs: Any,
    ):
        details = kwargs.pop("details", {})
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id

        super().__init__(
            message=message,
            code=ErrorCode.ALREADY_EXISTS,
            category=ErrorCategory.USER_ERROR,
            details=details,
            user_message=(
                f"{resource_type} already exists" if resource_type else "Resource already exists"
            ),
            recoverable=False,
            **kwargs,
        )
