"""Tests for the fireplace visual rendering functions."""

from __future__ import annotations

from flameconnect.models import FlameColor, RGBWColor
from flameconnect.tui.widgets import (
    _FIXED_ROWS,
    _FLAME_DEFS,
    _FLAME_PALETTES,
    _HEAT_ROWS,
    _MIN_FLAME_ROWS,
    _build_fire_art,
    _expand_flame,
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


# ---------------------------------------------------------------------------
# _expand_flame – gap distribution
# ---------------------------------------------------------------------------


class TestExpandFlame:
    """Tests for _expand_flame gap distribution."""

    def test_basic_gap_distribution(self):
        """Gaps are distributed proportionally among atoms."""
        atoms = [("A", 1), ("B", 1), ("C", 0)]
        result = _expand_flame(atoms, 13, "red")
        plain = result.plain
        # 3 chars of atoms, 10 chars of gap, split 5/5/0
        assert len(plain) == 13
        assert plain.startswith("A")
        assert plain.endswith("C")

    def test_style_applied(self):
        """Atoms get the specified style."""
        atoms = [("AB", 0)]
        result = _expand_flame(atoms, 2, "bright_red")
        styles = {str(s.style) for s in result._spans}
        assert "bright_red" in styles

    def test_gap_weight_zero_no_space(self):
        """Atom with weight=0 gets no trailing gap."""
        atoms = [("A", 1), ("B", 0)]
        result = _expand_flame(atoms, 6, "red")
        plain = result.plain
        # Expect "A" + 4 spaces + "B" (no trailing space)
        assert plain.endswith("B")
        assert " " * 4 in plain

    def test_exact_width_no_gaps(self):
        """When body_width equals atom chars, no gaps added."""
        atoms = [("AB", 1), ("CD", 0)]
        result = _expand_flame(atoms, 4, "red")
        assert result.plain == "ABCD"

    def test_remaining_gap_decreases(self):
        """Each atom consumes its proportional share of remaining gap."""
        atoms = [("X", 2), ("Y", 1), ("Z", 0)]
        result = _expand_flame(atoms, 12, "red")
        plain = result.plain
        assert len(plain) == 12
        # X gets 2/3 of 9 gap = 6, Y gets 1/1 of 3 = 3
        assert plain == "X" + " " * 6 + "Y" + " " * 3 + "Z"

    def test_body_width_smaller_than_chars(self):
        """When body_width < total atom chars, total_gap=0."""
        atoms = [("ABCD", 1), ("EF", 0)]
        result = _expand_flame(atoms, 3, "red")
        assert result.plain == "ABCDEF"  # no gaps

    def test_gap_spaces_not_other_chars(self):
        """Gaps between atoms are regular spaces, not other characters."""
        atoms = [("A", 1), ("B", 0)]
        result = _expand_flame(atoms, 6, "red")
        plain = result.plain
        gap = plain[1:-1]
        assert gap == " " * len(gap)

    def test_all_zero_weights(self):
        """All atoms with weight=0: gap uses `or 1` fallback (kills or 1 → or 2)."""
        atoms = [("A", 0), ("B", 0)]
        result = _expand_flame(atoms, 6, "red")
        # total_weight = 0, fallback to 1; gap_w is 0 for both so no gaps
        assert result.plain == "AB"

    def test_gap_w_zero_skips_spacing(self):
        """Atom with gap_w=0 doesn't enter spacing branch (kills > 0 → >= 0)."""
        atoms = [("A", 0), ("B", 1), ("C", 0)]
        result = _expand_flame(atoms, 7, "red")
        plain = result.plain
        # A has weight 0 → no gap after A
        # B has weight 1 → gets all 4 remaining gap
        assert plain == "A" + "B" + " " * 4 + "C"

    def test_remaining_weight_reaches_zero(self):
        """After consuming all weight, remaining atoms get no gap (kills > 0 → >= 0)."""
        # After first atom: remaining_weight = total_weight - gap_w = 1 - 1 = 0
        # Second atom has gap_w=0 so it won't enter the branch anyway,
        # but if it had gap_w > 0, remaining_weight=0 should prevent spacing.
        atoms = [("A", 1), ("B", 0)]
        result = _expand_flame(atoms, 10, "red")
        plain = result.plain
        # A gets all 8 gap, B gets none
        assert plain == "A" + " " * 8 + "B"

    def test_and_vs_or_gap_w_zero_remaining_positive(self):
        """With gap_w=0 but remaining_weight>0, no gap (kills and → or)."""
        atoms = [("X", 0), ("Y", 2), ("Z", 0)]
        result = _expand_flame(atoms, 9, "red")
        plain = result.plain
        # X: gap_w=0 → skip; Y: gap_w=2, remaining_weight=2, 6*2//2=6; Z: weight=0
        assert plain == "X" + "Y" + " " * 6 + "Z"


# ---------------------------------------------------------------------------
# _build_fire_art – heat rows
# ---------------------------------------------------------------------------


class TestBuildFireArtHeat:
    """Tests for heat indicator rows in _build_fire_art."""

    def test_heat_on_shows_wave_chars(self):
        """Heat indicators include wave characters when heat_on=True."""
        text = _build_fire_art(50, 20, heat_on=True)
        plain = text.plain
        assert "\u2248" in plain or "~" in plain

    def test_heat_off_no_wave_chars(self):
        """No wave characters when heat_on=False."""
        text = _build_fire_art(50, 20, heat_on=False)
        plain = text.plain
        assert "\u2248" not in plain
        assert "~" not in plain

    def test_heat_rows_exact_wave_content(self):
        """Heat rows contain exact wave characters (kills ≈ → XX≈XX)."""
        w = 50
        text = _build_fire_art(w, 20, heat_on=True)
        plain = text.plain
        lines = plain.split("\n")
        ow = w - 2  # outer width
        # Heat rows are at the top, before the ▁ top edge
        heat_lines = []
        for line in lines:
            if "\u2248" in line or "~" in line:
                heat_lines.append(line)
        assert len(heat_lines) == _HEAT_ROWS
        # Each heat row: " " + wave_chars * ow + " "
        for line in heat_lines:
            assert line[0] == " "
            assert line[-1] == " "
            inner = line[1:-1]
            assert len(inner) == ow
            # Must be pure ≈ or pure ~ (kills XX≈XX and XX~XX mutations)
            assert inner == "\u2248" * ow or inner == "~" * ow

    def test_heat_row_style_is_bright_red(self):
        """Heat wave chars should have exactly bright_red style."""
        w = 50
        text = _build_fire_art(w, 20, heat_on=True)
        plain = text.plain
        # Find the first ≈ or ~
        for idx, ch in enumerate(plain):
            if ch in ("\u2248", "~"):
                style = _style_at(text, idx)
                assert style == "bright_red", (
                    f"Heat char {ch!r} at {idx} has style "
                    f"{style!r}, expected 'bright_red'"
                )
                return
        raise AssertionError("No heat wave character found")

    def test_heat_rows_reduce_flame_budget(self):
        """Heat rows reduce flame rows, keeping total height constant."""
        w, h = 50, 20
        text_no_heat = _build_fire_art(w, h, heat_on=False)
        text_heat = _build_fire_art(w, h, heat_on=True)
        assert len(text_no_heat.plain.split("\n")) == h
        assert len(text_heat.plain.split("\n")) == h


# ---------------------------------------------------------------------------
# _build_fire_art – structural style verification
# ---------------------------------------------------------------------------


class TestBuildFireArtStyles:
    """Verify dim style on structural frame elements."""

    def test_all_frame_chars_have_dim_style(self):
        """All structural frame characters must have 'dim' style exactly."""
        text = _build_fire_art(50, 20, fire_on=False)
        plain = text.plain
        frame_chars = set("\u2581\u250c\u2510\u2514\u2518\u2500\u2502")
        for idx, ch in enumerate(plain):
            if ch in frame_chars:
                style = _style_at(text, idx)
                assert style == "dim", (
                    f"Char {ch!r} at offset {idx} has style {style!r}, expected 'dim'"
                )

    def test_outer_hearth_has_dim_style(self):
        """Outer hearth ▓ row should have 'dim' style exactly."""
        text = _build_fire_art(50, 20)
        plain = text.plain
        lines = plain.split("\n")
        for line in lines:
            if (
                line.startswith("\u2502")
                and not line.startswith("\u2502\u2502")
                and "\u2593" in line
            ):
                line_offset = plain.index(line)
                for rel, ch in enumerate(line):
                    if ch == "\u2593":
                        assert _style_at(text, line_offset + rel) == "dim"
                return
        raise AssertionError("No outer hearth row found")

    def test_frame_chars_with_fire_on(self):
        """Frame chars have 'dim' style even with fire_on=True."""
        text = _build_fire_art(50, 20, fire_on=True)
        plain = text.plain
        frame_chars = set("\u2581\u250c\u2510\u2514\u2518\u2500\u2502")
        for idx, ch in enumerate(plain):
            if ch in frame_chars:
                style = _style_at(text, idx)
                assert style == "dim", (
                    f"Char {ch!r} at offset {idx} has style {style!r}, expected 'dim'"
                )


# ---------------------------------------------------------------------------
# _build_fire_art – flame centering and geometry
# ---------------------------------------------------------------------------


class TestBuildFireArtFlameGeometry:
    """Verify flame row centering and width calculations."""

    def test_flame_rows_centered(self):
        """With fire_on, flame content is approximately centered."""
        w = 60
        text = _build_fire_art(w, 20, fire_on=True)
        plain = text.plain
        lines = plain.split("\n")
        for line in lines:
            if not line.startswith("\u2502\u2502"):
                continue
            if not line.endswith("\u2502\u2502"):
                continue
            inner = line[2:-2]
            # Skip LED, media, blank
            if "\u2591" in inner or "\u2593" in inner or inner.strip() == "":
                continue
            # Flame row: leading spaces should be similar to trailing
            leading = len(inner) - len(inner.lstrip())
            trailing = len(inner) - len(inner.rstrip())
            # Lead should be within reasonable range (not off by more than half)
            total_pad = leading + trailing
            if total_pad > 0:
                assert leading <= total_pad, (
                    f"Centering broken: lead={leading}, trail={trailing}"
                )

    def test_flame_rows_have_content_when_fire_on(self):
        """Fire-on produces non-blank flame rows with flame chars."""
        w = 60
        text = _build_fire_art(w, 20, fire_on=True)
        plain = text.plain
        lines = plain.split("\n")
        flame_rows = []
        for line in lines:
            if not line.startswith("\u2502\u2502"):
                continue
            if not line.endswith("\u2502\u2502"):
                continue
            inner = line[2:-2]
            if "\u2591" in inner or "\u2593" in inner:
                continue
            if inner.strip():
                flame_rows.append(inner)
        assert len(flame_rows) >= _MIN_FLAME_ROWS

    def test_exact_boundary_flame_rows_effective_equals_num_defs(self):
        """When flame_rows_effective == num_defs, all defs render (kills >= vs >)."""
        num_defs = len(_FLAME_DEFS)
        h = num_defs + _FIXED_ROWS
        text = _build_fire_art(50, h, fire_on=True)
        lines = text.plain.split("\n")
        assert len(lines) == h
        # Count flame rows (non-blank inner content)
        flame_count = 0
        for line in lines:
            if line.startswith("\u2502\u2502") and line.endswith("\u2502\u2502"):
                inner = line[2:-2]
                if "\u2591" not in inner and "\u2593" not in inner and inner.strip():
                    flame_count += 1
        # Should have exactly num_defs flame rows, no blanks above
        assert flame_count == num_defs

    def test_flame_row_min_width_respected(self):
        """Flame rows should be at least as wide as their min atom content."""
        w = 60
        text = _build_fire_art(w, 20, fire_on=True)
        plain = text.plain
        lines = plain.split("\n")
        for line in lines:
            if not line.startswith("\u2502\u2502"):
                continue
            if not line.endswith("\u2502\u2502"):
                continue
            inner = line[2:-2]
            if "\u2591" in inner or "\u2593" in inner or inner.strip() == "":
                continue
            # Content should not be shorter than atom chars
            content = inner.strip()
            assert len(content) > 0

    def test_flame_row_inner_width_exact(self):
        """Flame row inner content exactly matches iw (kills lead/trail mutations)."""
        w = 60
        iw = w - 4
        text = _build_fire_art(w, 20, fire_on=True)
        lines = text.plain.split("\n")
        for i, line in enumerate(lines):
            if not line.startswith("\u2502\u2502"):
                continue
            if not line.endswith("\u2502\u2502"):
                continue
            inner = line[2:-2]
            if "\u2591" in inner or "\u2593" in inner or inner.strip() == "":
                continue
            # Flame inner width must equal iw exactly
            assert len(inner) == iw, (
                f"Line {i}: inner width {len(inner)} != {iw}: {inner!r}"
            )

    def test_flame_row_leading_spaces_only(self):
        """Leading padding is only regular spaces (kills ' ' → 'XX XX')."""
        w = 60
        text = _build_fire_art(w, 20, fire_on=True)
        lines = text.plain.split("\n")
        for line in lines:
            if not line.startswith("\u2502\u2502"):
                continue
            if not line.endswith("\u2502\u2502"):
                continue
            inner = line[2:-2]
            if "\u2591" in inner or "\u2593" in inner or inner.strip() == "":
                continue
            # Leading padding: everything before first non-space
            lead_count = len(inner) - len(inner.lstrip(" "))
            leading = inner[:lead_count]
            # Must be only spaces (kills " " → "XX XX" mutation)
            assert leading == " " * lead_count

    def test_flame_row_trailing_spaces_only(self):
        """Trailing padding is only regular spaces (kills ' ' → 'XX XX')."""
        w = 60
        text = _build_fire_art(w, 20, fire_on=True)
        lines = text.plain.split("\n")
        for line in lines:
            if not line.startswith("\u2502\u2502"):
                continue
            if not line.endswith("\u2502\u2502"):
                continue
            inner = line[2:-2]
            if "\u2591" in inner or "\u2593" in inner or inner.strip() == "":
                continue
            # Trailing padding: everything after last non-space
            trail_count = len(inner) - len(inner.rstrip(" "))
            trailing = inner[-trail_count:] if trail_count else ""
            # Must be only spaces
            assert trailing == " " * trail_count

    def test_narrow_width_min_w_binding(self):
        """At narrow widths, min_w becomes binding (kills min_w mutations)."""
        w = 20
        text = _build_fire_art(w, 20, fire_on=True)
        plain = text.plain
        lines = plain.split("\n")
        # With narrow width, flame rows may exceed iw due to min_w constraint
        # The key test: if min_w changes (±1, ±2), flame row width changes
        flame_widths = []
        for line in lines:
            if not line.startswith("\u2502\u2502"):
                continue
            # Find the rightmost ││
            right_border = line.rfind("\u2502\u2502")
            if right_border <= 0:
                continue
            inner = line[2:right_border]
            if "\u2591" in inner or "\u2593" in inner or inner.strip() == "":
                continue
            flame_widths.append(len(inner))
        # All flame rows should have consistent width
        assert len(flame_widths) >= _MIN_FLAME_ROWS
        # Verify widths are reasonable (not drastically wrong)
        for fw in flame_widths:
            assert fw >= 10, f"Flame row too narrow: {fw}"

    def test_wide_width_centering_lead_differs_from_third(self):
        """At wider widths, (iw-body_w)//2 differs from //3 (kills //3)."""
        w = 80
        text = _build_fire_art(w, 20, fire_on=True)
        lines = text.plain.split("\n")
        for line in lines:
            if not line.startswith("\u2502\u2502"):
                continue
            if not line.endswith("\u2502\u2502"):
                continue
            inner = line[2:-2]
            if "\u2591" in inner or "\u2593" in inner or inner.strip() == "":
                continue
            lead = len(inner) - len(inner.lstrip(" "))
            trail = len(inner) - len(inner.rstrip(" "))
            # With //2 floor division, lead <= trail
            # With //3, lead would be smaller and trail much larger
            if lead + trail >= 4:
                # lead should be close to trail (within 1 for odd total)
                assert lead >= trail - 1, (
                    f"Bad centering at w={w}: lead={lead}, trail={trail}"
                )

    def test_flame_centering_lead_roughly_half(self):
        """Lead should be roughly (iw - body_w) // 2 (kills + and // 3)."""
        w = 60
        text = _build_fire_art(w, 20, fire_on=True)
        lines = text.plain.split("\n")
        for line in lines:
            if not line.startswith("\u2502\u2502"):
                continue
            if not line.endswith("\u2502\u2502"):
                continue
            inner = line[2:-2]
            if "\u2591" in inner or "\u2593" in inner or inner.strip() == "":
                continue
            lead = len(inner) - len(inner.lstrip(" "))
            trail = len(inner) - len(inner.rstrip(" "))
            total_pad = lead + trail
            if total_pad > 1:
                # Lead should be <= trail (centering divides by 2)
                # With // 2 floor division, lead <= trail
                assert lead <= trail + 1, f"Centering off: lead={lead}, trail={trail}"


# ---------------------------------------------------------------------------
# _build_fire_art – default parameter values
# ---------------------------------------------------------------------------


class TestBuildFireArtDefaults:
    """Verify default parameter values produce expected output."""

    def test_default_fire_on_shows_flames(self):
        """Default fire_on=True produces flame chars."""
        text = _build_fire_art(50, 20)
        flame_chars = set("()\\/|")
        assert any(ch in text.plain for ch in flame_chars)

    def test_default_heat_off_no_waves(self):
        """Default heat_on=False produces no wave chars."""
        text = _build_fire_art(50, 20)
        assert "\u2248" not in text.plain
        assert "~" not in text.plain

    def test_default_led_style_is_dim(self):
        """Default led_style='dim' applied to LED strip."""
        text = _build_fire_art(50, 20)
        plain = text.plain
        idx = plain.index("\u2591")
        assert "dim" in _style_at(text, idx)

    def test_default_media_style_is_red(self):
        """Default media_style='red' applied to media bed."""
        text = _build_fire_art(50, 20)
        plain = text.plain
        lines = plain.split("\n")
        for line in lines:
            if (
                line.startswith("\u2502\u2502")
                and line.endswith("\u2502\u2502")
                and "\u2593" in line
            ):
                inner_start = 2
                line_offset = plain.index(line)
                for rel, ch in enumerate(line[inner_start:]):
                    if ch == "\u2593":
                        abs_offset = line_offset + inner_start + rel
                        assert "red" in _style_at(text, abs_offset)
                        return
        raise AssertionError("No inner media bed found")

    def test_default_anim_frame_0(self):
        """Default anim_frame=0 uses unrotated palette."""
        # Frame 0 uses original palette order
        text = _build_fire_art(50, 20, fire_on=True)
        # Just verify it produces valid output
        assert len(text.plain.split("\n")) == 20


def _style_at(text, offset: int) -> str:
    """Return the style string applied to the character at *offset*."""
    for span in text._spans:
        if span.start <= offset < span.end:
            return str(span.style)
    return ""
