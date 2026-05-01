# Spec — 001 Telegram Foundation

## Goal

Create the first repeatable ingestion layer for the tone-of-voice system by reusing the existing Telegram access pattern already proven in `<sibling Telegram project>`.

## Why This Slice First

- Telegram is the most mature and accessible source right now.
- The current voice snapshot already depends on Telegram evidence.
- This is the lowest-risk path toward an automated refresh loop.

## Scope

In scope:

- export Telegram channel posts into a normalized local corpus
- compute baseline text metrics from the exported corpus
- document how this foundation supports future refresh and learning loops

Out of scope:

- Threads ingestion
- LinkedIn ingestion
- Telegram bot user interface
- automatic prompt optimization
- final feedback-learning loop

## Requirements

1. The export path must support reuse of existing Telethon credentials and session state.
2. The exported data must be normalized into a structured machine-readable format.
3. The metrics path must work on exported data without needing Telegram access.
4. The implementation must keep secrets out of git.
5. The documentation must explain how this slice fits into the broader self-improving system.

## Acceptance Criteria

- A user can export Telegram posts from a configured channel into a local corpus file.
- A user can generate baseline metrics from the exported corpus file.
- The repository contains durable docs for the roadmap and this feature slice.
- The code is structured so later refresh and bot workflows can reuse it.
