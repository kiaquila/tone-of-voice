#!/usr/bin/env python3
from __future__ import annotations

import argparse

from tone_of_voice.experiments_cli import build_experiment_parser, run_experiment_cli
from tone_of_voice.generated_output_experiments import (
    DEFAULT_GENERATED_OUTPUT_SUITE,
    DEFAULT_VARIANTS,
    evaluate_generated_output_suite,
    format_generated_output_report,
    load_generated_output_suite,
)


def parse_args() -> argparse.Namespace:
    parser = build_experiment_parser(
        description="Run offline generated-output A/B experiments for retrieval variants.",
        default_suite=DEFAULT_GENERATED_OUTPUT_SUITE,
        suite_help="Path to a generated-output experiment suite JSON file.",
        variants=DEFAULT_VARIANTS,
        variant_help="Variant to evaluate. Can be passed more than once.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return run_experiment_cli(
        args,
        load_suite=load_generated_output_suite,
        evaluate_suite=evaluate_generated_output_suite,
        format_report=format_generated_output_report,
        default_variants=DEFAULT_VARIANTS,
    )


if __name__ == "__main__":
    raise SystemExit(main())
