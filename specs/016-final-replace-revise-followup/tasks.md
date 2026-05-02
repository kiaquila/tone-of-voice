# Tasks - Final Replace And Revise Follow-Up

- [x] Add `/final --replace <text or Telegram link>` for same-draft replacement.
- [x] Add pending `/final --replace` mode for long corrected finals.
- [x] Add pending `/revise` mode for next-message revision instructions.
- [x] Update Telegram bot, feedback, and roadmap docs for the new workflow.
- [x] Add feature tests for replace and pending revise behavior.
- [x] Replace user-facing resolver and generator exception details with generic messages.
- [x] Add an indexed feedback-source lookup for duplicate and replace checks.
- [x] Label feedback memory samples as inert style references.
- [x] Add explicit tests for `/cancel` during `awaiting_final`, `published_at`, generic errors, index use, and inert memory context.
- [x] Document Telegram link resolver visibility boundaries.
- [x] Make `write_feedback_pair` atomic per file so a partial replace cannot leave a half-written raw or analysis JSON.
- [x] Stream `BotStateStore.review_history` and resolve replace candidates against a single feedback-source index lookup.
- [x] Add tests for `/cancel` during `awaiting_revision` and `awaiting_final_replace`, and for `/draft` blocked while awaiting revision.
