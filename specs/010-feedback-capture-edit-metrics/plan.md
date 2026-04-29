# Plan - Feedback Capture And Edit Metrics

## Approach

Build the smallest manual learning loop that can later feed evals:

1. Add a reusable `tone_of_voice.feedback` module.
2. Define a `FeedbackInput` schema that accepts either direct draft text or a draft artifact from Step 2.
3. Write raw feedback records under `data/working/feedback/raw/`.
4. Write normalized analysis records under `data/working/feedback/analysis/`.
5. Compute character and word edit distance, percent changed, line changes, punctuation changes, and emoji changes.
6. Add `scripts/capture_feedback.py` for manual capture.
7. Add `scripts/summarize_feedback.py` for trend summaries.
8. Add a sample Telegram feedback input.
9. Update docs, roadmap, and CI CLI smoke checks.
10. Add focused unit tests.

## Design Notes

- Use the standard library only so the baseline install stays small.
- Keep feedback data under ignored `data/working/` because real draft/final pairs may contain unpublished text.
- Store correction tags manually at first; reliable automatic tone diagnosis belongs in a later eval/tuning step.
- Keep platform validation shared with the drafting module to avoid drift.

## Risks

- Manual capture can become annoying.
  - Mitigation: allow reuse of local draft artifacts and keep the JSON shape small.
- Correction tags may fragment.
  - Mitigation: document a short starting tag list and keep tags `snake_case`.
- Edit distance can be over-interpreted.
  - Mitigation: treat metrics as trend signals, not as a standalone quality score.
