# Tasks — 004 Quality And Packaging Fixes

- [x] Add `pyproject.toml` with `setuptools` build backend, `src/` package discovery, and pytest config.
- [x] Remove `sys.path.insert` shims from scripts and tests; rely on installed package.
- [x] Wrap `int(api_id)` in `ensure_telegram_credentials` with a `RuntimeError`.
- [x] Replace emoji regex in `compute_corpus_metrics` with a precompiled `EMOJI_PATTERN`.
- [x] Make `default_env_candidates` honour `TONE_OF_VOICE_FALLBACK_ENV`; document inline.
- [x] Convert `scripts/check_feature_memory.py` to `argparse`; broaden `PRODUCT_FILES`.
- [x] Align `.github/workflows/pr-guard.yml` tracked file list with the Python guard.
- [x] Pin `actions/checkout@v4` in `ai-review.yml`; annotate `osv-scanner-action` SHA with version comment.
- [x] Expand `.gitignore` with Python build artefacts and tooling caches; ignore `data/` fully.
- [x] Add `requirements-dev.txt` with `pytest`.
- [x] Add `tests/test_config.py`, `tests/test_telegram_export.py`, `tests/test_check_feature_memory.py`.
- [x] Update `docs/05-roadmap.md` Phase 0 to `complete` and note the hardening pass under Phase 1.
- [x] Run `pip install -e '.[dev]'` and `python -m pytest tests` locally; confirm 100% pass.
