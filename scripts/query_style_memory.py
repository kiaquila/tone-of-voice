#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tone_of_voice.config import repo_root
from tone_of_voice.drafting import DraftRequest, load_reference_library
from tone_of_voice.style_memory import (
    DEFAULT_FEEDBACK_DIRS,
    DEFAULT_STYLE_INDEX_PATH,
    StyleMemoryQuery,
    build_style_memory_index,
    load_style_memory_index,
    retrieve_style_memory,
    style_memory_query_from_request,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query the local style-memory index for RAG-style drafting context."
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="Free-text query. Omit when --request is provided.",
    )
    parser.add_argument(
        "--request",
        help="Draft request JSON file. Use '-' to read JSON from stdin.",
    )
    parser.add_argument(
        "--index",
        default=DEFAULT_STYLE_INDEX_PATH,
        help="Path to an existing style-memory index.",
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="Build an in-memory index from the current repository instead of reading --index.",
    )
    parser.add_argument("--platform", help="Optional platform filter/boost.")
    parser.add_argument("--post-type", help="Optional post type filter/boost.")
    parser.add_argument(
        "--topic",
        action="append",
        dest="topics",
        help="Topic boost. Can be passed more than once.",
    )
    parser.add_argument(
        "--mood",
        action="append",
        dest="mood",
        help="Mood boost. Can be passed more than once.",
    )
    parser.add_argument(
        "--source-type",
        action="append",
        dest="source_types",
        help="Restrict to a source type such as reference_example or feedback_final.",
    )
    parser.add_argument("--limit", type=int, default=8, help="Maximum matches to print.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of a markdown-style report.",
    )
    return parser.parse_args()


def load_request(path: str) -> DraftRequest:
    if path == "-":
        return DraftRequest.from_mapping(json.load(sys.stdin))
    with open(path, encoding="utf-8") as fh:
        return DraftRequest.from_mapping(json.load(fh))


def build_query(args: argparse.Namespace) -> StyleMemoryQuery:
    if args.request:
        request = load_request(args.request)
        query = style_memory_query_from_request(request)
        return StyleMemoryQuery(
            text=query.text,
            platform=args.platform or query.platform,
            post_type=args.post_type or query.post_type,
            topics=tuple(args.topics or query.topics),
            mood=tuple(args.mood or query.mood),
            source_types=tuple(args.source_types or query.source_types),
        )
    if not args.query:
        raise SystemExit("Provide a query or --request.")
    return StyleMemoryQuery.from_mapping(
        {
            "text": args.query,
            "platform": args.platform,
            "post_type": args.post_type,
            "topics": args.topics or [],
            "mood": args.mood or [],
            "source_types": args.source_types or [],
        }
    )


def load_or_build_index(args: argparse.Namespace):
    index_path = Path(args.index).expanduser()
    if not index_path.is_absolute():
        index_path = repo_root() / index_path
    if args.build or not index_path.exists():
        root = repo_root()
        library = load_reference_library(root)
        return build_style_memory_index(
            root=root,
            reference_entries=library.entries,
            feedback_dirs=DEFAULT_FEEDBACK_DIRS,
        )
    return load_style_memory_index(index_path)


def main() -> int:
    args = parse_args()
    query = build_query(args)
    index = load_or_build_index(args)
    matches = retrieve_style_memory(index, query, limit=args.limit)

    if args.json:
        print(
            json.dumps(
                {
                    "query": {
                        "text": query.text,
                        "platform": query.platform,
                        "post_type": query.post_type,
                        "topics": list(query.topics),
                        "mood": list(query.mood),
                        "source_types": list(query.source_types),
                    },
                    "matches": [match.to_dict() for match in matches],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    print("# Style Memory Query")
    print("")
    print(f"- Matches: {len(matches)}")
    print("")
    for match in matches:
        print(
            f"- `{match.record.record_id}` score={round(match.score, 2)} "
            f"source_type={match.record.source_type} polarity={match.record.polarity}"
        )
        if match.reasons:
            print(f"  reasons: {', '.join(match.reasons)}")
        print(f"  title: {match.record.title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
