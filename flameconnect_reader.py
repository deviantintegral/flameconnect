#!/usr/bin/env python3
"""
Flame Connect API Reader
Connects to the GDHV IoT cloud API and reads the current state
of a registered Dimplex Bold Ignite XL (or compatible) fireplace.

Usage:
    pip install requests
    python3 flameconnect_reader.py
"""

import json
import os
import re
import sys
import time
from urllib.parse import urlencode, unquote, urlparse, parse_qs

import msal
import requests

# --- Azure AD B2C Configuration ---
CLIENT_ID = "1af761dc-085a-411f-9cb9-53e5e2115bd2"
AUTHORITY = (
    "https://gdhvb2cflameconnect.b2clogin.com/"
    "gdhvb2cflameconnect.onmicrosoft.com/"
    "B2C_1A_FirePhoneSignUpOrSignInWithPhoneOrEmail"
)
SCOPES = ["https://gdhvb2cflameconnect.onmicrosoft.com/Mobile/read"]
API_BASE = "https://mobileapi.gdhv-iot.com"

# --- Enum Lookups ---
FIRE_MODE = {0: "Standby", 1: "Manual"}
FLAME_EFFECT = {0: "Off", 1: "On"}
HEAT_STATUS = {0: "Off", 1: "On"}
HEAT_MODE = {0: "Normal", 1: "Boost", 2: "Eco", 3: "Fan Only", 4: "Schedule"}
HEAT_CONTROL = {0: "Software Disabled", 1: "Hardware Disabled", 2: "Enabled"}
FLAME_COLOR = {0: "All", 1: "Yellow/Red", 2: "Yellow/Blue", 3: "Blue", 4: "Red", 5: "Yellow", 6: "Blue/Red"}
LIGHT_STATUS = {0: "Off", 1: "On"}
TIMER_STATUS = {0: "Disabled", 1: "Enabled"}
TEMP_UNIT = {0: "Fahrenheit", 1: "Celsius"}
LOG_EFFECT = {0: "Off", 1: "On"}
MEDIA_THEME = {0: "User Defined", 1: "Theme 1", 2: "Theme 2", 3: "Theme 3",
               4: "Theme 4", 5: "Theme 5", 6: "Theme 6", 7: "Theme 7", 8: "Theme 8"}
CONNECTION_STATE = {0: "Unknown", 1: "Not Connected", 2: "Connected", 3: "Updating Firmware"}

# Maps ParameterId to a human-readable name
PARAM_NAMES = {
    236: "Temperature Unit",
    321: "Mode",
    322: "Flame Effect",
    323: "Heat Settings",
    325: "Heat Mode",
    326: "Timer Mode",
    327: "Software Version",
    329: "Error",
    369: "Sound",
    370: "Log Effect",
}


CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".flameconnect_token.json")
REDIRECT_URI = f"msal{CLIENT_ID}://auth"


def _build_msal_app():
    """Build an MSAL PublicClientApplication with persistent token cache."""
    cache = msal.SerializableTokenCache()
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            cache.deserialize(f.read())

    app = msal.PublicClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        validate_authority=False,
        token_cache=cache,
    )
    return app, cache


def _save_cache(cache):
    """Persist the MSAL token cache to disk."""
    if cache.has_state_changed:
        with open(CACHE_FILE, "w") as f:
            f.write(cache.serialize())


def authenticate():
    """Authenticate via Azure AD B2C using MSAL auth code flow.

    Uses MSAL's built-in PKCE and token cache. On first run, opens a browser
    login. On subsequent runs, silently refreshes the token from cache.
    """
    app, cache = _build_msal_app()

    # Try silent token acquisition from cache (uses refresh token internally)
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            _save_cache(cache)
            print("Using cached token (silently refreshed).")
            return result["access_token"]

    # No cached token -- do interactive auth code flow
    # MSAL generates the auth URL with PKCE internally
    flow = app.initiate_auth_code_flow(
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    if "auth_uri" not in flow:
        print("Failed to initiate auth flow:")
        print(json.dumps(flow, indent=2))
        sys.exit(1)

    print()
    print("=" * 60)
    print("AUTHENTICATION REQUIRED")
    print("=" * 60)
    print()
    print("1. Open this URL in any browser:")
    print()
    print(f"   {flow['auth_uri']}")
    print()
    print("2. Log in with your Flame Connect account.")
    print()
    print("3. After login, your browser will try to redirect to")
    print(f"   {REDIRECT_URI}?code=...")
    print("   The page won't load -- that's expected.")
    print()
    print("4. Copy the FULL URL from your browser's address bar")
    print("   and paste it below.")
    print()
    print("   IMPORTANT: If the URL has '...' in the middle, it was")
    print("   truncated. Use F12 > Console > copy(location.href)")
    print("   to get the full URL.")
    print()
    print("=" * 60)

    redirect_response = input("\nPaste the redirect URL here: ").strip()

    # Check for browser URL truncation (ellipsis character)
    if "\u2026" in redirect_response:
        print()
        print("ERROR: The URL contains an ellipsis character.")
        print("Your browser truncated the long URL in the address bar.")
        print("Use F12 > Console > copy(location.href) to get the full URL.")
        sys.exit(1)

    # Parse the redirect URL into the format MSAL expects:
    # a dict with at least 'code' (and optionally 'state', 'error', etc.)
    auth_response = {}
    query_string = ""
    if "?" in redirect_response:
        query_string = redirect_response.split("?", 1)[1]
    elif "#" in redirect_response:
        query_string = redirect_response.split("#", 1)[1]

    for part in query_string.split("&"):
        if "=" in part:
            key, val = part.split("=", 1)
            auth_response[key] = unquote(val)

    if "code" not in auth_response:
        if "error_description" in auth_response:
            print(f"\nAuth error: {auth_response['error_description']}")
        elif "error" in auth_response:
            print(f"\nAuth error: {auth_response['error']}")
        else:
            print("\nError: No authorization code found in the URL.")
        sys.exit(1)

    # Let MSAL exchange the code (it handles PKCE verification internally)
    result = app.acquire_token_by_auth_code_flow(flow, auth_response)

    if "access_token" not in result:
        print(f"\nToken exchange failed:")
        print(f"  Error: {result.get('error', 'unknown')}")
        print(f"  Description: {result.get('error_description', 'N/A')}")
        sys.exit(1)

    _save_cache(cache)
    print("\nAuthentication successful! Token will auto-refresh on future runs.\n")
    return result["access_token"]


def make_session(token):
    """Create a requests session with the required headers."""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "app_name": "FlameConnect",
        "api_version": "1.0",
        "app_version": "2.22.0",
        "app_device_os": "android",
        "device_version": "14",
        "device_manufacturer": "Python",
        "device_model": "FlameConnectReader",
        "lang_code": "en",
        "country": "US",
        "logging_required_flag": "True",
    })
    return session


def get_fires(session):
    """Fetch all registered fireplaces."""
    r = session.get(f"{API_BASE}/api/Fires/GetFires")
    r.raise_for_status()
    return r.json()


def get_fire_overview(session, fire_id):
    """Fetch current state/parameters for a fireplace."""
    r = session.get(f"{API_BASE}/api/Fires/GetFireOverview", params={"FireId": fire_id})
    r.raise_for_status()
    return r.json()



def format_rgbw(theme):
    """Format an RGBW media theme dict for display."""
    if not theme:
        return "N/A"
    name = MEDIA_THEME.get(theme.get("Theme", -1), f"Unknown({theme.get('Theme')})")
    r, g, b, w = theme.get("Red", 0), theme.get("Green", 0), theme.get("Blue", 0), theme.get("White", 0)
    return f"{name} | RGBW({r}, {g}, {b}, {w})"


def display_fire_info(fire):
    """Display basic fire registration info."""
    print(f"  Name:             {fire.get('FriendlyName', 'N/A')}")
    print(f"  Fire ID:          {fire.get('FireId', 'N/A')}")
    print(f"  Brand:            {fire.get('Brand', 'N/A')}")
    print(f"  Product Type:     {fire.get('ProductType', 'N/A')}")
    print(f"  Product Model:    {fire.get('ProductModel', 'N/A')}")
    print(f"  Item Code:        {fire.get('ItemCode', 'N/A')}")
    state = fire.get("IoTConnectionState", 0)
    print(f"  Connection:       {CONNECTION_STATE.get(state, f'Unknown({state})')}")
    print(f"  Has Heat:         {fire.get('WithHeat', 'N/A')}")
    print(f"  Is IoT Fire:      {fire.get('IsIotFire', 'N/A')}")


def display_parameter(param):
    """Display a single WiFi parameter in human-readable form."""
    pid = param.get("ParameterId", -1)
    name = PARAM_NAMES.get(pid, f"Unknown Parameter")
    print(f"\n  [{pid}] {name}")
    print(f"  {'─' * 40}")

    if pid == 321:  # Mode
        mode = param.get("Mode", -1)
        print(f"    Mode:           {FIRE_MODE.get(mode, f'Unknown({mode})')}")
        print(f"    Temperature:    {param.get('Temperature', 'N/A')}°")

    elif pid == 322:  # Flame Effect
        effect = param.get("FlameEffect", -1)
        print(f"    Flame:          {FLAME_EFFECT.get(effect, f'Unknown({effect})')}")
        print(f"    Flame Speed:    {param.get('FlameSpeed', 'N/A')} / 5")
        print(f"    Brightness:     {param.get('Brightness', 'N/A')} / 255")
        color = param.get("FlameColor", -1)
        print(f"    Flame Color:    {FLAME_COLOR.get(color, f'Unknown({color})')}")
        print(f"    Fuel Bed Light: {format_rgbw(param.get('MediaTheme'))}")
        print(f"    Overhead Light: {format_rgbw(param.get('OverheadLightTheme'))}")
        ls = param.get("LightStatus", -1)
        print(f"    Light Status:   {LIGHT_STATUS.get(ls, f'Unknown({ls})')}")
        amb = param.get("AmbientSensorStatus", -1)
        print(f"    Ambient Sensor: {LIGHT_STATUS.get(amb, f'Unknown({amb})')}")

    elif pid == 323:  # Heat Settings
        hs = param.get("HeatStatus", -1)
        hm = param.get("HeatMode", -1)
        print(f"    Heat:           {HEAT_STATUS.get(hs, f'Unknown({hs})')}")
        print(f"    Heat Mode:      {HEAT_MODE.get(hm, f'Unknown({hm})')}")
        print(f"    Setpoint Temp:  {param.get('SetpointTemperature', 'N/A')}°")
        print(f"    Boost Duration: {param.get('BoostDuration', 'N/A')}")

    elif pid == 325:  # Heat Mode
        hc = param.get("HeatControl", -1)
        print(f"    Heat Control:   {HEAT_CONTROL.get(hc, f'Unknown({hc})')}")

    elif pid == 326:  # Timer
        ts = param.get("TimerStatus", -1)
        print(f"    Timer:          {TIMER_STATUS.get(ts, f'Unknown({ts})')}")
        dur = param.get("Duration", 0)
        print(f"    Duration:       {dur} min ({dur // 60}h {dur % 60}m)")

    elif pid == 327:  # Software Version
        ui = f"{param.get('UIMajor', '?')}.{param.get('UIMinor', '?')}.{param.get('UITest', '?')}"
        ctrl = f"{param.get('ControlMajor', '?')}.{param.get('ControlMinor', '?')}.{param.get('ControlTest', '?')}"
        relay = f"{param.get('RelayMajor', '?')}.{param.get('RelayMinor', '?')}.{param.get('RelayTest', '?')}"
        print(f"    UI Version:      {ui}")
        print(f"    Control Version: {ctrl}")
        print(f"    Relay Version:   {relay}")

    elif pid == 329:  # Error
        for i in range(1, 5):
            key = f"ErrorByte{i}"
            val = param.get(key, 0)
            print(f"    Error Byte {i}:   0x{val:02X} ({val:08b})")
        errors = param.get("FireErrors", [])
        if errors:
            print(f"    Active Faults:  {len(errors)}")
            for err in errors:
                print(f"      - {err}")
        else:
            print(f"    Active Faults:  None")

    elif pid == 369:  # Sound
        print(f"    Volume:         {param.get('Volume', 'N/A')} / 255")
        print(f"    Sound File:     {param.get('SoundFile', 'N/A')}")

    elif pid == 370:  # Log Effect
        le = param.get("LogEffect", -1)
        print(f"    Log Effect:     {LOG_EFFECT.get(le, f'Unknown({le})')}")
        print(f"    Colors:         {format_rgbw(param.get('MediaTheme'))}")
        print(f"    Pattern:        {param.get('Pattern', 'N/A')}")

    elif pid == 236:  # Temperature Unit
        tu = param.get("TemperatureUnit", -1)
        print(f"    Unit:           {TEMP_UNIT.get(tu, f'Unknown({tu})')}")

    else:
        # Dump unknown parameters as raw JSON
        print(f"    Raw: {json.dumps(param, indent=6)}")


def main():
    print("Flame Connect API Reader")
    print("=" * 60)

    # Step 1: Authenticate
    print("\nStep 1: Authenticating with Azure AD B2C...")
    token = authenticate()

    session = make_session(token)

    # Step 2: List fires
    print("Step 2: Fetching registered fireplaces...")
    fires = get_fires(session)

    if not fires:
        print("\nNo fireplaces registered to this account.")
        print("You need to register a fireplace using the Flame Connect app first.")
        sys.exit(0)

    print(f"\nFound {len(fires)} fireplace(s):\n")
    for i, fire in enumerate(fires):
        print(f"{'─' * 60}")
        print(f"Fireplace #{i + 1}")
        print(f"{'─' * 60}")
        display_fire_info(fire)

    # Step 3: Get overview for each connected fire
    print(f"\n{'=' * 60}")
    print("Step 3: Reading fireplace state...")
    print(f"{'=' * 60}")

    for fire in fires:
        fire_id = fire.get("FireId")
        name = fire.get("FriendlyName", fire_id)

        print(f"\n{'━' * 60}")
        print(f"  FIREPLACE: {name}")
        print(f"  ID: {fire_id}")
        print(f"{'━' * 60}")

        try:
            overview = get_fire_overview(session, fire_id)
            params = overview.get("Parameters", [])

            if not params:
                print("\n  No parameters returned (fireplace may be offline).")
                continue

            print(f"\n  {len(params)} parameter(s) reported:")

            for param in params:
                display_parameter(param)

        except requests.HTTPError as e:
            print(f"\n  Error fetching overview: {e}")
            if e.response is not None:
                print(f"  Response: {e.response.text[:500]}")

    # Also dump raw JSON for debugging
    print(f"\n{'=' * 60}")
    print("Raw JSON (for debugging)")
    print(f"{'=' * 60}")
    for fire in fires:
        fire_id = fire.get("FireId")
        try:
            overview = get_fire_overview(session, fire_id)
            print(json.dumps(overview, indent=2))
        except requests.HTTPError:
            pass

    print("\nDone.")


if __name__ == "__main__":
    main()
