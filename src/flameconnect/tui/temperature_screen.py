"""Temperature adjustment modal for the FlameConnect TUI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

from flameconnect.models import TempUnit
from flameconnect.tui.widgets import ArrowNavMixin

if TYPE_CHECKING:
    from textual.app import ComposeResult


def _convert_temp(celsius: float, unit: TempUnit) -> float:
    """Convert a Celsius temperature for display.

    Returns the value unchanged when *unit* is CELSIUS, or
    converts to Fahrenheit (rounded to 1 decimal) when FAHRENHEIT.
    """
    if unit == TempUnit.CELSIUS:
        return celsius
    return round(celsius * 9 / 5 + 32, 1)


def _convert_to_celsius(
    fahrenheit: float,
) -> float:
    """Convert a Fahrenheit value back to Celsius (rounded to 1 dp)."""
    return round((fahrenheit - 32) * 5 / 9, 1)

_CSS = """
TemperatureScreen {
    align: center middle;
}

#temp-dialog {
    width: 50;
    height: auto;
    padding: 1 2;
    border: thick $primary;
    background: $surface;
}

#temp-title {
    text-align: center;
    text-style: bold;
    margin-bottom: 1;
}

#temp-input {
    width: 1fr;
    margin-bottom: 1;
}

#temp-range {
    text-align: center;
    margin-bottom: 1;
    color: $text-muted;
}

#temp-buttons {
    height: auto;
    align: center middle;
}

#temp-buttons Button {
    margin: 0 1;
    min-width: 16;
}
"""


class TemperatureScreen(ArrowNavMixin, ModalScreen[float | None]):
    """Modal screen for adjusting the heater setpoint temperature."""

    CSS = _CSS

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(
        self,
        current_temp: float,
        unit: TempUnit,
        name: str | None = None,
    ) -> None:
        super().__init__(name=name)
        self._current_temp = current_temp
        self._unit = unit

    def compose(self) -> ComposeResult:
        unit_str = "\u00b0C" if self._unit == TempUnit.CELSIUS else "\u00b0F"
        celsius = self._unit == TempUnit.CELSIUS
        range_str = "5.0 \u2013 35.0" if celsius else "40.0 \u2013 95.0"
        display_temp = _convert_temp(
            self._current_temp, self._unit
        )
        with Vertical(id="temp-dialog"):
            yield Static(
                f"Set Temperature (current: {display_temp}{unit_str})",
                id="temp-title",
            )
            yield Input(
                value=str(display_temp),
                placeholder=f"Enter temperature ({range_str} {unit_str})",
                type="number",
                id="temp-input",
            )
            yield Static(
                f"Valid range: {range_str} {unit_str}",
                id="temp-range",
            )
            with Horizontal(id="temp-buttons"):
                yield Button("Set", variant="primary", id="set-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    def _validate_and_dismiss(self) -> None:
        """Validate input and dismiss with the temperature value."""
        input_widget = self.query_one("#temp-input", Input)
        try:
            temp = float(input_widget.value)
        except ValueError:
            self.notify("Please enter a valid number", severity="error")
            return
        if self._unit == TempUnit.CELSIUS:
            min_t, max_t = 5.0, 35.0
        else:
            min_t, max_t = 40.0, 95.0
        if not (min_t <= temp <= max_t):
            self.notify(
                f"Temperature must be between {min_t} and {max_t}",
                severity="error",
            )
            return
        # Convert back to Celsius for the device when unit is Fahrenheit.
        if self._unit == TempUnit.FAHRENHEIT:
            temp = _convert_to_celsius(temp)
        self.dismiss(temp)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "set-btn":
            self._validate_and_dismiss()
        elif event.button.id == "cancel-btn":
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._validate_and_dismiss()

    def action_cancel(self) -> None:
        self.dismiss(None)
