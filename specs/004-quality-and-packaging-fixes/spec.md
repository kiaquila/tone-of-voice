# Spec — 004 Quality And Packaging Fixes

## Goal

Address critic and reviewer feedback against the v1 bootstrap so the repository is ready for Phase 2 work without dragging packaging debt or guard inconsistencies forward.

## Scope

In scope:

- packaging metadata (`pyproject.toml`) so the project is installable and tests can drop `sys.path` hacks
- defensive validation of Telegram credentials
- correctness of the emoji signal in baseline metrics
- consistency between the bash docs guard and the Python feature-memory guard
- workflow hygiene (pinned action versions, comments)
- broader unit test coverage for `config`, `telegram_export`, and `check_feature_memory`
- developer ergonomics: `requirements-dev.txt`, expanded `.gitignore`, `argparse` for the feature-memory guard

Out of scope:

- new product features (drafting, refresh log, eval loop)
- runtime infrastructure or deployment changes
- voice snapshot updates

## Requirements

1. The repository must expose a standard `pyproject.toml` with a `[project]` table so `pip install -e .` works and tests/scripts import the package without modifying `sys.path`.
2. `ensure_telegram_credentials` must surface a clear `RuntimeError` when `TELEGRAM_API_ID` is set to a non-integer value.
3. The emoji signal in `compute_corpus_metrics` must use a single, well-formed regex that covers the standard emoji unicode blocks instead of an ad-hoc range with literal emoji.
4. The bash docs guard, the Python `check_feature_memory` script, and the docs guard's tracked-file list must agree on which top-level files (e.g. `README.md`, `pyproject.toml`, `requirements-dev.txt`) require feature memory.
5. Workflow files must use consistent `actions/checkout` versions, and SHA-pinned third-party actions must annotate the version in a comment.
6. `.gitignore` must cover Python build artifacts and tooling caches (`*.egg-info/`, `dist/`, `build/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`).
7. `tone_of_voice.config`, `tone_of_voice.telegram_export.ensure_telegram_credentials`, and `scripts/check_feature_memory.py` must each have unit tests covering happy path and at least one error case.
8. The fallback path for sibling-repo `.env` reuse in `default_env_candidates` must be overridable via an environment variable so it does not silently couple the project to a fixed local layout.

## Acceptance Criteria

- `pip install -e '.[dev]'` installs the package and dev dependencies cleanly.
- `python -m pytest tests` passes locally with all new tests green.
- PR Guard, OSV Scan, and AI Review workflows continue to pass on the resulting PR.
- `docs/05-roadmap.md` reflects the post-bootstrap status accurately.
