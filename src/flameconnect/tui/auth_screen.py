"""Authentication modal screen for the FlameConnect TUI."""

from __future__ import annotations

import logging
import webbrowser
from typing import TYPE_CHECKING

from textual.containers import Vertical

if TYPE_CHECKING:
    from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static

from flameconnect.exceptions import AuthenticationError

_LOGGER = logging.getLogger(__name__)

_AUTH_CSS = """
AuthScreen {
    align: center middle;
}

#auth-dialog {
    width: 64;
    height: auto;
    padding: 1 2;
    border: thick $primary;
    background: $surface;
}

#auth-title {
    text-align: center;
    text-style: bold;
    margin-bottom: 1;
}

#auth-error {
    color: $error;
    margin-top: 1;
    display: none;
}

#auth-status {
    color: $text-muted;
    margin-top: 1;
    display: none;
}

#auth-hint {
    color: $text-muted;
    margin-top: 1;
    display: none;
}

.auth-label {
    margin-top: 1;
}

#sign-in-btn {
    margin-top: 1;
    width: 100%;
}
"""


class AuthScreen(ModalScreen[str | None]):
    """Modal screen for entering authentication credentials.

    Attempts direct B2C credential login first, then falls back to
    browser-based auth with URL paste if credentials fail.
    """

    CSS = _AUTH_CSS

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(
        self,
        auth_uri: str,
        redirect_uri: str,
        name: str | None = None,
    ) -> None:
        super().__init__(name=name)
        self._auth_uri = auth_uri
        self._redirect_uri = redirect_uri
        self._browser_fallback = False

    def compose(self) -> ComposeResult:
        with Vertical(id="auth-dialog"):
            yield Static("Authentication Required", id="auth-title")
            yield Label("Email", classes="auth-label")
            yield Input(placeholder="you@example.com", id="email-input")
            yield Label("Password", classes="auth-label")
            yield Input(placeholder="Password", password=True, id="password-input")
            yield Static("", id="auth-error")
            yield Static("", id="auth-status")
            yield Static("", id="auth-hint")
            yield Button("Sign In", variant="primary", id="sign-in-btn")

    def on_mount(self) -> None:
        self.query_one("#email-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "email-input" and not self._browser_fallback:
            self.query_one("#password-input", Input).focus()
        elif event.input.id in ("password-input", "url-input"):
            self._on_submit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "sign-in-btn":
            self._on_submit()

    def _on_submit(self) -> None:
        if self._browser_fallback:
            self._submit_url()
        else:
            self._submit_credentials()

    def _submit_credentials(self) -> None:
        email_input = self.query_one("#email-input", Input)
        password_input = self.query_one("#password-input", Input)
        email = email_input.value.strip()
        password = password_input.value

        if not email or not password:
            self._show_error("Email and password are required.")
            return

        self._set_inputs_disabled(True)
        self._show_status("Signing in...")
        self._hide_error()
        self.run_worker(
            self._do_credential_login(email, password),
            exclusive=True,
            thread=False,
        )

    async def _do_credential_login(self, email: str, password: str) -> None:
        from flameconnect.b2c_login import b2c_login_with_credentials

        try:
            redirect_url = await b2c_login_with_credentials(
                self._auth_uri, email, password
            )
            self.dismiss(redirect_url)
        except AuthenticationError as exc:
            _LOGGER.debug("Direct login failed: %s", exc)
            self._switch_to_browser_fallback(str(exc))

    def _switch_to_browser_fallback(self, error_msg: str) -> None:
        self._browser_fallback = True

        # Hide credential inputs
        self.query_one("#email-input", Input).display = False
        self.query_one("#password-input", Input).display = False
        for label in self.query(".auth-label"):
            label.display = False

        # Show error explaining why we fell back
        self._show_error(f"Direct login failed: {error_msg}")

        # Mount URL paste input
        btn = self.query_one("#sign-in-btn", Button)
        url_label = Label("Paste redirect URL", classes="auth-label browser-label")
        url_input = Input(placeholder="msal...://auth?code=...", id="url-input")
        self.query_one("#auth-dialog", Vertical).mount(url_label, before=btn)
        self.query_one("#auth-dialog", Vertical).mount(url_input, before=btn)

        # Update button and status
        btn.label = "Submit URL"
        self._show_hint(
            "A browser has been opened. Log in and paste the redirect URL above."
        )
        self._hide_status()
        self._set_inputs_disabled(False)

        # Open browser
        webbrowser.open(self._auth_uri)

        # Focus the new URL input after mount
        self.set_timer(0.1, lambda: self.query_one("#url-input", Input).focus())

    def _submit_url(self) -> None:
        url_input = self.query_one("#url-input", Input)
        url = url_input.value.strip()
        if not url:
            self._show_error("Please paste the redirect URL.")
            return
        self.dismiss(url)

    def action_cancel(self) -> None:
        self.dismiss(None)

    # --- UI helpers ---

    def _show_error(self, msg: str) -> None:
        error = self.query_one("#auth-error", Static)
        error.update(msg)
        error.display = True

    def _hide_error(self) -> None:
        self.query_one("#auth-error", Static).display = False

    def _show_status(self, msg: str) -> None:
        status = self.query_one("#auth-status", Static)
        status.update(msg)
        status.display = True

    def _hide_status(self) -> None:
        self.query_one("#auth-status", Static).display = False

    def _show_hint(self, msg: str) -> None:
        hint = self.query_one("#auth-hint", Static)
        hint.update(msg)
        hint.display = True

    def _set_inputs_disabled(self, disabled: bool) -> None:
        for inp in self.query(Input):
            inp.disabled = disabled
        self.query_one("#sign-in-btn", Button).disabled = disabled
