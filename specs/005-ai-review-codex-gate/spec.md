# Spec — 005 AI Review Codex Gate

## Goal

Make the `AI Review` GitHub Actions check a real merge gate: it should fail (and therefore block merge under branch protection) whenever no qualifying Codex Cloud review exists for the current head SHA of a pull request.

The previous workflow only handled `claude` and silently passed when `vars.AI_REVIEW_AGENT` was anything else. Combined with no branch protection on `main`, this allowed PRs to merge with a green "AI Review" check even though no review actually happened.

## Scope

In scope:

- replacing `.github/workflows/ai-review.yml` with a gate-based workflow that polls for a real review on the current head SHA
- adding `.github/workflows/ai-command-policy.yml` to validate which trusted humans may trigger AI review/implementation commands
- adding the three Node 24 scripts that power the gate: `scripts/resolve-pr-context.mjs`, `scripts/ai-review-gate.mjs`, `scripts/ai-review-helpers.mjs`
- documenting the bootstrap-skip carve-out so this PR (which introduces the gate) can land without depending on the gate it adds
- documenting the branch-protection settings that must be applied on `main` after the workflow lands

Out of scope:

- supporting `claude` or `gemini` as review backends in tone-of-voice — this gate is codex-only by repository policy
- automating branch-protection setup from inside this PR; that change is owner-only and is applied via `gh api` after merge
- changing CI, OSV, or PR Guard workflows
- product changes (Telegram ingestion, metrics, voice docs)

## Requirements

1. The `AI Review` job must run on every non-draft `pull_request` and on `workflow_dispatch`.
2. The gate must fail if, within 20 minutes of the workflow starting, no Codex Cloud review or qualifying summary comment exists on the PR for the current head SHA.
3. The gate must pass only when:
   - a formal Codex review (`chatgpt-codex-connector[bot]`) for the current head SHA is `APPROVED`, or
   - a `COMMENTED` Codex review for the current head SHA contains only P3-severity inline findings, or
   - a Codex summary comment posted after the latest head activation contains a recognized "no major issues" reply.
4. The gate must fail with a clear message if Codex reports "no environment configured" or "no connected account" for the repository.
5. The workflow must NOT have a bootstrap-skip carve-out. Skipped steps report success to branch protection, which would turn the required AI Review check green without a real review on the current head SHA — the same merge-bypass shape the agent-validation requirement closes. The introducing PR for the gate is merged via a single owner-only `gh pr merge --admin` override (because branch protection is not yet active for it), and every PR after that runs the full gate.
6. `vars.AI_REVIEW_AGENT` defaults to `codex` when unset. Any other value (including typos like `codez` or unsupported agents like `claude`/`gemini`) must fail the AI Review check rather than skip the job — silently skipped jobs report success for required status checks, which would reintroduce a merge-bypass path.
7. `ai-command-policy.yml` must reject AI commands from non-trusted comment authors (must be `OWNER`, `MEMBER`, or `COLLABORATOR`).
8. After the PR lands, classic branch protection on `main` must require the status checks `baseline-checks`, `guard`, and `AI Review`, with `enforce_admins: true`.

## Acceptance Criteria

- The new workflow files exist and `node --check` passes on all three `scripts/*.mjs` files.
- On the bootstrap PR itself, the `AI Review` check completes green via the bootstrap-skip path, with a step summary explaining the skip.
- On the next PR after merge, the `AI Review` check actually polls for a Codex review on the head SHA and fails if no review exists within the 20-minute window.
- Branch protection settings on `main` match `pallete-maker`'s settings: required status checks `baseline-checks`, `guard`, `AI Review`; `strict: false`; `enforce_admins: true`.
- `gh api repos/kiaquila/tone-of-voice/branches/main/protection --jq '{checks: .required_status_checks.contexts, enforce_admins: .enforce_admins.enabled}'` returns the expected configuration.
