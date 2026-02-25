# FlameConnect

[![CI](https://github.com/USERNAME/flameconnect/actions/workflows/ci.yml/badge.svg)](https://github.com/USERNAME/flameconnect/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/flameconnect)](https://pypi.org/project/flameconnect/)
[![Python](https://img.shields.io/pypi/pyversions/flameconnect)](https://pypi.org/project/flameconnect/)

Async Python library for controlling Dimplex, Faber, and Real Flame fireplaces via the Flame Connect cloud API.

## Installation

```bash
pip install flameconnect
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add flameconnect
```

To include the interactive terminal dashboard (TUI):

```bash
pip install flameconnect[tui]
# or
uv add flameconnect[tui]
```

## Quick Start

```python
import asyncio
from flameconnect import FlameConnectClient, MsalAuth

async def main():
    auth = MsalAuth()
    async with FlameConnectClient(auth=auth) as client:
        fires = await client.get_fires()
        for fire in fires:
            print(f"{fire.friendly_name} ({fire.fire_id})")

        # Turn on the first fireplace
        await client.turn_on(fires[0].fire_id)

        # Read current state
        overview = await client.get_fire_overview(fires[0].fire_id)
        for param in overview.parameters:
            print(param)

asyncio.run(main())
```

## Authentication

FlameConnect supports two authentication modes depending on your use case.

### Standalone (CLI / TUI)

Uses the built-in `MsalAuth` provider, which runs an interactive Azure AD B2C login
through your browser. On first run a browser window opens for you to sign in with
your Flame Connect account credentials. Subsequent runs reuse the cached token
stored at `~/.flameconnect_token.json`, refreshing it automatically when it expires.

```python
from flameconnect import FlameConnectClient, MsalAuth

auth = MsalAuth()
async with FlameConnectClient(auth=auth) as client:
    ...
```

### Integration (Home Assistant, etc.)

Use `TokenAuth` to inject your own bearer token or an async token provider function.
This avoids any interactive browser flow and lets your integration manage tokens
externally.

```python
from flameconnect import FlameConnectClient, TokenAuth

# With a static token string:
auth = TokenAuth("your-bearer-token")

# Or with an async token provider:
auth = TokenAuth(my_async_token_func)

async with FlameConnectClient(auth=auth) as client:
    ...
```

You can also pass an existing `aiohttp.ClientSession` to share a session with your
application:

```python
async with FlameConnectClient(auth=auth, session=my_session) as client:
    ...
```

## CLI Usage

The `flameconnect` command provides a straightforward interface for controlling your
fireplace from the terminal. Add `-v` to any command for debug logging.

### List registered fireplaces

```bash
flameconnect list
```

### Show current status

```bash
flameconnect status <fire_id>
```

### Turn on / off

```bash
flameconnect on <fire_id>
flameconnect off <fire_id>
```

### Set parameters

```bash
# Set operating mode (standby or manual)
flameconnect set <fire_id> mode manual

# Set flame speed (1-5)
flameconnect set <fire_id> flame-speed 3

# Set brightness (0-255)
flameconnect set <fire_id> brightness 200

# Set heat mode (normal, boost, eco, fan-only)
flameconnect set <fire_id> heat-mode eco

# Set heater target temperature
flameconnect set <fire_id> heat-temp 22.5

# Set countdown timer in minutes (0 to disable)
flameconnect set <fire_id> timer 120
```

### Launch the TUI

```bash
flameconnect tui
```

## TUI

`flameconnect tui` launches an interactive terminal dashboard built with
[Textual](https://textual.textualize.io/). It requires the TUI extra:

```bash
pip install flameconnect[tui]
```

The dashboard displays real-time fireplace status and auto-refreshes every 10
seconds. Key bindings:

| Key | Action |
|-----|--------|
| `p` | Toggle power on/off |
| `r` | Manual refresh |
| `q` | Quit |

## API Coverage

The table below lists all known Flame Connect cloud API endpoints and their
implementation status in this library.

### Fireplace Control (Core)

| Endpoint | Method | Status |
|----------|--------|--------|
| `/api/Fires/GetFires` | GET | Implemented |
| `/api/Fires/GetFireOverview` | GET | Implemented |
| `/api/Fires/WriteWifiParameters` | POST | Implemented |

### Fireplace Management

| Endpoint | Method | Status |
|----------|--------|--------|
| `/api/Fires/AddFire` | POST | Not implemented |
| `/api/Fires/DeleteFire` | POST | Not implemented |
| `/api/Fires/VerifyFireIdAndCode` | POST | Not implemented |
| `/api/Fires/ClaimOwnership` | POST | Not implemented |
| `/api/Fires/GetFireUsers` | GET | Not implemented |
| `/api/Fires/DeleteFireUsersAccess` | POST | Not implemented |
| `/api/Fires/AcceptOrRejectRequest` | POST | Not implemented |
| `/api/Fires/RequestAccessToFire` | POST | Not implemented |
| `/api/Fires/UpdateFireDetails` | POST | Not implemented |

### Identity

| Endpoint | Method | Status |
|----------|--------|--------|
| `/api/Identity/RegisterNewUserReturnHubsAndSites` | GET | Not implemented |
| `/api/Identity/GetUserContext` | GET | Not implemented |
| `/api/Identity/AcceptTermsAndConditions` | POST | Not implemented |
| `/api/Identity/EditProfile` | POST | Not implemented |
| `/api/Identity/DeleteUser` | POST | Not implemented |
| `/api/Identity/AddOrUpdateMobileAppUserRecord` | POST | Not implemented |
| `/api/Identity/CheckAppUnderMaintenance` | GET | Not implemented |
| `/api/Identity/GetAppUrls` | GET | Not implemented |
| `/api/Identity/GetMinimumAppVersionByMobileAppName` | GET | Not implemented |

### Favourites

| Endpoint | Method | Status |
|----------|--------|--------|
| `/api/Fires/AddFavourite` | POST | Not implemented |
| `/api/Fires/UpdateFavourite` | POST | Not implemented |
| `/api/Fires/DeleteFavourite` | POST | Not implemented |

### Schedules

| Endpoint | Method | Status |
|----------|--------|--------|
| `/api/Fires/UpdateFireSchedule` | POST | Not implemented |

### Guest Mode

| Endpoint | Method | Status |
|----------|--------|--------|
| `/api/Fires/GetGuestMode` | GET | Not implemented |
| `/api/Fires/SaveGuestMode` | POST | Not implemented |

### Notifications

| Endpoint | Method | Status |
|----------|--------|--------|
| `/api/Fires/GetNotifications` | GET | Not implemented |
| `/api/Fires/DeleteInAppNotifications` | POST | Not implemented |

### Hubs

| Endpoint | Method | Status |
|----------|--------|--------|
| `/api/Hubs/FetchTimezoneDetails` | GET | Not implemented |
| `/api/Fires/UpdateFirmwareVersion` | POST | Not implemented |
| `/api/BluetoothFirmware/AddBluetoothFirmwareHistory` | POST | Not implemented |

## Contributing

```bash
# Clone and install with dev dependencies
git clone https://github.com/USERNAME/flameconnect.git
cd flameconnect
uv sync --dev

# Lint and type-check
uv run ruff check .
uv run mypy src/

# Run tests
uv run pytest

# Mutation testing (protocol layer)
uv run mutmut run --paths-to-mutate=src/flameconnect/protocol.py
```

Please follow [Conventional Commits](https://www.conventionalcommits.org/) for
commit messages.

## License

Apache-2.0
