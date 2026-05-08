# Spec: RAG Style Memory And Experiments

## Problem

The Telegram bot can draft and capture feedback, but its reference selection is
still a small heuristic over the markdown reference library. That makes it hard
to demonstrate RAG, A/B experimentation, or retrieval-quality reasoning for the
AI Engineer gap-skills sprint.

## Goal

Add a local, deterministic style-memory retrieval layer and an offline
experiment harness that compares retrieval variants before changing model
generation behavior.

## Non-Goals

- no model calls inside the retrieval experiment gate
- no external vector database dependency in the first pass
- no auto-publishing or removal of the existing human approval loop
- no cross-platform ingestion expansion in this step

## Requirements

- Build an inspectable style-memory index from curated references, voice docs,
  stop-list rules, drafting recipes, and local feedback records when present.
- Query the index directly and from a draft request.
- Support `heuristic`, `style_memory`, and `hybrid` retrieval strategies.
- Record retrieval strategy and style-memory matches in draft artifacts.
- Compare retrieval variants with precision/recall-style metrics and MRR.
- Run the retrieval experiment suite in CI.
- Keep roadmap, delivery workflow, README, and product docs in sync.

## Acceptance Criteria

- `python3 scripts/build_style_memory_index.py` writes an index artifact.
- `python3 scripts/query_style_memory.py --request examples/draft-request.telegram.json --build` returns ranked matches.
- `python3 scripts/run_retrieval_experiments.py` passes locally and in CI.
- `python3 scripts/draft_post.py examples/draft-request.telegram.json --dry-run --retrieval-strategy style_memory` writes a prompt artifact with retrieved style memory.
- `python3 scripts/run_telegram_bot.py --help` documents `--retrieval-strategy`.
