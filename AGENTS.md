# AGENTS.md — tone-of-voice

## Mission

This repository stores durable memory about the author's public writing voice so future AI sessions can help create new content without flattening it into generic marketing copy.

## Priority Order

Before proposing or drafting posts, read in this order:

1. `docs/00-principles.md`
2. `docs/01-current-voice-snapshot.md`
3. `docs/04-platform-adaptation.md`
4. `docs/02-memory-system.md`
5. `docs/05-roadmap.md`
6. `docs/06-delivery-workflow.md`
7. `docs/07-product-execution-plan.md`
8. `docs/10-reference-library.md`
9. `docs/11-refresh-log.md`
10. `docs/12-stop-list.md`
11. `docs/13-drafting-recipes.md`
12. Any later benchmark or reference-library files added to `docs/`

For implementation or workflow changes, also read:

1. `.specify/memory/constitution.md`
2. `CLAUDE.md` when Claude is participating as implementation agent
3. active `specs/<feature-id>/spec.md`
4. active `specs/<feature-id>/plan.md`
5. active `specs/<feature-id>/tasks.md`

## What Good Help Looks Like

- Preserve the human, in-the-field quality of the voice.
- Keep expertise grounded in lived usage, experiments, and opinion.
- Prefer strong hooks, clear takes, and concise structure.
- Adapt tone by platform without erasing author identity.

## What To Avoid

- Generic founder or marketer language
- Flat corporate summaries
- Over-polished copy that removes spontaneity
- Mimicry that copies old posts mechanically instead of extending the voice

## Update Rule

Do not overwrite the voice snapshot casually. Update it only when there is meaningful new source material or a visible shift in how the author writes publicly.

## Delivery Rule

Software changes in this repository should land through pull requests and keep the documented roadmap, feature memory, and delivery workflow in sync.

Feature memory follows the adapted Unicorn/SENAR contract: product-code and
workflow PRs need a complete `specs/<feature-id>/` folder with goal, scope,
acceptance criteria, negative scenarios, verification evidence, and process
memory. `.unicorn-hub/config.json` records the repository-local process paths
and required checks.

## GitHub Freshness Rule

When answering questions about the current repository status, roadmap state, pull requests, branches, CI, or what should happen next, do not rely on local git state alone.

Before answering, refresh and verify GitHub state:

1. Run `git fetch --all --prune`.
2. Check the relevant PR, branch, or workflow with `gh pr view`, `gh pr list`, `gh run list`, `gh api`, or the GitHub connector when applicable.
3. Compare local `main` with `origin/main`.
4. If local state is stale, update it or explicitly say it is stale before drawing conclusions.

Never infer whether a PR is open, merged, or current only from local branches. GitHub is the source of truth for PR state.

If GitHub or `gh` is unavailable, clearly say that the answer is based on local state only.

## CI Gate Security

`pr-guard.yml` is a required merge gate. Its checkout step pins `ref` to
`github.event.pull_request.base.sha` so the gate script always runs from the
trusted base branch. Never remove or loosen this pin — doing so lets a PR
replace the gate script with one that always passes.
