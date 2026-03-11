"""Tests for the shared HTTP logging helpers."""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import MagicMock

import aiohttp
import pytest
from aioresponses import aioresponses as aioresponses_mock
from yarl import URL

from flameconnect._http_logging import (
    log_request,
    log_response,
    redact_body,
    redact_headers,
)
from flameconnect.auth import TokenAuth
from flameconnect.client import FlameConnectClient
from flameconnect.const import API_BASE

# ---------------------------------------------------------------------------
# redact_headers
# ---------------------------------------------------------------------------


class TestRedactHeaders:
    """Tests for redact_headers."""

    def test_authorization_with_scheme(self) -> None:
        assert redact_headers({"Authorization": "Bearer my-token"}) == {
            "Authorization": "Bearer ***"
        }

    def test_authorization_without_scheme(self) -> None:
        assert redact_headers({"Authorization": "my-token"}) == {"Authorization": "***"}

    def test_cookie_redacted(self) -> None:
        assert redact_headers({"Cookie": "session=abc"}) == {"Cookie": "***"}

    def test_set_cookie_redacted(self) -> None:
        assert redact_headers({"Set-Cookie": "session=abc"}) == {"Set-Cookie": "***"}

    def test_x_csrf_token_redacted(self) -> None:
        assert redact_headers({"X-CSRF-TOKEN": "tok123"}) == {"X-CSRF-TOKEN": "***"}

    def test_case_insensitivity(self) -> None:
        for key in ("AUTHORIZATION", "authorization", "Authorization"):
            result = redact_headers({key: "Bearer secret"})
            assert result[key] == "Bearer ***"

    def test_non_sensitive_passes_through(self) -> None:
        assert redact_headers({"Content-Type": "application/json"}) == {
            "Content-Type": "application/json"
        }

    def test_empty_dict(self) -> None:
        assert redact_headers({}) == {}


# ---------------------------------------------------------------------------
# redact_body
# ---------------------------------------------------------------------------


class TestRedactBody:
    """Tests for redact_body."""

    def test_password_redacted(self) -> None:
        assert redact_body({"password": "s3cret", "user": "bob"}) == {
            "password": "***",
            "user": "bob",
        }

    def test_other_keys_unchanged(self) -> None:
        assert redact_body({"email": "a@b.com"}) == {"email": "a@b.com"}

    def test_empty_dict(self) -> None:
        assert redact_body({}) == {}


# ---------------------------------------------------------------------------
# log_request
# ---------------------------------------------------------------------------


class TestLogRequest:
    """Tests for log_request."""

    def test_logs_method_and_url(self) -> None:
        logger = MagicMock(spec=logging.Logger)
        log_request(logger, "GET", "https://example.com/api")
        logger.debug.assert_any_call(">>> %s %s", "GET", "https://example.com/api")

    def test_logs_redacted_headers(self) -> None:
        logger = MagicMock(spec=logging.Logger)
        log_request(
            logger,
            "POST",
            "https://example.com",
            headers={"Authorization": "Bearer tok", "Accept": "text/html"},
        )
        logger.debug.assert_any_call(
            ">>>   headers: %s",
            {"Authorization": "Bearer ***", "Accept": "text/html"},
        )

    def test_logs_redacted_body(self) -> None:
        logger = MagicMock(spec=logging.Logger)
        log_request(
            logger,
            "POST",
            "https://example.com",
            data={"password": "secret", "user": "alice"},
        )
        logger.debug.assert_any_call(
            ">>>   body: %s",
            {"password": "***", "user": "alice"},
        )

    def test_logs_params(self) -> None:
        logger = MagicMock(spec=logging.Logger)
        log_request(
            logger,
            "GET",
            "https://example.com",
            params={"q": "fire"},
        )
        logger.debug.assert_any_call(">>>   params: %s", {"q": "fire"})

    def test_no_headers_body_params_when_none(self) -> None:
        logger = MagicMock(spec=logging.Logger)
        log_request(logger, "GET", "https://example.com")
        # Only one debug call: the method/url line
        assert logger.debug.call_count == 1


# ---------------------------------------------------------------------------
# log_response
# ---------------------------------------------------------------------------


class TestLogResponse:
    """Tests for log_response."""

    def _make_response(
        self,
        status: int = 200,
        url: str = "https://example.com",
        headers: dict[str, str] | None = None,
    ) -> MagicMock:
        resp = MagicMock(spec=aiohttp.ClientResponse)
        resp.status = status
        resp.url = URL(url)
        resp.headers = headers or {"Content-Type": "text/html"}
        return resp

    def test_logs_status_and_url(self) -> None:
        logger = MagicMock(spec=logging.Logger)
        resp = self._make_response(200, "https://example.com/path")
        log_response(logger, resp)
        logger.debug.assert_any_call("<<< %s %s", 200, URL("https://example.com/path"))

    def test_logs_redacted_response_headers(self) -> None:
        logger = MagicMock(spec=logging.Logger)
        resp = self._make_response(headers={"Set-Cookie": "x=1"})
        log_response(logger, resp)
        logger.debug.assert_any_call("<<<   headers: %s", {"Set-Cookie": "***"})

    def test_logs_body(self) -> None:
        logger = MagicMock(spec=logging.Logger)
        resp = self._make_response()
        log_response(logger, resp, body="hello world")
        logger.debug.assert_any_call("<<<   body: %s", "hello world")

    def test_truncates_long_body(self) -> None:
        logger = MagicMock(spec=logging.Logger)
        resp = self._make_response()
        long_body = "x" * 3000
        log_response(logger, resp, body=long_body)
        expected = "x" * 2000 + "... (3000 bytes total)"
        logger.debug.assert_any_call("<<<   body: %s", expected)

    def test_no_body_when_none(self) -> None:
        logger = MagicMock(spec=logging.Logger)
        resp = self._make_response()
        log_response(logger, resp, body=None)
        # Two debug calls: status/url + headers, but no body
        assert logger.debug.call_count == 2


# ---------------------------------------------------------------------------
# client.py integration tests
# ---------------------------------------------------------------------------


class TestClientHttpLogging:
    """Verify _request in FlameConnectClient uses shared logging helpers."""

    @pytest.fixture()
    def mock_api(self) -> Any:
        with aioresponses_mock() as m:
            yield m

    @pytest.fixture()
    def token_auth(self) -> TokenAuth:
        return TokenAuth("test-token-123")

    async def test_request_logs_debug_headers_and_body(
        self,
        mock_api: Any,
        token_auth: TokenAuth,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        url = f"{API_BASE}/api/Fires/GetFires"
        mock_api.get(url, payload=[{"id": 1}])

        with caplog.at_level(logging.DEBUG, logger="flameconnect.client"):
            async with FlameConnectClient(token_auth) as client:
                await client._request("GET", url)

        # Request headers should be logged (redacted)
        assert any(
            ">>> GET" in rec.message and url in rec.message for rec in caplog.records
        )
        assert any(">>>   headers:" in rec.message for rec in caplog.records)
        # Response body should be logged
        assert any("<<<   body:" in rec.message for rec in caplog.records)

    async def test_request_redacts_bearer_token(
        self,
        mock_api: Any,
        token_auth: TokenAuth,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        url = f"{API_BASE}/api/Fires/GetFires"
        mock_api.get(url, payload=[])

        with caplog.at_level(logging.DEBUG, logger="flameconnect.client"):
            async with FlameConnectClient(token_auth) as client:
                await client._request("GET", url)

        header_logs = [
            rec.message for rec in caplog.records if ">>>   headers:" in rec.message
        ]
        assert len(header_logs) >= 1
        # Token must be redacted
        assert "Bearer ***" in header_logs[0]
        assert "test-token-123" not in header_logs[0]
