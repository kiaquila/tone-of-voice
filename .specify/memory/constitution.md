# tone-of-voice Constitution

## Core Principles

### I. Voice Memory First

The repository exists to preserve and reuse the author's public writing voice.
Implementation work must not flatten that voice into generic marketing copy or
replace documented style memory with ad hoc prompt habits.

### II. Spec-First Development

Every software or workflow PR must include a complete feature-memory folder
under `specs/<feature-id>/` with `spec.md`, `plan.md`, and `tasks.md`.

### III. Supervised Verification

Every feature must name its goal, scope, acceptance criteria, negative
scenarios, and verification evidence. AI summaries do not replace concrete
evidence from commands, tests, diffs, screenshots, or GitHub checks.

### IV. Testable Boundaries

New behavior should be testable without real model, Telegram, GitHub, or AWS
credentials unless the test is explicitly integration-level and documented.

### V. PR-Only Workflow

Software changes land through pull requests. Do not push directly to `main`.
Required checks and Codex review must stay green before merge.

### VI. Trusted Gates

Trust-sensitive policy must run from trusted base-branch code. In particular,
`pr-guard.yml` must keep its checkout pinned to
`github.event.pull_request.base.sha`, and required gates must fail closed rather
than report success through skipped jobs.

### VII. Human Approval

Drafting and publishing remain human-in-the-loop. Automation may propose,
evaluate, or hand off text, but it must not auto-publish content.

### VIII. Simplicity

New abstractions, services, or cross-cutting process layers require a current
reason documented in `plan.md`. Do not add architecture only for hypothetical
future consumers.

### IX. Process Memory

`specs/<feature-id>/tasks.md` must record dead ends, decisions, and known
issues before merge so future agents inherit the actual working context.

## Workflow

1. Read `AGENTS.md` and the relevant `docs/` memory files.
2. Create or update feature memory under `specs/<feature-id>/`.
3. Name scope, acceptance criteria, and negative scenarios.
4. Implement in an isolated branch or worktree.
5. Record verification evidence and process memory.
6. Run local preflight or the closest available equivalent.
7. Open a PR.
8. Trigger Codex review from a trusted human account.
9. Merge only when required checks are green and blocking findings are resolved.

## Governance

Changes to this constitution require a PR that updates dependent agent guidance,
delivery docs, and feature-memory templates in the same change.
