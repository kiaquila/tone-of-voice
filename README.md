# tone-of-voice

Working repository for capturing, updating, and reusing the author's evolving voice across Telegram, Threads, and LinkedIn.

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
- retrieval experiments for RAG-style voice memory
- generated-output A/B experiments for draft quality comparisons

## Initial Scope

- Capture the current `<your channel>` tone snapshot
- Store the first voice-memory architecture
- Assess reuse of the existing Telethon integration from `<sibling Telegram project>`
- Account for channel differences between Telegram, Threads, and LinkedIn

## Recommended Working Loop

1. Refresh source content from Telegram and other platforms.
2. Update the current voice snapshot only when there is enough new material.
3. Curate strong examples into a tagged reference library.
4. Draft new platform-specific posts from the memory layers, not from a single prompt.
5. Periodically revise the invariants and stop-list as the public voice evolves.

## Repository Layout

- `.unicorn-hub/config.json` — repository-local process config adapted from Unicorn Hub
- `.specify/` — constitution and feature-memory templates for spec-first work
- `AGENTS.md` — instructions for future AI sessions
- `CLAUDE.md` — Claude-specific implementation-agent guidance
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
- `docs/17-rag-style-memory.md` — RAG-style memory index, retrieval strategies, and experiment workflow
- `evals/regression/` — committed draft/final eval suites
- `evals/retrieval/` — committed retrieval experiment suites
- `evals/generated-output/` — committed generated-output A/B suites
- `examples/draft-request.telegram.json` — sample structured input for the local drafting MVP
- `examples/feedback-capture.telegram.json` — sample manual feedback input
- `specs/` — lightweight feature memory for software changes
- `src/` — reusable implementation modules
- `scripts/` — CLI entrypoints for ingestion and analysis

## Current Decision

Use the existing `docs/` voice-memory system as the durable project context, and
borrow the target-repo pieces of Unicorn Hub where they make delivery safer:
process config, spec/SENAR templates, local preflight, and AI-review routing.
Do not import blueprint-source-only folders such as `templates/`, `profiles/`,
or `docs_project/`.

The current implementation order for future sessions lives in
`docs/07-product-execution-plan.md`. Step 5 has a production Telegram bot in
`<your group>`, and Step 6 now has local and LlamaIndex-backed RAG-style memory
paths plus the first generated-output A/B harness. The next product sequence is
judge-style evals before cross-platform expansion.

## Using The Telegram Bot

The production bot is `@<your bot>` in the `<your group>` Telegram chat. It drafts Telegram-native posts only after an explicit request; it never auto-publishes.

To create a post draft, send:

```text
/draft <your idea>
```

In a group chat, mention the bot if Telegram does not route slash commands automatically:

```text
/draft@<your bot> short post about shipping the drafting bot, with a human-in-the-loop angle
```

After the bot replies with a draft:

- send `/revise <what to change>` to iterate on the active draft
- send a plain text revision request if a draft is already active
- send `/approve` to save the draft to review history and clear the active session
- send `/cancel` to discard the active session
- send `/status` to see whether a draft is active

Approval is only a handoff marker. Publishing stays manual.

## First Working Commands

Export Telegram posts:

```bash
python3 scripts/export_telegram_posts.py "<your channel>" --limit 20
```

Build metrics from an exported corpus:

```bash
python3 scripts/build_telegram_metrics.py "data/raw/telegram/<your channel>.jsonl"
```

Assemble a local draft prompt without calling a model:

```bash
python3 scripts/draft_post.py examples/draft-request.telegram.json --dry-run
```

Generate a draft with the Anthropic Messages API:

```bash
export ANTHROPIC_API_KEY=...
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

Build and query the style-memory index:

```bash
python3 scripts/build_style_memory_index.py
python3 scripts/query_style_memory.py --request examples/draft-request.telegram.json --build
```

Build and query the LlamaIndex-backed retrieval path:

```bash
python3 scripts/build_style_memory_index.py --llama-index
python3 scripts/query_style_memory.py "multi-agent setup costs" --build --backend llama_index --source-type reference_example
```

Run the retrieval experiment slice:

```bash
python3 scripts/run_retrieval_experiments.py
```

Run the generated-output A/B experiment slice:

```bash
python3 scripts/run_generated_output_experiments.py
```

The eval runners share the same `--suite`, `--variant` where applicable, and
`--json-output` behavior. Suite and report paths must stay inside the
repository: parent-directory escapes, absolute paths outside the repo, and
symlink targets outside the repo all exit with code `2`. Use
`data/working/evals/` for private ignored reports.

The same repository-local path contract applies to user-supplied artifact paths
for `draft_post.py`, `build_style_memory_index.py`, `query_style_memory.py`,
and `capture_feedback.py`. The intentional exception is `draft_post.py
--env-file`, which may point outside the repository when explicitly used for
local credential reuse.

Assemble a draft with RAG-style retrieval:

```bash
python3 scripts/draft_post.py examples/draft-request.telegram.json --dry-run --retrieval-strategy style_memory
python3 scripts/draft_post.py examples/draft-request.telegram.json --dry-run --retrieval-strategy llama_index
```

Run an offline Telegram bot smoke check:

```bash
python3 scripts/smoke_telegram_bot.py
```

Run the Telegram bot:

```bash
export TONE_OF_VOICE_TELEGRAM_BOT_TOKEN=...
export ANTHROPIC_API_KEY=...
python3 scripts/run_telegram_bot.py --allowed-chat-id <your-chat-id>
```

If this repository does not have its own `.env`, set `TONE_OF_VOICE_FALLBACK_ENV` or pass `--env-file` explicitly to reuse credentials from another local project.

Draft artifacts are written to `data/working/drafts/` by default and are intentionally ignored by git.
Feedback artifacts are written to `data/working/feedback/` by default and are intentionally ignored by git.
Structured eval reports can be written under `data/working/evals/` and are intentionally ignored by git.
Style-memory index artifacts are written under `data/working/style-memory/` by default and are intentionally ignored by git.
Telegram bot state, review history, and bot draft artifacts are written under `data/working/bot/` by default and are intentionally ignored by git.
