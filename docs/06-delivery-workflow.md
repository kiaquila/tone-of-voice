# Delivery Workflow

## Current Policy

This repository uses a lightweight PR-first delivery model for software changes.

Current required checks:

- `baseline-checks`
- `guard`
- `AI Review` (Codex gate for non-draft pull requests)
- `osv-scan`

Repository process defaults live in `.unicorn-hub/config.json`. The durable
project memory still lives under `docs/`, not `docs_project/`.

## What These Checks Do

### baseline-checks

Runs the minimum validation needed to keep the repository healthy:

- dependency install
- Python syntax validation
- unit tests
- Node helper tests for AI review routing and rerun behavior
- offline regression eval slice for drafting, eval, feedback, and core voice-memory changes
- offline retrieval experiment slice for style-memory variants
- offline generated-output A/B experiment slice for saved draft variants
- shared experiment CLI/path helpers that keep eval suite input and JSON report
  output repository-local
- path filters that include bot/config/eval/dependency changes when those can
  affect drafting or retrieval behavior, with one shared detection step feeding
  the three eval slices
- CLI `--help` smoke checks
- local preflight parity through `pnpm run preflight`

Trust-boundary note:

- Verified with `gh api` on 2026-05-11: branch protection requires
  `baseline-checks`, `guard`, `AI Review`, and `osv-scan`.
- `baseline-checks` is a repo-health gate. It intentionally installs and tests
  proposed PR code, so it must stay least-privilege (`contents: read`, no
  secrets) and should not own trusted policy decisions.
- Trust-sensitive policy stays in base-branch-controlled workflows such as
  `pr-guard.yml` and `ai-review.yml`.

### guard

Protects repository memory and process discipline:

- product or workflow changes must include a durable docs update
- product or workflow changes must include a complete `specs/<feature-id>/` folder
- trusted guard code must keep running from the base branch checkout pinned to
  `github.event.pull_request.base.sha`
- process-control paths such as `.unicorn-hub/`, `.specify/`, `AGENTS.md`,
  `CLAUDE.md`, and pnpm metadata are tracked workflow paths for guard purposes

### AI Review

Runs the codex-only review gate. The gate is event-driven: it fails quickly
when current-head trusted review evidence is missing, records trusted
`@codex review` requests through `AI Command Policy`, and reruns the PR-linked
`AI Review` check when trusted review triggers or Codex evidence appear.

## Current Scope

Already implemented:

- CI for Python validation and tests
- PR guard for docs/spec coverage
- feature-memory validation script
- first live PR verification with required checks passing
- OSV dependency scan for `requirements.txt`
- root `osv-scanner.toml` for dated, reasoned OSV exceptions when an advisory
  has no fixed release yet
- Codex-only AI review gate for pull requests
- trusted-comment policy workflow for AI commands
- classic branch protection on `main` with required checks and admin enforcement
- regression eval slice inside `baseline-checks`
- retrieval experiment slice inside `baseline-checks`
- LlamaIndex-backed retrieval variant in the offline retrieval experiment slice
- generated-output A/B experiment slice inside `baseline-checks`
- shared experiment harness helpers and consolidated eval path-filter detection
- Telegram bot runner, offline smoke check, final feedback capture, and `/stat` scoring
- automated production deploy workflow for the Telegram bot via GitHub OIDC, S3 release artifacts, AWS SSM, and systemd
- adapted Unicorn Hub process config under `.unicorn-hub/`
- `.specify/` constitution and feature-memory templates
- `CLAUDE.md` implementation-agent guidance
- local `pnpm run preflight` orchestration
- event-driven `AI Review` rerun workflow

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
- bot-authored trigger comments do not start policy routing
- trusted review evidence reruns the original PR-linked `AI Review` workflow
  rather than creating a detached `workflow_dispatch` check
- trusted review evidence newer than the last green `AI Review` reruns the
  check instead of treating the old success as final
- newly introduced rerun workflows no-op during bootstrap when the trusted base
  branch does not yet contain their trusted script, then activate after merge

Local preflight:

```bash
pnpm run preflight
```

This wraps the repository baseline, feature-memory guard for both dirty
worktree changes and the committed branch diff, Python syntax/tests, Node
syntax/tests, and offline eval slices. It does not require model credentials,
Telegram credentials, or AWS production credentials.

## Notes For Future Sessions

- Treat this file as the canonical summary of what delivery automation is already active.
- If a future session changes AI review, eval, or deploy automation, update this file in the same PR.
- If a future session changes style-memory retrieval or retrieval experiment thresholds, update `docs/17-rag-style-memory.md` in the same PR.
- If a future session changes generated-output A/B thresholds or suite shape, update `docs/17-rag-style-memory.md` in the same PR.
- If branch protection changes, update this file in the same PR and verify with `gh api`.
- If `osv-scanner.toml` contains an `ignoreUntil` date, revisit it before expiry
  and remove the exception as soon as a fixed dependency path is available.
