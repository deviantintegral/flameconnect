"""Flame speed selection modal for the FlameConnect TUI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult

_CSS = """
FlameSpeedScreen {
    align: center middle;
}

#flame-speed-dialog {
    width: 40;
    height: auto;
    padding: 1 2;
    border: thick $primary;
    background: $surface;
}

#flame-speed-title {
    text-align: center;
    text-style: bold;
    margin-bottom: 1;
}

#flame-speed-buttons {
    height: auto;
    align: center middle;
}

#flame-speed-buttons Button {
    margin: 0 1;
    min-width: 5;
}
"""


class FlameSpeedScreen(ModalScreen[int | None]):
    """Modal screen for selecting flame speed (1-5)."""

    CSS = _CSS

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("1", "select_speed(1)", "Speed 1"),
        ("2", "select_speed(2)", "Speed 2"),
        ("3", "select_speed(3)", "Speed 3"),
        ("4", "select_speed(4)", "Speed 4"),
        ("5", "select_speed(5)", "Speed 5"),
    ]

    def __init__(self, current_speed: int, name: str | None = None) -> None:
        super().__init__(name=name)
        self._current_speed = current_speed

    def compose(self) -> ComposeResult:
        with Vertical(id="flame-speed-dialog"):
            yield Static(
                f"Flame Speed (current: {self._current_speed})",
                id="flame-speed-title",
            )
            with Horizontal(id="flame-speed-buttons"):
                for i in range(1, 6):
                    variant = "primary" if i == self._current_speed else "default"
                    yield Button(str(i), id=f"speed-{i}", variant=variant)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id and button_id.startswith("speed-"):
            speed = int(button_id.removeprefix("speed-"))
            self.dismiss(speed)

    def action_select_speed(self, speed: int) -> None:
        self.dismiss(speed)

    def action_cancel(self) -> None:
        self.dismiss(None)
