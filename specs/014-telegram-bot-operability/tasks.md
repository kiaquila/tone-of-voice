# Tasks: Telegram Bot Operability

## Implementation

- [x] Add configurable stale-update cutoff to the Telegram bot runner.
- [x] Expose the stale-update grace window in the CLI.
- [x] Document bare `/draft` group command usage.
- [x] Add unit coverage for stale-update decisions.
- [x] Add deploy workflow using a generic AWS SSM release pattern.
- [x] Add host deploy script with systemd management.
- [x] Stop existing manually launched tone-of-voice bot processes during deploy.

## Verification

- [x] Run the offline bot smoke check.
- [x] Run focused bot, drafting, and config tests.
- [x] Run the full unit test suite.
- [x] Validate feature memory.
- [x] Syntax-check the deploy script.
- [x] Validate deploy workflow YAML.

## Notes

- The live bot was not started during implementation to avoid replying to
  existing queued Telegram updates while diagnosing the production issue.
- AWS inspection found a previously running `tone-of-voice-telegram-bot.service`
  active on the production EC2 instance; it was stopped via SSM before updating
  the managed deploy path.
- GitHub repository variables for the deploy workflow were configured to match
  the production host and current bot runtime env/allowlist.
