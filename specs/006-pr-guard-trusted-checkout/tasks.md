# Tasks — 006 PR Guard Trusted Checkout

- [x] Pin `pr-guard.yml` checkout to `github.event.pull_request.base.sha`
- [x] Update `has_complete_feature_memory` to use `git cat-file -e <head_ref>:<path>`
- [x] Update both call sites in `main()` to pass `args.head_ref`
- [x] Add `AGENTS.md` CI Gate Security section
- [x] Add `specs/006-pr-guard-trusted-checkout/{spec,plan,tasks}.md`
- [ ] Verify `guard` check turns green on PR #4
