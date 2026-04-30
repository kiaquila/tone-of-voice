# Plan - 009 Local Drafting MVP

## Approach

Build the smallest laptop-first drafting loop that can become the base for feedback capture later:

1. Define a JSON request contract in code and docs.
2. Parse the curated reference library into structured entries.
3. Select 3 to 5 references using platform, recipe, post type, mood, topic, and request-text signals.
4. Assemble a single prompt from the durable memory docs plus selected examples.
5. Add a CLI that can either call the configured model backend or run in prompt-only dry-run mode.
6. Store every run as an inspectable artifact with the original request and selected context.
7. Add tests and CI help smoke coverage.

## Backend Choice

Use the Anthropic Messages API through Python's standard library for live generation.

Reasons:

- no new runtime dependency is required
- the author's adjacent bot workflow already has `ANTHROPIC_API_KEY`
- the backend remains easy to swap once feedback and evals show a reason to do so

The command reads `ANTHROPIC_API_KEY` and defaults to `TONE_OF_VOICE_ANTHROPIC_MODEL` or `ANTHROPIC_MODEL` when set. Otherwise it uses `claude-sonnet-4-6`, which is documented as Anthropic's current Sonnet API alias.

## Risks

- Reference selection can become too clever too early.
  - Mitigation: keep scoring simple and inspectable.
- Prompt artifacts can grow noisy.
  - Mitigation: store full prompt text separately from the compact JSON run artifact.
- Generated drafts can sound plausible but miss the voice.
  - Mitigation: preserve selected context in every artifact so Step 3 can compare draft/final pairs.
