# Plan - 007 Reference Library Refresh Loop

## Approach

Use the existing Telegram exporter to create a temporary fresh corpus, select a small set of high-signal examples, and turn them into structured memory files for future drafting.

The implementation is documentation-first because Step 1 is about durable voice memory, not runtime behavior.

## Steps

1. Export recent `<your channel>` posts into `/tmp` using the existing exporter.
2. Select examples that cover different post types: quick reaction, practice lesson, workflow explanation, contrarian tool take, project update, setup breakdown, and teaser.
3. Add `docs/10-reference-library.md` with tags and retrieval shortcuts.
4. Add `docs/11-refresh-log.md` with the refresh decision and next triggers.
5. Add `docs/12-stop-list.md` with hard stops, risky language, and platform-specific risks.
6. Add `docs/13-drafting-recipes.md` with reusable workflows for Telegram, Threads, and LinkedIn.
7. Update `AGENTS.md`, `README.md`, `docs/05-roadmap.md`, and `docs/07-product-execution-plan.md`.
8. Run relevant validation and publish through a PR.

## Risks

- The reference library can become a dump instead of retrieval memory. Mitigation: keep the seed small and tagged.
- Exact examples can invite mechanical mimicry. Mitigation: each entry includes `best_for`, `watch_out`, and "why it matters" notes.
- The snapshot can drift if every refresh rewrites it. Mitigation: the refresh log records an explicit decision not to update the snapshot when new posts only reinforce existing patterns.
