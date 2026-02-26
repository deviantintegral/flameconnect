# 🔥 FlameConnect

[![CI](https://github.com/deviantintegral/flameconnect/actions/workflows/ci.yml/badge.svg)](https://github.com/deviantintegral/flameconnect/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/flameconnect)](https://pypi.org/project/flameconnect/)
[![Python](https://img.shields.io/pypi/pyversions/flameconnect)](https://pypi.org/project/flameconnect/)

Async Python library for controlling Dimplex, Faber, and Real Flame fireplaces via the Flame Connect cloud API.

![FlameConnect TUI](images/flameconnect-0.1.0.png)

## Installation

```bash
uv add flameconnect
```

To include the interactive terminal dashboard (TUI):

```bash
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
stored at `$XDG_CACHE_HOME/flameconnect/token.json` (defaulting to
`~/.cache/flameconnect/token.json`), refreshing it automatically when it expires.

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
# Fire control
flameconnect set <fire_id> mode manual          # standby, manual

# Flame
flameconnect set <fire_id> flame-effect on       # on, off
flameconnect set <fire_id> flame-speed 3         # 1-5
flameconnect set <fire_id> flame-color blue       # all, yellow-red, yellow-blue,
                                                  #   blue, red, yellow, blue-red
flameconnect set <fire_id> brightness low         # low, high
flameconnect set <fire_id> pulsating on           # on, off

# Media lighting
flameconnect set <fire_id> media-theme prism      # user-defined, white, blue,
                                                  #   purple, red, green, prism,
                                                  #   kaleidoscope, midnight
flameconnect set <fire_id> media-light on         # on, off
flameconnect set <fire_id> media-color 255,0,0,80 # R,G,B,W (0-255) or preset name

# Overhead lighting
flameconnect set <fire_id> overhead-light on      # on, off
flameconnect set <fire_id> overhead-color dark-blue # R,G,B,W or preset name

# Ambient
flameconnect set <fire_id> ambient-sensor on      # on, off

# Heat
flameconnect set <fire_id> heat-status on         # on, off
flameconnect set <fire_id> heat-mode eco          # normal, boost, eco, boost:<min>
flameconnect set <fire_id> heat-temp 22.5         # target temperature

# Timer & units
flameconnect set <fire_id> timer 120              # minutes (0 to disable)
flameconnect set <fire_id> temp-unit celsius      # celsius, fahrenheit
```

### Launch the TUI

```bash
flameconnect tui
```

## TUI

`flameconnect tui` launches an interactive terminal dashboard built with
[Textual](https://textual.textualize.io/). It requires the TUI extra:

```bash
uv add flameconnect[tui]
```

The dashboard displays real-time fireplace status and auto-refreshes every 10
seconds. Key bindings:

| Key | Action |
|-----|--------|
| `p` | Toggle power on/off |
| `f` | Set flame speed (1-5) |
| `e` | Toggle flame effect |
| `c` | Set flame color |
| `b` | Toggle brightness (high/low) |
| `g` | Toggle pulsating effect |
| `m` | Set media theme |
| `l` | Toggle media light |
| `d` | Set media color (RGBW) |
| `o` | Toggle overhead light |
| `v` | Set overhead color (RGBW) |
| `a` | Toggle ambient sensor |
| `s` | Toggle heat on/off |
| `h` | Set heat mode |
| `n` | Set temperature |
| `u` | Toggle temp unit (°C/°F) |
| `t` | Set timer |
| `w` | Switch fireplace |
| `?` | Toggle help overlay |
| `r` | Manual refresh |
| `q` | Quit |

## API Coverage

The table below lists all known Flame Connect cloud API endpoints and their
implementation status in this library.

From a semantic versioning standpoint, the upstream API is not versioned and can change at any time. In general, we will not consider fixes around the API itself to be breaking changes, even of those change the data or methods exposed. Where possible, we will provide wrappers to translate API changes to preserve compatibility.

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
git clone https://github.com/deviantintegral/flameconnect.git
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

## Do you work at Dimplex, Faber, or Real Flame, or support the underlying web services?

This library and app aims to follow the same patterns as the official apps to minimize load on back-end infrastructure. We avoid making API calls whenever possible, and mirror the app by making data refreshes a specific user action. This library implementation is a last resort. We're glad to implement improvements if this library is causing any challenges on the back-end servers.

But really... making these remote calls is laggy and complex! As a comparison, take a look at the Lennox iComfort S30 and similar line of themostats. They have a cloud API, but also have a fully local API that works even when the internet is down. And, it's way, way faster to respond. If a local API is made available, I'd be glad to drop this library in favour of it. Let's talk!

## License

Apache-2.0
