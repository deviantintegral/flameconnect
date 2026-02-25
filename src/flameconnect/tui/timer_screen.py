"""Timer duration modal for the FlameConnect TUI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

from flameconnect.tui.widgets import ArrowNavMixin

if TYPE_CHECKING:
    from textual.app import ComposeResult

_CSS = """
TimerScreen {
    align: center middle;
}

#timer-dialog {
    width: 50;
    height: auto;
    padding: 1 2;
    border: thick $primary;
    background: $surface;
}

#timer-title {
    text-align: center;
    text-style: bold;
    margin-bottom: 1;
}

#timer-input {
    width: 1fr;
    margin-bottom: 1;
}

#timer-range {
    text-align: center;
    margin-bottom: 1;
    color: $text-muted;
}

#timer-buttons {
    height: auto;
    align: center middle;
}

#timer-buttons Button {
    margin: 0 1;
    min-width: 16;
}
"""


class TimerScreen(ArrowNavMixin, ModalScreen[int | None]):
    """Modal screen for setting the timer duration in minutes."""

    CSS = _CSS

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(
        self,
        current_duration: int = 60,
        name: str | None = None,
    ) -> None:
        super().__init__(name=name)
        self._current_duration = current_duration

    def compose(self) -> ComposeResult:
        with Vertical(id="timer-dialog"):
            yield Static("Set Timer Duration", id="timer-title")
            yield Input(
                value=str(self._current_duration),
                placeholder="Enter duration (1 \u2013 480 minutes)",
                type="integer",
                id="timer-input",
            )
            yield Static(
                "Valid range: 1 \u2013 480 minutes",
                id="timer-range",
            )
            with Horizontal(id="timer-buttons"):
                yield Button("Set", variant="primary", id="set-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    def _validate_and_dismiss(self) -> None:
        """Validate input and dismiss with the duration value."""
        input_widget = self.query_one("#timer-input", Input)
        try:
            duration = int(input_widget.value)
        except ValueError:
            self.notify("Please enter a valid number", severity="error")
            return
        if not (1 <= duration <= 480):
            self.notify(
                "Duration must be between 1 and 480 minutes",
                severity="error",
            )
            return
        self.dismiss(duration)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "set-btn":
            self._validate_and_dismiss()
        elif event.button.id == "cancel-btn":
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._validate_and_dismiss()

    def action_cancel(self) -> None:
        self.dismiss(None)
