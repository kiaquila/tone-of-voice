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

## Architect-driven fixes (PR #3 round 3)

The PR #3 gate reported SUCCESS even though Codex flagged P1/P2 findings. Architect review identified the root cause: the bootstrap-skip carve-out was activating (the PR diff trips every entry in `bootstrapFiles`), so all validation steps were skipped, and skipped steps report success to branch protection — same merge-bypass shape as the agent-filter case.

- [x] **Removed the bootstrap-skip carve-out entirely.** Deleted the `Detect bootstrap review-infrastructure PR` and `Explain bootstrap skip` steps and the three `if: steps.bootstrap.outputs.skip != 'true'` guards on the policy / start / route steps. The workflow now always runs the full gate against any non-draft PR.
- [x] **Removed the claude-dispatch from `ai-command-policy.yml`.** It dispatched `ai-review.yml` for `@claude review once`, but the workflow now hard-fails on `selected_agent != 'codex'` (introduced in round 2). Codex finding [P2] confirmed this would always produce a failure rather than a useful action. The comment block now records the rationale; if claude is ever re-enabled, restore the dispatch.
- [ ] **Merge strategy for PR #3:** because the gate now runs against itself, this PR needs a Codex review with no P0–P2 findings before merge. If review keeps surfacing infrastructure-related findings, the PR is merged with `gh pr merge 3 --admin --squash` as a one-shot owner override. Branch protection is applied immediately afterwards so subsequent PRs cannot use the same path.

## Codex P0 fix (PR #3 round 4)

Codex flagged a P0 on round 3 head SHA `c6f450e`: the workflow checked out the PR ref by default and then ran `node scripts/resolve-pr-context.mjs` and `node scripts/ai-review-gate.mjs` from THAT workspace. A contributor could short-circuit the required `AI Review` check by editing the gate scripts in their PR to exit 0 without contacting Codex. This is a textbook required-check bypass.

- [x] **P0 — Check out the trusted base (main) instead of the PR ref.** Replaced the `actions/checkout@v4` defaults with `ref: ${{ github.event.repository.default_branch }}`. The gate scripts only need `GITHUB_EVENT_PATH`, `GITHUB_TOKEN`, and the GitHub API — they never read PR-supplied code, so checking out main is sufficient and safe. Side effect: the introducing PR (this one) cannot run the gate (main lacks the scripts until merge), so it will fail-closed with a red check until merged via `gh pr merge --admin`. Every PR after the merge runs the gate from trusted main code.
