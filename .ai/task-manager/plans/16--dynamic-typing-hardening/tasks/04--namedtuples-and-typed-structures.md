---
id: 4
group: "dynamic-typing-hardening"
dependencies: []
status: "pending"
created: 2026-03-01
skills:
  - "python-typing"
  - "refactoring"
---
# Replace Unnamed Tuples with NamedTuples and Add TypedDicts

## Objective
Replace all unnamed tuples used as structured data with NamedTuples, and replace plain dicts with known schemas with TypedDicts/NamedTuples. Also narrow the `_request()` method parameter type. Covers Components 3 and 4 of the plan.

## Skills Required
Python NamedTuple, TypedDict, Literal typing, refactoring.

## Acceptance Criteria
- [ ] `_FlameEffectSetter` NamedTuple in `cli.py` replaces `tuple[str, dict[str, object], str]`
- [ ] `_ControlCommand` NamedTuple in `tui/app.py` replaces `tuple[str, str, str]`
- [ ] `FormattedParam` NamedTuple in `tui/widgets.py` replaces `tuple[str, str, str | None]` return type
- [ ] `_ThemeLabel` NamedTuple in `tui/media_theme_screen.py` replaces `tuple[str, str]`
- [ ] `_ColorLabel` NamedTuple in `tui/flame_color_screen.py` replaces `tuple[str, str]`
- [ ] `_PresetCol` NamedTuple in `tui/color_screen.py` replaces `tuple[str, str, str, str]`
- [ ] `_B2CLoginFields` NamedTuple in `b2c_login.py` replaces dict return of `_parse_login_page()`
- [ ] `_WireParam` TypedDict in `client.py` replaces `dict[str, Any]`
- [ ] `_request()` method parameter changed to `Literal["GET", "POST"]`
- [ ] All callers updated (attribute access instead of dict key access for B2CLoginFields)
- [ ] `uv run ruff check .` passes
- [ ] `uv run mypy src/` passes
- [ ] `uv run pytest` passes

## Technical Requirements

### NamedTuples to add:

**In `cli.py`:**
```
class _FlameEffectSetter(NamedTuple):
    field: str
    lookup: dict[str, object]
    label: str
```
Update `_FLAME_EFFECT_SETTERS` dict values to use `_FlameEffectSetter(...)`.

**In `tui/app.py`:**
```
class _ControlCommand(NamedTuple):
    name: str
    help_text: str
    action: str
```
Update `_CONTROL_COMMANDS` list entries.

**In `tui/widgets.py`:**
```
class FormattedParam(NamedTuple):
    label: str
    value: str
    action: str | None
```
Update `format_parameters()` return type annotation and all return points.

**In `tui/media_theme_screen.py`:**
```
class _ThemeLabel(NamedTuple):
    label: str
    hotkey: str
```
Update `_THEME_LABELS` dict values.

**In `tui/flame_color_screen.py`:**
```
class _ColorLabel(NamedTuple):
    label: str
    hotkey: str
```
Update `_COLOR_LABELS` dict values.

**In `tui/color_screen.py`:**
```
class _PresetCol(NamedTuple):
    key: str
    label: str
    dark_name: str
    light_name: str
```
Update `_PRESET_COLS` list entries.

### TypedDict and NamedTuple for dicts:

**In `b2c_login.py`:**
```
class _B2CLoginFields(NamedTuple):
    csrf: str
    tx: str
    p: str
    post_url: str
    confirmed_url: str
```
Update `_parse_login_page()` to return `_B2CLoginFields(...)` and all callers to use attribute access (`fields.csrf` instead of `fields["csrf"]`).

**In `client.py`:**
```
class _WireParam(TypedDict):
    ParameterId: int
    Value: str
```
Update `wire_params` annotation to `list[_WireParam]`.

**In `client.py`:**
Change `_request(self, method: str, ...)` to `_request(self, method: Literal["GET", "POST"], ...)`. Import `Literal` from `typing`.

## Input Dependencies
None — this is a standalone task.

## Output Artifacts
NamedTuples and TypedDicts in place across multiple modules.

## Implementation Notes
- NamedTuples support positional unpacking, so `for label, value, action in fields` still works.
- NamedTuples support indexing, so `result[0][1]` in tests still works.
- `_B2CLoginFields` callers in `b2c_login.py` currently use `fields["csrf"]`, `fields["tx"]`, etc. — switch to `fields.csrf`, `fields.tx`, etc.
- `_WireParam` is a `TypedDict`, which is a plain dict at runtime, so JSON serialization is unaffected.
