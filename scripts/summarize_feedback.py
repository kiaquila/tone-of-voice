#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tone_of_voice.feedback import (
    DEFAULT_FEEDBACK_DIR,
    format_feedback_summary_markdown,
    load_feedback_analyses,
    summarize_feedback,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize draft/final feedback metrics and recurring correction tags."
    )
    parser.add_argument(
        "--feedback-dir",
        default=DEFAULT_FEEDBACK_DIR,
        help="Feedback storage root. Defaults to data/working/feedback.",
    )
    parser.add_argument(
        "--json-output",
        help="Optional path for structured JSON summary output.",
    )
    parser.add_argument(
        "--markdown-output",
        help="Optional path for markdown summary output.",
    )
    parser.add_argument(
        "--recent-limit",
        type=int,
        default=10,
        help="Number of recent records to include in the summary.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = summarize_feedback(
        load_feedback_analyses(args.feedback_dir),
        recent_limit=args.recent_limit,
    )

    if args.json_output:
        json_path = Path(args.json_output).expanduser().resolve()
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    markdown = format_feedback_summary_markdown(summary)
    if args.markdown_output:
        markdown_path = Path(args.markdown_output).expanduser().resolve()
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(markdown, encoding="utf-8")
    else:
        print(markdown)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
