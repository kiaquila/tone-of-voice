# Spec - Feedback Capture And Edit Metrics

Execute Step 3 from `docs/07-product-execution-plan.md`: capture draft/final pairs and compute edit metrics so the writing system can learn from Kristina's edits.

## Scope

In scope:

- manual JSON capture of generated draft, approved draft, edited draft, and final published text
- feedback storage under ignored local working data
- separate raw and analysis artifacts
- edit-distance and revision-quality metrics
- a repeatable summary command for common edits and tone corrections
- docs, examples, and tests for the workflow

Out of scope:

- automatic Telegram bot capture
- CI regression eval gates
- automatic updates to the voice snapshot
- publishing or approving posts

## Requirements

1. Feedback capture must work from an explicit JSON input.
2. Feedback capture should optionally reuse a `data/working/drafts/*.json` artifact from the local drafting MVP.
3. Raw feedback text must be stored separately from normalized analysis output.
4. Metrics must include draft-to-final edit distance and percent changed.
5. The summary command must aggregate metrics by platform/post type and count recurring tone correction tags.
6. The storage shape must support Telegram first while allowing Threads and LinkedIn records.
7. README, roadmap, execution plan, and durable docs must point future sessions at Step 4 after this lands.

## Acceptance Criteria

- `python3 scripts/capture_feedback.py --help` works.
- `python3 scripts/summarize_feedback.py --help` works.
- `python3 scripts/capture_feedback.py examples/feedback-capture.telegram.json --output-dir <tmp>` writes `raw/` and `analysis/` records.
- `python3 scripts/summarize_feedback.py --feedback-dir <tmp>` prints a markdown summary.
- Unit tests cover edit metrics, storage separation, artifact-derived context, and summary aggregation.
- Roadmap and README mark Step 3 as implemented and point future work at Step 4.
