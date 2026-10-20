# Runbook

Procedures for case-studies. `README.md` describes what each command does; this file says when
to run it and in what order.

## On open

```bash
git status --short
git log -3 --oneline
```

## On close

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
uv run pytest -q
```

## Run

`uv run memos site`, then open `site/index.html`. No network is needed.

## Refresh a snapshot

1. `uv run memos extract-taxi` or `uv run memos extract-cfpb` (network; the taxi extract
   reads about 700 MB).
2. `uv run pytest`. The pins in `tests/test_memos.py` fail when a figure moved: re-read the
   memo, update the quoted figures in the memo module and its template, then the pins.
3. Commit the snapshot, the memo and the tests together.

## Release

Follows `~/developer/hq/CONVENTIONS.md` §Versioning.

1. Bump `version` in `pyproject.toml` and `__version__` in `src/case_studies/__init__.py`,
   then `uv lock` (CI installs with `--locked`).
2. Commit `chore: Release vX.Y.Z`, tag `git tag -a vX.Y.Z`, push `main` and the tag.
3. `gh release create vX.Y.Z` with handwritten notes; mark it latest.

## Deploy

Nothing by hand. Every push to `main` runs CI (lint, tests, site render) and deploys the
rendered site to GitHub Pages. `gh run list --limit 3` shows whether it landed.

## Restore on a new machine

1. Clone the repo, `uv sync`.
2. `uv run memos site`. There are no keys and no downloads: the snapshots are committed.

## Validate

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src/
uv run pytest
uv run memos site
python3 ~/.claude/scripts/doc-check.py --repo .
```
