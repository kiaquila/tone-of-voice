# Spec — 002 CI And PR Guard

## Goal

Add the first repository-owned delivery automation so the `tone-of-voice` project can evolve through repeatable pull-request checks instead of informal local state.

## Scope

In scope:

- baseline CI workflow
- PR guard workflow
- feature-memory validation script
- durable docs updates that describe the current delivery contract

Out of scope:

- AI review workflow
- deploy workflow
- bot runtime infrastructure
- eval automation for model quality

## Requirements

1. Pull requests must run baseline validation automatically.
2. Pull requests that change product or workflow paths must also update durable docs.
3. Pull requests that change product or workflow paths must include a complete `specs/<feature-id>/` folder.
4. The repository must document which checks are active now and which are still planned.

## Acceptance Criteria

- GitHub Actions runs a `baseline-checks` job on PRs and pushes to `main`.
- GitHub Actions runs a `guard` job on PRs.
- Guard fails when tracked paths change without docs/spec coverage.
- Repository docs clearly show the current delivery workflow status.
