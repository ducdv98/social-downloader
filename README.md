# social-downloader

Paste a social media link, get the media back. A Python port of the [cobalt](https://github.com/imput-net/cobalt) API.

> Learning project: built step by step to learn Python, with industry-standard tooling (typed, tested, deployable). Not usable yet. See `docs/ROADMAP.md` for progress.

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12+.

```sh
uv sync                       # create .venv and install dependencies
uv run pre-commit install     # enable git hooks (once per clone)
```

## Checks

```sh
uv run ruff check             # lint
uv run ruff format --check    # formatting (drop --check to apply)
uv run mypy src tests         # types (strict)
uv run pytest                 # tests
```

The same checks run in CI on every push to `main` and every pull request.
