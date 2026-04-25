# Tasks — 005 AI Review Codex Gate

- [x] Copy `scripts/resolve-pr-context.mjs` from pallete-maker.
- [x] Copy `scripts/ai-review-gate.mjs` from pallete-maker.
- [x] Copy `scripts/ai-review-helpers.mjs` from pallete-maker.
- [x] Copy `.github/workflows/ai-command-policy.yml` from pallete-maker.
- [x] Replace `.github/workflows/ai-review.yml` with the gate version, including a `Detect bootstrap review-infrastructure PR` step and an `Explain bootstrap skip` step gated on `steps.bootstrap.outputs.skip == 'true'`.
- [x] Replace the `docs_pallete_maker/...` reference inside the policy summary with `specs/005-ai-review-codex-gate/spec.md`.
- [x] Run `node --check` on all three `scripts/*.mjs` files; confirm syntax.
- [x] Run `python scripts/check_feature_memory.py origin/main HEAD` after staging; confirm guard passes via `specs/005-...`.
- [ ] Open PR against `main` and verify the `AI Review` check goes green via the bootstrap-skip carve-out.
- [ ] After merge, apply classic branch protection on `main` requiring `baseline-checks`, `guard`, `AI Review` with `enforce_admins: true` (one-shot owner action via `gh api`).
- [ ] Verify branch protection with `gh api repos/kiaquila/tone-of-voice/branches/main/protection --jq '{checks: .required_status_checks.contexts, enforce_admins: .enforce_admins.enabled}'`.
- [ ] Open a follow-up trivial PR after the gate lands to confirm the gate actually runs and polls for a Codex review (smoke test of the live behaviour).

## Post-Codex-review fixes (PR #3 round 2)

- [x] **P1 — Reject unsupported `AI_REVIEW_AGENT` values instead of skipping the job.** The previous job-level `if:` filtered to `''/gemini/codex`, which meant any typo silently skipped the job, and skipped jobs report success for required checks (merge-bypass risk). Dropped the agent-value filter from the job condition; agent validation now happens inside the policy step and exits 1 on any value other than `codex` or empty.
- [x] **P2 — Match Codex reviews on identity + head SHA only.** `matchesCodexReview` no longer requires the review body to contain `"Codex Review"`. Connector templates change and a valid empty-body review would otherwise time out the gate. Reviewer-bot login plus `commit_id === headSha` is sufficient.
