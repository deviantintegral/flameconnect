"""Shared fixtures for flameconnect tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from flameconnect.auth import TokenAuth

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def token_auth() -> TokenAuth:
    """Return a TokenAuth instance with a static test token."""
    return TokenAuth("test-token-123")


@pytest.fixture
def get_fires_json() -> list[dict]:
    """Load the get_fires fixture JSON."""
    return json.loads((FIXTURES_DIR / "get_fires.json").read_text())


@pytest.fixture
def get_fire_overview_json() -> dict:
    """Load the get_fire_overview fixture JSON."""
    return json.loads((FIXTURES_DIR / "get_fire_overview.json").read_text())
