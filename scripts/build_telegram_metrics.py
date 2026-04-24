#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tone_of_voice.metrics import (
    compute_corpus_metrics,
    format_metrics_markdown,
    read_jsonl,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute baseline metrics from an exported Telegram JSONL corpus."
    )
    parser.add_argument("input", help="Path to the Telegram JSONL corpus file")
    parser.add_argument(
        "--channel",
        help="Optional channel label. Defaults to the input filename stem.",
    )
    parser.add_argument(
        "--json-output",
        help="Optional path for structured JSON metrics output.",
    )
    parser.add_argument(
        "--markdown-output",
        help="Optional path for markdown metrics output.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    channel = args.channel or input_path.stem
    records = read_jsonl(str(input_path))
    metrics = compute_corpus_metrics(records)

    if args.json_output:
        json_path = Path(args.json_output).expanduser().resolve()
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    markdown = format_metrics_markdown(channel, metrics)
    if args.markdown_output:
        markdown_path = Path(args.markdown_output).expanduser().resolve()
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(markdown, encoding="utf-8")
    else:
        print(markdown)


if __name__ == "__main__":
    main()
