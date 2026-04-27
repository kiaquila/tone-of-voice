# Plan — 005 AI Review Codex Gate

## Approach

Port the proven AI Review architecture from the sibling repository `kiaquila/pallete-maker` with minimal adaptation for tone-of-voice. The Node 24 gate scripts are already repo-agnostic and copy in unchanged. The workflow files need two adaptations:

1. Add a bootstrap-skip step in `ai-review.yml` so this PR (which adds the gate) can land without depending on the gate.
2. Replace the pallete-maker docs reference with a tone-of-voice spec reference inside the policy step's summary output.

`ai-command-policy.yml` and the three gate scripts are copied verbatim. They use only Node built-ins (`node:fs`) and the native `fetch` API (Node 24+), so no `node_modules` install is needed in the runner.

## Steps

1. Copy `scripts/resolve-pr-context.mjs`, `scripts/ai-review-gate.mjs`, `scripts/ai-review-helpers.mjs` from pallete-maker into tone-of-voice's `scripts/` directory.
2. Copy `.github/workflows/ai-command-policy.yml` from pallete-maker verbatim.
3. Replace `.github/workflows/ai-review.yml` with the pallete-maker gate workflow, with two changes: add a `Detect bootstrap review-infrastructure PR` step plus an `Explain bootstrap skip` step before the policy/gate steps; and change the `docs_pallete_maker/...` reference in the policy summary to `specs/005-ai-review-codex-gate/spec.md`.
4. The bootstrap-skip step must list PR files via the GitHub API and skip the rest of the job if the diff contains any of: `.github/workflows/ai-review.yml`, `.github/workflows/ai-command-policy.yml`, `scripts/ai-review-gate.mjs`, `scripts/ai-review-helpers.mjs`, `scripts/resolve-pr-context.mjs`.
5. Run `node --check` on all three scripts locally.
6. Run `python scripts/check_feature_memory.py origin/main HEAD` after staging this spec to confirm the guard passes via `specs/005-ai-review-codex-gate/`.
7. Open a PR against `main`. The PR's own `AI Review` check should turn green via the bootstrap-skip carve-out.
8. After merge, apply classic branch protection on `main` from a local shell:
   ```bash
   gh api repos/kiaquila/tone-of-voice/branches/main/protection \
     --method PUT \
     --field required_status_checks='{"strict":false,"contexts":["baseline-checks","guard","AI Review"]}' \
     --field enforce_admins=true \
     --field required_pull_request_reviews=null \
     --field restrictions=null
   ```
9. Verify with:
   ```bash
   gh api repos/kiaquila/tone-of-voice/branches/main/protection \
     --jq '{checks: .required_status_checks.contexts, enforce_admins: .enforce_admins.enabled}'
   ```
   Expected: `{"checks":["baseline-checks","guard","AI Review"],"enforce_admins":true}`.

## Risks

- **Bootstrap chicken-and-egg.** The gate runs against the introducing PR with no special carve-out. The earlier draft used a bootstrap-skip step, but architect review identified that mechanism as a merge-bypass (skipped steps report success to branch protection — same shape as the agent-filter bypass closed in round 2). The bootstrap-skip is removed. The introducing PR for the gate is therefore merged via a single owner-only `gh pr merge --admin` override; branch protection is applied immediately afterwards so subsequent PRs cannot use the same path.
- **Branch protection applied too eagerly.** If branch protection is enabled before merging this PR, the bootstrap PR cannot merge under `enforce_admins: true`. Mitigation: apply protection only after this PR lands, as documented in step 8.
- **Codex Cloud configuration drift.** The gate fails if Codex says "create an environment for this repo" or "create a Codex account and connect to GitHub". This is intentional — those are real configuration problems — but the user must complete the Codex Cloud setup (already in progress, see `project_review_workflows.md`) before the next PR or it will keep failing.
- **Node 24 dependency.** The scripts use Node 24's native `fetch`. The runner is Ubuntu 24.04 with Node 24 by default for `actions/setup-node@v5`, and the gate workflow does not pin Node explicitly — it relies on the runner default plus `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"`. Verified via `node --check` locally on Node 24.2.
- **Issue-comment workflow on a private repo.** `ai-command-policy.yml` runs on `issue_comment` events, which require the repo to grant the workflow `actions: write` permission to dispatch other workflows. The permission is set in the workflow file's `permissions:` block, so no repo-level setting change is needed.
