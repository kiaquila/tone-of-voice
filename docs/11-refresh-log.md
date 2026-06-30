# Refresh Log

## Purpose

This file records meaningful source refreshes and explains whether they changed the active voice memory.

Use it to avoid casually rewriting `docs/01-current-voice-snapshot.md`. New material should update the snapshot only when it shows a visible shift in public writing, not just because more posts exist.

## Refresh Workflow

1. Export recent source material.
2. Build or inspect metrics.
3. Identify candidate examples for `docs/10-reference-library.md`.
4. Add a dated refresh note here.
5. Update `docs/01-current-voice-snapshot.md` only when the new material changes stable voice understanding.
6. Update `docs/12-stop-list.md` or `docs/13-drafting-recipes.md` when the new material reveals a repeatable drafting rule.

## Snapshot Update Threshold

Update the active voice snapshot when at least one of these is true:

- 10 to 20 new posts reinforce a pattern not currently captured
- platform behavior changes materially
- recurring phrases, structures, or topics shift
- draft/final feedback shows repeated tone corrections
- the current snapshot causes generated drafts to miss the voice in a consistent way

Do not update the snapshot for a single one-off joke, a temporary news burst, or a topic that does not change the writing behavior.

## 2026-06-30 - Draft-vs-Published Editing Pass

Source:

- Platform: Telegram-oriented drafting workflow
- Source material: recent draft-vs-published comparison from the author's editing pass
- Source location: private/working draft feedback material, not committed as raw text
- Review focus: how the final published voice changed hooks, self-deprecation, attribution, reader questions, emoji placement, CTAs, and anti-polish guardrails

Changes made:

- Updated `docs/01-current-voice-snapshot.md` with new stable Strong Signals.
- Updated `docs/01-current-voice-snapshot.md` with new Guardrails for formatting, directive framing, abstract padding, and emoji handling.

Observed voice signals:

- Final edits reinforced hook variety as a voice requirement, not a surface preference.
- Self-deprecation and small admissions worked as trust moves when tied to lived work.
- The final voice preferred clipped asides, light attribution, noun-phrase reader prompts, and concrete gamified CTAs.
- Emoji stayed sparse but meaningful; removing them almost entirely made the draft read flatter and less human.

Snapshot decision:

- Update `docs/01-current-voice-snapshot.md`.
- Reason: the draft/final comparison showed repeated tone corrections that affect future drafting behavior, meeting the snapshot threshold for feedback-driven stable voice rules.

## 2026-04-28 - Telegram Reference Seed

Source:

- Platform: Telegram
- Channel: `<your channel>`
- Exported posts: 52
- Source date range: 2026-03-22 to 2026-04-27
- Export command: `python3 scripts/export_telegram_posts.py "<your channel>" --limit 80 --output /tmp/tov-channel-step1.jsonl`
- Env source: `<fallback env file>`
- Session source: `<telegram session>`

Changes made:

- Added `docs/10-reference-library.md` with 10 tagged Telegram examples.
- Added `docs/12-stop-list.md` with anti-patterns and replacement moves.
- Added `docs/13-drafting-recipes.md` with platform-aware drafting workflows.
- Updated roadmap and README to point to the new memory layers.

Observed voice signals:

- The voice still depends strongly on first-person practice: "погоняла", "прикрутила", "сейчас пилю", "пришла к схеме".
- Tool opinions are strongest when paired with cost, workflow, or failure evidence.
- Recent posts show more product-building transparency: stack cost, LinkedIn profile experiment, and the tone-of-voice bot premise.
- The author keeps a clear anti-slop line: automation is useful only if it preserves taste, scoring, and human judgment.
- Telegram continues to tolerate sharp jokes, emoji, and compact insider shorthand.

Snapshot decision:

- Do not rewrite `docs/01-current-voice-snapshot.md` yet.
- Reason: the new material reinforces the existing snapshot rather than changing the stable voice profile.
- Revisit after 10 to 20 additional posts or after the first draft/final feedback pairs exist.

Reference candidates selected:

- REF-TG-034: community field note
- REF-TG-084: compact practice lesson
- REF-TG-088: multi-agent workflow authority
- REF-TG-098: beginner advice with edge
- REF-TG-102: contrarian tool take
- REF-TG-106: first project share
- REF-TG-120: tool decision update
- REF-TG-129: product meta in the author's voice
- REF-TG-134: setup cost breakdown
- REF-TG-137: teaser from research

Next refresh should look for:

- whether the LinkedIn experiment changes cross-platform packaging
- whether the tone-of-voice bot posts create a stronger product narrative
- whether "Applied AI Engineer" career/topic posts become a durable content lane
