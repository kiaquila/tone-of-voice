# Telegram Bot Product

## Purpose

The Telegram bot turns the local drafting MVP into a phone-usable workflow:

1. send an idea
2. receive a Telegram-native draft
3. revise in the same chat
4. approve for manual handoff

The first release never auto-publishes. Approval only records review history.

## Commands

- `/draft <idea>` creates a new Telegram draft from the idea.
- `/revise <instruction>` revises the active draft while preserving prior context.
- `/approve` saves the current draft to review history for manual handoff.
- `/status` shows the active session.
- `/cancel` clears the active session.
- `/help` lists commands.

If a chat already has an active draft, a plain text message is treated as a revision request.

## Runtime

Run the bot locally or on the AWS host:

```bash
python3 scripts/run_telegram_bot.py
```

Useful options:

```bash
python3 scripts/run_telegram_bot.py --dry-run
python3 scripts/run_telegram_bot.py --allowed-chat-id 123456789
python3 scripts/run_telegram_bot.py --session-dir /srv/tone-of-voice/sessions
python3 scripts/run_telegram_bot.py --output-dir /srv/tone-of-voice/data/bot
```

Dry run mode writes prompt artifacts without calling OpenAI. It is useful for host smoke checks and bot-token validation.

## Environment

Required for Telegram:

- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`
- `TONE_OF_VOICE_TELEGRAM_BOT_TOKEN` or `TELEGRAM_BOT_TOKEN`

Required for live generation:

- `OPENAI_API_KEY`

Optional:

- `OPENAI_MODEL`
- `TONE_OF_VOICE_BOT_ALLOWED_CHAT_IDS`, comma-separated
- `TELEGRAM_SESSION_NAME`
- `TONE_OF_VOICE_FALLBACK_ENV`

The env loader still checks this repository's `.env` first and then falls back to `../vb-influencer/.env` when present.

## Storage

Default state root:

```text
data/working/bot/
```

Layout:

- `sessions/chat-<id>.json` stores the active draft session.
- `history/<timestamp>-chat-<id>.json` stores approved review history.
- `drafts/` stores prompt and generation artifacts from the drafting pipeline.

These are working artifacts and should not be committed.

## Smoke Checks

Offline smoke check:

```bash
python3 scripts/smoke_telegram_bot.py
```

Live process help check:

```bash
python3 scripts/run_telegram_bot.py --help
```

Host smoke before enabling systemd:

```bash
python3 scripts/run_telegram_bot.py --dry-run --allowed-chat-id <your-chat-id>
```

Then send `/draft smoke test for the bot` to the bot. The expected result is a dry-run reply with artifact paths and no OpenAI call.

## Failure Recovery

- If the bot cannot start, check `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, and bot token env vars first.
- If generation fails, confirm `OPENAI_API_KEY` and rerun with `--dry-run` to separate prompt assembly from model access.
- If the bot gets stuck in a stale draft, send `/cancel`.
- If systemd restarts repeatedly, inspect the journal and run the offline smoke check from the same checkout and env file.

## Systemd

Use `deploy/systemd/tone-of-voice-telegram-bot.service.example` as the starting point for the host unit. Keep the real env file outside git.
