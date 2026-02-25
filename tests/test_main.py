"""Tests for the __main__ entry point."""

from __future__ import annotations

from unittest.mock import patch


class TestMainEntryPoint:
    """Test that python -m flameconnect invokes cli.main()."""

    def test_main_calls_cli_main(self):
        """Importing __main__ should call cli.main()."""
        with patch("flameconnect.cli.main") as mock_main:
            # runpy.run_module executes __main__.py as a script
            import runpy

            runpy.run_module("flameconnect", run_name="__main__")
            mock_main.assert_called_once()
