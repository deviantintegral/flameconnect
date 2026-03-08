# Agents

FlameConnect is an async Python library for controlling Dimplex, Faber, and Real Flame fireplaces via the Flame Connect cloud API. It includes a CLI and an optional TUI dashboard.

## Package Management

This project uses [`uv`](https://docs.astral.sh/uv/) for package management. Do **not** use `pip` directly.

Install dependencies with:

```bash
uv sync --dev
```

After syncing, install pre-commit hooks:

```bash
uv run pre-commit install --install-hooks
```

Add packages with:

```bash
uv add <package>
```

## Pull Requests

Use [conventional commit](https://www.conventionalcommits.org/) formatting for pull request titles and descriptions. The pull request title and description should typically match the message and description of the first commit.

## Development

```bash
# Lint and type-check
uv run ruff check .
uv run mypy src/

# Run tests
uv run pytest
```

## Architecture

- The library is async-first, using `aiohttp` for HTTP communication.
- Authentication is handled via `msal` against Azure AD B2C.
- The optional TUI is built with the `textual` framework (installed via the `tui` extra).
- Strict `mypy` type checking is enforced across the entire `src/` directory.
- Test coverage must remain at or above 95%.
- New code must include corresponding tests.

