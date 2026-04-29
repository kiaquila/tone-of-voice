#!/usr/bin/env python3
from __future__ import annotations

import argparse

from tone_of_voice.bot import (
    BotStateStore,
    TelegramDraftAssistant,
    make_draft_generator,
)
from tone_of_voice.config import load_project_env


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an offline smoke check for the Telegram bot draft loop."
    )
    parser.add_argument(
        "--env-file",
        help="Optional env file path. Defaults to .env or ../vb-influencer/.env if present.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/working/bot-smoke",
        help="Output directory for smoke state and prompt artifacts.",
    )
    parser.add_argument(
        "--idea",
        default="short note about testing the Telegram bot handoff",
        help="Idea to send through the offline /draft handler.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_project_env(args.env_file)

    store = BotStateStore(args.output_dir)
    assistant = TelegramDraftAssistant(
        store=store,
        generator=make_draft_generator(
            draft_output_dir=f"{args.output_dir}/drafts",
            dry_run=True,
        ),
        allowed_chat_ids={1},
    )
    replies = assistant.handle_text(1, f"/draft {args.idea}")
    for reply in replies:
        print(reply)
    print("Offline Telegram bot smoke check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
