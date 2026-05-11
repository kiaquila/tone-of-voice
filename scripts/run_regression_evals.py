#!/usr/bin/env python3
from __future__ import annotations

import argparse

from tone_of_voice.evals import (
    DEFAULT_EVAL_SUITE,
    evaluate_suite,
    format_eval_report,
    load_eval_suite,
)
from tone_of_voice.experiments_cli import build_experiment_parser, run_experiment_cli


def parse_args() -> argparse.Namespace:
    parser = build_experiment_parser(
        description="Run the offline draft/final regression eval slice.",
        default_suite=DEFAULT_EVAL_SUITE,
        suite_help=f"Eval suite JSON path. Defaults to {DEFAULT_EVAL_SUITE}.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return run_experiment_cli(
        args,
        load_suite=load_eval_suite,
        evaluate_suite=evaluate_suite,
        format_report=format_eval_report,
    )


if __name__ == "__main__":
    raise SystemExit(main())
