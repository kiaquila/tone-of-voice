# Plan: Telegram Bot Operability

## Approach

Add a narrow startup filter in the Telegram event handler. The filter compares
the event message date with a startup cutoff and ignores messages that predate
the configured grace window. Expose the grace window through the existing
runner CLI so host operators can tune or disable it without editing code.

Then add the missing production deploy surface as a generic GitHub OIDC + S3 +
AWS SSM release flow: GitHub Actions checks out the release revision, archives
it, uploads it to S3, and sends an AWS SSM command to the production EC2
instance. The remote deploy script installs the package into the target
virtualenv, writes a systemd unit, stops any old manually launched
tone-of-voice bot process, and restarts the managed service.

## Files

- `src/tone_of_voice/bot.py`
- `scripts/run_telegram_bot.py`
- `scripts/deploy_release.sh`
- `.github/workflows/deploy.yml`
- `deploy/systemd/tone-of-voice-telegram-bot.service.example`
- `tests/test_bot.py`
- `docs/05-roadmap.md`
- `docs/06-delivery-workflow.md`
- `docs/07-product-execution-plan.md`
- `docs/16-telegram-bot-product.md`

## Verification

- `PYTHONPATH=src .venv/bin/python scripts/smoke_telegram_bot.py`
- `PYTHONPATH=src .venv/bin/python -m pytest`
- `PYTHONPATH=src .venv/bin/python scripts/check_feature_memory.py`
- `bash -n scripts/deploy_release.sh`
