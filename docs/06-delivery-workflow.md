# Delivery Workflow

## Current Policy

This repository uses a lightweight PR-first delivery model for software changes.

Current required checks:

- `baseline-checks`
- `guard`
- `AI Review` (Codex gate for non-draft pull requests)
- `osv-scan`

## What These Checks Do

### baseline-checks

Runs the minimum validation needed to keep the repository healthy:

- dependency install
- Python syntax validation
- unit tests
- offline regression eval slice for drafting, eval, feedback, and core voice-memory changes
- offline retrieval experiment slice for style-memory variants
- offline generated-output A/B experiment slice for saved draft variants
- path filters that include bot/config/eval/dependency changes when those can
  affect drafting or retrieval behavior
- CLI `--help` smoke checks

### guard

Protects repository memory and process discipline:

- product or workflow changes must include a durable docs update
- product or workflow changes must include a complete `specs/<feature-id>/` folder

## Current Scope

Already implemented:

- CI for Python validation and tests
- PR guard for docs/spec coverage
- feature-memory validation script
- first live PR verification with required checks passing
- OSV dependency scan for `requirements.txt`
- Codex-only AI review gate for pull requests
- trusted-comment policy workflow for AI commands
- classic branch protection on `main` with required checks and admin enforcement
- regression eval slice inside `baseline-checks`
- retrieval experiment slice inside `baseline-checks`
- LlamaIndex-backed retrieval variant in the offline retrieval experiment slice
- generated-output A/B experiment slice inside `baseline-checks`
- Telegram bot runner, offline smoke check, final feedback capture, and `/stat` scoring
- automated production deploy workflow for the Telegram bot via GitHub OIDC, S3 release artifacts, AWS SSM, and systemd

Planned later:

- deploy promotion and rollback helpers after the first production smoke is stable

## Definition Of Done For This Stage

A software PR is considered ready for review when:

- `baseline-checks` is green
- `guard` is green
- `AI Review` is green
- `osv-scan` is green
- docs reflect behavior or workflow changes
- the active `specs/<feature-id>/` folder is complete

Branch protection on `main` currently requires:

- `baseline-checks`
- `guard`
- `AI Review`
- `osv-scan`

Branch protection settings:

- `strict: false`
- `enforce_admins: true`

AI Review notes:

- the repository is codex-only for AI review
- the gate runs from the trusted base branch, not the PR workspace
- unsupported `AI_REVIEW_AGENT` values fail closed
- trusted human associations for AI command triggers are `OWNER`, `MEMBER`, and `COLLABORATOR`

## Notes For Future Sessions

- Treat this file as the canonical summary of what delivery automation is already active.
- If a future session changes AI review, eval, or deploy automation, update this file in the same PR.
- If a future session changes style-memory retrieval or retrieval experiment thresholds, update `docs/17-rag-style-memory.md` in the same PR.
- If a future session changes generated-output A/B thresholds or suite shape, update `docs/17-rag-style-memory.md` in the same PR.
- If branch protection changes, update this file in the same PR and verify with `gh api`.
