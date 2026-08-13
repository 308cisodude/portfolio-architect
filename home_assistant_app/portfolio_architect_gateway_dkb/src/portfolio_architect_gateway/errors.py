"""Gateway-specific exceptions without secret-bearing payloads."""

from __future__ import annotations


class GatewayError(RuntimeError):
    """Base exception for an expected gateway failure."""


class ConfigurationError(GatewayError):
    """Raised for an invalid local configuration."""


class ProtocolError(GatewayError):
    """Raised for malformed or unexpected remote data."""


class AuthenticationError(GatewayError):
    """Raised when the bank authentication flow fails."""


class ReauthenticationRequired(AuthenticationError):
    """Raised when an interactive bootstrap is required."""


class RemoteApiError(GatewayError):
    """A bounded remote HTTP failure that does not retain response bodies."""

    def __init__(
        self,
        status: int,
        message: str,
        *,
        retry_after: int | None = None,
        operation: str | None = None,
        error_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after
        self.operation = operation
        self.error_code = error_code
