# Feedback Capture

## Purpose

This layer stores what changed between a generated draft and the final published text. It gives the system a way to learn from the author's edits instead of only from old source posts.

Feedback can be captured manually from JSON files or through the Telegram bot's
`/final` command. The bot path still keeps the author in the loop: it records a
finished text after manual edits, but it does not publish anything.

## Storage Layout

Feedback artifacts live under `data/working/feedback/`, which is ignored by git:

- `raw/` stores human-readable draft/final records with the original text.
- `analysis/` stores normalized metrics derived from the raw record.

Separating raw text from analysis keeps future evals from mixing source material, notes, and computed metrics in one blob.

The Telegram bot stores the same raw/analysis shape under its bot output root,
for example `data/working/bot/feedback/` locally or
`/opt/tone-of-voice/data/bot/feedback/` on a host configured with that
`--output-dir`.

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

## Telegram Bot Workflow

After a generated draft has been manually edited, capture the final version:

```text
/final <final post text>
```

For long posts, send `/final` and then the final text as the next plain
message. If the final post is already published in Telegram, send the post link
as the entire `/final` value:

```text
/final https://t.me/<channel>/<message-id>
```

The bot reads the visible Telegram post text, including topic/thread links,
stores the source URL and publish time when available, computes the
draft-to-final metrics, and clears the active session. It rejects duplicate
`/final` captures for the same draft artifact.
If a pasted final text contains a Telegram URL alongside other text, the pasted
text wins and no link fetch is attempted.

If the final was captured too early, use `/final --replace <text or Telegram
link>` to overwrite the existing raw/analysis pair for the same draft artifact.
For long replacements, send `/final --replace` first and then send the corrected
final text as the next plain message.

Use `/stat` to inspect same-chat feedback pairs, latest fit score, rolling
trend, median edit percentages, common correction tags, and the learning signal.
Feedback memory and stats are scoped to the chat where the final was captured.

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
