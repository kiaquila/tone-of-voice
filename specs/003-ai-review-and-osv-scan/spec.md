# Spec — 003 AI Review And OSV Scan

## Goal

Extend the repository delivery contract with mandatory review and dependency-vulnerability scanning infrastructure.

## Scope

In scope:

- GitHub Actions workflow for AI review with Claude-ready configuration
- GitHub Actions workflow for OSV scanning of Python dependencies
- durable docs updates describing active and configurable checks

Out of scope:

- deploy workflows
- bot runtime setup
- eval automation for drafting quality

## Requirements

1. The repository must have an `osv-scan` workflow appropriate for Python dependency manifests.
2. The repository must have an `AI Review` workflow that can run Claude review once repository configuration is provided.
3. The repository docs must clearly distinguish between workflow code that exists and review configuration that still needs repository settings.
4. The current PR should be updated and verified after these workflows are added.
5. OSV exceptions must be dated, reasoned, and limited to advisories with no fixed dependency path.

## Acceptance Criteria

- `osv-scan` appears on the PR and passes.
- `AI Review` appears on the PR and provides a clear configured or disabled state.
- Delivery docs explain how Claude review becomes active.
- Fixable dependency advisories are handled by raising package floors rather than ignoring them.
- Any no-fix OSV exception is recorded in `osv-scanner.toml` with an `ignoreUntil` date and a reason.
