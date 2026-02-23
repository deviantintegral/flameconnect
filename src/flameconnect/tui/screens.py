"""Textual screens for the FlameConnect TUI."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from flameconnect.tui.widgets import (
    FireplaceInfo,
    ParameterPanel,
    _format_connection_state,
)

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from flameconnect.client import FlameConnectClient
    from flameconnect.models import FireOverview, ModeParam

_LOGGER = logging.getLogger(__name__)

_DASHBOARD_CSS = """
#dashboard-container {
    padding: 1 2;
}
#fire-info {
    height: auto;
    margin-bottom: 1;
    padding: 1 2;
    border: solid $primary;
}
#param-panel {
    height: auto;
    padding: 1 2;
    border: solid $secondary;
}
#status-bar {
    height: 1;
    dock: bottom;
    background: $surface;
    color: $text-muted;
    padding: 0 2;
}
"""


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

    def compose(self) -> ComposeResult:
        """Compose the dashboard layout."""
        yield Header()
        with Vertical(id="dashboard-container"):
            yield FireplaceInfo(id="fire-info")
            yield ParameterPanel(id="param-panel")
        yield Static("", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Set up auto-refresh and do initial data load."""
        self.set_interval(10, self.refresh_state)
        self.call_after_refresh(self._initial_load)

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

        param_panel = self.query_one("#param-panel", ParameterPanel)
        param_panel.update_parameters(overview.parameters)

        # Track the current mode for power toggle
        for param in overview.parameters:
            if isinstance(param, ModeParam):
                self._current_mode = param
                break

        status_bar = self.query_one("#status-bar", Static)
        status_bar.update(
            "[dim]Press [bold]r[/bold] to refresh  |  "
            "[bold]p[/bold] to toggle power  |  "
            "[bold]q[/bold] to quit[/dim]"
        )

    @property
    def current_mode(self) -> ModeParam | None:
        """Return the current mode parameter, if known."""
        return self._current_mode
