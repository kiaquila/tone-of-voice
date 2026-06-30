# Roadmap

## Product Goal

Build a self-improving writing system that learns the author's style from published content and from draft-to-final edits, so a future interaction can be:

1. send an idea
2. choose a platform
3. receive a near-finished post in the author's style
4. make fewer edits over time

## Success Metric

Primary metric:

- median edit distance between generated draft and final published version

Supporting metrics:

- percentage of generated text changed before publish
- number of structural rewrites per draft
- number of tone corrections per draft
- metric trends by platform and post type

## Current Progress Snapshot

Already completed:

- durable voice-memory foundation docs
- initial Telegram export and metrics scripts
- baseline CI workflow
- PR guard workflow
- OSV scan workflow
- Codex AI-review gate on pull requests
- classic branch protection on `main`
- reference library, refresh log, stop-list, and drafting recipes
- local drafting MVP with structured JSON requests, reference retrieval, prompt artifacts, and Anthropic Messages API generation
- feedback capture and edit metrics with raw/analysis storage and summary scripts
- offline regression eval gate for drafting, feedback, eval, and core voice-memory changes
- Telegram bot product implementation with draft, revise, approve, status, cancel, dry-run smoke checks, and operator docs
- RAG-style memory index, query command, retrieval strategies, and offline retrieval experiment gate
- opt-in LlamaIndex-backed retrieval strategy with persistent local index storage
- offline generated-output A/B experiment harness for comparing draft variants,
  selected variants, final edits, and correction tags
- shared, path-hardened experiment CLI helpers for the regression, retrieval,
  and generated-output harnesses
- adapted Unicorn Hub process layer with repository-local config, spec/SENAR
  templates, Claude implementation guidance, local preflight/orchestration, and
  event-driven Codex review reruns
- repository-local path hardening for the remaining draft, style-memory query,
  style-memory build, and feedback capture CLIs

Next recommended steps:

- continue the Step 6 follow-up sequence in `docs/17-rag-style-memory.md`:
  add a Ragas or lightweight judge eval layer on top of the generated-output
  A/B harness
- start Step 7 cross-platform expansion only after the retrieval and generated
  output eval loops are stable enough to protect voice quality across platforms

## Product Principles

- Human approval remains in the loop.
- The system learns from edits, not only from source corpora.
- Platform adaptation is explicit.
- New automation is introduced only when it improves quality or convenience.
- Evaluation must prevent regressions in voice quality.

## Phased Plan

### Phase 0 — Memory Foundation

Status: complete

Goals:

- establish durable voice docs
- define memory layers
- capture current Telegram-based tone snapshot

### Phase 1 — Telegram Foundation

Goals:

- export Telegram posts into a normalized corpus
- compute baseline metrics from Telegram history
- make voice refresh repeatable

Deliverables:

- Telegram export script
- corpus format
- baseline metrics script
- first implementation spec

Status:

- export script implemented
- baseline metrics script implemented
- feature memory documented
- post-review hardening: pyproject install layout, broader test coverage, emoji-signal regex fix, workflow consistency

### Phase 2 — Reference Library And Refresh Loop

Status: complete

Goals:

- store curated examples by post type and mood
- introduce refresh notes driven by newly published posts
- version the active voice profile instead of rewriting it ad hoc

Deliverables:

- reference-library docs
- refresh log
- stop-list and drafting recipes

Status notes:

- `docs/10-reference-library.md` seeded from a 52-post Telegram export
- `docs/11-refresh-log.md` records the first refresh decision
- `docs/12-stop-list.md` documents anti-patterns and safer replacements
- `docs/13-drafting-recipes.md` defines first reusable drafting workflows

### Phase 3 — Feedback And Eval Loop

Status: complete

Goals:

- capture draft vs final post pairs
- compute edit-based quality metrics
- detect recurring mistakes and update memory layers safely

Deliverables:

- feedback schema - complete
- edit diff storage - complete
- offline eval set - complete
- regression gate for prompt or rule changes - complete

Status notes:

- `scripts/capture_feedback.py` stores manual draft/final pairs under `data/working/feedback/raw/`.
- `scripts/summarize_feedback.py` aggregates edit-distance metrics and correction tags from `data/working/feedback/analysis/`.
- `docs/14-feedback-capture.md` documents the storage schema that evals can draw from.
- `docs/15-regression-evals.md` documents the first offline eval gate.

### Phase 4 — Telegram Bot Assistant

Status: complete

Goals:

- let the author create drafts from a phone
- preserve a tight human-in-the-loop workflow
- deploy the bot on the same AWS host family used by `<sibling Telegram project>`

Deliverables:

- Telegram bot handlers
- draft, revise, approve, final-capture, and stat flows
- publish-ready text handoff without auto-publishing
- feedback-memory learning signal from captured final versions
- deployment and smoke checks

Status notes:

- `scripts/run_telegram_bot.py` runs the Telethon bot process.
- `scripts/smoke_telegram_bot.py` exercises the draft loop offline in dry-run mode.
- `docs/16-telegram-bot-product.md` documents env vars, storage, smoke checks, and recovery.
- Production is enabled on the target AWS host as the `tone-of-voice-telegram-bot.service` systemd service.
- The runner defaults to a stale-update guard so restarts do not answer old queued Telegram commands.
- Production deploy now follows a GitHub OIDC + S3 + AWS SSM release pattern and manages the bot through systemd.
- `/final` captures pasted final text or a Telegram post link into bot-local feedback storage.
- `/final --replace` overwrites a captured final for the same draft when a manual correction arrives late.
- `/revise` can wait for the next plain message as its revision instruction.
- `/stat` reports fit-score trend and whether recent final versions are being used as feedback memory in future drafts.

### Phase 5 — RAG Style Memory And Experiments

Status: complete

Goals:

- turn the current reference selection into an inspectable retrieval pipeline
- build a local style-memory index from examples, rules, and feedback pairs
- compare heuristic, RAG-style, hybrid, and LlamaIndex retrieval variants
  before changing generation behavior
- make A/B-style prompt and retrieval experiments part of the normal workflow

Deliverables:

- style-memory index and query commands - complete
- retrieval experiment suite and report command - complete
- draft artifacts that record retrieval strategy - complete
- docs for the retrieval architecture and experiment workflow - complete
- opt-in LlamaIndex-backed retrieval path with persistent storage - complete

### Phase 6 — Cross-Platform Expansion

Status: planned

Goals:

- include Threads and LinkedIn in both memory and drafting
- keep one voice core with platform-specific packaging

Deliverables:

- platform-specific ingestion inputs
- platform playbooks with stronger retrieval
- per-platform eval slices

## Near-Term Execution Order

Canonical step-by-step plan:

- `docs/07-product-execution-plan.md`

Execution order:

1. Step 1 - Reference Library And Refresh Loop - complete
2. Step 2 - Local Drafting MVP - complete
3. Step 3 - Feedback Capture And Edit Metrics - complete
4. Step 4 - Regression Eval Gate - complete
5. Step 5 - Telegram Bot Product - complete
6. Step 6 - RAG Style Memory And Experiment Harness - complete
7. Step 6 follow-ups - generated-output A/B tests - first offline harness complete
8. Step 6 follow-ups - experiment harness hardening - complete
9. Step 6 follow-ups - Unicorn process and CLI hardening - complete
10. Step 6 follow-ups - judge evals before cross-platform expansion
11. Step 7 - Cross-Platform Expansion - planned after retrieval and generated-output eval loops are stable

## Spec Pattern

This repository should use a lightweight spec pattern for software changes:

- `specs/<feature-id>/spec.md`
- `specs/<feature-id>/plan.md`
- `specs/<feature-id>/tasks.md`

Use specs for:

- scripts
- bots
- deployment changes
- evaluation pipelines

Do not require specs for:

- simple documentation refreshes
- routine voice-snapshot updates
- adding curated examples
