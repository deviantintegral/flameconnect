"""Shared HTTP logging helpers with credential redaction."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any
from urllib.parse import unquote

if TYPE_CHECKING:
    import logging
    from collections.abc import Mapping

    import aiohttp

_REDACTED = "***"

_SENSITIVE_HEADERS: frozenset[str] = frozenset(
    {"authorization", "cookie", "set-cookie", "x-csrf-token"}
)


def redact_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Return a copy of *headers* with sensitive values replaced by ``"***"``.

    Keys are matched case-insensitively against :data:`_SENSITIVE_HEADERS`.
    For the ``Authorization`` header the scheme prefix is preserved
    (e.g. ``"Bearer ***"``).  ``Location`` headers keep the URL but have
    sensitive query parameters masked (see :func:`redact_url`).
    """
    result: dict[str, str] = {}
    for key, value in headers.items():
        if key.lower() == "location":
            result[key] = redact_url(value)
        elif key.lower() in _SENSITIVE_HEADERS:
            if key.lower() == "authorization":
                parts = value.split(None, 1)
                if len(parts) == 2:  # noqa: PLR2004
                    result[key] = f"{parts[0]} {_REDACTED}"
                else:
                    result[key] = _REDACTED
            else:
                result[key] = _REDACTED
        else:
            result[key] = value
    return result


# Keys whose values are replaced entirely.
_FULLY_REDACTED_KEYS: frozenset[str] = frozenset({"password", "pin"})

# Identifier keys whose values keep their last few characters, so log lines
# can still be correlated with a particular device.
_PARTIALLY_REDACTED_KEYS: frozenset[str] = frozenset({"bleidentifier"})

_SENSITIVE_KEYS: frozenset[str] = _FULLY_REDACTED_KEYS | _PARTIALLY_REDACTED_KEYS

# OAuth values that only matter in URLs (e.g. the B2C redirect
# ``msal...://auth?code=...``).  Kept separate so that a JSON body field
# called ``code`` (often a harmless error code) is not hidden.
_URL_SECRET_KEYS: frozenset[str] = frozenset(
    {"code", "id_token", "access_token", "refresh_token", "client_info"}
)

_VISIBLE_SUFFIX_LEN = 4

_KEY_ALTERNATION = "|".join(sorted(_SENSITIVE_KEYS))
_QUERY_KEY_ALTERNATION = "|".join(sorted(_SENSITIVE_KEYS | _URL_SECRET_KEYS))

# ``key=value`` pairs in a URL query string, URL fragment or form body.
_QUERY_RE = re.compile(
    rf"(?P<prefix>(?:^|[?&;#])(?P<key>{_QUERY_KEY_ALTERNATION})=)"
    r"(?P<value>[^&#;\s\"'<>]*)",
    re.IGNORECASE,
)

# ``"key": "value"`` / ``"key": 1234`` in text that looks like JSON but could
# not be parsed (e.g. malformed or embedded in another document).
_JSON_TEXT_RE = re.compile(
    rf'(?P<prefix>"(?P<key>{_KEY_ALTERNATION})"\s*:\s*)'
    r'(?P<value>"(?:[^"\\]|\\.)*"|[^,}\]\s]+)',
    re.IGNORECASE,
)


def mask_value(key: str, value: Any) -> Any:
    """Mask *value* if *key* names a sensitive field.

    Keys are matched case-insensitively.  Secrets (``Pin``, ``password``)
    are replaced with ``"***"``.  Identifiers (``FireId``, ``BleIdentifier``)
    keep their last four characters (``"***abcd"``); identifiers of four
    characters or fewer are fully redacted.  ``None`` and ``""`` are returned
    unchanged, as are values for non-sensitive keys.
    """
    lowered = key.lower()
    if lowered not in _SENSITIVE_KEYS or value is None or value == "":
        return value
    if lowered in _FULLY_REDACTED_KEYS:
        return _REDACTED
    text = str(value)
    if len(text) <= _VISIBLE_SUFFIX_LEN:
        return _REDACTED
    return f"{_REDACTED}{text[-_VISIBLE_SUFFIX_LEN:]}"


def _redact_any(data: Any) -> Any:
    """Recursively mask sensitive keys in nested dicts and lists."""
    if isinstance(data, dict):
        return {
            k: (
                mask_value(k, v)
                if isinstance(k, str) and k.lower() in _SENSITIVE_KEYS
                else _redact_any(v)
            )
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [_redact_any(item) for item in data]
    return data


def redact_body(data: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy of *data* with sensitive keys masked.

    Keys are matched case-insensitively at any depth of nested dicts and
    lists.  See :func:`mask_value` for how each key is masked.  The input is
    never modified.
    """
    result: dict[str, Any] = _redact_any(dict(data))
    return result


def _sub_query(match: re.Match[str]) -> str:
    key, value = match["key"], unquote(match["value"])
    if key.lower() in _URL_SECRET_KEYS:
        masked = _REDACTED if value else value
    else:
        masked = mask_value(key, value)
    return f"{match['prefix']}{masked}"


def _sub_json_text(match: re.Match[str]) -> str:
    value = match["value"]
    if value.startswith('"'):
        value = value[1:-1]
    return f'{match["prefix"]}"{mask_value(match["key"], value)}"'


def redact_url(url: object) -> str:
    """Return *url* as a string with sensitive query parameters masked.

    For example ``msal...://auth?code=abc&state=xyz`` becomes
    ``msal...://auth?code=***&state=xyz``.
    """
    return _QUERY_RE.sub(_sub_query, str(url))


def redact_text(body: str) -> str:
    """Return a request/response body string with sensitive values masked.

    JSON object/array bodies are parsed and masked recursively; if anything
    was masked they are re-serialised compactly, otherwise the original text
    is returned untouched.  Anything else (HTML, form data, malformed JSON)
    gets a best-effort regex pass covering ``"Key": value`` and
    ``Key=value`` forms.
    """
    try:
        parsed = json.loads(body)
    except ValueError:
        pass
    else:
        if isinstance(parsed, (dict, list)):
            redacted = _redact_any(parsed)
            if redacted == parsed:
                return body
            return json.dumps(redacted, separators=(",", ":"))
    return _QUERY_RE.sub(_sub_query, _JSON_TEXT_RE.sub(_sub_json_text, body))


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
    logger.debug(">>> %s %s", method, redact_url(url))
    if params:
        logger.debug(">>>   params: %s", redact_body(params))
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
    logger.debug("<<< %s %s", response.status, redact_url(response.url))
    logger.debug("<<<   headers: %s", redact_headers(response.headers))
    if body is not None:
        body = redact_text(body)
        preview = body[:2000]
        if len(body) > 2000:  # noqa: PLR2004
            preview += f"... ({len(body)} bytes total)"
        logger.debug("<<<   body: %s", preview)
