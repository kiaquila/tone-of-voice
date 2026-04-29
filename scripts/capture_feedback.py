#!/usr/bin/env python3
from __future__ import annotations

import argparse

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
    feedback = (
        read_feedback_input_from_stdin(source_draft_artifact=args.draft_artifact)
        if args.input == "-"
        else load_feedback_input(args.input, source_draft_artifact=args.draft_artifact)
    )
    raw_path, analysis_path, record, analysis = write_feedback_pair(
        feedback,
        output_dir=args.output_dir,
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
