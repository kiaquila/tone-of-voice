# Spec: Anthropic Drafting Backend

## Goal

Use an existing Anthropic API key for live draft generation so the Telegram bot can run without requiring a separate OpenAI key.

## Requirements

- Live draft generation must call the Anthropic Messages API.
- The runtime must read `ANTHROPIC_API_KEY` from the normal env loading path, including an explicit fallback env path when configured.
- The default model must be an Anthropic model, with CLI/request/env overrides still supported.
- Dry-run mode must remain fully offline and must not require model credentials.
- Draft artifacts must continue recording backend and model metadata.

## Non-Goals

- No change to Telegram bot commands or session storage.
- No channel auto-publishing.
- No additional model provider abstraction until a second live backend is needed again.

## Acceptance Criteria

- `scripts/draft_post.py` generates with Anthropic when not in dry-run mode.
- `scripts/run_telegram_bot.py` generates bot drafts with Anthropic when not in dry-run mode.
- Missing credential errors point to `ANTHROPIC_API_KEY`.
- Docs and feature memory no longer instruct operators to configure `OPENAI_API_KEY`.
- Tests cover Anthropic response extraction and env handling.
