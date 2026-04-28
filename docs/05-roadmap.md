# Roadmap

## Product Goal

Build a self-improving writing system that learns Kristina's style from published content and from draft-to-final edits, so a future interaction can be:

1. send an idea
2. choose a platform
3. receive a near-finished post in Kristina's style
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

Next recommended steps:

- execute `docs/07-product-execution-plan.md` from Step 2 onward
- ship a local drafting MVP before the Telegram bot
- add feedback capture, evals, and only then the phone workflow

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

Status: planned

Goals:

- capture draft vs final post pairs
- compute edit-based quality metrics
- detect recurring mistakes and update memory layers safely

Deliverables:

- feedback schema
- edit diff storage
- offline eval set
- regression gate for prompt or rule changes

### Phase 4 — Telegram Bot Assistant

Status: planned

Goals:

- let Kristina create drafts from a phone
- preserve a tight human-in-the-loop workflow
- deploy the bot on the same AWS host family used by `vb-influencer`

Deliverables:

- Telegram bot handlers
- draft, revise, approve flows
- publish-ready text handoff
- deployment and smoke checks

### Phase 5 — Cross-Platform Expansion

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
2. Step 2 - Local Drafting MVP - next
3. Step 3 - Feedback Capture And Edit Metrics
4. Step 4 - Regression Eval Gate
5. Step 5 - Telegram Bot Product
6. Step 6 - Cross-Platform Expansion

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
