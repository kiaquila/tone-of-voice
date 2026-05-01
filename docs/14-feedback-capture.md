# Feedback Capture

## Purpose

This layer stores what changed between a generated draft and the final published text. It gives the system a way to learn from the author's edits instead of only from old source posts.

The first version is intentionally manual. Automation can come later after the storage shape proves useful.

## Storage Layout

Feedback artifacts live under `data/working/feedback/`, which is ignored by git:

- `raw/` stores human-readable draft/final records with the original text.
- `analysis/` stores normalized metrics derived from the raw record.

Separating raw text from analysis keeps future evals from mixing source material, notes, and computed metrics in one blob.

## Raw Record Schema

Each raw record includes:

- `schema_version`
- `id`
- `created_at`
- `platform`
- `source.draft_artifact_path`
- `request`
- `draft_text`
- `approved_draft_text`
- `edited_text`
- `final_text`
- `published.url`
- `published.published_at`
- `classification.post_type`
- `classification.topics`
- `classification.mood`
- `classification.tone_corrections`
- `classification.structural_notes`
- `notes`

`final_text` is required. `edited_text` is optional because some drafts may go straight from generated draft to final text.

## Analysis Schema

Each analysis record includes:

- `feedback_id`
- `created_at`
- `platform`
- `post_type`
- `topics`
- `tone_corrections`
- `structural_notes`
- `comparisons.draft_to_final`
- `comparisons.draft_to_edited` when edited text exists
- `comparisons.edited_to_final` when edited text exists

Each comparison stores character and word edit distance, percent changed, line delta, emoji delta, question delta, and exclamation delta.

## Manual Workflow

Capture a pair from a JSON file:

```bash
python3 scripts/capture_feedback.py examples/feedback-capture.telegram.json
```

Capture against a generated draft artifact:

```bash
python3 scripts/capture_feedback.py feedback.json --draft-artifact data/working/drafts/<artifact>.json
```

Summarize recent pairs:

```bash
python3 scripts/summarize_feedback.py
```

Write a markdown summary:

```bash
python3 scripts/summarize_feedback.py --markdown-output data/working/feedback/summary.md
```

## Correction Tags

Use small `snake_case` tags for repeated tone changes. Good starting tags:

- `stronger_hook`
- `less_generic`
- `add_human_wink`
- `more_first_person`
- `more_concrete_tool_detail`
- `reduce_corporate_language`
- `shorter_structure`

Do not over-design the taxonomy early. Add a tag when it helps describe a repeated edit pattern.

## How Future Evals Use This

The regression eval gate can promote selected records from this storage shape into committed eval cases. Read analysis files for metrics and raw files only when the paired texts are deliberately being added to an eval suite.
