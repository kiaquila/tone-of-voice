# Tasks — 006 PR Guard Trusted Checkout

- [x] Pin `pr-guard.yml` checkout to `github.event.pull_request.base.sha`
- [x] Update `has_complete_feature_memory` to use `git cat-file -e <head_ref>:<path>`
- [x] Update both call sites in `main()` to pass `args.head_ref`
- [x] Update `tests/test_check_feature_memory.py::HasCompleteFeatureMemoryTest`
      to commit fixtures into a temp git repo (the function now resolves files
      via `git cat-file`, so disk-only fixtures no longer suffice)
- [x] Add `AGENTS.md` CI Gate Security section
- [x] Add `specs/006-pr-guard-trusted-checkout/{spec,plan,tasks}.md`
- [x] Accept that `guard` stays red on PR #4 (bootstrap: the gate runs from
      base, so it executes the old `Path.exists()` script that cannot see
      PR-only specs); merge with admins-temporarily-bypassed once. Future PRs
      run the new `git cat-file` script from base and pass without bootstrap.
