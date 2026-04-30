# Spec: Telegram Bot Product

## Goal

Turn the local drafting MVP into a Telegram bot that Kristina can use from a phone while preserving human approval before anything is published.

## User Flow

1. Kristina sends `/draft <idea>` to the bot.
2. The bot converts the idea into a Telegram `DraftRequest`.
3. The existing drafting pipeline assembles voice memory, references, prompt artifacts, and an Anthropic Messages API draft.
4. Kristina can send `/revise <instruction>` to loop on the active draft without losing the original context.
5. Kristina sends `/approve` when the draft is ready for manual handoff.

## Requirements

- The first bot release must not auto-publish.
- Session state must survive process restarts.
- Review history must be stored separately from the active session.
- The bot must support an offline dry-run smoke check that does not require Telegram or Anthropic network calls.
- The runtime must reuse the existing `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, and sibling `vb-influencer` env fallback when available.
- Bot access should be restrictable by chat id.

## Non-Goals

- No channel posting automation.
- No multi-user collaboration state.
- No cross-platform bot UI beyond Telegram drafting.
- No production secret material in the repository.

## Acceptance Criteria

- `/draft`, `/revise`, `/approve`, `/status`, `/cancel`, and `/help` are implemented.
- Bot draft and revision artifacts are written under `data/working/bot/`.
- Approval creates an append-only review history record.
- `scripts/run_telegram_bot.py --help` documents runtime options.
- `scripts/smoke_telegram_bot.py` performs an offline dry-run of the draft loop.
- Tests cover command parsing, state storage, allowlist behavior, draft/revise/approve, and message splitting.
