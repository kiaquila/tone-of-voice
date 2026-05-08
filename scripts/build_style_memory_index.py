#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter

from tone_of_voice.config import repo_root
from tone_of_voice.drafting import load_reference_library
from tone_of_voice.style_memory import (
    DEFAULT_FEEDBACK_DIRS,
    DEFAULT_STYLE_INDEX_PATH,
    build_style_memory_index,
    save_style_memory_index,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the local style-memory index used for RAG-style retrieval."
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_STYLE_INDEX_PATH,
        help="Path for the JSON index artifact.",
    )
    parser.add_argument(
        "--feedback-dir",
        action="append",
        dest="feedback_dirs",
        help=(
            "Feedback root or raw directory to include. Can be passed more than once. "
            "Defaults to data/working/feedback and data/working/bot/feedback."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()
    library = load_reference_library(root)
    index = build_style_memory_index(
        root=root,
        reference_entries=library.entries,
        feedback_dirs=args.feedback_dirs or DEFAULT_FEEDBACK_DIRS,
    )
    output_path = save_style_memory_index(index, args.output)

    source_counts = Counter(record.source_type for record in index.records)
    print(f"Style-memory index: {output_path}")
    print(f"Records: {len(index.records)}")
    print(
        "Source types: "
        + ", ".join(f"{name}={count}" for name, count in sorted(source_counts.items()))
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
