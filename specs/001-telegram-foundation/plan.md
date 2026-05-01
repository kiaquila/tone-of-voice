# Plan — 001 Telegram Foundation

## Technical Approach

Use a small Python implementation with reusable modules under `src/tone_of_voice/` and CLI entrypoints under `scripts/`.

Main pieces:

- environment resolution with support for local `.env` or an explicit fallback env path
- Telethon-based export of text posts from a Telegram channel
- normalized JSONL corpus output
- metrics computation from local exported files

## File Plan

- `requirements.txt`
- `src/tone_of_voice/config.py`
- `src/tone_of_voice/telegram_export.py`
- `src/tone_of_voice/metrics.py`
- `scripts/export_telegram_posts.py`
- `scripts/build_telegram_metrics.py`
- `tests/test_metrics.py`
- roadmap/spec docs updates

## Data Shape

Each exported record should contain:

- `platform`
- `source`
- `channel`
- `post_id`
- `url`
- `published_at`
- `raw_text`
- `text_length`
- `line_count`

## Risks

- Telethon session reuse can be fragile if the session path is assumed incorrectly.
- Telegram exports can include non-text messages; those should be skipped cleanly.
- Metrics should stay simple and deterministic at this stage.

## Validation

- run Python syntax validation
- run unit tests for metrics helpers
- run CLI `--help` checks
