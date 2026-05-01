# Tasks — 005 AI Review Codex Gate

- [x] Copy `scripts/resolve-pr-context.mjs` from the sibling project.
- [x] Copy `scripts/ai-review-gate.mjs` from the sibling project.
- [x] Copy `scripts/ai-review-helpers.mjs` from the sibling project.
- [x] Copy `.github/workflows/ai-command-policy.yml` from the sibling project.
- [x] Replace `.github/workflows/ai-review.yml` with the gate version, including a `Detect bootstrap review-infrastructure PR` step and an `Explain bootstrap skip` step gated on `steps.bootstrap.outputs.skip == 'true'`.
- [x] Replace the sibling project docs reference inside the policy summary with `specs/005-ai-review-codex-gate/spec.md`.
- [x] Run `node --check` on all three `scripts/*.mjs` files; confirm syntax.
- [x] Run `python scripts/check_feature_memory.py origin/main HEAD` after staging; confirm guard passes via `specs/005-...`.
- [ ] Open PR against `main` and verify the `AI Review` check goes green via the bootstrap-skip carve-out.
- [ ] After merge, apply classic branch protection on `main` requiring `baseline-checks`, `guard`, `AI Review` with `enforce_admins: true` (one-shot owner action via `gh api`).
- [ ] Verify branch protection with `gh api repos/<your org>/tone-of-voice/branches/main/protection --jq '{checks: .required_status_checks.contexts, enforce_admins: .enforce_admins.enabled}'`.
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

## Codex P1 fix (PR #3 round 5)

Codex flagged a P1 on round 4 head SHA `22e130`: `classifyCodexReview` and `classifyGeminiReview` both fetched inline review comments via `/pulls/{pr}/comments?since=<review.submitted_at>`, but GitHub's `since` filter returns only comments with `updated_at` STRICTLY AFTER the supplied timestamp. Inline comments timestamped in the same second as the review's submission would be excluded — `commentsForReview.length === 0` — and the gate would incorrectly classify a `COMMENTED` review with real findings as "no inline findings, pass". A blocking Codex review could merge anyway. Same race condition as same-second-Last-Modified caching elsewhere.

- [x] **P1 — Drop `since` cutoff when loading inline review comments.** Both `classifyCodexReview` (line ~374) and `classifyGeminiReview` (line ~462) now call `buildPullReviewCommentsPath()` with no argument, fetching all PR review comments and filtering by `pull_request_review_id` — which is the authoritative correlation between comment and review. The function definition keeps `sinceTimestamp` as an optional parameter for future non-classifier use cases but ships a long warning comment explaining why it must NOT be used in classification paths.

## Codex P2 fix (PR #3 round 6)

Codex flagged a P2 on round 5 head SHA `a07336`: `listNewestPullReviews` only fetched the LAST page of `/pulls/{n}/reviews?per_page=100` when pagination was present (chasing the `link rel="last"` header). The reviews endpoint returns reviews in chronological order (oldest first, newest last), so this strategy correctly captures the latest reviews IF the total count is ≤100, but silently drops everything before the last page once the PR exceeds 100 reviews. A valid Codex review for the current head SHA could land on an earlier page and be missed entirely, making the gate time out (or fail) even though a qualifying review exists. This is the same merge-bypass class as the `since`-cutoff race — a quietly empty result that the classifier reads as "no qualifying review".

- [x] **P2 — Replace `listNewestPullReviews` with full pagination.** Renamed to `listAllPullReviews` and reimplemented as `listPaginated(path)`. Both call sites (codex and gemini paths) now enumerate every page of reviews, and downstream filters by trigger time + head SHA + reviewer login still pick the right one. For the typical PR with ≤100 reviews this is one request (vs the previous two — first + last), so it's actually cheaper. For PRs with >100 reviews it scales linearly, which is acceptable given how rare that case is and that the alternative is silent miss.

## Codex P1 fix (PR #3 round 7)

Codex flagged a P1 on round 6 head SHA `2b61cd2`: `isHumanCodexTriggerComment` accepted any non-bot `@codex review` comment as an authoritative trigger boundary, without checking `author_association`. On a public PR, an untrusted commenter (`author_association: NONE`) could post `@codex review`, Codex Cloud would respond with a "create an environment for this repo" or "connect a Codex account" setup error, and `pickAuthoritativeCodexSkipModeComment` would treat that error as the latest gate verdict — failing the required `AI Review` check even when a valid Codex review for the head SHA already existed earlier in the timeline. This is a denial-of-service / spoofing class merge-bypass: an untrusted user can break the gate from the outside.

`ai-command-policy.yml` enforces the same restriction at the command-routing layer (rejects `@codex review` from non-trusted authors), but the gate's own timeline analysis runs independently and must enforce it too.

- [x] **P1 — Restrict `@codex review` trigger boundary to trusted associations.** Added `trustedTriggerAssociations = {"OWNER", "MEMBER", "COLLABORATOR"}` to `ai-review-helpers.mjs`. `isHumanCodexTriggerComment` now requires the entry's `author_association` to be in that set in addition to the existing bot-login check. Untrusted `@codex review` comments are no-ops for the gate's boundary-detection logic — they cannot move the latest-Codex-reply window forward. Long inline comment explaining the attack and why command-policy + helpers must both enforce.

## Codex P1 fix (PR #3 round 8)

Codex flagged a follow-on P1 on round 7 head SHA `b96613`: round 7's fix only stopped untrusted `@codex review` comments from moving the boundary forward, but `pickAuthoritativeCodexSkipModeComment` then selected the LATEST Codex bot comment after the boundary without checking whether an untrusted trigger occurred between. Attack: owner posts `@codex review` (boundary advances), Codex replies with a clean review summary, then an untrusted user posts `@codex review`, Codex replies with a "create environment" / "connect account" setup error. Boundary stays at owner's trigger (round 7 fix), but the latest bot comment is now the setup-error reply — gate fails. DoS / spoof, same class as round 7.

- [x] **P1 — Ignore Codex bot replies that follow untrusted trigger comments.** Added `isUntrustedCodexTriggerComment` helper. `pickAuthoritativeCodexSkipModeComment` now walks forward from `boundaryIndex + 1` with a `zoneTaintedByUntrustedTrigger` flag: any untrusted trigger taints the zone for all subsequent bot comments until either a new trusted trigger advances the boundary (handled outside this loop on a future invocation) or the walk ends. Verified with an inline sanity test: owner-trigger → clean review → untrusted-trigger → setup-error correctly classifies as `pass` with the clean review, not `fail` with the setup error.

## Codex P2 fix (PR #3 round 9)

Codex flagged a P2 on round 8 head SHA `ac3c99a`: when the newest Codex review for the head SHA had a state outside `{APPROVED, CHANGES_REQUESTED, COMMENTED}` (notably `DISMISSED`), `classifyCodexReview` returned `outcome: "pending"`. The polling loop sees pending and continues, but `pickLatestCodexReview` keeps re-selecting the same newest review because nothing filters out the unsupported state. The loop never falls through to an earlier qualifying review on the same SHA, so a recoverable situation turns into a guaranteed 20-minute timeout. Same merge-bypass class — false-fail this time, but identical mechanism (an opt-out state silently consumes the gate's verdict slot).

- [x] **P2 — Filter unsupported review states at the pick stage.** Exported `supportedReviewStates = {APPROVED, CHANGES_REQUESTED, COMMENTED}` from `ai-review-helpers.mjs`. `matchesCodexReview` and `matchesGeminiReview` now require the review state to be in this set. The polling loop now correctly falls through to the next-most-recent review when the latest is `DISMISSED` (or any future unsupported state). The classifier's "pending" branch for unsupported states is kept as defense-in-depth. Verified with an inline sanity test: with two reviews on the same SHA — newer DISMISSED, older COMMENTED — `matchesCodexReview` filters out the DISMISSED one and the COMMENTED review becomes the candidate.
