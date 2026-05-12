# CLAUDE.md — tone-of-voice

Claude is the default implementation partner for this repository unless a
specific session or repository variable says otherwise. Codex remains the
required review gate.

## Read Before Coding

1. `.specify/memory/constitution.md`
2. `AGENTS.md`
3. `docs/00-principles.md`
4. `docs/01-current-voice-snapshot.md`
5. `docs/04-platform-adaptation.md`
6. `docs/05-roadmap.md`
7. `docs/06-delivery-workflow.md`
8. `docs/07-product-execution-plan.md`
9. active `specs/<feature-id>/spec.md`
10. active `specs/<feature-id>/plan.md`
11. active `specs/<feature-id>/tasks.md`
12. relevant implementation files

## Operating Rules

- Product and workflow changes go through pull requests.
- Product changes start from an active `specs/<feature-id>/` folder.
- Keep `docs/05-roadmap.md`, `docs/06-delivery-workflow.md`, and
  `docs/07-product-execution-plan.md` aligned with behavior or workflow
  changes.
- Record dead ends, decisions, and known issues before calling work complete.
- Run local preflight or the closest available equivalent before pushing.
- Never merge while required checks are queued, running, red, skipped, or
  missing.
- Do not overwrite voice snapshots casually; update them only with meaningful
  new source material or visible voice shifts.

## Review Contract

- Implementation default: `AI_IMPLEMENTATION_AGENT=claude`.
- Review default: `AI_REVIEW_AGENT=codex`.
- This repository is codex-only for the required `AI Review` gate.
- A trusted human account must trigger Codex review with `@codex review` when a
  PR is ready.

## Local Workflow

```bash
pnpm run preflight
node scripts/new-worktree.mjs --slug 021-example
node scripts/publish-branch.mjs
```

Use the project-equivalent Python checks if `pnpm` dependencies are not
installed yet.

## Do Not

- Do not push directly to `main`.
- Do not run two implementation agents in the same worktree.
- Do not satisfy review gates with stale comments or old SHAs.
- Do not remove the trusted base checkout from `pr-guard.yml`.
- Do not put secrets, private draft artifacts, or production credentials in
  docs, specs, tests, or examples.
