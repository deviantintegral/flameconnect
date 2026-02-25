"""Media theme selection modal for the FlameConnect TUI."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from flameconnect.models import MediaTheme
from flameconnect.tui.widgets import ArrowNavMixin

if TYPE_CHECKING:
    from textual.app import ComposeResult

_ButtonVariant = Literal["default", "primary", "success", "warning", "error"]

_THEME_LABELS: dict[MediaTheme, tuple[str, str]] = {
    MediaTheme.USER_DEFINED: ("User Defined", "u"),
    MediaTheme.WHITE: ("White", "w"),
    MediaTheme.BLUE: ("Blue", "b"),
    MediaTheme.PURPLE: ("Purple", "p"),
    MediaTheme.RED: ("Red", "r"),
    MediaTheme.GREEN: ("Green", "g"),
    MediaTheme.PRISM: ("Prism", "i"),
    MediaTheme.KALEIDOSCOPE: ("Kaleidoscope", "k"),
    MediaTheme.MIDNIGHT: ("Midnight", "m"),
}

_CSS = """
MediaThemeScreen {
    align: center middle;
}

#media-theme-dialog {
    width: 72;
    height: auto;
    padding: 1 2;
    border: thick $primary;
    background: $surface;
}

#media-theme-title {
    text-align: center;
    text-style: bold;
    margin-bottom: 1;
}

#media-theme-row1, #media-theme-row2 {
    height: auto;
    align: center middle;
}

#media-theme-row1 Button, #media-theme-row2 Button {
    margin: 0 1;
    min-width: 8;
}
"""


class MediaThemeScreen(ArrowNavMixin, ModalScreen[MediaTheme | None]):
    """Modal screen for selecting media theme preset."""

    CSS = _CSS

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("u", "select_theme('USER_DEFINED')", "User Defined"),
        ("w", "select_theme('WHITE')", "White"),
        ("b", "select_theme('BLUE')", "Blue"),
        ("p", "select_theme('PURPLE')", "Purple"),
        ("r", "select_theme('RED')", "Red"),
        ("g", "select_theme('GREEN')", "Green"),
        ("i", "select_theme('PRISM')", "Prism"),
        ("k", "select_theme('KALEIDOSCOPE')", "Kaleidoscope"),
        ("m", "select_theme('MIDNIGHT')", "Midnight"),
    ]

    def __init__(self, current_theme: MediaTheme, name: str | None = None) -> None:
        super().__init__(name=name)
        self._current_theme = current_theme

    def _variant_for(self, theme: MediaTheme) -> _ButtonVariant:
        return "primary" if theme == self._current_theme else "default"

    def compose(self) -> ComposeResult:
        current_label = _THEME_LABELS[self._current_theme][0]
        themes = list(_THEME_LABELS.items())
        row1 = themes[:5]
        row2 = themes[5:]
        with Vertical(id="media-theme-dialog"):
            yield Static(
                f"Media Theme (current: {current_label})",
                id="media-theme-title",
            )
            with Horizontal(id="media-theme-row1"):
                for theme, (label, key) in row1:
                    yield Button(
                        f"[{key.upper()}] {label}",
                        id=f"theme-{theme.name.lower()}",
                        variant=self._variant_for(theme),
                    )
            with Horizontal(id="media-theme-row2"):
                for theme, (label, key) in row2:
                    yield Button(
                        f"[{key.upper()}] {label}",
                        id=f"theme-{theme.name.lower()}",
                        variant=self._variant_for(theme),
                    )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id and button_id.startswith("theme-"):
            name = button_id.removeprefix("theme-").upper()
            self.dismiss(MediaTheme[name])

    def action_select_theme(self, theme_name: str) -> None:
        self.dismiss(MediaTheme[theme_name])

    def action_cancel(self) -> None:
        self.dismiss(None)
