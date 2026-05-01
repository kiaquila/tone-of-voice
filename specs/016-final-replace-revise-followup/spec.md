# Feature Spec - Final Replace And Revise Follow-Up

## User Need

The Telegram bot needs to tolerate the real editorial loop: a final can be sent
too early and corrected later, and a revision request can start with a bare
`/revise` before the instruction is ready to paste.

## Scope

- Add `/final --replace <text or Telegram link>` to overwrite the captured final
  for the same draft artifact instead of creating a duplicate feedback pair.
- Support `/final --replace` without a body by treating the next plain message
  as the replacement final.
- Support `/revise` without a body by treating the next plain message as the
  revision instruction.
- Keep `/final`, `/stat`, and feedback memory scoped to the requesting chat.
- Harden the previous `/final` implementation review findings without changing
  the human-in-the-loop/no-autoposting model.

## Non-Goals

- No auto-publishing.
- No model fine-tuning.
- No new public multi-user authorization model for Telegram link reads.
- No change to the current fit-score formula.

## Success Criteria

- A corrected final can replace the prior raw/analysis feedback pair for the
  same draft and `/stat` still counts it as one pair.
- A bare `/revise` moves the session into a waiting state and the next plain
  message revises the draft.
- Duplicate `/final` still fails closed unless `--replace` is explicit.
- Follow-up review hardening removes user-facing exception details, avoids a
  raw-file scan for the common duplicate lookup, documents Telegram link
  visibility boundaries, and extends tests for the low-risk gaps.
