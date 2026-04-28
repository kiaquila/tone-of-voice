# Spec — 006 PR Guard Trusted Checkout

## Goal

Close the merge-bypass where an attacker could replace `scripts/check_feature_memory.py`
in their PR with a version that always returns 0, silently passing the required `guard` check.

## Problem

`pr-guard.yml` used `actions/checkout@v4` with no `ref:`, which defaults to the PR merge
ref. Any gate script invoked after that step runs from PR-supplied code, not from the
trusted base branch — a classic supply-chain bypass for a required check.

## Scope

In scope:
- Pin the `pr-guard.yml` checkout to `github.event.pull_request.base.sha`
- Fix `scripts/check_feature_memory.py` to check feature-memory file existence via
  `git cat-file -e <head_ref>:<path>` in CI mode (so newly added `specs/` folders in
  the PR are visible even when the checkout is on the base SHA), while keeping
  `Path.exists()` semantics for `--worktree` mode (so staged/unstaged spec files in
  a dirty local worktree are visible to local runs)

Out of scope:
- Changes to `ci.yml`, `ai-review.yml`, `osv-scan.yml`, or `ai-command-policy.yml`
- Product changes

## Requirements

1. `pr-guard.yml` checkout step must set `ref: ${{ github.event.pull_request.base.sha }}`.
2. `check_feature_memory.py::has_complete_feature_memory` must verify file existence at
   the PR head ref using `git cat-file -e` when called from CI mode (i.e. with explicit
   base/head SHAs and the trusted-base checkout).
3. `--worktree` mode must continue to inspect the working-directory filesystem so
   staged/unstaged files are visible (preserves the documented "dirty worktree" semantics).
4. The `guard` job must pass on a PR that adds both a tracked-path change and a complete
   `specs/<id>/` folder in the same PR — for any PR landing AFTER this one merges.

## Acceptance Criteria

- `pr-guard.yml` diff shows `ref: ${{ github.event.pull_request.base.sha }}` in the
  checkout step.
- `has_complete_feature_memory` accepts a `use_worktree` keyword flag and routes
  between `Path.exists()` (worktree) and `git cat-file -e` (CI). Both call sites in
  `main()` thread `args.worktree` through.
- Tests cover both paths: a git-tree path (committed fixtures) and a worktree path
  (uncommitted fixtures on disk).
- `guard` is expected to stay red on this PR (bootstrap: gate runs the pre-fix script
  from base). It must turn green automatically on the next PR after this one merges.
