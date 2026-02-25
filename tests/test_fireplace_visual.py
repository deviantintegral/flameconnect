"""Tests for the fireplace visual rendering functions."""

from __future__ import annotations

from flameconnect.models import FlameColor, RGBWColor
from flameconnect.tui.widgets import (
    _FIXED_ROWS,
    _FLAME_PALETTES,
    _MIN_FLAME_ROWS,
    _build_fire_art,
    _rgbw_to_style,
)

# ---------------------------------------------------------------------------
# _rgbw_to_style
# ---------------------------------------------------------------------------


class TestRgbwToStyle:
    """Tests for RGBW-to-style conversion."""

    def test_rgbw_to_style_basic(self):
        """Pure RGB with zero white channel passes through unchanged."""
        color = RGBWColor(red=255, green=0, blue=0, white=0)
        assert _rgbw_to_style(color) == "rgb(255,0,0)"

    def test_rgbw_to_style_white_blend(self):
        """White channel is added to each RGB component."""
        color = RGBWColor(red=200, green=100, blue=50, white=80)
        assert _rgbw_to_style(color) == "rgb(255,180,130)"

    def test_rgbw_to_style_clamp(self):
        """Components exceeding 255 are clamped."""
        color = RGBWColor(red=250, green=250, blue=250, white=50)
        assert _rgbw_to_style(color) == "rgb(255,255,255)"


# ---------------------------------------------------------------------------
# _build_fire_art – structural characters
# ---------------------------------------------------------------------------


class TestFrameStructure:
    """Verify the fireplace frame contains expected structural characters."""

    def test_frame_structure(self):
        """Output plain text contains all expected frame characters."""
        text = _build_fire_art(50, 20)
        plain = text.plain
        # Top edge
        assert "\u2581" in plain  # ▁
        # Outer frame corners
        assert "\u250c" in plain  # ┌
        assert "\u2510" in plain  # ┐
        # LED strip
        assert "\u2591" in plain  # ░
        # Media bed
        assert "\u2593" in plain  # ▓
        # Bottom corners
        assert "\u2514" in plain  # └
        assert "\u2518" in plain  # ┘

    def test_double_frame(self):
        """Double border (outer + inner frame) present in output."""
        text = _build_fire_art(50, 20)
        plain = text.plain
        assert "\u2502\u2502" in plain  # ││


# ---------------------------------------------------------------------------
# _build_fire_art – flames on / off
# ---------------------------------------------------------------------------


class TestFlameVisibility:
    """Verify flame characters appear or are hidden based on fire state."""

    def test_flames_shown_when_on(self):
        """fire_on=True causes flame characters to appear."""
        text = _build_fire_art(50, 20, fire_on=True)
        plain = text.plain
        flame_chars = set("()\\/|")
        content_has_flames = any(ch in plain for ch in flame_chars)
        assert content_has_flames

    def test_flames_hidden_in_standby(self):
        """fire_on=False: no flame characters between the inner borders."""
        text = _build_fire_art(50, 20, fire_on=False)
        plain = text.plain
        lines = plain.split("\n")
        # Flame rows are lines that have ││ on both sides and are not
        # the LED strip (░) or media bed (▓) or structural lines.
        for line in lines:
            if not line.startswith("\u2502\u2502"):
                continue
            if not line.endswith("\u2502\u2502"):
                continue
            inner = line[2:-2]
            # Skip LED strip and media bed rows
            if "\u2591" in inner or "\u2593" in inner:
                continue
            # Inner content should be spaces only
            assert inner.strip() == "", f"Expected blank flame row, got: {inner!r}"


# ---------------------------------------------------------------------------
# _build_fire_art – style application
# ---------------------------------------------------------------------------


class TestStyleApplication:
    """Verify styles are applied to the correct characters."""

    def test_led_style_applied(self):
        """LED strip (░) characters carry the given led_style."""
        led = "rgb(255,128,0)"
        text = _build_fire_art(50, 20, led_style=led)
        plain = text.plain
        # Find any ░ character and check its style
        found = False
        for idx, ch in enumerate(plain):
            if ch == "\u2591":
                span_style = _style_at(text, idx)
                assert led in span_style, (
                    f"Expected led_style {led!r} at offset {idx}, got {span_style!r}"
                )
                found = True
                break
        assert found, "No LED strip character found"

    def test_media_style_applied(self):
        """Inner media bed ▓ (between ││ borders) carries the given style."""
        media = "rgb(255,0,0)"
        text = _build_fire_art(50, 20, media_style=media)
        plain = text.plain
        lines = plain.split("\n")
        for line in lines:
            if (
                line.startswith("\u2502\u2502")
                and line.endswith("\u2502\u2502")
                and "\u2593" in line
            ):
                # This is the inner media bed row
                inner_start = 2
                inner_end = len(line) - 2
                # Compute the absolute offset of this line in the full
                # plain text.
                line_offset = plain.index(line)
                for rel, ch in enumerate(line[inner_start:inner_end]):
                    if ch == "\u2593":
                        abs_offset = line_offset + inner_start + rel
                        span_style = _style_at(text, abs_offset)
                        assert media in span_style, (
                            f"Expected media_style {media!r} at "
                            f"offset {abs_offset}, got {span_style!r}"
                        )
                        return
        raise AssertionError(  # noqa: TRY003
            "No inner media bed row found"
        )

    def test_outer_hearth_always_dim(self):
        """Outer hearth ▓ row (single │ borders) always has 'dim' style."""
        text = _build_fire_art(50, 20, media_style="rgb(0,255,0)")
        plain = text.plain
        lines = plain.split("\n")
        for line in lines:
            # Outer hearth: starts with single │ (not ││) and contains ▓
            if (
                line.startswith("\u2502")
                and not line.startswith("\u2502\u2502")
                and "\u2593" in line
            ):
                # Check style on the first ▓ after the leading │
                hearth_start = 1
                line_offset = plain.index(line)
                for rel, ch in enumerate(line[hearth_start:]):
                    if ch == "\u2593":
                        abs_offset = line_offset + hearth_start + rel
                        span_style = _style_at(text, abs_offset)
                        assert "dim" in span_style, (
                            f"Expected 'dim' style on outer hearth, got {span_style!r}"
                        )
                        return
        raise AssertionError(  # noqa: TRY003
            "No outer hearth row found"
        )


# ---------------------------------------------------------------------------
# _build_fire_art – height adaptation
# ---------------------------------------------------------------------------


class TestHeightAdaptation:
    """Verify the flame zone scales to fit the requested height."""

    def test_height_adaptation_more_rows(self):
        """With h=25, total line count equals 25."""
        text = _build_fire_art(50, 25)
        lines = text.plain.split("\n")
        assert len(lines) == 25

    def test_height_adaptation_fewer_rows(self):
        """With h=12 (< 8 fixed + 8 flame defs), flame rows are trimmed."""
        text = _build_fire_art(50, 12)
        lines = text.plain.split("\n")
        assert len(lines) == 12

    def test_height_adaptation_minimum(self):
        """With h=5 (< fixed + min), at least 2 flame rows are present."""
        text = _build_fire_art(50, 5)
        lines = text.plain.split("\n")
        # Total should be _FIXED_ROWS + _MIN_FLAME_ROWS
        assert len(lines) == _FIXED_ROWS + _MIN_FLAME_ROWS
        # Verify at least 2 flame rows exist (lines with ││ that are
        # not LED, media, or structural)
        flame_count = 0
        for line in lines:
            if line.startswith("\u2502\u2502") and line.endswith("\u2502\u2502"):
                inner = line[2:-2]
                if "\u2591" not in inner and "\u2593" not in inner:
                    flame_count += 1
        assert flame_count >= 2


# ---------------------------------------------------------------------------
# _build_fire_art – flame palette
# ---------------------------------------------------------------------------


class TestFlamePalette:
    """Verify custom flame palettes are applied to flame text."""

    def test_flame_palette_applied(self):
        """Flame spans use the given palette style strings."""
        palette = ("bright_cyan", "bright_blue", "blue")
        text = _build_fire_art(50, 20, fire_on=True, flame_palette=palette)
        # Collect all unique style strings from spans
        styles_found: set[str] = set()
        for span in text._spans:
            style_str = str(span.style)
            styles_found.add(style_str)

        # At least one of the palette entries should appear in spans
        palette_found = styles_found & set(palette)
        assert palette_found, (
            f"Expected one of {palette} in spans, found styles: {styles_found}"
        )


# ---------------------------------------------------------------------------
# _build_fire_art – width consistency
# ---------------------------------------------------------------------------


class TestWidthConsistency:
    """Verify every line has consistent width.

    Flame rows may exceed ``w`` when their minimum atom text is wider
    than the scaled body width.  Structural (non-flame) rows must
    always match ``w`` exactly, and every line must be at least ``w``.
    """

    def test_width_consistency(self):
        """Every line should be at least w; structural lines exactly w."""
        w = 60
        text = _build_fire_art(w, 20)
        lines = text.plain.split("\n")
        for i, line in enumerate(lines):
            assert len(line) >= w, (
                f"Line {i} has width {len(line)}, expected >= {w}: {line!r}"
            )

    def test_structural_lines_exact_width(self):
        """Non-flame structural rows have exactly width w."""
        w = 60
        text = _build_fire_art(w, 20, fire_on=False)
        lines = text.plain.split("\n")
        for i, line in enumerate(lines):
            assert len(line) == w, (
                f"Line {i} has width {len(line)}, expected {w}: {line!r}"
            )


# ---------------------------------------------------------------------------
# _FLAME_PALETTES completeness
# ---------------------------------------------------------------------------


class TestFlamePalettesCompleteness:
    """Verify palette coverage of all FlameColor enum members."""

    def test_all_palettes_defined(self):
        """Every FlameColor enum value has an entry in _FLAME_PALETTES."""
        for member in FlameColor:
            assert member in _FLAME_PALETTES, (
                f"Missing palette for FlameColor.{member.name}"
            )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _style_at(text, offset: int) -> str:
    """Return the style string applied to the character at *offset*."""
    for span in text._spans:
        if span.start <= offset < span.end:
            return str(span.style)
    return ""
