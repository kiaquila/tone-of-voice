# Plan — 002 CI And PR Guard

## Technical Approach

Use a Python-friendly workflow layer instead of porting the JavaScript helper stack from other repositories.

Pieces:

- `.github/workflows/ci.yml`
- `.github/workflows/pr-guard.yml`
- `scripts/check_feature_memory.py`

## Tracked Paths For Guard

The guard should treat these as product or workflow paths:

- `src/`
- `scripts/`
- `tests/`
- `.github/workflows/`
- `requirements.txt`
- `README.md`

Changes in these areas should require durable docs and complete feature memory.

## Durable Docs That Satisfy Guard

- `docs/*.md`
- `specs/<feature-id>/*.md`
- `AGENTS.md`
- `README.md`

## Validation

- local syntax and unit test run
- local CLI help checks
- push branch and inspect GitHub Actions results on the PR
