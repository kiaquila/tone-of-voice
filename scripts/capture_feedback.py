#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from tone_of_voice.config import repo_root
from tone_of_voice.experiments_common import resolve_repo_path
from tone_of_voice.feedback import (
    DEFAULT_FEEDBACK_DIR,
    load_feedback_input,
    read_feedback_input_from_stdin,
    write_feedback_pair,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture a manual draft/final feedback pair and compute edit metrics."
    )
    parser.add_argument(
        "input",
        help="Path to a feedback JSON file. Use '-' to read JSON from stdin.",
    )
    parser.add_argument(
        "--draft-artifact",
        help="Optional draft artifact JSON to use as the source draft/request context.",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_FEEDBACK_DIR,
        help="Feedback storage root. Defaults to data/working/feedback.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()
    try:
        draft_artifact = (
            resolve_repo_path(args.draft_artifact, root=root, label="draft artifact")
            if args.draft_artifact
            else None
        )
        output_dir = resolve_repo_path(args.output_dir, root=root, label="feedback output")
        input_path = (
            None
            if args.input == "-"
            else resolve_repo_path(args.input, root=root, label="feedback input")
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        feedback = (
            read_feedback_input_from_stdin(
                source_draft_artifact=draft_artifact,
                root=root,
            )
            if args.input == "-"
            else load_feedback_input(
                input_path,
                source_draft_artifact=draft_artifact,
                root=root,
            )
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    raw_path, analysis_path, record, analysis = write_feedback_pair(
        feedback,
        output_dir=output_dir,
    )
    draft_metrics = analysis["comparisons"]["draft_to_final"]

    print(f"Feedback: {record['id']}")
    print(f"Raw: {raw_path}")
    print(f"Analysis: {analysis_path}")
    print(f"Character change: {draft_metrics['char_percent_changed']}%")
    print(f"Word change: {draft_metrics['word_percent_changed']}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
