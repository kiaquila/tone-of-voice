# Spec — 006 Product Plan And Required Gates

## Goal

Turn the current state assessment into durable execution memory and align repository branch protection with the checks already documented as required.

## Scope

In scope:

- adding a canonical numbered product execution plan for future AI sessions
- updating roadmap, README, AGENTS, and delivery-workflow docs so they point to the same plan
- correcting delivery docs to reflect the codex-based `AI Review` gate already implemented in the repository
- making `osv-scan` required on `main` so live branch protection matches the documented required checks

Out of scope:

- implementing Step 1 or any later product work from the new execution plan
- changing CI, PR Guard, AI Review gate logic, or OSV workflow behavior
- adding deployment automation for the future bot

## Requirements

1. The repository must contain a single canonical numbered plan that future sessions can reference by step number.
2. The plan must cover the path from the current foundation to a full cross-platform product in 4 to 6 pull requests.
3. `AGENTS.md`, `README.md`, and `docs/05-roadmap.md` must point future sessions to the same canonical plan file.
4. `docs/06-delivery-workflow.md` must describe the live codex-based AI Review gate rather than the older Claude wording.
5. Classic branch protection on `main` must require `baseline-checks`, `guard`, `AI Review`, and `osv-scan`, with `strict: false` and `enforce_admins: true`.

## Acceptance Criteria

- `docs/07-product-execution-plan.md` exists and can be referenced directly in a new session.
- `AGENTS.md`, `README.md`, `docs/05-roadmap.md`, and `docs/06-delivery-workflow.md` are consistent with that plan.
- `gh api repos/kiaquila/tone-of-voice/branches/main/protection --jq '{checks: .required_status_checks.contexts, strict: .required_status_checks.strict, enforce_admins: .enforce_admins.enabled}'` returns the expected required checks and settings.
