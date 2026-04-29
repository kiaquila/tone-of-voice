# Plan: Telegram Bot Product

## Implementation

1. Add a reusable `tone_of_voice.bot` module with state storage, command handling, draft generation glue, and Telegram message chunking.
2. Add `scripts/run_telegram_bot.py` as the production entrypoint.
3. Add `scripts/smoke_telegram_bot.py` as the offline deployment smoke check.
4. Add operator documentation for env vars, startup, restart, and failure recovery.
5. Add a systemd service template for the AWS host family used by sibling services.
6. Update roadmap, execution plan, delivery docs, README, CI smoke checks, and tests.

## Data Layout

- `data/working/bot/sessions/chat-<id>.json` stores the active session.
- `data/working/bot/history/<timestamp>-chat-<id>.json` stores approved review history.
- `data/working/bot/drafts/` stores draft prompt and generation artifacts.

All paths are working artifacts and remain ignored by git.

## Runtime Configuration

- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`
- `TONE_OF_VOICE_TELEGRAM_BOT_TOKEN` or `TELEGRAM_BOT_TOKEN`
- `OPENAI_API_KEY` for live generation
- `OPENAI_MODEL` or CLI `--model` to override the drafting model
- `TONE_OF_VOICE_BOT_ALLOWED_CHAT_IDS` for optional access control

## Deployment Shape

The first release is a long-running Telethon bot process managed by systemd. It should be installed from the repository checkout on the same AWS host family as `vb-influencer`, with secrets supplied through an env file outside git.
