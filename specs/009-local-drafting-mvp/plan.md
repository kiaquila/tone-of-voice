# Plan - 009 Local Drafting MVP

## Approach

Build the smallest laptop-first drafting loop that can become the base for feedback capture later:

1. Define a JSON request contract in code and docs.
2. Parse the curated reference library into structured entries.
3. Select 3 to 5 references using platform, recipe, post type, mood, topic, and request-text signals.
4. Assemble a single prompt from the durable memory docs plus selected examples.
5. Add a CLI that can either call the OpenAI Responses API or run in prompt-only dry-run mode.
6. Store every run as an inspectable artifact with the original request and selected context.
7. Add tests and CI help smoke coverage.

## Backend Choice

Use the OpenAI Responses API through Python's standard library for the first backend.

Reasons:

- no new runtime dependency is required
- Kristina's current workflow already uses OpenAI/Codex tooling
- the backend remains easy to swap once feedback and evals exist

The command reads `OPENAI_API_KEY` and defaults to `OPENAI_MODEL` when set. Otherwise it uses `gpt-5.2`, which is documented as the current general-purpose GPT-5.2 model family default.

## Risks

- Reference selection can become too clever too early.
  - Mitigation: keep scoring simple and inspectable.
- Prompt artifacts can grow noisy.
  - Mitigation: store full prompt text separately from the compact JSON run artifact.
- Generated drafts can sound plausible but miss the voice.
  - Mitigation: preserve selected context in every artifact so Step 3 can compare draft/final pairs.
