"""Main Textual application for the FlameConnect TUI."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, OptionList, Static
from textual.widgets.option_list import Option

from flameconnect.tui.auth_screen import AuthScreen
from flameconnect.tui.screens import DashboardScreen

if TYPE_CHECKING:
    import asyncio

    from flameconnect.client import FlameConnectClient
    from flameconnect.models import Fire

_LOGGER = logging.getLogger(__name__)

_APP_CSS = """
#fire-selector {
    margin: 2 4;
}
#loading-label {
    text-align: center;
    margin: 2 4;
    color: $text-muted;
}
"""


class FlameConnectApp(App[None]):
    """Textual TUI application for monitoring and controlling fireplaces."""

    TITLE = "FlameConnect"
    CSS = _APP_CSS

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("p", "toggle_power", "Power On/Off"),
    ]

    def __init__(self, client: FlameConnectClient) -> None:
        super().__init__()
        self.client = client
        self.fire_id: str | None = None
        self.fires: list[Fire] = []

    def compose(self) -> ComposeResult:
        """Compose the initial app layout with fireplace selector."""
        yield Header()
        yield Static("[bold]Loading fireplaces...[/bold]", id="loading-label")
        yield Footer()

    def on_mount(self) -> None:
        """Fetch the list of fireplaces on startup."""
        self.call_after_refresh(self._load_fires)

    async def _load_fires(self) -> None:
        """Fetch fireplaces and either auto-select or show a list."""
        try:
            self.fires = await self.client.get_fires()
        except Exception as exc:
            _LOGGER.exception("Failed to fetch fireplaces")
            self.notify(f"Failed to load fireplaces: {exc}", severity="error")
            return

        loading = self.query_one("#loading-label", Static)

        if not self.fires:
            loading.update("[bold red]No fireplaces found.[/bold red]")
            return

        if len(self.fires) == 1:
            # Auto-select the only fireplace
            fire = self.fires[0]
            self.fire_id = fire.fire_id
            loading.remove()
            self._push_dashboard(fire)
            return

        # Show a selection list
        loading.update("[bold]Select a fireplace:[/bold]")
        options = [
            Option(
                f"{fire.friendly_name} ({fire.connection_state.name})",
                id=fire.fire_id,
            )
            for fire in self.fires
        ]
        selector = OptionList(*options, id="fire-selector")
        await self.mount(selector, before="#loading-label")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle fireplace selection from the option list."""
        option_id = event.option.id
        if option_id is None:
            return

        for fire in self.fires:
            if fire.fire_id == option_id:
                self.fire_id = fire.fire_id
                self._push_dashboard(fire)
                break

    def show_auth_screen(
        self,
        auth_uri: str,
        redirect_uri: str,
        future: asyncio.Future[str],
    ) -> None:
        """Push the authentication modal and resolve *future* on dismiss."""
        from flameconnect.exceptions import AuthenticationError

        screen = AuthScreen(auth_uri=auth_uri, redirect_uri=redirect_uri)

        def _on_dismiss(result: str | None) -> None:
            if future.done():
                return
            if result is None:
                future.set_exception(
                    AuthenticationError("Authentication cancelled")
                )
            else:
                future.set_result(result)

        self.push_screen(screen, callback=_on_dismiss)

    def _push_dashboard(self, fire: Fire) -> None:
        """Push the dashboard screen for the selected fireplace.

        Args:
            fire: The selected Fire instance.
        """
        screen = DashboardScreen(
            client=self.client,
            fire_id=fire.fire_id,
            fire_name=fire.friendly_name,
        )
        self.push_screen(screen)

    async def action_refresh(self) -> None:
        """Handle the 'r' key binding to refresh the dashboard."""
        screen = self.screen
        if isinstance(screen, DashboardScreen):
            await screen.refresh_state()
            self.notify("Refreshed", timeout=2)

    async def action_toggle_power(self) -> None:
        """Handle the 'p' key binding to toggle fireplace power."""
        from flameconnect.models import FireMode

        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return

        if self.fire_id is None:
            self.notify("No fireplace selected", severity="warning")
            return

        current_mode = screen.current_mode
        try:
            if current_mode is not None and current_mode.mode == FireMode.MANUAL:
                await self.client.turn_off(self.fire_id)
                self.notify("Turning off...", timeout=3)
            else:
                await self.client.turn_on(self.fire_id)
                self.notify("Turning on...", timeout=3)
            # Refresh after toggling
            await screen.refresh_state()
        except Exception as exc:
            _LOGGER.exception("Failed to toggle power")
            self.notify(f"Power toggle failed: {exc}", severity="error")


async def run_tui() -> None:
    """Launch the FlameConnect TUI dashboard.

    Creates an authenticated client and runs the Textual application.
    The client session is managed via an async context manager.
    """
    import asyncio

    from flameconnect.auth import MsalAuth
    from flameconnect.client import FlameConnectClient

    app: FlameConnectApp | None = None

    async def _tui_auth_prompt(auth_uri: str, redirect_uri: str) -> str:
        """Show a Textual modal for credential entry.

        Uses an asyncio.Future so the Textual event loop keeps running
        while the user interacts with the auth dialog.
        """
        assert app is not None  # noqa: S101
        loop = asyncio.get_running_loop()
        future: asyncio.Future[str] = loop.create_future()
        app.show_auth_screen(auth_uri, redirect_uri, future)
        return await future

    auth = MsalAuth(prompt_callback=_tui_auth_prompt)
    async with FlameConnectClient(auth=auth) as client:
        app = FlameConnectApp(client)
        await app.run_async()
