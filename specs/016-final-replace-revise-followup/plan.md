# Plan - Final Replace And Revise Follow-Up

## Implementation

1. Extend the bot command flow with explicit waiting states for bare `/revise`
   and `/final --replace`.
2. Reuse the existing feedback writer with the existing feedback record id when
   replacing a final so the raw/analysis pair is overwritten in place.
3. Update bot and feedback docs so the phone workflow explains replacement and
   pending revision behavior.
4. Address the previous review findings in a separate fixes commit: sanitize
   user-facing errors, index source-artifact lookups, make feedback memory
   prompt-injection-resistant, and cover the missing tests.

## Verification

- Unit tests for pending revise, direct replace, pending replace, duplicate
  guard, and replace-without-existing-feedback behavior.
- Unit tests for the review fixes: generic resolver/generator errors,
  published timestamp capture, cancel while awaiting final, source index use,
  and inert feedback memory wording.
- Full local regression command set before opening the PR.
