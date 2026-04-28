# Memory System

## Goal

Support future post creation from durable memory, not from a single static prompt.

## Recommended Layers

### 1. Voice Core

Stable identity-level rules that should change rarely:

- tone traits
- recurring strengths
- stylistic guardrails
- stop-list for off-brand language

### 2. Platform Playbooks

Per-platform bending rules:

- Telegram
- Threads
- LinkedIn

The core voice stays the same, but packaging, density, and explicitness shift by platform.

### 3. Reference Library

A curated set of best-fit examples tagged by:

- platform
- post type
- mood
- depth
- topic
- performance notes if available

The goal is not to store everything. The goal is to store the best examples for retrieval.

### 4. Refresh Notes

Periodic updates describing what changed in the public voice:

- new recurring phrases
- higher or lower density
- more or less irony
- shifts in subject matter
- shifts in platform behavior

### 5. Drafting Recipes

Reusable drafting workflows such as:

- quick Telegram reaction post
- Threads take with narrative arc
- LinkedIn version with slightly more grounding and less insider shorthand

## Implemented File Design

The first growth layer is now implemented as:

- `docs/10-reference-library.md`
- `docs/11-refresh-log.md`
- `docs/12-stop-list.md`
- `docs/13-drafting-recipes.md`

## Retrieval Workflow

When drafting a new post:

1. Load the voice core.
2. Load the target platform playbook.
3. Retrieve 3 to 5 relevant reference examples by topic and format.
4. Draft to the requested angle.
5. Check against guardrails before finalizing.

## Update Cadence

- Light refresh: every 10 to 20 new posts
- Full profile refresh: every noticeable shift in style or platform strategy
- Platform playbook refresh: whenever one platform starts behaving materially differently
