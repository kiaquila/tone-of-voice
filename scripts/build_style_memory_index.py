#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from collections import Counter

from tone_of_voice.config import repo_root
from tone_of_voice.drafting import load_reference_library
from tone_of_voice.experiments_common import resolve_repo_path
from tone_of_voice.llama_index_memory import (
    DEFAULT_LLAMA_INDEX_DIR,
    build_or_load_llama_index,
)
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
    parser.add_argument(
        "--llama-index",
        action="store_true",
        help="Also build the persistent LlamaIndex vector index.",
    )
    parser.add_argument(
        "--llama-index-dir",
        default=DEFAULT_LLAMA_INDEX_DIR,
        help="Persistent LlamaIndex storage directory.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()
    try:
        output_path = resolve_repo_path(args.output, root=root, label="style-memory output")
        feedback_dirs = (
            [
                resolve_repo_path(path, root=root, label="feedback dir")
                for path in args.feedback_dirs
            ]
            if args.feedback_dirs
            else DEFAULT_FEEDBACK_DIRS
        )
        llama_index_dir = resolve_repo_path(
            args.llama_index_dir,
            root=root,
            label="llama index dir",
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    library = load_reference_library(root)
    index = build_style_memory_index(
        root=root,
        reference_entries=library.entries,
        feedback_dirs=feedback_dirs,
    )
    output_path = save_style_memory_index(index, output_path)

    source_counts = Counter(record.source_type for record in index.records)
    print(f"Style-memory index: {output_path}")
    print(f"Records: {len(index.records)}")
    print(
        "Source types: "
        + ", ".join(f"{name}={count}" for name, count in sorted(source_counts.items()))
    )
    if args.llama_index:
        llama_index = build_or_load_llama_index(
            index,
            persist_dir=llama_index_dir,
            root=root,
            rebuild=True,
        )
        print(f"LlamaIndex storage: {llama_index.persist_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
