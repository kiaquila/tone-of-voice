#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio

from tone_of_voice.bot import (
    DEFAULT_BOT_OUTPUT_DIR,
    DEFAULT_BOT_SESSION_NAME,
    allowed_chat_ids_from_env,
    bot_token_from_env,
    run_telegram_bot,
)
from tone_of_voice.config import load_project_env


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Telegram bot drafting assistant."
    )
    parser.add_argument(
        "--env-file",
        help="Optional env file path. Defaults to .env or ../vb-influencer/.env if present.",
    )
    parser.add_argument(
        "--session-dir",
        help="Optional directory for the Telethon bot session sqlite file.",
    )
    parser.add_argument(
        "--session-name",
        default=DEFAULT_BOT_SESSION_NAME,
        help=f"Telethon session name. Defaults to {DEFAULT_BOT_SESSION_NAME}.",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_BOT_OUTPUT_DIR,
        help=f"Bot state and draft artifact directory. Defaults to {DEFAULT_BOT_OUTPUT_DIR}.",
    )
    parser.add_argument(
        "--allowed-chat-id",
        type=int,
        action="append",
        default=[],
        help="Restrict bot usage to this chat id. Can be supplied more than once.",
    )
    parser.add_argument(
        "--allow-public",
        action="store_true",
        help=(
            "Explicitly opt out of the allowlist. Required when no --allowed-chat-id "
            "and no TONE_OF_VOICE_BOT_ALLOWED_CHAT_IDS are supplied."
        ),
    )
    parser.add_argument(
        "--model",
        help=(
            "Model override. Defaults to request.model, "
            "TONE_OF_VOICE_ANTHROPIC_MODEL, ANTHROPIC_MODEL, or the drafting default."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Assemble prompt artifacts without calling the model backend.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Anthropic API timeout in seconds.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    load_project_env(args.env_file)
    await run_telegram_bot(
        bot_token=bot_token_from_env(),
        output_dir=args.output_dir,
        session_name=args.session_name,
        session_dir=args.session_dir,
        dry_run=args.dry_run,
        model=args.model,
        allowed_chat_ids=allowed_chat_ids_from_env(args.allowed_chat_id),
        allow_public=args.allow_public,
        timeout=args.timeout,
    )


if __name__ == "__main__":
    asyncio.run(main())
