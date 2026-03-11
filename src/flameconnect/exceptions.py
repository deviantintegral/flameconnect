"""Exception hierarchy for the flameconnect library."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flameconnect.models import FireOverviewResultCode

if TYPE_CHECKING:
    from flameconnect.models import Fire


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


class FireUnavailableError(FlameConnectError):
    """Raised when the fireplace is offline, failed, or otherwise unavailable.

    The ``result_code`` attribute contains the specific
    :class:`~flameconnect.models.FireOverviewResultCode` returned by the API.
    When the API includes ``FireDetails`` in the response, the ``fire``
    attribute contains the parsed :class:`~flameconnect.models.Fire` metadata;
    otherwise it is ``None``.
    """

    def __init__(
        self,
        result_code: FireOverviewResultCode | int,
        fire: Fire | None = None,
    ) -> None:
        self.result_code = result_code
        self.fire = fire
        try:
            label = FireOverviewResultCode(result_code).name
        except ValueError:
            label = f"UNKNOWN({result_code})"
        super().__init__(f"Fire unavailable: {label}")
