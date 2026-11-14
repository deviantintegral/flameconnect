"""Tests for the shared HTTP logging helpers."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import aiohttp
import pytest
from aioresponses import aioresponses as aioresponses_mock
from yarl import URL

from flameconnect._http_logging import (
    log_request,
    log_response,
    mask_value,
    redact_body,
    redact_headers,
    redact_text,
    redact_url,
)
from flameconnect.auth import TokenAuth
from flameconnect.client import FlameConnectClient
from flameconnect.const import API_BASE

FIXTURES = Path(__file__).parent / "fixtures"

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

    def test_password_case_insensitive(self) -> None:
        for key in ("Password", "PASSWORD", "password"):
            result = redact_body({key: "s3cret"})
            assert result[key] == "***"

    def test_other_keys_unchanged(self) -> None:
        assert redact_body({"email": "a@b.com"}) == {"email": "a@b.com"}

    def test_empty_dict(self) -> None:
        assert redact_body({}) == {}

    def test_pin_fully_redacted(self) -> None:
        assert redact_body({"Pin": "1234"}) == {"Pin": "***"}
        assert redact_body({"pin": 987654}) == {"pin": "***"}

    def test_fire_id_not_masked(self) -> None:
        assert redact_body({"FireId": "abcdef-123456"}) == {"FireId": "abcdef-123456"}

    def test_ble_identifier_keeps_last_four(self) -> None:
        assert redact_body({"BleIdentifier": "AA:BB:CC:DD:EE:FF"}) == {
            "BleIdentifier": "***E:FF"
        }

    def test_code_key_in_body_not_masked(self) -> None:
        # OAuth "code" is only treated as secret in URLs, not JSON bodies.
        assert redact_body({"code": "E123"}) == {"code": "E123"}

    def test_nested_and_lists(self) -> None:
        data = {
            "FireId": "fire-0001-aaaa",
            "Parameters": [{"ParameterId": 321, "Value": "x"}],
            "Inner": {"Fires": [{"BleIdentifier": "ble-0002-bbbb", "Pin": "0000"}]},
        }
        assert redact_body(data) == {
            "FireId": "fire-0001-aaaa",
            "Parameters": [{"ParameterId": 321, "Value": "x"}],
            "Inner": {"Fires": [{"BleIdentifier": "***bbbb", "Pin": "***"}]},
        }

    def test_does_not_mutate_input(self) -> None:
        data = {"Fires": [{"Pin": "1234"}]}
        redact_body(data)
        assert data == {"Fires": [{"Pin": "1234"}]}


# ---------------------------------------------------------------------------
# mask_value
# ---------------------------------------------------------------------------


class TestMaskValue:
    """Tests for mask_value."""

    def test_non_sensitive_key_unchanged(self) -> None:
        assert mask_value("FriendlyName", "Living Room") == "Living Room"

    def test_short_identifier_fully_redacted(self) -> None:
        assert mask_value("BleIdentifier", "1234") == "***"

    def test_none_and_empty_unchanged(self) -> None:
        assert mask_value("BleIdentifier", None) is None
        assert mask_value("Pin", "") == ""

    def test_case_insensitive(self) -> None:
        assert mask_value("BLEIDENTIFIER", "abcdefgh") == "***efgh"
        assert mask_value("PIN", "1234") == "***"

    def test_non_string_identifier(self) -> None:
        assert mask_value("BleIdentifier", 123456789) == "***6789"

    def test_fire_id_unchanged(self) -> None:
        assert mask_value("FireId", "abcdefgh") == "abcdefgh"


# ---------------------------------------------------------------------------
# redact_url
# ---------------------------------------------------------------------------


class TestRedactUrl:
    """Tests for redact_url."""

    def test_fire_id_query_not_masked(self) -> None:
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId=abcdef-123456"
        assert redact_url(url) == url

    def test_oauth_code_redacted(self) -> None:
        url = "msalabc://auth?code=secret-auth-code&state=xyz"
        assert redact_url(url) == "msalabc://auth?code=***&state=xyz"

    def test_tokens_in_fragment_redacted(self) -> None:
        url = "https://x/cb#id_token=aaa&access_token=bbb&client_info=ccc&x=1"
        assert redact_url(url) == (
            "https://x/cb#id_token=***&access_token=***&client_info=***&x=1"
        )

    def test_empty_code_unchanged(self) -> None:
        assert redact_url("https://x/y?code=&a=1") == "https://x/y?code=&a=1"

    def test_percent_encoded_value(self) -> None:
        url = "https://x/y?BleIdentifier=ab%2Fcd%2Fef12"
        assert redact_url(url) == "https://x/y?BleIdentifier=***ef12"

    def test_multiple_params_and_fragment(self) -> None:
        url = "https://x/y?a=1&bleidentifier=abcdefgh&Pin=9999&b=2#frag"
        assert redact_url(url) == (
            "https://x/y?a=1&bleidentifier=***efgh&Pin=***&b=2#frag"
        )

    def test_yarl_url(self) -> None:
        assert redact_url(URL("https://x/y?code=abcdefgh")) == ("https://x/y?code=***")

    def test_no_query_unchanged(self) -> None:
        assert redact_url("https://x/api/Fires/GetFires") == (
            "https://x/api/Fires/GetFires"
        )

    def test_path_segment_not_matched(self) -> None:
        # "code=" only counts as a query key after ? & ; or #
        url = "https://x/zipcode=abcdefgh"
        assert redact_url(url) == url


# ---------------------------------------------------------------------------
# redact_text
# ---------------------------------------------------------------------------


class TestRedactText:
    """Tests for redact_text."""

    def test_get_fires_list(self) -> None:
        body = json.dumps(
            [
                {"FireId": "fire-0001-aaaa", "Pin": "1234", "FriendlyName": "A"},
                {"FireId": "fire-0002-bbbb", "Pin": "5678", "FriendlyName": "B"},
            ]
        )
        result = redact_text(body)
        assert json.loads(result) == [
            {"FireId": "fire-0001-aaaa", "Pin": "***", "FriendlyName": "A"},
            {"FireId": "fire-0002-bbbb", "Pin": "***", "FriendlyName": "B"},
        ]
        for secret in ("1234", "5678"):
            assert secret not in result

    def test_nested_object(self) -> None:
        body = json.dumps(
            {
                "WifiFireOverview": {
                    "FireId": "fire-0001-aaaa",
                    "BleIdentifier": "AA:BB:CC:DD",
                    "Parameters": [],
                }
            }
        )
        assert json.loads(redact_text(body)) == {
            "WifiFireOverview": {
                "FireId": "fire-0001-aaaa",
                "BleIdentifier": "***C:DD",
                "Parameters": [],
            }
        }

    def test_fixture_get_fires_unchanged(self) -> None:
        # The fixture has no Pin/BleIdentifier, so it is logged verbatim.
        body = (FIXTURES / "get_fires.json").read_text()
        assert redact_text(body) == body

    def test_unchanged_json_preserved_verbatim(self) -> None:
        body = '{"status":  "200",\n "x": [1, 2]}'
        assert redact_text(body) == body

    def test_json_scalar_unchanged(self) -> None:
        assert redact_text('"FireId"') == '"FireId"'

    def test_malformed_json_regex_fallback(self) -> None:
        body = '[{"BleIdentifier": "ble-0001-aaaa", "Pin": 1234, "Name": "x"'
        assert redact_text(body) == (
            '[{"BleIdentifier": "***aaaa", "Pin": "***", "Name": "x"'
        )

    def test_malformed_json_escaped_quote(self) -> None:
        body = '{"Pin": "12\\"34", "x":'
        assert redact_text(body) == '{"Pin": "***", "x":'

    def test_form_encoded_body(self) -> None:
        body = "FireId=fire-0001-aaaa&Pin=1234&other=1"
        assert redact_text(body) == "FireId=fire-0001-aaaa&Pin=***&other=1"

    def test_html_with_oauth_redirect(self) -> None:
        body = '<a href="msalabc://auth?code=SECRET123&amp;state=s">go</a>'
        assert redact_text(body) == (
            '<a href="msalabc://auth?code=***&amp;state=s">go</a>'
        )

    def test_html_without_sensitive_data_unchanged(self) -> None:
        body = "<html><body>Hello</body></html>"
        assert redact_text(body) == body


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

    def test_masks_url_params_and_body(self) -> None:
        logger = MagicMock(spec=logging.Logger)
        log_request(
            logger,
            "POST",
            "https://example.com/x?FireId=fire-0001-aaaa&code=SECRET",
            params={"BleIdentifier": "ble-0001-aaaa"},
            data={"FireId": "fire-0001-aaaa", "Parameters": [{"Pin": "1"}]},
        )
        logger.debug.assert_any_call(
            ">>> %s %s",
            "POST",
            "https://example.com/x?FireId=fire-0001-aaaa&code=***",
        )
        logger.debug.assert_any_call(">>>   params: %s", {"BleIdentifier": "***aaaa"})
        logger.debug.assert_any_call(
            ">>>   body: %s",
            {"FireId": "fire-0001-aaaa", "Parameters": [{"Pin": "***"}]},
        )

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
        logger.debug.assert_any_call("<<< %s %s", 200, "https://example.com/path")

    def test_masks_url_and_body(self) -> None:
        logger = MagicMock(spec=logging.Logger)
        resp = self._make_response(url="https://example.com/cb?code=SECRET&state=s")
        log_response(
            logger, resp, body='{"FireId":"fire-0001-aaaa","Pin":"1234","N":1}'
        )
        logger.debug.assert_any_call(
            "<<< %s %s", 200, "https://example.com/cb?code=***&state=s"
        )
        logger.debug.assert_any_call(
            "<<<   body: %s", '{"FireId":"fire-0001-aaaa","Pin":"***","N":1}'
        )

    def test_location_header_code_redacted(self) -> None:
        logger = MagicMock(spec=logging.Logger)
        resp = self._make_response(
            status=302,
            headers={"Location": "msalabc://auth?code=SECRET&state=s"},
        )
        log_response(logger, resp)
        logger.debug.assert_any_call(
            "<<<   headers: %s", {"Location": "msalabc://auth?code=***&state=s"}
        )

    def test_masks_before_truncating(self) -> None:
        logger = MagicMock(spec=logging.Logger)
        resp = self._make_response()
        body = json.dumps([{"Pin": "1234", "Pad": "x" * 3000}])
        log_response(logger, resp, body=body)
        logged = logger.debug.call_args_list[-1].args[1]
        assert "1234" not in logged
        assert logged.startswith('[{"Pin":"***"')

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

    async def test_get_fires_masks_pin_and_ble_identifier(
        self,
        mock_api: Any,
        token_auth: TokenAuth,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        url = f"{API_BASE}/api/Fires/GetFires"
        mock_api.get(
            url,
            payload=[
                {
                    "FireId": "secret-fire-id-9f3c",
                    "Pin": "4821",
                    "BleIdentifier": "secret-ble-77aa",
                    "FriendlyName": "Lounge",
                }
            ],
        )

        with caplog.at_level(logging.DEBUG, logger="flameconnect.client"):
            async with FlameConnectClient(token_auth) as client:
                result = await client._request("GET", url)

        # Non-logging behaviour is unchanged: callers still get real values.
        assert result[0]["FireId"] == "secret-fire-id-9f3c"
        assert result[0]["Pin"] == "4821"
        assert result[0]["BleIdentifier"] == "secret-ble-77aa"
        assert "4821" not in caplog.text
        assert "secret-ble" not in caplog.text
        assert "***77aa" in caplog.text
        # FireId is not considered private and is logged as-is.
        assert "secret-fire-id-9f3c" in caplog.text
