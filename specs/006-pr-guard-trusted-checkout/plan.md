# Plan — 006 PR Guard Trusted Checkout

## Approach

Two minimal, coupled changes in one PR:

1. **`pr-guard.yml`** — add `ref: ${{ github.event.pull_request.base.sha }}` to the
   `actions/checkout@v4` step. No other workflow changes.

2. **`scripts/check_feature_memory.py`** — replace `Path("specs/id/file").exists()`
   with `git cat-file -e <head_ref>:specs/id/file` (exit code 0 = file exists in that
   tree). The `head_ref` is already available as `args.head_ref` (defaults to `"HEAD"`),
   so the worktree mode and the CI mode both work without extra plumbing.

## Steps

1. Edit `pr-guard.yml`: insert `ref:` line under `actions/checkout@v4 with:`.
2. Edit `check_feature_memory.py`: update `has_complete_feature_memory` signature and
   body; update two call sites in `main()` to pass `args.head_ref`.
3. Add `specs/006-pr-guard-trusted-checkout/{spec,plan,tasks}.md`.
4. Update `AGENTS.md` with a CI Gate Security section documenting the pin.
5. Open PR, verify `guard` turns green.

## Risks

- **Codex P1 regression (now fixed):** the initial commit only pinned the checkout ref
  without fixing `Path.exists()`. Codex caught this in review. The `git cat-file` fix
  ships in the same PR.
- **`git cat-file` availability:** always present in standard GitHub-hosted runners.
- **Worktree mode unaffected:** `--worktree` path uses `HEAD` as the default head_ref,
  so `git cat-file -e HEAD:specs/...` works correctly against the dirty worktree.
- **Bootstrap (accepted):** `guard` runs the script from base, so until this PR lands
  on main it still executes the old `Path.exists()` script. That script cannot see
  the PR-only `specs/006-pr-guard-trusted-checkout/` files in the base checkout, so
  `guard` will fail on this PR. Merge with admin-bypass once; subsequent PRs run the
  new git-tree-based script and need no bypass.
- **Test fixtures must commit to git:** because `has_complete_feature_memory` now
  resolves files via `git cat-file`, `HasCompleteFeatureMemoryTest` initialises a
  temp git repo and commits the fixture files. Otherwise the disk-only fixtures
  produce false negatives.
