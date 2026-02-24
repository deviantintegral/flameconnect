"""Textual screens for the FlameConnect TUI."""

from __future__ import annotations

import dataclasses
import logging
from datetime import datetime
from typing import TYPE_CHECKING

from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, RichLog, Static

from flameconnect.tui.widgets import (
    FireplaceInfo,
    FireplaceVisual,
    ParameterPanel,
    _format_connection_state,
)

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from flameconnect.client import FlameConnectClient
    from flameconnect.models import FireOverview, ModeParam, Parameter

_LOGGER = logging.getLogger(__name__)

_LEVEL_MARKUP: dict[int, tuple[str, str]] = {
    logging.DEBUG: ("[dim]", "[/dim]"),
    logging.INFO: ("", ""),
    logging.WARNING: ("[yellow]", "[/yellow]"),
    logging.ERROR: ("[red]", "[/red]"),
    logging.CRITICAL: ("[bold red]", "[/bold red]"),
}

_DASHBOARD_CSS = """
#dashboard-container {
    padding: 1 2;
}
#fire-info {
    height: auto;
    padding: 1 2;
    border: solid $primary;
}
#status-section {
    height: auto;
}
#fireplace-visual {
    width: 1fr;
    padding: 1 2;
    border: solid $primary;
}
#param-panel {
    height: auto;
    width: 2fr;
    padding: 1 2;
    border: solid $secondary;
}
#messages-label {
    height: auto;
    margin-top: 1;
    padding: 0 2;
    text-style: bold;
}
#messages-panel {
    height: 1fr;
    min-height: 4;
    padding: 0 2;
    border: solid $accent;
}
#status-bar {
    height: 1;
    dock: bottom;
    background: $surface;
    color: $text-muted;
    padding: 0 2;
}
"""


class _TuiLogHandler(logging.Handler):
    """Logging handler that writes records into a Textual RichLog widget."""

    def __init__(self, rich_log: RichLog) -> None:
        super().__init__()
        self._rich_log = rich_log

    def emit(self, record: logging.LogRecord) -> None:
        try:
            ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
            msg = self.format(record)
            open_tag, close_tag = _LEVEL_MARKUP.get(
                record.levelno, ("", "")
            )
            self._rich_log.write(
                f"[dim]{ts}[/dim] {open_tag}{msg}{close_tag}",
                shrink=False,
            )
        except Exception:  # noqa: BLE001
            self.handleError(record)


class DashboardScreen(Screen[None]):
    """Main dashboard screen showing fireplace status and parameters.

    Displays the currently selected fireplace with all its decoded
    parameters, auto-refreshing every 10 seconds.
    """

    CSS = _DASHBOARD_CSS

    def __init__(
        self,
        client: FlameConnectClient,
        fire_id: str,
        fire_name: str,
        name: str | None = None,
    ) -> None:
        super().__init__(name=name)
        self.client = client
        self.fire_id = fire_id
        self.fire_name = fire_name
        self._current_mode: ModeParam | None = None
        self._previous_params: dict[type, Parameter] = {}
        self._log_handler: _TuiLogHandler | None = None

    def compose(self) -> ComposeResult:
        """Compose the dashboard layout."""
        yield Header()
        with Vertical(id="dashboard-container"):
            yield FireplaceInfo(id="fire-info")
            with Horizontal(id="status-section"):
                yield FireplaceVisual(id="fireplace-visual")
                yield ParameterPanel(id="param-panel")
            yield Static("[bold]Messages[/bold]", id="messages-label")
            yield RichLog(id="messages-panel", markup=True, wrap=True)
        yield Static("", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Install log handler and do initial data load."""
        rich_log = self.query_one("#messages-panel", RichLog)
        self._log_handler = _TuiLogHandler(rich_log)
        self._log_handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        fc_logger = logging.getLogger("flameconnect")
        fc_logger.addHandler(self._log_handler)

        self.call_after_refresh(self._initial_load)

    def on_unmount(self) -> None:
        """Remove the TUI log handler when the screen is unmounted."""
        if self._log_handler is not None:
            fc_logger = logging.getLogger("flameconnect")
            fc_logger.removeHandler(self._log_handler)
            self._log_handler = None

    def log_message(self, msg: str, level: int = logging.INFO) -> None:
        """Write a timestamped, level-colored message to the messages panel.

        Args:
            msg: The message text (may contain Rich markup).
            level: A :mod:`logging` level constant (DEBUG, INFO, WARNING, ERROR).
        """
        ts = datetime.now().strftime("%H:%M:%S")
        open_tag, close_tag = _LEVEL_MARKUP.get(level, ("", ""))
        rich_log = self.query_one("#messages-panel", RichLog)
        rich_log.write(f"[dim]{ts}[/dim] {open_tag}{msg}{close_tag}", shrink=False)

    async def _initial_load(self) -> None:
        """Perform the initial data load."""
        await self.refresh_state()

    async def refresh_state(self) -> None:
        """Fetch the latest fireplace state and update the display."""
        try:
            overview = await self.client.get_fire_overview(self.fire_id)
            self._update_display(overview)
        except Exception as exc:
            _LOGGER.exception("Failed to refresh fireplace state")
            self.notify(str(exc), severity="error", timeout=5)

    def _update_display(self, overview: FireOverview) -> None:
        """Update all widgets with fresh data from the API.

        Args:
            overview: The latest FireOverview from the API.
        """
        from flameconnect.models import ModeParam

        fire_info = self.query_one("#fire-info", FireplaceInfo)
        fire_info.fire_name = overview.fire.friendly_name
        fire_info.fire_id = overview.fire.fire_id
        fire_info.connection = _format_connection_state(overview.fire.connection_state)
        fire_info.last_updated = datetime.now().strftime("%H:%M:%S")

        param_panel = self.query_one("#param-panel", ParameterPanel)
        param_panel.update_parameters(overview.parameters)

        # Log changed attributes
        current_params: dict[type, Parameter] = {
            type(p): p for p in overview.parameters
        }
        if self._previous_params:
            self._log_param_changes(self._previous_params, current_params)
        self._previous_params = current_params

        # Track the current mode for power toggle
        for param in overview.parameters:
            if isinstance(param, ModeParam):
                self._current_mode = param
                break

        status_bar = self.query_one("#status-bar", Static)
        status_bar.update(
            "[dim]Press [bold]r[/bold]efresh  |  "
            "[bold]p[/bold]ower  |  "
            "[bold]f[/bold]lame speed  |  "
            "[bold]b[/bold]rightness  |  "
            "[bold]h[/bold]eat mode  |  "
            "[bold]t[/bold]imer  |  "
            "temp [bold]u[/bold]nit  |  "
            "[bold]q[/bold]uit[/dim]"
        )

    def _log_param_changes(
        self,
        old: dict[type, Parameter],
        new: dict[type, Parameter],
    ) -> None:
        """Compare old and new parameters, logging any changed fields."""
        for param_type, new_param in new.items():
            old_param = old.get(param_type)
            if old_param is None or old_param == new_param:
                continue
            name = param_type.__name__.removesuffix("Param")
            for field in dataclasses.fields(new_param):
                old_val = getattr(old_param, field.name)
                new_val = getattr(new_param, field.name)
                if old_val != new_val:
                    label = field.name.replace("_", " ").title()
                    self.log_message(f"[bold]{name}[/bold] {label}: {old_val} → {new_val}")

    @property
    def current_parameters(self) -> dict[type, Parameter]:
        """Return the current cached parameters."""
        return dict(self._previous_params)

    @property
    def current_mode(self) -> ModeParam | None:
        """Return the current mode parameter, if known."""
        return self._current_mode
