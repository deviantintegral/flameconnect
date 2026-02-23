# Flame Connect API Reverse Engineering Report

## Dimplex Bold Ignite XL Fireplace - Cloud API Control

**Source:** Flame Connect APK v2.22.0 (Xamarin/.NET MAUI 9 application)
**Date:** 2026-02-22

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Authentication](#2-authentication)
3. [API Base URLs & HTTP Headers](#3-api-base-urls--http-headers)
4. [API Endpoints Reference](#4-api-endpoints-reference)
5. [Fireplace Control Protocol](#5-fireplace-control-protocol)
6. [WiFi Parameter Binary Format](#6-wifi-parameter-binary-format)
7. [Parameter Reference](#7-parameter-reference)
8. [Enum Reference](#8-enum-reference)
9. [Example Workflows](#9-example-workflows)
10. [Python Reference Implementation](#10-python-reference-implementation)

---

## 1. Architecture Overview

```
+-----------------+        HTTPS/REST          +----------------------------+       MQTT/IoT Hub       +------------+
|  Your Client    | ------------------------>  |  Azure Backend API         | --------------------->  |  Fireplace |
|  (or App)       | <------------------------  |  mobileapi.gdhv-iot.com    | <---------------------  |  (IoT Hub) |
+-----------------+    JSON + Bearer Token     +----------------------------+    Azure IoT Hub MQTT   +------------+
```

**Key insight:** The app does **NOT** communicate directly with the fireplace via MQTT. Instead, all communication goes through a REST API at `mobileapi.gdhv-iot.com`, which acts as a server-side proxy. The Azure backend handles the MQTT/IoT Hub connection to the physical fireplace device.

The fireplace's MQTT on port 8883 is used by the Azure IoT Hub infrastructure (device-to-cloud), not by the mobile app directly.

---

## 2. Authentication

### Azure AD B2C Configuration

| Setting | Value |
|---------|-------|
| **Instance** | `https://gdhvb2cflameconnect.b2clogin.com` |
| **Domain** | `gdhvb2cflameconnect.onmicrosoft.com` |
| **Tenant ID** | `b2185c80-45e7-454d-93c0-1f04e286f2ed` |
| **Client ID** | `1af761dc-085a-411f-9cb9-53e5e2115bd2` |
| **Sign-Up/Sign-In Policy** | `B2C_1A_FirePhoneSignUpOrSignInWithPhoneOrEmail` |
| **Social-Only Sign-In Policy** | `B2C_1A_FirePhoneSignInSocialOnly` |
| **Reset Password Policy** | `B2C_1A_FirePhonePasswordResetEmail` |
| **API Scope** | `https://gdhvb2cflameconnect.onmicrosoft.com/Mobile/read` |

### Authentication Flow (MSAL / OAuth 2.0 Authorization Code with PKCE)

1. **Obtain an access token** via Azure AD B2C using MSAL (Microsoft Authentication Library):
   - Authorization endpoint: `https://gdhvb2cflameconnect.b2clogin.com/gdhvb2cflameconnect.onmicrosoft.com/B2C_1A_FirePhoneSignUpOrSignInWithPhoneOrEmail/oauth2/v2.0/authorize`
   - Token endpoint: `https://gdhvb2cflameconnect.b2clogin.com/gdhvb2cflameconnect.onmicrosoft.com/B2C_1A_FirePhoneSignUpOrSignInWithPhoneOrEmail/oauth2/v2.0/token`
   - Scope: `https://gdhvb2cflameconnect.onmicrosoft.com/Mobile/read`
   - Client ID: `1af761dc-085a-411f-9cb9-53e5e2115bd2`
   - Response type: `code`
   - Use PKCE (code_challenge + code_verifier)

2. **Include the Bearer token** in all authenticated API requests:
   ```
   Authorization: Bearer <access_token>
   ```

3. **Token refresh**: MSAL handles token caching and refresh automatically. Access tokens expire; use the refresh token flow to obtain new ones.

### Practical Authentication Approach

Since this is a public B2C tenant, you can authenticate using MSAL libraries available in most languages:

```python
# Python example using msal library
import msal

app = msal.PublicClientApplication(
    "1af761dc-085a-411f-9cb9-53e5e2115bd2",
    authority="https://gdhvb2cflameconnect.b2clogin.com/gdhvb2cflameconnect.onmicrosoft.com/B2C_1A_FirePhoneSignUpOrSignInWithPhoneOrEmail"
)

# Interactive login (opens browser)
result = app.acquire_token_interactive(
    scopes=["https://gdhvb2cflameconnect.onmicrosoft.com/Mobile/read"]
)

access_token = result["access_token"]
```

---

## 3. API Base URLs & HTTP Headers

### Base URLs

| Purpose | URL |
|---------|-----|
| **Authenticated API** | `https://mobileapi.gdhv-iot.com` |
| **Guest API (unauthenticated)** | `https://app-mobileapiext-gdhv.azurewebsites.net` |

### Required HTTP Headers

All API requests must include these headers:

```http
Authorization: Bearer <access_token>
Content-Type: application/json
app_name: FlameConnect
api_version: 1.0
app_version: 2.22.0
app_device_os: android
device_version: <android_version>
device_manufacturer: <manufacturer>
device_model: <model>
lang_code: en
country: US
logging_required_flag: True
```

### JSON Serialization

The API uses **Newtonsoft.Json** with these settings:
- `NullValueHandling.Ignore`
- `TypeNameHandling.None`
- Polymorphic WiFi parameter deserialization via `JsonSubTypes`

---

## 4. API Endpoints Reference

All endpoints are relative to `https://mobileapi.gdhv-iot.com`.

### Identity / User Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/Identity/RegisterNewUserReturnHubsAndSites` | Register new user, returns hubs and sites |
| GET | `/api/Identity/GetUserContext` | Get current user context |
| POST | `/api/Identity/AcceptTermsAndConditions` | Accept terms and conditions |
| POST | `/api/Identity/EditProfile` | Edit user profile |
| POST | `/api/Identity/DeleteUser` | Delete account |
| POST | `/api/Identity/AddOrUpdateMobileAppUserRecord` | Add/update mobile app user record |
| GET | `/api/Identity/CheckAppUnderMaintenance` | Check if app is under maintenance |
| GET | `/api/Identity/GetAppUrls` | Get app URLs |
| GET | `/api/Identity/GetMinimumAppVersionByMobileAppName?mobileAppName={name}` | Get minimum app version |

### Fireplace Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/Fires/GetFires` | **List all registered fireplaces** |
| POST | `/api/Fires/AddFire` | Register a new fireplace |
| POST | `/api/Fires/DeleteFire` | Delete/unregister a fireplace |
| POST | `/api/Fires/VerifyFireIdAndCode` | Verify fire ID and PIN code |
| POST | `/api/Fires/ClaimOwnership` | Claim ownership of a fireplace |
| GET | `/api/Fires/GetFireUsers?FireId={fireId}` | Get users with access to a fire |
| POST | `/api/Fires/DeleteFireUsersAccess` | Remove user access |
| POST | `/api/Fires/AcceptOrRejectRequest` | Accept/reject access request |
| POST | `/api/Fires/RequestAccessToFire` | Request access to a fire |
| POST | `/api/Fires/UpdateFireDetails` | Update fire details |

### Fireplace Control (Core)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/Fires/GetFireOverview?FireId={fireId}` | **Get current fireplace state** |
| POST | `/api/Fires/WriteWifiParameters` | **Send control commands** |

### Favourites (Presets)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/Fires/AddFavourite` | Create a preset/favourite |
| POST | `/api/Fires/UpdateFavourite` | Update an existing preset |
| POST | `/api/Fires/DeleteFavourite` | Delete a preset |

### Schedules

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/Fires/UpdateFireSchedule` | Update fire schedule |

### Guest Mode

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/Fires/GetGuestMode?FireId={fireId}` | Get guest mode settings |
| POST | `/api/Fires/SaveGuestMode` | Save guest mode settings |

### Notifications

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/Fires/GetNotifications?FireId={fireId}` | Get notifications |
| POST | `/api/Fires/DeleteInAppNotifications` | Delete notifications |

### Hubs & Infrastructure

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/Hubs/FetchTimezoneDetails?FireId={fireId}` | Get timezone details |
| POST | `/api/Fires/UpdateFirmwareVersion` | Update firmware version |
| POST | `/api/BluetoothFirmware/AddBluetoothFirmwareHistory` | Add BLE firmware update history |

### Guest Endpoints (Unauthenticated)

These use the guest base URL: `https://app-mobileapiext-gdhv.azurewebsites.net`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/Fires/GetGuestMode?FireId={fireId}` | Get guest mode config |
| GET | `/api/Fires/GetFireOverview?FireId={fireId}` | Get fire state (guest) |
| POST | `/api/Fires/WriteWifiParameters` | Send commands (guest) |

---

## 5. Fireplace Control Protocol

### Reading Fireplace State

```http
GET https://mobileapi.gdhv-iot.com/api/Fires/GetFireOverview?FireId={fireId}
Authorization: Bearer <token>
```

**Response** (`WiFiFireOverview`):
```json
{
  "FireId": "your-fire-id",
  "Parameters": [
    {
      "ParameterId": 321,
      "ParameterSize": 3,
      "Mode": 1,
      "Temperature": 21.0
    },
    {
      "ParameterId": 322,
      "ParameterSize": 20,
      "FlameEffect": 1,
      "FlameSpeed": 3,
      "Brightness": 128,
      "MediaTheme": { "Theme": 0, "Light": 1, "Red": 255, "Green": 128, "Blue": 0, "White": 0 },
      "OverheadLightTheme": { "Light": 2, "Red": 255, "Green": 255, "Blue": 255, "White": 255 },
      "LightStatus": 1,
      "FlameColor": 0,
      "AmbientSensorStatus": 0
    },
    {
      "ParameterId": 323,
      "ParameterSize": 5,
      "HeatStatus": 1,
      "HeatMode": 0,
      "SetpointTemperature": 21.0,
      "BoostDuration": 0
    }
  ]
}
```

The `Parameters` array uses **polymorphic JSON deserialization** via the `ParameterId` field as the discriminator. Unknown parameter types are filtered out.

### Writing Fireplace Commands

```http
POST https://mobileapi.gdhv-iot.com/api/Fires/WriteWifiParameters
Authorization: Bearer <token>
Content-Type: application/json
```

**Request body** (`WriteWiFiParametersRequest`):
```json
{
  "FireId": "your-fire-id",
  "Parameters": [
    {
      "ParameterId": 321,
      "ParameterSize": 3,
      "Mode": 1,
      "Temperature": 21.0
    }
  ]
}
```

You can send **multiple parameters** in a single request to change several settings atomically.

---

## 6. WiFi Parameter Binary Format

Each WiFi parameter follows this binary wire format (used internally, but JSON properties mirror this structure):

```
[ParameterId_Hi] [ParameterId_Lo] [ParameterSize] [Value_0] [Value_1] ... [Value_N]
 \_______ 2 bytes _______/         \__ 1 byte __/  \______ ParameterSize bytes ______/
```

- `ParameterId`: 2 bytes, big-endian (MSB first)
- `ParameterSize`: 1 byte, number of value bytes
- `Value`: variable length byte array

### Temperature Encoding

Temperatures are encoded as 2 bytes: `[whole_part, decimal_part]`
- Example: 21.5°C = `[21, 5]` = `[0x15, 0x05]`
- Example: 18.0°C = `[18, 0]` = `[0x12, 0x00]`
- Minimum temperature: 7.0°C

---

## 7. Parameter Reference

### Mode Parameter (ID: 321, Size: 3)

Controls the fireplace operating mode.

| Field | Type | Values |
|-------|------|--------|
| `Mode` | byte | 0=Standby, 1=Manual |
| `Temperature` | 2 bytes | Current ambient temperature reading |

**JSON:**
```json
{
  "ParameterId": 321,
  "ParameterSize": 3,
  "Mode": 1,
  "Temperature": 21.0
}
```

### Flame Effect Parameter (ID: 322, Size: 20)

Controls flame visuals, lighting, and colors.

| Offset | Field | Type | Description |
|--------|-------|------|-------------|
| 0 | `FlameEffect` | byte | 0=Off, 1=On |
| 1 | `FlameSpeed` | byte | 0-4 on wire (displayed as 1-5 in app) |
| 2 | `Brightness` | byte | 0-255 brightness level |
| 3 | `MediaTheme.Theme` | byte | 0=UserDefined, 1-8=Theme1-8 |
| 4 | `MediaTheme.Light` | byte | 0=None, 1=FuelBedLight, 2=OverheadLight |
| 5 | `MediaTheme.Red` | byte | 0-255 red channel |
| 6 | `MediaTheme.Blue` | byte | 0-255 blue channel |
| 7 | `MediaTheme.Green` | byte | 0-255 green channel |
| 8 | `MediaTheme.White` | byte | 0-255 white channel |
| 9 | (padding) | byte | 0x00 |
| 10 | `OverheadLightTheme.Light` | byte | Light type enum |
| 11 | `OverheadLightTheme.Red` | byte | 0-255 |
| 12 | `OverheadLightTheme.Blue` | byte | 0-255 |
| 13 | `OverheadLightTheme.Green` | byte | 0-255 |
| 14 | `OverheadLightTheme.White` | byte | 0-255 |
| 15 | `LightStatus` | byte | 0=Off, 1=On |
| 16 | `FlameColor` | byte | See EWiFiFlameColor enum |
| 17 | (padding) | byte | 0x00 |
| 18 | (padding) | byte | 0x00 |
| 19 | `AmbientSensorStatus` | byte | 0=Off, 1=On |

**JSON:**
```json
{
  "ParameterId": 322,
  "ParameterSize": 20,
  "FlameEffect": 1,
  "FlameSpeed": 3,
  "Brightness": 200,
  "MediaTheme": {
    "Theme": 0,
    "Light": 1,
    "Red": 255,
    "Green": 100,
    "Blue": 0,
    "White": 0
  },
  "OverheadLightTheme": {
    "Theme": 0,
    "Light": 2,
    "Red": 255,
    "Green": 255,
    "Blue": 255,
    "White": 128
  },
  "LightStatus": 1,
  "FlameColor": 0,
  "AmbientSensorStatus": 0
}
```

**Important notes:**
- `FlameSpeed` in the JSON uses 1-5 scale (app-facing). The wire format uses 0-4. The API likely accepts the 1-5 scale.
- `MediaTheme` controls the fuel bed lighting (RGBW)
- `OverheadLightTheme` controls the overhead/accent lighting (RGBW)

### Heat Settings Parameter (ID: 323, Size: 5)

Controls the heater.

| Field | Type | Values |
|-------|------|--------|
| `HeatStatus` | byte | 0=Off, 1=On |
| `HeatMode` | byte | 0=Normal, 1=Boost, 2=Eco, 3=Fan, 4=Schedule |
| `SetpointTemperature` | 2 bytes | Target temp (min 7.0°C) |
| `BoostDuration` | byte | Boost duration value |

**JSON:**
```json
{
  "ParameterId": 323,
  "ParameterSize": 5,
  "HeatStatus": 1,
  "HeatMode": 0,
  "SetpointTemperature": 22.0,
  "BoostDuration": 0
}
```

### Heat Mode Parameter (ID: 325, Size: 1)

Controls whether heating hardware is enabled.

| Field | Type | Values |
|-------|------|--------|
| `HeatControl` | byte | 0=SoftwareDisable, 1=HardwareDisable, 2=Enabled |

**JSON:**
```json
{
  "ParameterId": 325,
  "ParameterSize": 1,
  "HeatControl": 2
}
```

### Timer Mode Parameter (ID: 326, Size: 3)

Controls the countdown timer.

| Field | Type | Values |
|-------|------|--------|
| `TimerStatus` | byte | 0=Disable, 1=Enable |
| `Duration` | 2 bytes (LSB,MSB) | Duration in minutes |

**JSON:**
```json
{
  "ParameterId": 326,
  "ParameterSize": 3,
  "TimerStatus": 1,
  "Duration": 120
}
```

**Note:** Duration bytes are in LSB-MSB order (little-endian): `Duration = (MSB << 8) | LSB`

### Software Version Parameter (ID: 327, Size: 9) - Read Only

Returns firmware version information.

| Field | Type | Description |
|-------|------|-------------|
| `UIMajor` | byte | UI board major version |
| `UIMinor` | byte | UI board minor version |
| `UITest` | byte | UI board test version |
| `ControlMajor` | byte | Control board major version |
| `ControlMinor` | byte | Control board minor version |
| `ControlTest` | byte | Control board test version |
| `RelayMajor` | byte | Relay board major version |
| `RelayMinor` | byte | Relay board minor version |
| `RelayTest` | byte | Relay board test version |

### Error Parameter (ID: 329, Size: 4) - Read Only

Returns error/fault codes as a 32-bit bitmask (4 bytes).

| Byte | Bit 7 (MSB) | Bit 6 | Bit 5 | Bit 4 | Bit 3 | Bit 2 | Bit 1 | Bit 0 (LSB) |
|------|-------------|-------|-------|-------|-------|-------|-------|-------------|
| 1 | PWM Fan Speed Error | PWM Fan Error | PWM Fan No Load | Line Over Current | Line Under Voltage | Line Over Voltage | Thermo Cutout Trip | - |
| 2 | NTC Short | NTC Error | Ambient Temp Low | Ambient Temp High | AC Fan No Load | AC Fan Error | Heater No Load | Heater Error |
| 3 | Relay Board Comm Error | Step Motor No Load | Flame No Load | RGBW CH2 No Load | RGBW CH1 No Load | RGBW CH2 Error | RGBW CH1 Error | NTC Open |
| 4 | Fault 31 | Fault 30 | Fault 29 | Fault 28 | Fault 27 | Fault 26 | Display Board Comm Error | Control Board Comm Error |

### Sound Parameter (ID: 369, Size: 2)

Controls fireplace sound effects.

| Field | Type | Description |
|-------|------|-------------|
| `Volume` | byte | Volume level (0-255) |
| `SoundFile` | byte | Sound file index |

**JSON:**
```json
{
  "ParameterId": 369,
  "ParameterSize": 2,
  "Volume": 128,
  "SoundFile": 1
}
```

### Log Effect Parameter (ID: 370, Size: 8)

Controls the log/ember bed lighting effect.

| Field | Type | Description |
|-------|------|-------------|
| `LogEffect` | byte | 0=Off, 1=On |
| `MediaTheme.Theme` | byte | Theme preset (0=UserDefined, 1-8) |
| `MediaTheme.Red` | byte | Red 0-255 |
| `MediaTheme.Blue` | byte | Blue 0-255 |
| `MediaTheme.Green` | byte | Green 0-255 |
| `MediaTheme.White` | byte | White 0-255 |
| `Pattern` | byte | Pattern index (default 1) |
| (padding) | byte | 0x00 |

**JSON:**
```json
{
  "ParameterId": 370,
  "ParameterSize": 8,
  "LogEffect": 1,
  "MediaTheme": {
    "Theme": 0,
    "Red": 255,
    "Green": 80,
    "Blue": 0,
    "White": 0
  },
  "Pattern": 1
}
```

### Temperature Unit Parameter (ID: 236, Size: 1)

| Field | Type | Values |
|-------|------|--------|
| `TemperatureUnit` | byte | 0=Fahrenheit, 1=Celsius |

### Factory Reset Parameter (ID: 64541)

Triggers a factory reset. Use with caution.

---

## 8. Enum Reference

### EWiFiFireMode
| Value | Name |
|-------|------|
| 0 | Standby |
| 1 | Manual |

### EWiFiFlameEffect
| Value | Name |
|-------|------|
| 0 | Off |
| 1 | On |

### EWiFiHeatStatus
| Value | Name |
|-------|------|
| 0 | Off |
| 1 | On |

### EWiFiHeatMode
| Value | Name |
|-------|------|
| 0 | Normal |
| 1 | Boost |
| 2 | Eco |
| 3 | Fan (fan only, no heat) |
| 4 | Schedule |

### EHeatControl
| Value | Name |
|-------|------|
| 0 | SoftwareDisable |
| 1 | HardwareDisable |
| 2 | Enabled |

### EWiFiFlameColor
| Value | Name |
|-------|------|
| 0 | All |
| 1 | YellowRed |
| 2 | YellowBlue |
| 3 | Blue |
| 4 | Red |
| 5 | Yellow |
| 6 | BlueRed |

### EWiFiBrightness
| Value | Name |
|-------|------|
| 0 | High |
| 1 | Low |
| 2 | FlickerHigh |
| 3 | FlickerLow |

### EWiFiMediaTheme
| Value | Name |
|-------|------|
| 0 | UserDefined |
| 1-8 | Theme1-Theme8 |

### EWiFiLight
| Value | Name |
|-------|------|
| 0 | None |
| 1 | FuelBedLight |
| 2 | OverheadLight |

### EWifiOverheadLightStatus
| Value | Name |
|-------|------|
| 0 | Off |
| 1 | On |

### EWifiAmbientSensorStatus
| Value | Name |
|-------|------|
| 0 | Off |
| 1 | On |

### EWiFiTimerStatus
| Value | Name |
|-------|------|
| 0 | Disable |
| 1 | Enable |

### EWiFiTemperatureUnit
| Value | Name |
|-------|------|
| 0 | Fahrenheit |
| 1 | Celsius |

### EWiFiLogEffect
| Value | Name |
|-------|------|
| 0 | Off |
| 1 | On |

### EIotHubConnectionState
| Value | Name |
|-------|------|
| 0 | Unknown |
| 1 | NotConnected |
| 2 | Connected |
| 3 | MostLikelyUpdatingFirmware |

---

## 9. Example Workflows

### Initial Setup Flow

1. **Authenticate** via Azure AD B2C (get access token)
2. **Register user**: `GET /api/Identity/RegisterNewUserReturnHubsAndSites`
3. **Accept T&C**: `POST /api/Identity/AcceptTermsAndConditions`
4. **Add fireplace**: `POST /api/Fires/AddFire` (requires FireId and PIN from the physical unit)
5. **Verify**: `POST /api/Fires/VerifyFireIdAndCode`
6. **Claim ownership**: `POST /api/Fires/ClaimOwnership`

### Turn On Fireplace

```json
POST /api/Fires/WriteWifiParameters
{
  "FireId": "your-fire-id",
  "Parameters": [
    {
      "ParameterId": 321,
      "ParameterSize": 3,
      "Mode": 1,
      "Temperature": 21.0
    },
    {
      "ParameterId": 322,
      "ParameterSize": 20,
      "FlameEffect": 1,
      "FlameSpeed": 3,
      "Brightness": 200,
      "MediaTheme": { "Theme": 1, "Light": 1, "Red": 255, "Green": 128, "Blue": 0, "White": 0 },
      "OverheadLightTheme": { "Light": 2, "Red": 255, "Green": 255, "Blue": 255, "White": 128 },
      "LightStatus": 1,
      "FlameColor": 0,
      "AmbientSensorStatus": 0
    }
  ]
}
```

### Turn Off Fireplace

```json
POST /api/Fires/WriteWifiParameters
{
  "FireId": "your-fire-id",
  "Parameters": [
    {
      "ParameterId": 321,
      "ParameterSize": 3,
      "Mode": 0,
      "Temperature": 0.0
    }
  ]
}
```

### Set Flame Color to Blue

```json
POST /api/Fires/WriteWifiParameters
{
  "FireId": "your-fire-id",
  "Parameters": [
    {
      "ParameterId": 322,
      "ParameterSize": 20,
      "FlameEffect": 1,
      "FlameSpeed": 4,
      "Brightness": 255,
      "MediaTheme": { "Theme": 0, "Light": 1, "Red": 0, "Green": 0, "Blue": 255, "White": 0 },
      "OverheadLightTheme": { "Light": 2, "Red": 0, "Green": 0, "Blue": 255, "White": 0 },
      "LightStatus": 1,
      "FlameColor": 3,
      "AmbientSensorStatus": 0
    }
  ]
}
```

### Enable Heater at 22°C

```json
POST /api/Fires/WriteWifiParameters
{
  "FireId": "your-fire-id",
  "Parameters": [
    {
      "ParameterId": 323,
      "ParameterSize": 5,
      "HeatStatus": 1,
      "HeatMode": 0,
      "SetpointTemperature": 22.0,
      "BoostDuration": 0
    }
  ]
}
```

### Set 2-Hour Sleep Timer

```json
POST /api/Fires/WriteWifiParameters
{
  "FireId": "your-fire-id",
  "Parameters": [
    {
      "ParameterId": 326,
      "ParameterSize": 3,
      "TimerStatus": 1,
      "Duration": 120
    }
  ]
}
```

### Enable Log Effect with Custom Color

```json
POST /api/Fires/WriteWifiParameters
{
  "FireId": "your-fire-id",
  "Parameters": [
    {
      "ParameterId": 370,
      "ParameterSize": 8,
      "LogEffect": 1,
      "MediaTheme": { "Theme": 0, "Red": 255, "Green": 60, "Blue": 0, "White": 0 },
      "Pattern": 1
    }
  ]
}
```

### Set Sound

```json
POST /api/Fires/WriteWifiParameters
{
  "FireId": "your-fire-id",
  "Parameters": [
    {
      "ParameterId": 369,
      "ParameterSize": 2,
      "Volume": 150,
      "SoundFile": 1
    }
  ]
}
```

### Poll Current State

```
GET /api/Fires/GetFireOverview?FireId=your-fire-id
```

Returns all current parameter values in the `Parameters` array.

---

## 10. Python Reference Implementation

```python
"""
Flame Connect API Client
Controls Dimplex Bold Ignite XL (and compatible) fireplaces
via the GDHV IoT cloud API.
"""

import msal
import requests
import json

# --- Configuration ---
CLIENT_ID = "1af761dc-085a-411f-9cb9-53e5e2115bd2"
AUTHORITY = "https://gdhvb2cflameconnect.b2clogin.com/gdhvb2cflameconnect.onmicrosoft.com/B2C_1A_FirePhoneSignUpOrSignInWithPhoneOrEmail"
SCOPES = ["https://gdhvb2cflameconnect.onmicrosoft.com/Mobile/read"]
API_BASE = "https://mobileapi.gdhv-iot.com"

# --- Authentication ---
class FlameConnectAuth:
    def __init__(self):
        self.app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)
        self.token_cache = {}

    def login(self):
        """Interactive login - opens browser for Azure AD B2C authentication."""
        result = self.app.acquire_token_interactive(scopes=SCOPES)
        if "access_token" in result:
            self.token_cache = result
            return result["access_token"]
        raise Exception(f"Auth failed: {result.get('error_description', 'Unknown error')}")

    def get_token(self):
        """Get cached token or refresh if expired."""
        accounts = self.app.get_accounts()
        if accounts:
            result = self.app.acquire_token_silent(SCOPES, account=accounts[0])
            if result and "access_token" in result:
                return result["access_token"]
        return self.login()


# --- API Client ---
class FlameConnectClient:
    def __init__(self, auth: FlameConnectAuth):
        self.auth = auth
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "app_name": "FlameConnect",
            "api_version": "1.0",
            "app_version": "2.22.0",
            "app_device_os": "android",
            "device_version": "14",
            "device_manufacturer": "Python",
            "device_model": "API Client",
            "lang_code": "en",
            "country": "US",
            "logging_required_flag": "True",
        })

    def _headers(self):
        return {"Authorization": f"Bearer {self.auth.get_token()}"}

    # --- Fire Management ---

    def get_fires(self):
        """List all registered fireplaces."""
        r = self.session.get(f"{API_BASE}/api/Fires/GetFires", headers=self._headers())
        r.raise_for_status()
        return r.json()

    def get_fire_overview(self, fire_id: str):
        """Get current fireplace state and parameters."""
        r = self.session.get(
            f"{API_BASE}/api/Fires/GetFireOverview",
            params={"FireId": fire_id},
            headers=self._headers()
        )
        r.raise_for_status()
        return r.json()

    def write_parameters(self, fire_id: str, parameters: list):
        """Send control parameters to the fireplace."""
        payload = {
            "FireId": fire_id,
            "Parameters": parameters
        }
        r = self.session.post(
            f"{API_BASE}/api/Fires/WriteWifiParameters",
            json=payload,
            headers=self._headers()
        )
        r.raise_for_status()
        return r.json() if r.content else None

    # --- Convenience Methods ---

    def set_mode(self, fire_id: str, mode: int, temperature: float = 21.0):
        """Set fireplace mode. 0=Standby, 1=Manual."""
        return self.write_parameters(fire_id, [{
            "ParameterId": 321,
            "ParameterSize": 3,
            "Mode": mode,
            "Temperature": temperature
        }])

    def turn_on(self, fire_id: str):
        """Turn fireplace on (Manual mode)."""
        return self.set_mode(fire_id, mode=1)

    def turn_off(self, fire_id: str):
        """Turn fireplace off (Standby mode)."""
        return self.set_mode(fire_id, mode=0, temperature=0.0)

    def set_flame(self, fire_id: str, on: bool = True, speed: int = 3,
                  brightness: int = 200, flame_color: int = 0,
                  media_r: int = 255, media_g: int = 128, media_b: int = 0, media_w: int = 0,
                  overhead_r: int = 255, overhead_g: int = 255, overhead_b: int = 255, overhead_w: int = 128,
                  overhead_light_on: bool = True, ambient_sensor: bool = False):
        """Set flame effect parameters."""
        return self.write_parameters(fire_id, [{
            "ParameterId": 322,
            "ParameterSize": 20,
            "FlameEffect": 1 if on else 0,
            "FlameSpeed": max(1, min(5, speed)),
            "Brightness": max(0, min(255, brightness)),
            "MediaTheme": {
                "Theme": 0, "Light": 1,
                "Red": media_r, "Green": media_g, "Blue": media_b, "White": media_w
            },
            "OverheadLightTheme": {
                "Theme": 0, "Light": 2,
                "Red": overhead_r, "Green": overhead_g, "Blue": overhead_b, "White": overhead_w
            },
            "LightStatus": 1 if overhead_light_on else 0,
            "FlameColor": flame_color,
            "AmbientSensorStatus": 1 if ambient_sensor else 0
        }])

    def set_heat(self, fire_id: str, on: bool = True, mode: int = 0,
                 temperature: float = 22.0, boost_duration: int = 0):
        """Set heater parameters. Mode: 0=Normal, 1=Boost, 2=Eco, 3=Fan, 4=Schedule."""
        return self.write_parameters(fire_id, [{
            "ParameterId": 323,
            "ParameterSize": 5,
            "HeatStatus": 1 if on else 0,
            "HeatMode": mode,
            "SetpointTemperature": max(7.0, temperature),
            "BoostDuration": boost_duration
        }])

    def set_timer(self, fire_id: str, enabled: bool = True, duration_minutes: int = 120):
        """Set countdown timer."""
        return self.write_parameters(fire_id, [{
            "ParameterId": 326,
            "ParameterSize": 3,
            "TimerStatus": 1 if enabled else 0,
            "Duration": duration_minutes
        }])

    def set_sound(self, fire_id: str, volume: int = 128, sound_file: int = 1):
        """Set sound effect."""
        return self.write_parameters(fire_id, [{
            "ParameterId": 369,
            "ParameterSize": 2,
            "Volume": volume,
            "SoundFile": sound_file
        }])

    def set_log_effect(self, fire_id: str, on: bool = True,
                       r: int = 255, g: int = 60, b: int = 0, w: int = 0, pattern: int = 1):
        """Set log/ember bed effect."""
        return self.write_parameters(fire_id, [{
            "ParameterId": 370,
            "ParameterSize": 8,
            "LogEffect": 1 if on else 0,
            "MediaTheme": {"Theme": 0, "Red": r, "Green": g, "Blue": b, "White": w},
            "Pattern": pattern
        }])

    def set_temperature_unit(self, fire_id: str, celsius: bool = True):
        """Set temperature display unit."""
        return self.write_parameters(fire_id, [{
            "ParameterId": 236,
            "ParameterSize": 1,
            "TemperatureUnit": 1 if celsius else 0
        }])


# --- Usage Example ---
if __name__ == "__main__":
    auth = FlameConnectAuth()
    client = FlameConnectClient(auth)

    # List fires
    fires = client.get_fires()
    print("Registered fires:", json.dumps(fires, indent=2))

    if fires:
        fire_id = fires[0]["FireId"]  # Use first fire

        # Get current state
        overview = client.get_fire_overview(fire_id)
        print("Current state:", json.dumps(overview, indent=2))

        # Turn on with blue flames
        client.turn_on(fire_id)
        client.set_flame(fire_id, on=True, speed=4, brightness=255,
                         flame_color=3,  # Blue
                         media_r=0, media_g=0, media_b=255, media_w=0)

        # Enable heater at 22°C
        client.set_heat(fire_id, on=True, temperature=22.0)

        # Set 2-hour timer
        client.set_timer(fire_id, enabled=True, duration_minutes=120)
```

---

## Notes and Caveats

1. **JSON structure for WriteWifiParameters**: The exact JSON property names used for each parameter type are based on the C# model property names. The polymorphic deserialization uses `ParameterId` as the discriminator, so include it in every parameter object.

2. **FlameSpeed mapping**: The app displays speeds 1-5, but the wire protocol uses 0-4. The API likely accepts the app-facing values (1-5) since the JSON model stores the +1 value.

3. **Fire ID**: You'll need to obtain your Fire ID by first registering the fireplace through the app (or via the API using the physical unit's ID and PIN code printed on the unit).

4. **Rate limiting**: Unknown - be conservative with polling intervals (the app typically polls every few seconds when active).

5. **Guest mode**: Some endpoints are accessible without full authentication via the guest API URL, if guest mode is enabled on the fireplace.

6. **Supported product models**: The app supports multiple product lines:
   - **Brands**: Dimplex, Real Flame, Faber
   - **Product types**: Optimyst V1/V2, Optiflame V1/V2/V3/V4
   - **Model identifiers**: XLF (Ignite XL), PLF, ASP, CDFI, ABN, CAS, OLF, 3STEP

7. **Feature availability**: Not all parameters are supported by all fireplace models. The `FireFeature` object returned with fire data indicates which features your specific model supports (Sound, AdvancedHeat, RgbFlameAccent, etc.).

8. **The MQTT port 8883**: This is used by the Azure IoT Hub infrastructure between the cloud backend and the physical fireplace, not by the mobile app. You don't need to interact with MQTT directly - the REST API handles everything.
