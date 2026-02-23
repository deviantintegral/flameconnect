---
id: 3
group: "core-library"
dependencies: [2]
status: "pending"
created: "2026-02-23"
skills:
  - python
---
# Implement binary wire protocol encoding and decoding

## Objective
Create `protocol.py` with complete encode/decode functions for all 11 parameter types in the Flame Connect binary wire format. This module converts between typed dataclasses (from `models.py`) and base64-encoded binary payloads used by the API. The existing script only has decoders for 8 of 11 parameter types and encoders for 2 — this task must implement all of them.

## Skills Required
- Python binary data handling (struct, base64)

## Acceptance Criteria
- [ ] `src/flameconnect/protocol.py` exists with all encode/decode functions
- [ ] **Decoders** implemented for all 11 parameter types: TempUnit (236), Mode (321), FlameEffect (322), HeatSettings (323), HeatMode (325), Timer (326), SoftwareVersion (327), Error (329), Sound (369), LogEffect (370)
- [ ] **Encoders** implemented for all writable parameters: TempUnit (236), Mode (321), FlameEffect (322), HeatSettings (323), HeatMode (325), Timer (326), Sound (369), LogEffect (370)
- [ ] Read-only parameters (327 SoftwareVersion, 329 Error) do NOT have encoders
- [ ] A top-level `decode_parameter(parameter_id: int, raw: bytes)` dispatches to the correct decoder
- [ ] A top-level `encode_parameter(param: <union of param types>)` dispatches to the correct encoder
- [ ] All functions use typed models from `models.py`, not raw dicts
- [ ] Passes `mypy --strict` and `ruff check`
- [ ] Validated by decoding real API parameter values (see Live API Validation Protocol below)

Use your internal Todo tool to track these and keep on track.

## Technical Requirements
- Binary format uses little-endian 2-byte parameter ID prefix + 1-byte size, then parameter-specific payload (see `FLAMECONNECT_API_REPORT.md` section 6-7)
- Temperature encoding: 2 bytes [integer_part, decimal_part] where decimal is tenths (e.g., 22.5 → bytes [22, 5])
- Flame speed on wire is 0-indexed (0-4), but model uses 1-indexed (1-5) — encode/decode must handle this offset
- BoostDuration and Timer Duration are little-endian 16-bit values
- RGBWColor byte order in the wire format: Red, Blue, Green, White (NOT Red, Green, Blue, White) — reference line 239-240 of flameconnect_reader.py carefully
- Raise `ProtocolError` from `exceptions.py` for malformed data

## Input Dependencies
- Task 2: `models.py` (dataclasses and enums), `const.py` (ParameterId values), `exceptions.py` (ProtocolError)

## Output Artifacts
- `src/flameconnect/protocol.py` — complete wire protocol module

## Implementation Notes

<details>
<summary>Detailed implementation guidance</summary>

1. **Reference the existing code carefully**. The existing `decode_parameter` function in `flameconnect_reader.py` (lines 224-283) handles: 236, 321, 322, 323, 325, 326, 327, 329. Port these, but return typed dataclasses instead of dicts.

2. **Missing decoders to implement** (use `FLAMECONNECT_API_REPORT.md` wire format docs):
   - **Sound (369)**: 2-byte payload — `[Volume, SoundFile]` after the 3-byte header. Reference the API report section "Sound Parameter (ID: 369, Size: 2)".
   - **Log Effect (370)**: Reference the API report. Structure includes LogEffect status, RGBW colors, and pattern.

3. **Missing encoders to implement**:
   The existing script only has `encode_mode_param` (321) and `encode_flame_effect_param` (322). Create encoders for all writable parameters. Each encoder should:
   - Accept the corresponding dataclass as input
   - Pack the 3-byte header: `struct.pack("<HB", parameter_id, payload_size)`
   - Pack parameter-specific payload bytes
   - Return `base64.b64encode(data).decode("ascii")`

4. **Wire format header**: Every parameter is prefixed with `struct.pack("<HB", param_id, payload_size)` — 2 bytes LE for param ID, 1 byte for payload size (not counting the header).

5. **Critical byte-order note for FlameEffect (322)**: In `flameconnect_reader.py` line 239, the MediaTheme is decoded as `"Red": raw[8], "Blue": raw[9], "Green": raw[10], "White": raw[11]`. The order on wire is R, B, G, W (not R, G, B, W). The RGBWColor dataclass stores them as red/green/blue/white, so the encoder must write them in the correct wire order (R, B, G, W).

6. **Temperature encode/decode**: Reference `encode_temp` function at line 286. For decoding: `float(raw[offset]) + float(raw[offset+1]) / 10.0`. For encoding: `bytes([int(temp), int((temp % 1) * 10)])`.

7. **Top-level dispatch functions**:
   ```python
   def decode_parameter(parameter_id: int, data: bytes) -> ModeParam | FlameEffectParam | ...
   def encode_parameter(param: ModeParam | FlameEffectParam | ...) -> str  # returns base64 string
   ```

8. Use `logging.getLogger(__name__)` for debug-level logging of encode/decode operations. No `print()`.

9. **Live API Validation Protocol**: The wire protocol can be validated against real API data. Before the async client exists (Task 05), you can use the existing `flameconnect_reader.py` to fetch real base64 parameter values, then test decoding them with the new protocol module. For each live API call:
   - **Explain**: Tell the user you will run the existing script to fetch current fireplace state (read-only GET /api/Fires/GetFireOverview).
   - **Confirm**: Wait for user approval.
   - **Verify**: Decode the real base64 values with the new protocol module and ask the user if the decoded values match their fireplace's actual state.

   This is especially valuable for validating the Sound (369) and Log Effect (370) decoders, which have no existing test vectors in the codebase.
</details>
