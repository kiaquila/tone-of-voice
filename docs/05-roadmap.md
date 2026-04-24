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

Next recommended steps:

- reference library and refresh log
- draft-versus-final feedback schema
- edit-distance and revision-quality metrics
- Telegram bot interface

## Product Principles

- Human approval remains in the loop.
- The system learns from edits, not only from source corpora.
- Platform adaptation is explicit.
- New automation is introduced only when it improves quality or convenience.
- Evaluation must prevent regressions in voice quality.

## Phased Plan

### Phase 0 — Memory Foundation

Status: in progress

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

### Phase 2 — Reference Library And Refresh Loop

Goals:

- store curated examples by post type and mood
- introduce refresh notes driven by newly published posts
- version the active voice profile instead of rewriting it ad hoc

Deliverables:

- reference-library docs
- refresh log
- stop-list and drafting recipes

### Phase 3 — Feedback And Eval Loop

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

Goals:

- include Threads and LinkedIn in both memory and drafting
- keep one voice core with platform-specific packaging

Deliverables:

- platform-specific ingestion inputs
- platform playbooks with stronger retrieval
- per-platform eval slices

## Near-Term Execution Order

1. Finish Telegram ingestion foundation.
2. Add reference-library structure and refresh log.
3. Add draft-versus-final feedback storage and edit metrics.
4. Ship the Telegram bot interface.
5. Expand to Threads and LinkedIn ingestion workflows.

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
