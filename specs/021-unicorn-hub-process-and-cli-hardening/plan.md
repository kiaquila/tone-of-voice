# Plan: Unicorn Hub Process And CLI Hardening

## Summary

Adopt the useful target-repo pieces from `kiaquila/unicorn-hub` while preserving
the existing `tone-of-voice` product workflow. The PR is intentionally layered:
first feature memory, then Python CLI hardening, then process memory, then local
preflight scripts, then event-driven AI review.

## Technical Context

- runtime: Python 3.12 in CI, Python package under `src/tone_of_voice`, Node 20
  for GitHub/process scripts
- dependencies: existing Python dependencies plus lightweight `pnpm` package
  metadata for local process scripts
- product paths: `src/`, `scripts/`, `tests/`, `.github/workflows/`, `evals/`,
  `docs/`, `specs/`, dependency/config files
- data changes: no committed private data; generated reports stay under
  ignored `data/working/`

## Scope Boundaries

- in scope: repository process config, CLI path hardening, local preflight,
  event-driven AI review rerun flow, docs/spec updates
- out of scope: production bot behavior, generation semantics, retrieval
  ranking changes, adding private draft/final data to eval suites

## Implementation Order

1. Add this feature folder and commit it alone.
2. Extend `resolve_repo_path` usage to remaining Python CLIs and add tests.
3. Add `.unicorn-hub`, `.specify`, `CLAUDE.md`, and docs updates.
4. Add Node preflight/orchestration scripts and package metadata.
5. Add event-driven AI review rerun workflow/scripts and tests.
6. Run the verification suite.
7. Commit by layer, push, open PR, and trigger `@codex review`.

## Constitution Check

- Spec-first: this folder defines goal, scope, acceptance criteria, negative
  scenarios, and verification before implementation.
- Testable boundaries: path hardening and AI review helpers will have automated
  unit tests; workflow YAML will be syntax-checked.
- PR-only: work lands through a PR against `main`.
- Simplicity: only target-repo pieces from `unicorn-hub` are adopted; blueprint
  source templates/profiles are not copied.
- Deployability: bot runtime/deploy files are not changed except docs if
  needed; local preflight avoids external credentials.

## Complexity Tracking

New Node process scripts are justified because `unicorn-hub`'s AI review rerun
and local orchestration pieces are Node-based and already tested upstream. The
Python product implementation remains Python-native; Node is confined to
repository control-plane scripts.

## Verification

| Acceptance criterion | Evidence |
| --- | --- |
| AC-001 | `python scripts/check_feature_memory.py --worktree` and PR `guard` |
| AC-002 | Python tests for path escape rejection |
| AC-003 | Test/docs explicitly leave `--env-file` as an external-path exception |
| AC-004 | Node tests for missing-marker fast-fail / gate summary behavior where practical |
| AC-005 | Node tests for command-policy marker and rerun selection |
| AC-006 | Node tests for trusted review evidence routing |
| AC-007 | Node helper tests for stale/untrusted evidence rejection |
| AC-008 | `pnpm run preflight` |

Negative scenario evidence:

- YAML inspection confirms `pr-guard.yml` keeps checkout pinned to
  `github.event.pull_request.base.sha`.
- `.unicorn-hub/config.json` and docs include `osv-scan` in required checks.
- AI command policy workflow excludes bot-authored comments.

## Risks

- Event-driven AI review changes required-check timing. Mitigation: keep it in
  a separate commit and adapt the upstream tests.
- Adding `pnpm` metadata to a Python repo could confuse future sessions.
  Mitigation: document that Node is only the process-control layer.
- Path hardening may break workflows that intentionally write outside the repo.
  Mitigation: keep credential env-file handling as an explicit exception and
  document private outputs under `data/working/`.
