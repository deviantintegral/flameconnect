"""Tests for the responsive TUI layout."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from textual.app import App
from textual.containers import Container, VerticalScroll

from flameconnect.models import ConnectionState, Fire
from flameconnect.tui.screens import DashboardScreen


def _make_fire() -> Fire:
    return Fire(
        fire_id="test-001",
        friendly_name="Test Fire",
        brand="Test",
        product_model="T100",
        product_type="Test Type",
        item_code="TC001",
        connection_state=ConnectionState.CONNECTED,
        with_heat=True,
        is_iot_fire=True,
    )


def _make_client() -> MagicMock:
    client = MagicMock()
    client.get_fire_overview = AsyncMock(side_effect=Exception("not wired"))
    return client


class ResponsiveApp(App[None]):
    """Minimal app for testing DashboardScreen layout."""

    def on_mount(self) -> None:
        fire = _make_fire()
        client = _make_client()
        self.push_screen(DashboardScreen(client, fire))


class TestComposeStructure:
    """Verify compose() produces the correct widget hierarchy."""

    async def test_status_section_is_container(self):
        app = ResponsiveApp()
        async with app.run_test(size=(120, 40)):
            screen = app.screen
            section = screen.query_one("#status-section")
            assert type(section) is Container

    async def test_param_scroll_wraps_param_panel(self):
        app = ResponsiveApp()
        async with app.run_test(size=(120, 40)):
            screen = app.screen
            scroll = screen.query_one("#param-scroll")
            assert isinstance(scroll, VerticalScroll)
            panel = scroll.query_one("#param-panel")
            assert panel is not None


class TestCompactClassToggling:
    """Verify on_resize toggles the .compact CSS class."""

    async def test_compact_at_small_width(self):
        app = ResponsiveApp()
        async with app.run_test(size=(80, 40)):
            screen = app.screen
            assert "compact" in screen.classes

    async def test_compact_at_small_height(self):
        app = ResponsiveApp()
        async with app.run_test(size=(120, 24)):
            screen = app.screen
            assert "compact" in screen.classes

    async def test_no_compact_at_large_size(self):
        app = ResponsiveApp()
        async with app.run_test(size=(120, 40)):
            screen = app.screen
            assert "compact" not in screen.classes

    async def test_boundary_not_compact(self):
        """Exactly 100x30 should NOT be compact."""
        app = ResponsiveApp()
        async with app.run_test(size=(100, 30)):
            screen = app.screen
            assert "compact" not in screen.classes
