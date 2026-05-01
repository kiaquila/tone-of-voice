# Feature Spec - Telegram Final Feedback And Stats

## User Need

After the Telegram bot produces a draft, the author often edits the post by hand before publishing. The bot needs a low-friction way to capture that final version, compare it with the generated draft, and show whether the feedback memory is improving future drafts.

## Scope

- Add `/final <text or Telegram link>` to capture the final edited version for the active draft or latest approved draft in the same chat.
- Support `/final` without a body by treating the next plain message as the final version.
- Support readable standalone Telegram post links, including topic/thread links, through the live Telethon bot, storing the source URL and publish time when available.
- Treat pasted final text that merely contains a Telegram URL as final text, not as a link-fetch request.
- Add duplicate protection so the same draft artifact is not captured twice.
- Add `/stat` to show same-chat feedback count, latest fit score, rolling trend, median edit percentages, common correction tags, and the learning signal.
- Use captured final versions as compact same-chat feedback memory in later `/draft` prompts.

## Non-Goals

- No auto-publishing.
- No model fine-tuning.
- No automatic rewrite of durable voice docs from every captured final.
- No guarantee that private Telegram links are readable unless the bot account can see the post.

## Success Criteria

- A user can complete `/draft -> /revise -> /approve -> /final -> /stat` from Telegram.
- A user can paste a final Telegram post link instead of the final text when the bot can read it.
- `/stat` makes same-chat progress visible as a rolling score trend rather than a single fragile number.
- Future drafts include a bounded memory block from recent final versions captured in the same chat.
- Unit tests cover text capture, link capture, pending final capture, stats, duplicate guard, and feedback-memory injection.
