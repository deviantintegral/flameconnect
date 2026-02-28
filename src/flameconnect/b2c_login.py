"""Direct HTTP credential submission to Azure AD B2C.

Submits email + password directly via HTTP requests to avoid requiring
the user to manually copy/paste redirect URLs from a browser.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urljoin, urlparse

import aiohttp
import yarl

from flameconnect.const import CLIENT_ID
from flameconnect.exceptions import AuthenticationError

_LOGGER = logging.getLogger(__name__)

_REDIRECT_URI_PREFIX = f"msal{CLIENT_ID}://auth?"


_B2C_POLICY = "B2C_1A_FirePhoneSignUpOrSignInWithPhoneOrEmail"


def _extract_base_path(page_url: str) -> str:
    """Extract the /{tenant}/{policy}/ base path from a B2C page URL.

    B2C page URLs look like:
        /{tenant}.onmicrosoft.com/{policy}/oauth2/v2.0/authorize?...
    or:
        /{tenant}.onmicrosoft.com/{policy}/api/CombinedSigninAndSignup/...

    Returns the ``/{tenant}/{policy}/`` prefix, using the hardcoded
    ``_B2C_POLICY`` constant for the policy segment to preserve the
    original mixed-case spelling that B2C requires.
    """
    parsed = urlparse(page_url)
    segments = parsed.path.strip("/").split("/")
    if len(segments) >= 2:
        # Use the tenant from the URL but the hardcoded policy constant
        # because B2C lowercases the policy in redirect URLs while the
        # API endpoints require the original mixed-case form.
        return f"/{segments[0]}/{_B2C_POLICY}/"
    return "/"


def _parse_login_page(html: str, page_url: str) -> dict[str, str]:
    """Extract B2C form fields from the login page HTML.

    Looks for the SETTINGS JavaScript object which contains transId and
    csrf, plus derives the SelfAsserted POST URL from the page URL.

    Returns a dict with keys: csrf, tx, p, base_url, post_url,
    confirmed_url.

    Raises:
        AuthenticationError: If required fields cannot be found.
    """
    # Extract CSRF token from var SETTINGS = {..., "csrf":"...", ...}
    csrf_match = re.search(r'"csrf"\s*:\s*"([^"]+)"', html)
    if not csrf_match:
        raise AuthenticationError("Could not find CSRF token in B2C login page")
    csrf = csrf_match.group(1)

    # Extract transId from SETTINGS
    tx_match = re.search(r'"transId"\s*:\s*"([^"]+)"', html)
    if not tx_match:
        raise AuthenticationError("Could not find transId in B2C login page")
    tx = tx_match.group(1)

    p = _B2C_POLICY

    # Build URLs using the /{tenant}/{policy}/ base path
    parsed = urlparse(page_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    base = _extract_base_path(page_url)
    qs = f"tx={tx}&p={p}"

    post_url = f"{origin}{base}SelfAsserted?{qs}"
    confirmed_url = f"{origin}{base}api/CombinedSigninAndSignup/confirmed"

    return {
        "csrf": csrf,
        "tx": tx,
        "p": p,
        "post_url": post_url,
        "confirmed_url": confirmed_url,
    }


def _build_cookie_header(
    cookie_jar: aiohttp.CookieJar,
    url: str,
) -> str:
    """Build an unquoted Cookie header from the jar.

    Python's http.cookies wraps values containing ``+``, ``/``, or ``=``
    in double-quotes, but Azure AD B2C expects unquoted values (as
    browsers send them).  This function formats cookies in the plain
    ``name=value; name2=value2`` style that B2C requires.
    """
    filtered = cookie_jar.filter_cookies(yarl.URL(url))
    return "; ".join(f"{m.key}={m.value}" for m in filtered.values())


def _log_request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    data: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
) -> None:
    """Log an outgoing HTTP request at DEBUG level."""
    _LOGGER.debug(">>> %s %s", method, url)
    if params:
        _LOGGER.debug(">>>   params: %s", params)
    if headers:
        _LOGGER.debug(">>>   headers: %s", headers)
    if data:
        safe = {k: ("***" if k == "password" else v) for k, v in data.items()}
        _LOGGER.debug(">>>   body: %s", safe)


def _log_response(
    resp: aiohttp.ClientResponse,
    body: str | None = None,
) -> None:
    """Log an incoming HTTP response at DEBUG level."""
    _LOGGER.debug(
        "<<< %s %s",
        resp.status,
        resp.url,
    )
    _LOGGER.debug("<<<   headers: %s", dict(resp.headers))
    if body is not None:
        preview = body[:2000]
        if len(body) > 2000:
            preview += f"... ({len(body)} bytes total)"
        _LOGGER.debug("<<<   body: %s", preview)


async def b2c_login_with_credentials(auth_uri: str, email: str, password: str) -> str:
    """Submit credentials directly to Azure AD B2C and return the redirect URL.

    Performs the same HTTP flow a browser would:
    1. GET the auth URI → follows redirects to the B2C login page
    2. Parse HTML for CSRF token, transaction ID, and policy
    3. POST credentials to the SelfAsserted endpoint
    4. GET the confirmed endpoint → follow redirects until we hit the
       custom-scheme redirect (msal{CLIENT_ID}://auth?code=...)

    Args:
        auth_uri: The MSAL-generated authorization URI.
        email: User's email address.
        password: User's password.

    Returns:
        The full redirect URL containing the authorization code.

    Raises:
        AuthenticationError: On any failure (bad credentials, unexpected
            page structure, network errors, etc.).
    """
    jar = aiohttp.CookieJar(unsafe=True)
    try:
        async with aiohttp.ClientSession(
            cookie_jar=jar,
        ) as session:
            # Step 1: GET the auth URI, follow redirects to B2C login page
            _log_request("GET", auth_uri)
            async with session.get(auth_uri, allow_redirects=True) as resp:
                login_html = await resp.text()
                page_url = str(resp.url)
                _log_response(resp, login_html)
                if resp.status != 200:
                    raise AuthenticationError(
                        f"B2C login page returned HTTP {resp.status}"
                    )

            # Step 2: Parse the login page
            fields = _parse_login_page(login_html, page_url)
            _LOGGER.debug(
                "Parsed login page: csrf=%s, tx=%s, p=%s",
                fields["csrf"][:16] + "...",
                fields["tx"][:40] + "...",
                fields["p"],
            )

            # Step 3: POST credentials to SelfAsserted endpoint
            post_data = {
                "request_type": "RESPONSE",
                "email": email,
                "password": password,
            }
            parsed_page = urlparse(page_url)
            origin = f"{parsed_page.scheme}://{parsed_page.netloc}"
            post_headers = {
                "X-CSRF-TOKEN": fields["csrf"],
                "X-Requested-With": "XMLHttpRequest",
                "Referer": auth_uri,
                "Origin": origin,
                "Accept": ("application/json, text/javascript, */*; q=0.01"),
                "Content-Type": ("application/x-www-form-urlencoded; charset=UTF-8"),
            }

            # Build an unquoted Cookie header — aiohttp's cookie jar
            # wraps values containing +/= in double-quotes, but B2C
            # requires plain unquoted values.
            cookie_header = _build_cookie_header(jar, fields["post_url"])
            post_headers["Cookie"] = cookie_header
            _LOGGER.debug(">>>   cookies: %s", cookie_header[:200])
            _log_request(
                "POST",
                fields["post_url"],
                headers=post_headers,
                data=post_data,
            )

            # Use a separate session with DummyCookieJar so it won't
            # store POST response cookies and then re-inject them
            # (with quoted values) into the confirmed GET, overriding
            # our manual unquoted Cookie header.
            async with aiohttp.ClientSession(
                cookie_jar=aiohttp.DummyCookieJar(),
            ) as raw_session:
                async with raw_session.post(
                    yarl.URL(fields["post_url"], encoded=True),
                    data=post_data,
                    headers=post_headers,
                    allow_redirects=False,
                ) as resp:
                    body = await resp.text()
                    _log_response(resp, body)
                    if resp.status != 200:
                        raise AuthenticationError(
                            f"Credential submission returned HTTP {resp.status}"
                        )
                    # Check for error in the JSON-like response
                    if '"status":"400"' in body or '"status": "400"' in body:
                        raise AuthenticationError("Invalid email or password")
                    # Merge cookies set by the POST response (e.g.
                    # updated x-ms-cpim-cache and x-ms-cpim-trans)
                    # into the cookie header for the confirmed GET.
                    # Parse into dict so updated cookies replace old
                    # values rather than creating duplicates.
                    cookies: dict[str, str] = {}
                    for part in cookie_header.split("; "):
                        if "=" in part:
                            n, v = part.split("=", 1)
                            cookies[n] = v
                    for raw_sc in resp.headers.getall("Set-Cookie", []):
                        sc_pair = raw_sc.split(";", 1)[0]
                        if "=" in sc_pair:
                            n, v = sc_pair.split("=", 1)
                            cookies[n] = v
                    cookie_header = "; ".join(f"{n}={v}" for n, v in cookies.items())

                # Step 4: GET the confirmed endpoint — follows redirects
                # until we hit the custom-scheme redirect
                # Build query string without URL-encoding = in
                # values; B2C expects literal = in base64 params
                # (csrf_token, tx) as browsers send them.
                confirmed_qs = (
                    f"rememberMe=false"
                    f"&csrf_token={fields['csrf']}"
                    f"&tx={fields['tx']}"
                    f"&p={fields['p']}"
                )

                # Follow redirects manually to catch custom-scheme one
                next_url: str = fields["confirmed_url"] + "?" + confirmed_qs
                confirmed_headers = {
                    "Cookie": cookie_header,
                }
                for _ in range(20):  # max redirect hops
                    _log_request("GET", next_url)
                    async with raw_session.get(
                        yarl.URL(next_url, encoded=True),
                        headers=confirmed_headers,
                        allow_redirects=False,
                    ) as resp:
                        resp_body = await resp.text()
                        _log_response(resp, resp_body)
                        if resp.status in (301, 302, 303, 307, 308):
                            location = resp.headers.get("Location", "")
                            if not location:
                                raise AuthenticationError(
                                    "Redirect without Location header"
                                )
                            # Custom-scheme redirect (msal{CLIENT_ID}://auth)
                            if location.startswith(_REDIRECT_URI_PREFIX):
                                _LOGGER.debug(
                                    "Captured custom-scheme redirect: %s",
                                    location[:120] + "...",
                                )
                                return location
                            # Resolve relative URLs
                            if not location.startswith("http"):
                                location = urljoin(next_url, location)
                            next_url = location
                            continue
                        if resp.status == 200:
                            redirect_match = re.search(
                                r"(msal[a-f0-9-]+://auth"
                                r'\?[^\s"\'<]+)',
                                resp_body,
                            )
                            if redirect_match:
                                return redirect_match.group(1)
                            raise AuthenticationError(
                                "Reached 200 response without finding redirect URL"
                            )
                        raise AuthenticationError(
                            f"Unexpected HTTP {resp.status} during redirect chain"
                        )

                raise AuthenticationError("Too many redirects during B2C login")
    except AuthenticationError:
        raise
    except aiohttp.ClientError as exc:
        raise AuthenticationError(f"Network error during B2C login: {exc}") from exc
