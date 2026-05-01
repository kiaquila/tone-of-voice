# Plan — 004 Quality And Packaging Fixes

## Approach

Treat the change set as a single review-driven hardening pass. Group fixes by concern so each diff hunk maps to one reviewer finding.

## Steps

1. Add `pyproject.toml` with a `setuptools` build backend, package discovery under `src/`, and a `[tool.pytest.ini_options]` table so tests resolve the package without `sys.path` shims.
2. Strip the three `sys.path.insert` blocks from `scripts/export_telegram_posts.py`, `scripts/build_telegram_metrics.py`, and `tests/test_metrics.py`. Lift imports to module top-level where possible.
3. Wrap the `int(api_id)` cast in `tone_of_voice.telegram_export.ensure_telegram_credentials` with a typed `RuntimeError`.
4. Replace the ad-hoc emoji character class in `tone_of_voice.metrics` with a precompiled `EMOJI_PATTERN` covering the canonical unicode emoji blocks. Reuse the pattern in `compute_corpus_metrics`.
5. Make `default_env_candidates` honour `TONE_OF_VOICE_FALLBACK_ENV` and document the external `.env` fallback inline.
6. Refactor `scripts/check_feature_memory.py` to use `argparse`, accept an optional `argv`, and broaden `PRODUCT_FILES` to include `pyproject.toml`, `requirements-dev.txt`, and `README.md`.
7. Align the bash guard in `.github/workflows/pr-guard.yml` with the Python product-file list.
8. Pin `actions/checkout` to `@v4` in `ai-review.yml` and add a version comment for the SHA-pinned `osv-scanner-action`.
9. Expand `.gitignore` with Python build and tooling cache patterns, and ignore `data/` rather than only `data/raw/`.
10. Add `requirements-dev.txt` that re-exports `requirements.txt` and pins `pytest`.
11. Add unit tests: `tests/test_config.py`, `tests/test_telegram_export.py`, `tests/test_check_feature_memory.py`. Keep the existing `tests/test_metrics.py` test passing.
12. Update `docs/05-roadmap.md` so Phase 0 reads `complete` and the Phase 1 status entry mentions this hardening pass.
13. Run `pip install -e '.[dev]'` and `python -m pytest tests` locally before opening the PR.

## Risks

- Worktree path resolution for the external `.env` fallback already pre-dated this change, so the new env-var override is additive only — no behaviour change in the default path.
- Broadening `PRODUCT_FILES` will start enforcing feature memory for top-level config files. Acceptable: this PR itself supplies the matching `specs/004-*` entry.
- Switching the package to a `src/` layout via `pyproject.toml` means anyone running scripts without installing the project will hit `ModuleNotFoundError`. Mitigated by documenting `pip install -e .` in the spec acceptance criteria and by keeping the package discoverable when the venv is active.
