# Telegram Bot Product

## Purpose

The Telegram bot turns the local drafting MVP into a phone-usable workflow:

1. send an idea
2. receive a Telegram-native draft
3. revise in the same chat
4. approve for manual handoff
5. capture the final edited version so future drafts can learn from the diff

The bot never auto-publishes. Approval records review history; `/final` captures
the final text or a Telegram post link for feedback learning.

## Production Chat Workflow

The production bot is `@<your bot>` in the `<your group>` Telegram chat.

Start a draft with:

```text
/draft <idea>
```

In the group chat, use the mentioned command if needed:

```text
/draft@<your bot> <idea>
```

Good requests include the angle, rough facts, desired mood, and any constraint that should survive into the post. For example:

```text
/draft@<your bot> короткий пост о том, что бот для черновиков запущен; акцент на human-in-the-loop, без пафоса
```

After a draft exists, use `/revise <instruction>` or send a plain text
revision request. You can also send `/revise` by itself and then provide the
revision instruction as the next plain message. Use `/approve` when the draft
is ready for manual handoff, or `/cancel` to clear the active draft without
saving approval history.

After manual edits, capture the final version:

```text
/final <final post text>
```

For long posts, send `/final` first and then send the final version as the next
plain message. If the final post is already published in a Telegram channel,
send the public or private Telegram post link as a standalone `/final` value;
topic/thread links are supported. The bot will try to read the post text through
Telethon and will ask for pasted text if the post is not visible to the bot.
If the final text merely contains a Telegram URL, the bot keeps the pasted text
as the final version instead of fetching the linked post.

If you already captured the final version and then edited it again, overwrite
the same draft/final pair instead of creating a duplicate:

```text
/final --replace <corrected final post text or Telegram link>
```

For long replacements, send `/final --replace` first and then send the corrected
final version as the next plain message.

Use `/stat` to inspect this chat's captured feedback count, latest fit score,
rolling score trend, and whether feedback memory is being used in future drafts.

## Commands

- `/draft <idea>` creates a new Telegram draft from the idea. Refuses if you already have an active in-progress draft; send `/cancel` or `/approve` first.
- `/revise <instruction>` revises the active draft while preserving prior context. `/revise` without text waits for the next plain message as the revision instruction.
- `/approve` saves the current draft to review history for manual handoff and clears the active session so the next `/draft` starts fresh.
- `/final <text or Telegram link>` captures the final edited version against the active draft or the latest approved draft from this chat. `/final` without text waits for the next plain message as the final version.
- `/final --replace <text or Telegram link>` overwrites the existing captured final for the current draft or latest finalized draft. `/final --replace` without text waits for the next plain message as the replacement.
- `/stat` shows same-chat feedback metrics, fit-score trend, and the current learning signal.
- `/status` shows the active session.
- `/cancel` clears the active session.
- `/help` lists commands.

If a chat already has an active draft, a plain text message is treated as a revision request. If the chat is waiting after `/revise`, the next plain text message is used as the revision instruction. If the chat is waiting after `/final` or `/final --replace`, the next plain text message is captured as the final version or replacement instead.

In the production group, use the short command form: `/draft <idea>`.
The handler also accepts `/draft@<your bot> <idea>`, but the username suffix is
only needed when another bot in the same group also responds to `/draft`.

## Runtime

Run the bot locally or on the AWS host:

```bash
python3 scripts/run_telegram_bot.py
```

Useful options:

```bash
python3 scripts/run_telegram_bot.py --dry-run
python3 scripts/run_telegram_bot.py --allowed-chat-id 123456789
python3 scripts/run_telegram_bot.py --drop-stale-seconds 300
python3 scripts/run_telegram_bot.py --session-dir /opt/tone-of-voice/sessions
python3 scripts/run_telegram_bot.py --output-dir /opt/tone-of-voice/data/bot
```

Dry run mode writes prompt artifacts without calling Anthropic. It is useful for host smoke checks and bot-token validation.

The runner refuses to start without an allowlist. Either pass `--allowed-chat-id <id>`, set `TONE_OF_VOICE_BOT_ALLOWED_CHAT_IDS=<id1>,<id2>`, or pass `--allow-public` to explicitly opt out (only sensible for short-lived smoke tests with a unique bot username).

By default, the runner ignores messages older than startup minus 300 seconds so
restarting a long-stopped bot does not answer stale drafts from the Telegram
update backlog. Use `--drop-stale-seconds <seconds>` to adjust the grace window,
or a negative value to process all queued updates during a controlled replay.

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

The env loader checks this repository's `.env` first. Set `TONE_OF_VOICE_FALLBACK_ENV` or pass `--env-file` explicitly to reuse credentials from another local project.

### Migration: session stem rename

Earlier revisions of the export tooling resolved Telethon sessions to a project-specific default stem. The default has been renamed to `telegram_session` to keep the public repository free of local identifiers. The Telegram bot itself is unaffected: it pins its own `tone_of_voice_bot` session name.

If you are upgrading from a previous deployment and have a `.session` file in the repository root with a different stem, pin the existing name before restarting any caller of `resolve_session_stem` (e.g. `scripts/export_telegram_posts.py`):

```bash
export TELEGRAM_SESSION_NAME=<existing-session-stem>
```

`resolve_session_stem` now prints a stderr warning when the default session file is missing but another `.session` file is present in the repo root, so a missed migration becomes visible instead of silently re-prompting for a fresh Telegram login.

## Storage

Default state root:

```text
data/working/bot/
```

The systemd template at `deploy/systemd/tone-of-voice-telegram-bot.service.example` overrides this with `--output-dir /opt/tone-of-voice/data/bot` so production state can live outside the repo checkout. Adjust the override to match your host layout.

Layout:

- `sessions/chat-<id>.json` stores the active draft session.
- `history/<timestamp>-chat-<id>-event-<n>-<rand>.json` stores approved review history. The history directory is append-only; rotate or archive externally if it grows too large.
- `drafts/` stores prompt and generation artifacts from the drafting pipeline. `/cancel` clears the session JSON but leaves draft artifacts in place for audit; remove them manually if no longer needed.
- `feedback/raw/` and `feedback/analysis/` store Telegram-captured draft/final pairs and normalized edit metrics from `/final`.

These are working artifacts and should not be committed.

## Learning Signal

`/final` does not fine-tune a model. It closes a feedback-memory loop:

- the bot stores the approved/generated draft and the final edited text
- edit metrics become a fit score, where fewer manual changes means a higher score
- `/stat` compares the latest and rolling fit scores so progress is visible over time
- future `/draft` calls include a compact memory block from recent final versions in the same chat

The score can move down on a harder topic. Treat the rolling trend as the useful
signal, not any single post.

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
- If a group command gets no reply, confirm the process is running and send the command with the bot username, for example `/draft@<your bot> <idea>`.
- If generation fails, confirm `ANTHROPIC_API_KEY` and rerun with `--dry-run` to separate prompt assembly from model access.
- If `/final <Telegram link>` cannot read a post, confirm the bot can see the channel post or paste the final text directly.
- If the bot gets stuck in a stale draft, send `/cancel`.
- If systemd restarts repeatedly, inspect the journal and run the offline smoke check from the same checkout and env file.

## Systemd

Use `deploy/systemd/tone-of-voice-telegram-bot.service.example` as the starting point for the host unit. Keep the real env file outside git.

Production can run as `tone-of-voice-telegram-bot.service` on your preferred host. A typical service uses:

- working directory: `/opt/tone-of-voice`
- environment file: `<env file path>`
- state root: `/opt/tone-of-voice/data/bot`
- session directory: `/opt/tone-of-voice/sessions`
- allowed chat: `<your-chat-id>`

## Production Deploy

Production deploys use `.github/workflows/deploy.yml`, which follows a generic GitHub OIDC + S3 + AWS SSM release flow. The required repository variables are:

- `AWS_REGION`
- `AWS_DEPLOY_ROLE_ARN`
- `DEPLOY_S3_BUCKET`
- `DEPLOY_INSTANCE_ID`
- `DEPLOY_TARGET_DIR`, for example `/opt/tone-of-voice`
- `BOT_ENV_FILE`, optional path to an env file outside the deploy directory; the deploy script consumes it via the `BOT_ENV_FILE` environment variable
- `BOT_ALLOWED_CHAT_IDS`, optional comma-separated allowlist of Telegram chat IDs

On the host, `scripts/deploy_release.sh` preserves `.env`, `.venv/`, `data/`,
Telegram session files, logs, and deploy metadata. It installs the Python package
into the target virtualenv, writes a systemd unit for
`tone-of-voice-telegram-bot`, stops any old manually launched tone-of-voice bot
process, and restarts the managed service.
