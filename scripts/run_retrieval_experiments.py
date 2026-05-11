#!/usr/bin/env python3
from __future__ import annotations

import argparse

from tone_of_voice.experiments_cli import build_experiment_parser, run_experiment_cli
from tone_of_voice.retrieval_experiments import (
    DEFAULT_RETRIEVAL_SUITE,
    DEFAULT_VARIANTS,
    evaluate_retrieval_suite,
    format_retrieval_report,
    load_retrieval_suite,
)


def parse_args() -> argparse.Namespace:
    parser = build_experiment_parser(
        description="Run offline retrieval experiments for style-memory variants.",
        default_suite=DEFAULT_RETRIEVAL_SUITE,
        suite_help="Path to a retrieval experiment suite JSON file.",
        variants=DEFAULT_VARIANTS,
        variant_help="Variant to evaluate. Can be passed more than once.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return run_experiment_cli(
        args,
        load_suite=load_retrieval_suite,
        evaluate_suite=evaluate_retrieval_suite,
        format_report=format_retrieval_report,
        default_variants=DEFAULT_VARIANTS,
    )


if __name__ == "__main__":
    raise SystemExit(main())
