"""Shared HTTP logging helpers with credential redaction."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import logging
    from collections.abc import Mapping
    from typing import Any

    import aiohttp

_SENSITIVE_HEADERS: frozenset[str] = frozenset(
    {"authorization", "cookie", "set-cookie", "x-csrf-token"}
)


def redact_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Return a copy of *headers* with sensitive values replaced by ``"***"``.

    Keys are matched case-insensitively against :data:`_SENSITIVE_HEADERS`.
    For the ``Authorization`` header the scheme prefix is preserved
    (e.g. ``"Bearer ***"``).
    """
    result: dict[str, str] = {}
    for key, value in headers.items():
        if key.lower() in _SENSITIVE_HEADERS:
            if key.lower() == "authorization":
                parts = value.split(None, 1)
                if len(parts) == 2:  # noqa: PLR2004
                    result[key] = f"{parts[0]} ***"
                else:
                    result[key] = "***"
            else:
                result[key] = "***"
        else:
            result[key] = value
    return result


def redact_body(data: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy of *data* with the ``password`` key redacted to ``"***"``."""
    return {k: ("***" if k == "password" else v) for k, v in data.items()}


def log_request(
    logger: logging.Logger,
    method: str,
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    data: Mapping[str, Any] | None = None,
    params: Mapping[str, str] | None = None,
) -> None:
    """Log an outgoing HTTP request at DEBUG level."""
    logger.debug(">>> %s %s", method, url)
    if params:
        logger.debug(">>>   params: %s", dict(params))
    if headers:
        logger.debug(">>>   headers: %s", redact_headers(headers))
    if data:
        logger.debug(">>>   body: %s", redact_body(data))


def log_response(
    logger: logging.Logger,
    response: aiohttp.ClientResponse,
    body: str | None = None,
) -> None:
    """Log an incoming HTTP response at DEBUG level."""
    logger.debug("<<< %s %s", response.status, response.url)
    logger.debug("<<<   headers: %s", redact_headers(response.headers))
    if body is not None:
        preview = body[:2000]
        if len(body) > 2000:  # noqa: PLR2004
            preview += f"... ({len(body)} bytes total)"
        logger.debug("<<<   body: %s", preview)
