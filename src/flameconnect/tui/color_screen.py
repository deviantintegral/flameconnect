"""Reusable RGBW colour picker modal for the FlameConnect TUI."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

from flameconnect.models import NAMED_COLORS, RGBWColor

if TYPE_CHECKING:
    from textual.app import ComposeResult

_ButtonVariant = Literal["default", "primary", "success", "warning", "error"]

# Preset layout: (key letter, display label, dark name, light name)
_PRESET_COLS: list[tuple[str, str, str, str]] = [
    ("R", "Red", "dark-red", "light-red"),
    ("Y", "Yellow", "dark-yellow", "light-yellow"),
    ("G", "Green", "dark-green", "light-green"),
    ("C", "Cyan", "dark-cyan", "light-cyan"),
    ("B", "Blue", "dark-blue", "light-blue"),
    ("P", "Purple", "dark-purple", "light-purple"),
    ("K", "Pink", "dark-pink", "light-pink"),
]

_CSS = """
ColorScreen {
    align: center middle;
}

#color-dialog {
    width: 70;
    height: auto;
    padding: 1 2;
    border: thick $primary;
    background: $surface;
}

#color-title {
    text-align: center;
    text-style: bold;
    margin-bottom: 1;
}

#dark-presets Button, #light-presets Button {
    margin: 0 1;
    min-width: 10;
}

#rgbw-inputs Input {
    width: 8;
    margin: 0 1;
}
"""


class ColorScreen(ModalScreen[RGBWColor | None]):
    """Modal screen for selecting an RGBW colour via presets or numeric input."""

    CSS = _CSS

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("r", "select_preset('dark-red')", "Dark Red"),
        ("R", "select_preset('light-red')", "Light Red"),
        ("y", "select_preset('dark-yellow')", "Dark Yellow"),
        ("Y", "select_preset('light-yellow')", "Light Yellow"),
        ("g", "select_preset('dark-green')", "Dark Green"),
        ("G", "select_preset('light-green')", "Light Green"),
        ("c", "select_preset('dark-cyan')", "Dark Cyan"),
        ("C", "select_preset('light-cyan')", "Light Cyan"),
        ("b", "select_preset('dark-blue')", "Dark Blue"),
        ("B", "select_preset('light-blue')", "Light Blue"),
        ("p", "select_preset('dark-purple')", "Dark Purple"),
        ("P", "select_preset('light-purple')", "Light Purple"),
        ("k", "select_preset('dark-pink')", "Dark Pink"),
        ("K", "select_preset('light-pink')", "Light Pink"),
    ]

    def __init__(
        self,
        current: RGBWColor,
        title: str,
        name: str | None = None,
    ) -> None:
        super().__init__(name=name)
        self._current = current
        self._title = title

    def compose(self) -> ComposeResult:
        cur = self._current
        with Vertical(id="color-dialog"):
            yield Static(
                f"{self._title} (current: R={cur.red} G={cur.green} "
                f"B={cur.blue} W={cur.white})",
                id="color-title",
            )
            yield Static("Dark Presets:")
            with Horizontal(id="dark-presets"):
                for key, label, dark_name, _light_name in _PRESET_COLS:
                    yield Button(
                        f"[{key}] {label}",
                        id=f"preset-{dark_name}",
                    )
            yield Static("Light Presets (Shift+letter):")
            with Horizontal(id="light-presets"):
                for key, label, _dark_name, light_name in _PRESET_COLS:
                    yield Button(
                        f"[{key}] {label}",
                        id=f"preset-{light_name}",
                    )
            yield Static("Custom RGBW:")
            with Horizontal(id="rgbw-inputs"):
                yield Static("R:")
                yield Input(
                    str(cur.red), id="input-r", type="integer",
                )
                yield Static("G:")
                yield Input(
                    str(cur.green), id="input-g", type="integer",
                )
                yield Static("B:")
                yield Input(
                    str(cur.blue), id="input-b", type="integer",
                )
                yield Static("W:")
                yield Input(
                    str(cur.white), id="input-w", type="integer",
                )
            with Horizontal(id="rgbw-actions"):
                yield Button("Set", id="set-rgbw", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id and button_id.startswith("preset-"):
            preset_name = button_id.removeprefix("preset-")
            self.dismiss(NAMED_COLORS[preset_name])
        elif button_id == "set-rgbw":
            self._apply_custom_rgbw()

    def _apply_custom_rgbw(self) -> None:
        """Validate RGBW inputs and dismiss with the custom colour."""
        try:
            r = int(self.query_one("#input-r", Input).value)
            g = int(self.query_one("#input-g", Input).value)
            b = int(self.query_one("#input-b", Input).value)
            w = int(self.query_one("#input-w", Input).value)
        except ValueError:
            self.notify("RGBW values must be integers 0-255", severity="error")
            return
        if not all(0 <= v <= 255 for v in (r, g, b, w)):
            self.notify("RGBW values must be integers 0-255", severity="error")
            return
        self.dismiss(RGBWColor(red=r, green=g, blue=b, white=w))

    def action_select_preset(self, preset_name: str) -> None:
        self.dismiss(NAMED_COLORS[preset_name])

    def action_cancel(self) -> None:
        self.dismiss(None)
