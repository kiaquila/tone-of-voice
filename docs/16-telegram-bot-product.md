# Telegram Bot Product

## Purpose

The Telegram bot turns the local drafting MVP into a phone-usable workflow:

1. send an idea
2. receive a Telegram-native draft
3. revise in the same chat
4. approve for manual handoff

The first release never auto-publishes. Approval only records review history.

## Production Chat Workflow

The production bot is `@vbnews_bot` in the `Editorial Room` Telegram chat.

Start a draft with:

```text
/draft <idea>
```

In the group chat, use the mentioned command if needed:

```text
/draft@vbnews_bot <idea>
```

Good requests include the angle, rough facts, desired mood, and any constraint that should survive into the post. For example:

```text
/draft@vbnews_bot короткий пост о том, что бот для черновиков запущен; акцент на human-in-the-loop, без пафоса
```

After a draft exists, use `/revise <instruction>` or send a plain text revision request. Use `/approve` when the draft is ready for manual handoff, or `/cancel` to clear the active draft without saving approval history.

## Commands

- `/draft <idea>` creates a new Telegram draft from the idea. Refuses if you already have an active in-progress draft; send `/cancel` or `/approve` first.
- `/revise <instruction>` revises the active draft while preserving prior context.
- `/approve` saves the current draft to review history for manual handoff and clears the active session so the next `/draft` starts fresh.
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

Dry run mode writes prompt artifacts without calling Anthropic. It is useful for host smoke checks and bot-token validation.

The runner refuses to start without an allowlist. Either pass `--allowed-chat-id <id>`, set `TONE_OF_VOICE_BOT_ALLOWED_CHAT_IDS=<id1>,<id2>`, or pass `--allow-public` to explicitly opt out (only sensible for short-lived smoke tests with a unique bot username).

## Environment

Required for Telegram:

- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`
- `TONE_OF_VOICE_TELEGRAM_BOT_TOKEN` or `TELEGRAM_BOT_TOKEN`

Required for live generation:

- `ANTHROPIC_API_KEY`

Optional:

- `TONE_OF_VOICE_ANTHROPIC_MODEL`
- `ANTHROPIC_MODEL`
- `TONE_OF_VOICE_ANTHROPIC_MAX_TOKENS`
- `ANTHROPIC_MAX_TOKENS`
- `TONE_OF_VOICE_BOT_ALLOWED_CHAT_IDS`, comma-separated
- `TELEGRAM_SESSION_NAME`
- `TONE_OF_VOICE_FALLBACK_ENV`

The env loader still checks this repository's `.env` first and then falls back to `../vb-influencer/.env` when present.

## Storage

Default state root:

```text
data/working/bot/
```

The systemd template at `deploy/systemd/tone-of-voice-telegram-bot.service.example` overrides this with `--output-dir /srv/tone-of-voice/data/bot` so production state lives under `/srv` rather than the repo checkout. Adjust the override to match your host layout.

Layout:

- `sessions/chat-<id>.json` stores the active draft session.
- `history/<timestamp>-chat-<id>-event-<n>-<rand>.json` stores approved review history. The history directory is append-only; rotate or archive externally if it grows too large.
- `drafts/` stores prompt and generation artifacts from the drafting pipeline. `/cancel` clears the session JSON but leaves draft artifacts in place for audit; remove them manually if no longer needed.

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

Then send `/draft smoke test for the bot` to the bot. The expected result is a dry-run reply with artifact paths and no Anthropic call.

## Failure Recovery

- If the bot cannot start, check `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, and bot token env vars first.
- If generation fails, confirm `ANTHROPIC_API_KEY` and rerun with `--dry-run` to separate prompt assembly from model access.
- If the bot gets stuck in a stale draft, send `/cancel`.
- If systemd restarts repeatedly, inspect the journal and run the offline smoke check from the same checkout and env file.

## Systemd

Use `deploy/systemd/tone-of-voice-telegram-bot.service.example` as the starting point for the host unit. Keep the real env file outside git.

Production currently runs as `tone-of-voice-telegram-bot.service` on the same AWS host family as `vb-influencer`. The live service uses:

- working directory: `/srv/tone-of-voice`
- environment file: `/home/ubuntu/vb-influencer/.env`
- state root: `/srv/tone-of-voice/data/bot`
- session directory: `/srv/tone-of-voice/sessions`
- allowed chat: `Editorial Room`
