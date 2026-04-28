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
  `git cat-file -e <head_ref>:<path>` rather than `Path.exists()` against the working
  tree, so newly added `specs/` folders in the PR are visible even when the checkout is
  on the base SHA

Out of scope:
- Changes to `ci.yml`, `ai-review.yml`, `osv-scan.yml`, or `ai-command-policy.yml`
- Product changes

## Requirements

1. `pr-guard.yml` checkout step must set `ref: ${{ github.event.pull_request.base.sha }}`.
2. `check_feature_memory.py::has_complete_feature_memory` must verify file existence at
   the PR head ref using `git cat-file -e`, not the filesystem.
3. The `guard` job must pass on a PR that adds both a tracked-path change and a complete
   `specs/<id>/` folder in the same PR.

## Acceptance Criteria

- `pr-guard.yml` diff shows `ref: ${{ github.event.pull_request.base.sha }}` in the
  checkout step.
- `check_feature_memory.py` has no remaining calls to `Path(...).exists()` for feature
  memory validation.
- The `guard` required check turns green on this PR (which adds `.github/workflows/`
  changes and a complete `specs/006-pr-guard-trusted-checkout/` folder).
