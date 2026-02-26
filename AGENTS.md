# Agents

## Package Management

This project uses [`uv`](https://docs.astral.sh/uv/) for package management. Do **not** use `pip` directly.

Install dependencies with:

```bash
uv sync --dev
```

Add packages with:

```bash
uv add <package>
```

## Development

```bash
# Lint and type-check
uv run ruff check .
uv run mypy src/

# Run tests
uv run pytest
```
