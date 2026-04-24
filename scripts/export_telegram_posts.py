#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export Telegram channel posts into a normalized JSONL corpus."
    )
    parser.add_argument("channel", help="Telegram channel username without @")
    parser.add_argument(
        "--env-file",
        help="Optional env file path. Defaults to .env or ../vb-influencer/.env if present.",
    )
    parser.add_argument(
        "--session-dir",
        help="Optional directory containing the Telethon session sqlite file.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Optional maximum number of text posts to export.",
    )
    parser.add_argument(
        "--output",
        help="Optional JSONL output path. Defaults to data/raw/telegram/<channel>.jsonl",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    from tone_of_voice.config import load_project_env, resolve_session_stem
    from tone_of_voice.telegram_export import export_channel_posts, write_jsonl

    env_path = load_project_env(args.env_file)
    session_stem = resolve_session_stem(session_dir=args.session_dir)

    output = args.output or f"data/raw/telegram/{args.channel}.jsonl"
    records = await export_channel_posts(
        session_stem=session_stem,
        channel=args.channel,
        limit=args.limit,
    )
    written = write_jsonl(records, output)

    print(f"Exported {len(records)} posts from @{args.channel}")
    print(f"Output: {written}")
    print(f"Env source: {env_path or 'not found'}")
    print(f"Session stem: {session_stem}")


if __name__ == "__main__":
    asyncio.run(main())
