# Tasks: Unicorn Hub Process And CLI Hardening

## Setup

- [x] T001 Refresh GitHub state and confirm `main` is current.
- [x] T002 Create implementation branch.
- [x] T003 Add feature memory before product changes.

## Implementation

- [x] T004 Harden `scripts/draft_post.py` user-supplied paths.
- [x] T005 Harden `scripts/build_style_memory_index.py` user-supplied paths.
- [x] T006 Harden `scripts/query_style_memory.py` user-supplied paths.
- [x] T007 Harden `scripts/capture_feedback.py` user-supplied paths.
- [x] T008 Add Python tests for parent, absolute, and symlink path escapes.
- [x] T009 Add `.unicorn-hub/config.json`.
- [x] T010 Add `.specify/` constitution and templates.
- [x] T011 Add `CLAUDE.md`.
- [x] T012 Update README, delivery workflow, roadmap, and product execution
  plan.
- [x] T013 Add Node process scripts and package metadata.
- [x] T014 Add event-driven AI review scripts/workflows.
- [x] T015 Add Node helper tests for AI review rerun behavior.

## Verification

- [x] T016 Run Python syntax validation.
- [x] T017 Run Python tests.
- [x] T018 Run regression evals.
- [x] T019 Run retrieval experiments.
- [x] T020 Run generated-output experiments.
- [x] T021 Run Node syntax/tests.
- [x] T022 Run `pnpm run preflight`.
- [x] T023 Run feature-memory guard in worktree mode.
- [x] T024 Run YAML/diff hygiene checks.

## Publish

- [ ] T025 Commit changes by layer.
- [ ] T026 Push branch.
- [ ] T027 Open PR against `main`.
- [ ] T028 Trigger Codex review with `@codex review`.

## Process Memory

### Dead Ends

- None yet.

### Decisions

- Keep `docs/` as the durable memory directory instead of importing
  `docs_project/`.
- Keep `--env-file` as an explicit external-path exception because it is used
  for credential reuse and does not write repository artifacts.
- Keep event-driven AI review in its own commit because it changes required
  check timing and should be easy to inspect or revert independently.
- Local preflight prefers `.venv/bin/python` when present so it matches the
  repository's existing local validation environment.
- `publish-branch.mjs` defaults to draft PRs, but supports `--ready`; this PR
  will be opened ready because the user explicitly requested an open PR and
  immediate Codex review.

### Known Issues

- Post-merge treatment metrics for event-driven AI review will require a later
  observation window after enough PRs run through the new gate.
- The event-driven AI Review workflow only becomes the default-branch control
  plane after this PR merges. This PR's own review trigger may still be routed
  partly through the pre-existing default-branch policy, so manual rerun may be
  needed if the first required check finishes before Codex evidence appears.
