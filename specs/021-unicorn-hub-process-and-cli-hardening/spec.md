# Spec: Unicorn Hub Process And CLI Hardening

## Problem

`tone-of-voice` already has a PR-first delivery workflow, required CI gates, a
Codex review gate, OSV scanning, and completed Step 6 experiment harness
hardening. The upstream `kiaquila/unicorn-hub` blueprint now contains additional
portable process pieces that this repository has not adopted yet:

- a repository-local process config
- a constitution and spec-kit/SENAR templates
- Claude-specific operating guidance
- local preflight and orchestration scripts
- event-driven `AI Review` reruns

PR #19 also left a review follow-up: extend `resolve_repo_path`-style hardening
to user-supplied paths in `draft_post.py`, `build_style_memory_index.py`,
`query_style_memory.py`, and `capture_feedback.py`.

## Scope

In scope:

- Add an adapted `.unicorn-hub/config.json` for this repository.
- Add adapted `.specify/` constitution and templates without replacing the
  existing `docs/` memory system.
- Add `CLAUDE.md` and update durable docs to describe the imported process
  surface.
- Add local preflight/orchestration scripts that call this repository's Python
  checks and eval slices.
- Add the event-driven `AI Review` rerun workflow from `unicorn-hub`, adapted
  to the existing codex-only review policy.
- Harden the remaining user-supplied Python CLI paths with repository-local
  resolution where appropriate.

Out of scope:

- Copying blueprint-source-only folders such as `templates/`, `profiles/`, or
  `docs_project/`.
- Replacing the existing `docs/` system with `docs_project/`.
- Changing the production Telegram bot behavior.
- Changing drafting or retrieval scoring semantics.
- Removing the required `osv-scan` gate.

## User Stories

### User Story 1

As the maintainer, I want the useful parts of `unicorn-hub` installed in this
repository, so future AI sessions follow a consistent process without needing
to re-discover the workflow.

### User Story 2

As a reviewer, I want path-taking CLIs to reject unexpected writes or reads
outside the repository, so local tooling cannot accidentally reach across trust
boundaries.

### User Story 3

As a PR operator, I want `AI Review` to rerun when trusted review triggers or
review evidence appear, so the required check does not depend on a long idle
polling window.

## Acceptance Criteria

1. Given a product or workflow change, when the PR touches tracked product
   paths, then the feature-memory guard still requires a complete
   `specs/<feature-id>/` folder.
2. Given `draft_post.py`, `build_style_memory_index.py`,
   `query_style_memory.py`, or `capture_feedback.py`, when a user-supplied
   path attempts parent traversal, an absolute path outside the repository, or
   a symlink escape, then the command rejects the path without reading or
   writing outside the repository.
3. Given `draft_post.py --env-file`, when the env file path points outside the
   repository, then the command still allows it as an explicit credential-file
   exception documented in project guidance.
4. Given an opened non-draft PR, when no trusted current-head Codex review
   request or evidence exists, then `AI Review` fails quickly with actionable
   instructions instead of waiting for the old long polling window.
5. Given a trusted human posts `@codex review`, when the command policy records
   a current-head request marker, then the failed PR-linked `AI Review` run is
   rerun natively for the same head SHA.
6. Given Codex posts trusted review evidence for the current PR head, when the
   rerun workflow receives the event, then it reruns `AI Review` so branch
   protection can observe the latest result.
7. Given a stale review, forged marker, untrusted trigger, or review for an old
   head SHA, when the gate evaluates evidence, then it fails closed.
8. Given local development, when `pnpm run preflight` is available, then it runs
   repository baseline checks, feature-memory validation, Python syntax/tests,
   and the offline eval/experiment slices.

## Negative Scenarios

1. `pr-guard.yml` must keep running trusted guard code from the base branch.
   Never loosen the base checkout pin or run the guard script from PR-supplied
   code.
2. `osv-scan` must remain a required check in documented branch protection and
   in `.unicorn-hub/config.json`.
3. A skipped workflow must not be treated as a successful required gate.
4. Bot-authored trigger comments must not recursively start AI command policy.
5. Event-driven AI review must not replace human final merge authority.
6. Local preflight must not require model credentials or Telegram production
   credentials.

## Requirements

- FR-001: Add repository-local path resolution for the remaining path-taking
  Python CLIs, with tests for parent escape, absolute escape, and symlink
  escape.
- FR-002: Preserve `-` stdin support for CLIs that already support stdin.
- FR-003: Install adapted Unicorn process config and docs without introducing
  blueprint-only target folders.
- FR-004: Add local Node process tooling without replacing the existing Python
  package layout.
- FR-005: Adapt event-driven AI review scripts/workflows to codex-only policy.
- FR-006: Update delivery docs, roadmap, README, and process memory to describe
  the new workflow surface.

## Success Criteria

- SC-001: Full local verification passes before publishing the PR.
- SC-002: The PR opens against `main` with separate commits for spec, CLI
  hardening, process memory, local preflight/orchestration, and event-driven AI
  review.
- SC-003: Codex review is triggered on the PR after it is opened.

## Assumptions

- `unicorn-hub` `main` as of 2026-05-12 is the source blueprint for this import.
- `tone-of-voice` remains codex-only for review unless repository policy changes
  in a future PR.
- This repository keeps `docs/` as the durable project memory directory.
