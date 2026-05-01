# Implementation Plan - Telegram Final Feedback And Stats

## Approach

Build on the existing bot session store and feedback engine instead of adding a parallel storage format.

1. Extend bot state with access to bot-local feedback storage and latest approved history lookup.
2. Add final capture commands to `TelegramDraftAssistant`.
3. Reuse `FeedbackInput` and `write_feedback_pair` to write raw/analysis feedback records.
4. Add a Telegram-link resolver in the live Telethon runner.
5. Add score helpers for latest score, rolling trend, and learning signal.
6. Feed recent final-version snippets into future draft requests as bounded prompt memory.
7. Update docs, roadmap, feature memory, and tests.

## Fit Score

The first score is intentionally simple and explainable:

- compute draft-to-final character and word percent changed
- weight word changes more heavily than character changes
- map the weighted edit percentage to `0..100`

This score measures draft closeness to the author's final edit. It is not a universal content quality metric and can dip on harder topics.

## Safety

- `/final` never publishes.
- Duplicate capture is blocked by source draft artifact path.
- Feedback memory and stats are bounded to a small number of recent final samples and filtered to the current chat.
- Telegram link capture only runs for standalone links and fails closed by asking the user to paste text manually.
