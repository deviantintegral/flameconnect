"""Heat mode selection modal for the FlameConnect TUI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

from flameconnect.models import HeatMode
from flameconnect.tui.widgets import ArrowNavMixin

if TYPE_CHECKING:
    from textual.app import ComposeResult

_CSS = """
HeatModeScreen {
    align: center middle;
}

#heat-mode-dialog {
    width: 45;
    height: auto;
    padding: 1 2;
    border: thick $primary;
    background: $surface;
}

#heat-mode-title {
    text-align: center;
    text-style: bold;
    margin-bottom: 1;
}

#heat-mode-buttons {
    height: auto;
    align: center middle;
}

#heat-mode-buttons Button {
    margin: 0 1;
    min-width: 8;
}

#boost-input-container {
    height: auto;
    margin-top: 1;
    align: center middle;
}

#boost-label {
    text-align: center;
}

#boost-duration {
    width: 20;
}
"""


class HeatModeScreen(ArrowNavMixin, ModalScreen[tuple[HeatMode, int | None] | None]):
    """Modal screen for selecting heat mode (Normal / Eco / Boost)."""

    CSS = _CSS

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("n", "select_mode('normal')", "Normal"),
        ("e", "select_mode('eco')", "Eco"),
        ("b", "select_boost", "Boost"),
    ]

    def __init__(
        self,
        current_mode: HeatMode,
        current_boost: int,
        name: str | None = None,
    ) -> None:
        super().__init__(name=name)
        self._current_mode = current_mode
        self._current_boost = current_boost
        self._boost_input_visible = False

    def compose(self) -> ComposeResult:
        with Vertical(id="heat-mode-dialog"):
            yield Static(
                f"Heat Mode (current:"
                f" {self._current_mode.name.replace('_', ' ').title()})",
                id="heat-mode-title",
            )
            with Horizontal(id="heat-mode-buttons"):
                for mode in (HeatMode.NORMAL, HeatMode.ECO, HeatMode.BOOST):
                    label = mode.name.replace("_", " ").title()
                    variant = "primary" if mode == self._current_mode else "default"
                    yield Button(label, id=f"mode-{mode.name.lower()}", variant=variant)
            with Vertical(id="boost-input-container"):
                yield Static("Boost duration (1-20 min):", id="boost-label")
                yield Input(
                    placeholder="minutes",
                    id="boost-duration",
                    value=str(self._current_boost),
                )

    def on_mount(self) -> None:
        container = self.query_one("#boost-input-container")
        container.display = False

    def _show_boost_input(self) -> None:
        container = self.query_one("#boost-input-container")
        container.display = True
        self._boost_input_visible = True
        boost_input = self.query_one("#boost-duration", Input)
        boost_input.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "mode-normal":
            self.dismiss((HeatMode.NORMAL, None))
        elif button_id == "mode-eco":
            self.dismiss((HeatMode.ECO, None))
        elif button_id == "mode-boost":
            self._show_boost_input()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "boost-duration":
            self._submit_boost(event.value)

    def _submit_boost(self, raw: str) -> None:
        try:
            minutes = int(raw)
        except ValueError:
            self.notify("Please enter a number between 1 and 20", severity="error")
            return
        if not 1 <= minutes <= 20:
            self.notify("Duration must be between 1 and 20 minutes", severity="error")
            return
        self.dismiss((HeatMode.BOOST, minutes))

    def action_select_mode(self, mode_name: str) -> None:
        if mode_name == "normal":
            self.dismiss((HeatMode.NORMAL, None))
        elif mode_name == "eco":
            self.dismiss((HeatMode.ECO, None))

    def action_select_boost(self) -> None:
        if self._boost_input_visible:
            # Already showing input; submit current value
            boost_input = self.query_one("#boost-duration", Input)
            self._submit_boost(boost_input.value)
        else:
            self._show_boost_input()

    def action_cancel(self) -> None:
        self.dismiss(None)
