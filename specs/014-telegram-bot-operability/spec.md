# Spec: Telegram Bot Operability

## Feature ID

`014-telegram-bot-operability`

## Problem

The Telegram drafting bot must be convenient from the production group, safe to
restart after downtime, and deployable through a repeatable AWS path. Without a
managed deploy path, a manually launched bot can drift from `main` and become
hard to inspect or stop.

## Scope

- Document that the production group should use bare `/draft` commands.
- Add a startup stale-update guard so ordinary restarts do not process old
  queued Telegram messages.
- Add a production deploy workflow and host deploy script using GitHub OIDC,
  S3 release artifacts, AWS SSM, and systemd.
- Stop existing manually launched tone-of-voice bot processes during managed
  deploy without touching unrelated services that share the host.
- Keep live generation and publishing behavior unchanged.

## Acceptance Criteria

1. Bot runtime docs explain that group commands can use bare `/draft <idea>`.
2. The runner ignores Telegram messages older than a configurable startup grace
   window by default.
3. Operators can disable stale-update filtering for a deliberate replay.
4. Unit tests cover stale-cutoff calculation and stale-message decisions.
5. A deploy workflow packages a release, uploads it to S3, and runs a host
   deploy through SSM.
6. The host deploy script installs dependencies, writes/enables a systemd unit,
   preserves runtime state, and stops only tone-of-voice bot processes before
   restarting the managed service.

## Negative Scenario

Restarting the bot after several hours offline must not generate replies for old
`/draft` messages that were sent while the bot process was down.

Deploying the managed service must not kill or reconfigure unrelated bot
processes that may share the same host.
