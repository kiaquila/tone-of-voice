# Delivery Workflow

## Current Policy

This repository uses a lightweight PR-first delivery model for software changes.

Current required checks:

- `baseline-checks`
- `guard`
- `AI Review` (configuration-aware; active Claude review after repository setup)
- `osv-scan`

## What These Checks Do

### baseline-checks

Runs the minimum validation needed to keep the repository healthy:

- dependency install
- Python syntax validation
- unit tests
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
- first live PR verification with both checks passing
- OSV dependency scan for `requirements.txt`
- Claude-review workflow scaffold with repository-level enablement switch
- bootstrap skip for the first PR that introduces or changes `ai-review.yml`

Planned later:

- deploy workflow for bot/server components
- eval workflow for draft-versus-final regression checks

## Definition Of Done For This Stage

A software PR is considered ready for review when:

- `baseline-checks` is green
- `guard` is green
- `osv-scan` is green
- docs reflect behavior or workflow changes
- the active `specs/<feature-id>/` folder is complete

When Claude review is enabled for the repository:

- `AI Review` is green

Bootstrap note:

- if a PR introduces or changes `.github/workflows/ai-review.yml`, the `AI Review` check will skip Claude execution and pass with an explanatory summary
- this avoids the GitHub validation trap where a review workflow cannot fully review the same PR that first introduces it

## Notes For Future Sessions

- Treat this file as the canonical summary of what delivery automation is already active.
- If a future session adds AI review or deploy automation, update this file in the same PR.
- Claude review activation requires repository configuration, not just workflow files.
