# Source Ingestion

## What We Can Reuse Right Now

The existing `vb-influencer` project already proves that Telegram collection via Telethon works in the current local environment.

What is already available in practice:

- Telegram API credentials
- working Telethon session
- ability to resolve public channels
- ability to iterate channel history and extract text posts

That means Telegram can become the first automated source for this repository with relatively little new work.

## What A Telegram Exporter Would Need

Minimal implementation:

- a small script that fetches posts from a configured channel
- normalization into a simple structured format such as JSON or Markdown
- optional filters for text-only posts, date range, and max post count
- metadata fields for platform, date, url, and source channel

Useful next step:

- an analysis script that turns raw posts into a refreshed voice snapshot and candidate reference examples

## Limits Of The Current Integration

The current Telethon access only solves the Telegram part.

It does not automatically solve:

- Threads ingestion
- LinkedIn ingestion
- cross-platform deduplication
- engagement-aware benchmarking

## Recommended Ingestion Strategy

### Phase 1

Automate Telegram only.

Why:

- lowest implementation risk
- already working credentials and session
- enough to keep the voice profile current for at least one active platform

### Phase 2

Add semi-manual ingestion for Threads and LinkedIn.

Possible paths:

- manual copy/export of selected posts into a structured file
- browser-assisted capture
- API-based collection where reliable and available

### Phase 3

Normalize all platforms into one shared content model:

- `platform`
- `published_at`
- `url`
- `raw_text`
- `notes`
- `tags`

## Recommendation

Yes, the current Telethon integration is useful for this project.

It is useful as:

- the first automated feed
- the basis for repeatable Telegram refreshes
- a template for the shape of a broader ingestion pipeline

It is not sufficient alone if the goal is a full cross-platform voice memory system.
