# Spec - 007 Reference Library Refresh Loop

## Goal

Execute Step 1 from `docs/07-product-execution-plan.md`: add the first reference library and refresh loop so future drafting sessions can retrieve curated examples instead of relying only on the static voice snapshot.

## Scope

In scope:

- adding the reference library, refresh log, stop-list, and drafting recipes
- seeding the reference library from the current Telegram corpus
- documenting the tagging scheme for future retrieval
- updating repository memory so future sessions read the new files
- updating roadmap and README so Step 1 is treated as complete and Step 2 becomes next

Out of scope:

- building the local drafting command from Step 2
- adding feedback storage or edit-distance metrics
- changing Telegram exporter behavior
- changing CI, PR Guard, AI Review, or OSV workflows

## Requirements

1. `docs/10-reference-library.md` must contain a compact set of curated examples with platform, post type, mood, depth, topic, best-use, and watch-out metadata.
2. `docs/11-refresh-log.md` must record the Telegram refresh source, date range, decision about whether to update the active snapshot, and next refresh triggers.
3. `docs/12-stop-list.md` must describe language patterns and drafting moves to avoid.
4. `docs/13-drafting-recipes.md` must contain reusable recipes for Telegram, Threads, and LinkedIn drafting.
5. `AGENTS.md`, `README.md`, and `docs/05-roadmap.md` must point future sessions toward the new memory layers.

## Acceptance Criteria

- A future session can answer: "Which examples should I retrieve for a Telegram tool breakdown?"
- A future session can answer: "Should I update the current voice snapshot after this refresh?"
- A future session can draft from a named recipe without inventing the workflow from scratch.
- Step 1 is visibly complete in roadmap/product-plan docs, and Step 2 is the next recommended implementation step.
