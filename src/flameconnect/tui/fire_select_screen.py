"""Fire selection modal for the FlameConnect TUI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from flameconnect.models import Fire
from flameconnect.tui.widgets import _display_name

if TYPE_CHECKING:
    from textual.app import ComposeResult

_CSS = """
FireSelectScreen {
    align: center middle;
}

#fire-select-dialog {
    width: 60;
    height: auto;
    max-height: 80%;
    padding: 1 2;
    border: thick $primary;
    background: $surface;
}

#fire-select-title {
    text-align: center;
    text-style: bold;
    margin-bottom: 1;
}

#fire-select-list {
    height: auto;
}

#fire-select-list Button {
    width: 100%;
    margin: 0 0 1 0;
}
"""


class FireSelectScreen(ModalScreen[Fire | None]):
    """Modal screen for selecting a fireplace from the list."""

    CSS = _CSS

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("1", "select_fire(1)", "Fire 1"),
        ("2", "select_fire(2)", "Fire 2"),
        ("3", "select_fire(3)", "Fire 3"),
        ("4", "select_fire(4)", "Fire 4"),
        ("5", "select_fire(5)", "Fire 5"),
        ("6", "select_fire(6)", "Fire 6"),
        ("7", "select_fire(7)", "Fire 7"),
        ("8", "select_fire(8)", "Fire 8"),
        ("9", "select_fire(9)", "Fire 9"),
    ]

    def __init__(
        self,
        fires: list[Fire],
        current_fire_id: str,
        name: str | None = None,
    ) -> None:
        super().__init__(name=name)
        self._fires = fires
        self._current_fire_id = current_fire_id

    def compose(self) -> ComposeResult:
        with Vertical(id="fire-select-dialog"):
            yield Static("Switch Fireplace", id="fire-select-title")
            with Vertical(id="fire-select-list"):
                for idx, fire in enumerate(self._fires):
                    conn = _display_name(fire.connection_state)
                    label = (
                        f"{idx + 1}. {fire.friendly_name}"
                        f" \u2014 {fire.brand} {fire.product_model}"
                        f" ({conn})"
                    )
                    variant = (
                        "primary"
                        if fire.fire_id == self._current_fire_id
                        else "default"
                    )
                    yield Button(
                        label,
                        id=f"fire-{idx}",
                        variant=variant,
                    )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id and button_id.startswith("fire-"):
            idx = int(button_id.removeprefix("fire-"))
            self._select_by_index(idx)

    def _select_by_index(self, idx: int) -> None:
        if idx < 0 or idx >= len(self._fires):
            return
        fire = self._fires[idx]
        if fire.fire_id == self._current_fire_id:
            self.dismiss(None)
        else:
            self.dismiss(fire)

    def action_select_fire(self, number: int) -> None:
        self._select_by_index(number - 1)

    def action_cancel(self) -> None:
        self.dismiss(None)
