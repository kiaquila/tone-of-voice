#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tone_of_voice.generated_output_experiments import (
    DEFAULT_GENERATED_OUTPUT_SUITE,
    DEFAULT_VARIANTS,
    evaluate_generated_output_suite,
    format_generated_output_report,
    load_generated_output_suite,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run offline generated-output A/B experiments for retrieval variants."
    )
    parser.add_argument(
        "--suite",
        default=DEFAULT_GENERATED_OUTPUT_SUITE,
        help="Path to a generated-output experiment suite JSON file.",
    )
    parser.add_argument(
        "--variant",
        action="append",
        dest="variants",
        choices=DEFAULT_VARIANTS,
        help="Variant to evaluate. Can be passed more than once.",
    )
    parser.add_argument(
        "--json-output",
        help="Optional path for the structured experiment result.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    suite = load_generated_output_suite(args.suite)
    result = evaluate_generated_output_suite(
        suite,
        variants=tuple(args.variants or DEFAULT_VARIANTS),
    )
    report = format_generated_output_report(result)
    print(report)

    if args.json_output:
        output_path = Path(args.json_output).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"JSON output: {output_path}")

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
