from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path

from telethon import TelegramClient

MAX_TEXT_LENGTH = 8000


@dataclass
class TelegramPostRecord:
    platform: str
    source: str
    channel: str
    post_id: int
    url: str
    published_at: str
    raw_text: str
    text_length: int
    line_count: int


def ensure_telegram_credentials() -> tuple[int, str]:
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")

    if not api_id or not api_hash:
        raise RuntimeError(
            "Missing TELEGRAM_API_ID or TELEGRAM_API_HASH. "
            "Provide an env file or export the variables before running."
        )

    try:
        return int(api_id), api_hash
    except ValueError as exc:
        raise RuntimeError(
            f"TELEGRAM_API_ID must be an integer, got: {api_id!r}"
        ) from exc


async def export_channel_posts(
    *,
    session_stem: str,
    channel: str,
    limit: int | None = None,
) -> list[TelegramPostRecord]:
    api_id, api_hash = ensure_telegram_credentials()

    async with TelegramClient(session_stem, api_id, api_hash) as client:
        entity = await client.get_entity(channel)
        posts: list[TelegramPostRecord] = []

        async for message in client.iter_messages(entity, reverse=True):
            if limit is not None and len(posts) >= limit:
                break

            text = (message.text or getattr(message, "message", None) or "").strip()
            if not text:
                continue

            if len(text) > MAX_TEXT_LENGTH:
                text = text[:MAX_TEXT_LENGTH] + "[...]"

            posts.append(
                TelegramPostRecord(
                    platform="telegram",
                    source=f"tg:{channel}",
                    channel=channel,
                    post_id=message.id,
                    url=f"https://t.me/{channel}/{message.id}",
                    published_at=message.date.isoformat(),
                    raw_text=text,
                    text_length=len(text),
                    line_count=text.count("\n") + 1,
                )
            )

    return posts


def write_jsonl(records: list[TelegramPostRecord], output_path: str) -> Path:
    path = Path(output_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

    return path
