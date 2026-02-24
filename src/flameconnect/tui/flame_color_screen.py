"""Flame color selection modal for the FlameConnect TUI."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from flameconnect.models import FlameColor

if TYPE_CHECKING:
    from textual.app import ComposeResult

_ButtonVariant = Literal["default", "primary", "success", "warning", "error"]

_COLOR_LABELS: dict[FlameColor, tuple[str, str]] = {
    FlameColor.ALL: ("All", "a"),
    FlameColor.YELLOW_RED: ("Yellow/Red", "y"),
    FlameColor.YELLOW_BLUE: ("Yellow/Blue", "w"),
    FlameColor.BLUE: ("Blue", "b"),
    FlameColor.RED: ("Red", "r"),
    FlameColor.YELLOW: ("Yellow", "e"),
    FlameColor.BLUE_RED: ("Blue/Red", "d"),
}

_CSS = """
FlameColorScreen {
    align: center middle;
}

#flame-color-dialog {
    width: 64;
    height: auto;
    padding: 1 2;
    border: thick $primary;
    background: $surface;
}

#flame-color-title {
    text-align: center;
    text-style: bold;
    margin-bottom: 1;
}

#flame-color-buttons {
    height: auto;
    align: center middle;
}

#flame-color-buttons Button {
    margin: 0 1;
    min-width: 8;
}
"""


class FlameColorScreen(ModalScreen[FlameColor | None]):
    """Modal screen for selecting flame color preset."""

    CSS = _CSS

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("a", "select_color('ALL')", "All"),
        ("y", "select_color('YELLOW_RED')", "Yellow/Red"),
        ("w", "select_color('YELLOW_BLUE')", "Yellow/Blue"),
        ("b", "select_color('BLUE')", "Blue"),
        ("r", "select_color('RED')", "Red"),
        ("e", "select_color('YELLOW')", "Yellow"),
        ("d", "select_color('BLUE_RED')", "Blue/Red"),
    ]

    def __init__(self, current_color: FlameColor, name: str | None = None) -> None:
        super().__init__(name=name)
        self._current_color = current_color

    def compose(self) -> ComposeResult:
        current_label = _COLOR_LABELS[self._current_color][0]
        with Vertical(id="flame-color-dialog"):
            yield Static(
                f"Flame Color (current: {current_label})",
                id="flame-color-title",
            )
            with Horizontal(id="flame-color-buttons"):
                for color, (label, key) in _COLOR_LABELS.items():
                    variant: _ButtonVariant = (
                        "primary" if color == self._current_color else "default"
                    )
                    yield Button(
                        f"[{key.upper()}] {label}",
                        id=f"color-{color.name.lower()}",
                        variant=variant,
                    )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id and button_id.startswith("color-"):
            name = button_id.removeprefix("color-").upper()
            self.dismiss(FlameColor[name])

    def action_select_color(self, color_name: str) -> None:
        self.dismiss(FlameColor[color_name])

    def action_cancel(self) -> None:
        self.dismiss(None)
