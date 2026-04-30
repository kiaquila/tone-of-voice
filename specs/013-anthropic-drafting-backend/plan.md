# Plan: Anthropic Drafting Backend

## Implementation

1. Replace the OpenAI Responses API call with a direct Anthropic Messages API call using the existing standard library HTTP stack.
2. Default drafting to `claude-sonnet-4-6`, while preserving request-level and CLI `--model` overrides.
3. Support `TONE_OF_VOICE_ANTHROPIC_MODEL` and `ANTHROPIC_MODEL` env overrides.
4. Support `TONE_OF_VOICE_ANTHROPIC_MAX_TOKENS` and `ANTHROPIC_MAX_TOKENS` for output-budget tuning.
5. Update the local drafting CLI, Telegram bot runner, README, operations docs, roadmap, and related feature memory.
6. Add focused tests for Anthropic response extraction and credential/token env handling.

## Runtime Configuration

- `ANTHROPIC_API_KEY` for live generation.
- `TONE_OF_VOICE_ANTHROPIC_MODEL` or `ANTHROPIC_MODEL` to override the default model.
- `TONE_OF_VOICE_ANTHROPIC_MAX_TOKENS` or `ANTHROPIC_MAX_TOKENS` to override the default output budget.

## Verification

- Run the drafting and bot test slice.
- Run the offline Telegram bot smoke check.
- Run the regression eval slice.
- Open a PR and trigger the Codex AI-review gate.
