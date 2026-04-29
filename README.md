# tone-of-voice

Private working repository for capturing, updating, and reusing Kristina's evolving author voice across Telegram, Threads, and LinkedIn.

## Naming

In prose, the standard phrase is `tone of voice`.

- Use `tone of voice` in normal writing.
- Use `tone-of-voice` as a repository name, slug, or compound label when a hyphenated identifier is convenient.
- This is a fixed collocation, not a set expression in the idiomatic sense.

## Goal

This repository is not a one-off prompt dump. It is durable memory for:

- voice invariants that should survive across sessions
- platform-specific adaptations
- tagged reference examples
- refresh notes based on newly published content
- generation workflows for drafting new posts on demand
- feedback capture from draft-to-final edits

## Initial Scope

- Capture the current `@vibecodesh` tone snapshot
- Store the first voice-memory architecture
- Assess reuse of the existing Telethon integration from `vb-influencer`
- Account for channel differences between Telegram, Threads, and LinkedIn

## Recommended Working Loop

1. Refresh source content from Telegram and other platforms.
2. Update the current voice snapshot only when there is enough new material.
3. Curate strong examples into a tagged reference library.
4. Draft new platform-specific posts from the memory layers, not from a single prompt.
5. Periodically revise the invariants and stop-list as the public voice evolves.

## Repository Layout

- `AGENTS.md` — instructions for future AI sessions
- `docs/00-principles.md` — what this repo is for and how to keep it useful
- `docs/01-current-voice-snapshot.md` — concise description of the current voice
- `docs/02-memory-system.md` — long-term memory design
- `docs/03-source-ingestion.md` — what we can ingest now and what needs new collectors
- `docs/04-platform-adaptation.md` — how the voice should bend by platform
- `docs/05-roadmap.md` — phased path toward a self-improving writing assistant
- `docs/06-delivery-workflow.md` — CI, guardrails, and PR delivery contract
- `docs/07-product-execution-plan.md` — canonical numbered implementation plan toward the full product
- `docs/10-reference-library.md` — curated tagged examples for retrieval before drafting
- `docs/11-refresh-log.md` — dated source refreshes and snapshot-update decisions
- `docs/12-stop-list.md` — language and drafting moves that flatten the voice
- `docs/13-drafting-recipes.md` — repeatable workflows for platform-specific drafts
- `docs/14-feedback-capture.md` — storage schema and workflow for draft/final feedback pairs
- `docs/15-regression-evals.md` — offline regression eval gate for drafting changes
- `docs/16-telegram-bot-product.md` — Telegram bot usage, operations, and recovery notes
- `evals/regression/` — committed draft/final eval suites
- `examples/draft-request.telegram.json` — sample structured input for the local drafting MVP
- `examples/feedback-capture.telegram.json` — sample manual feedback input
- `specs/` — lightweight feature memory for software changes
- `src/` — reusable implementation modules
- `scripts/` — CLI entrypoints for ingestion and analysis

## Current Decision

Use a lightweight documentation-first setup now. Borrow ideas from spec-driven workflows where they help, but avoid turning this repository into a heavy software process project before we actually need automation.

The current implementation order for future sessions lives in `docs/07-product-execution-plan.md`. Step 5 now has a Telegram bot implementation and should be smoke-tested on the target host before moving fully into cross-platform expansion.

## First Working Commands

Export Telegram posts:

```bash
python3 scripts/export_telegram_posts.py vibecodesh --limit 20
```

Build metrics from an exported corpus:

```bash
python3 scripts/build_telegram_metrics.py data/raw/telegram/vibecodesh.jsonl
```

Assemble a local draft prompt without calling a model:

```bash
python3 scripts/draft_post.py examples/draft-request.telegram.json --dry-run
```

Generate a draft with the OpenAI Responses API:

```bash
export OPENAI_API_KEY=...
python3 scripts/draft_post.py examples/draft-request.telegram.json
```

Capture a draft/final feedback pair:

```bash
python3 scripts/capture_feedback.py examples/feedback-capture.telegram.json
```

Summarize feedback metrics:

```bash
python3 scripts/summarize_feedback.py
```

Run the regression eval slice:

```bash
python3 scripts/run_regression_evals.py
```

Run an offline Telegram bot smoke check:

```bash
python3 scripts/smoke_telegram_bot.py
```

Run the Telegram bot:

```bash
export TONE_OF_VOICE_TELEGRAM_BOT_TOKEN=...
export OPENAI_API_KEY=...
python3 scripts/run_telegram_bot.py --allowed-chat-id <your-chat-id>
```

If this repository does not have its own `.env`, the exporter will automatically try to reuse `../vb-influencer/.env` and the sibling Telethon session when available.

Draft artifacts are written to `data/working/drafts/` by default and are intentionally ignored by git.
Feedback artifacts are written to `data/working/feedback/` by default and are intentionally ignored by git.
Structured eval reports can be written under `data/working/evals/` and are intentionally ignored by git.
Telegram bot state, review history, and bot draft artifacts are written under `data/working/bot/` by default and are intentionally ignored by git.
