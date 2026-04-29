# Plan - Regression Eval Gate

## Approach

Build the smallest useful offline gate before introducing the Telegram bot:

1. Add a reusable `tone_of_voice.evals` module.
2. Define a compact JSON suite format for regression cases.
3. Commit a first seed suite under `evals/regression/`.
4. Reuse feedback edit-distance metrics instead of adding a second metric implementation.
5. Add rule checks for banned and required phrases.
6. Add prompt-contract checks by dry-running `build_prompt_bundle` for cases with requests.
7. Add `scripts/run_regression_evals.py` for local and CI runs.
8. Extend CI so the eval slice runs only when drafting, eval, or core voice-memory surfaces change.
9. Add focused tests.
10. Update docs, roadmap, README, delivery workflow, and feature memory.

## Design Notes

- Keep the first gate deterministic so it can run without credentials.
- Treat metrics as guardrails, not a full quality score.
- Keep the suite small enough for humans to inspect in review.
- Real feedback records stay under ignored working data unless explicitly promoted into an eval suite.

## Risks

- The first suite is too small to catch subtle regressions.
  - Mitigation: document that real cases should be added after more feedback capture.
- Thresholds can become arbitrary.
  - Mitigation: keep per-case thresholds visible in JSON and explain the default values.
- CI can become noisy for doc refreshes.
  - Mitigation: path-filter the eval step inside `baseline-checks`.
