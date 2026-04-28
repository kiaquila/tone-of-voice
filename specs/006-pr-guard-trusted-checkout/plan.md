# Plan — 006 PR Guard Trusted Checkout

## Approach

Two minimal, coupled changes in one PR:

1. **`pr-guard.yml`** — add `ref: ${{ github.event.pull_request.base.sha }}` to the
   `actions/checkout@v4` step. No other workflow changes.

2. **`scripts/check_feature_memory.py`** — `has_complete_feature_memory` gains a
   `use_worktree` keyword flag that selects the lookup strategy:
   - `use_worktree=False` (CI / `base_ref head_ref` mode): query the head ref's git
     tree via `git cat-file -e <head_ref>:specs/id/file`. This works against the
     trusted-base checkout because the file is read from the head SHA's tree, not
     the working directory.
   - `use_worktree=True` (`--worktree` mode): fall back to `Path.exists()` against
     the working directory, so staged/unstaged files in a dirty worktree are still
     visible (the original semantics of `--worktree`).

## Steps

1. Edit `pr-guard.yml`: insert `ref:` line under `actions/checkout@v4 with:`.
2. Edit `check_feature_memory.py`: add `use_worktree: bool = False` kw-only flag
   to `has_complete_feature_memory`; route `Path.exists()` for `use_worktree=True`
   and `git cat-file` otherwise; thread `args.worktree` through both call sites.
3. Update `tests/test_check_feature_memory.py`: commit fixture files into a temp
   git repo for the default-mode tests, and add `--worktree`-mode tests that
   assert `Path.exists()` semantics (uncommitted files visible).
4. Add `specs/006-pr-guard-trusted-checkout/{spec,plan,tasks}.md`.
5. Update `AGENTS.md` with a CI Gate Security section documenting the pin.
6. Open PR, accept that `guard` stays red on this PR (bootstrap), admin-merge once.

## Risks

- **Codex P1 regression (now fixed):** the initial commit only pinned the checkout ref
  without fixing `Path.exists()`. Codex caught this in review. The `git cat-file` fix
  ships in the same PR.
- **`git cat-file` availability:** always present in standard GitHub-hosted runners.
- **Worktree mode regression (now fixed):** the first iteration routed `--worktree`
  through `git cat-file -e HEAD:...` too, which silently broke the "inspect dirty
  worktree" semantics — staged/unstaged spec files are not in `HEAD`'s tree.
  Codex flagged it as P1 on the second review round (`scripts/check_feature_memory.py:106`).
  Fix: `--worktree` mode falls back to `Path.exists()` against the filesystem; CI
  mode keeps using `git cat-file` against the explicit head_ref.
- **Bootstrap (accepted):** `guard` runs the script from base, so until this PR lands
  on main it still executes the old `Path.exists()` script. That script cannot see
  the PR-only `specs/006-pr-guard-trusted-checkout/` files in the base checkout, so
  `guard` will fail on this PR. Merge with admin-bypass once; subsequent PRs run the
  new git-tree-based script and need no bypass.
- **Fork PRs need explicit head fetch (now fixed):** `actions/checkout@v4 + ref:
  base.sha + fetch-depth: 0` only fetches `refs/heads/*` of the BASE repo. For PRs
  from forks, the head commit lives in the fork (and only in `refs/pull/<n>/head`
  on the base repo), so `git diff` and `git cat-file` fail with missing-object
  errors. Codex P1 finding on round 3 (`pr-guard.yml:20`). Fix: an extra
  `Fetch PR head ref` step pulls `+refs/pull/<n>/head:refs/remotes/origin/pr/<n>`
  before any diff or cat-file step runs, and asserts the head SHA is reachable.
- **Test fixtures must commit to git:** because `has_complete_feature_memory` now
  resolves files via `git cat-file`, `HasCompleteFeatureMemoryTest` initialises a
  temp git repo and commits the fixture files. Otherwise the disk-only fixtures
  produce false negatives.
