"""Exception hierarchy for the flameconnect library."""

from __future__ import annotations


class FlameConnectError(Exception):
    """Base exception for all flameconnect errors."""


class AuthenticationError(FlameConnectError):
    """Raised when authentication fails."""


class ApiError(FlameConnectError):
    """Raised when the API returns a non-2xx response."""

    def __init__(self, status: int, message: str) -> None:
        self.status = status
        super().__init__(f"API error {status}: {message}")


class ProtocolError(FlameConnectError):
    """Raised when wire protocol encoding/decoding fails."""
