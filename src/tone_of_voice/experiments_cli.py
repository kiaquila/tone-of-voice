from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from typing import Any

from tone_of_voice.experiments_common import resolve_repo_path, write_json_output


def build_experiment_parser(
    *,
    description: str,
    default_suite: str,
    suite_help: str | None = None,
    variants: Sequence[str] | None = None,
    variant_help: str | None = None,
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--suite",
        default=default_suite,
        help=suite_help or f"Experiment suite JSON path. Defaults to {default_suite}.",
    )
    if variants is not None:
        parser.add_argument(
            "--variant",
            action="append",
            dest="variants",
            choices=tuple(variants),
            help=variant_help or "Variant to evaluate. Can be passed more than once.",
        )
    parser.add_argument(
        "--json-output",
        help="Optional repository-local path for the structured experiment result.",
    )
    return parser


def run_experiment_cli(
    args: argparse.Namespace,
    *,
    load_suite: Callable[[str], dict[str, Any]],
    evaluate_suite: Callable[..., dict[str, Any]],
    format_report: Callable[[dict[str, Any]], str],
    default_variants: Sequence[str] | None = None,
) -> int:
    try:
        output_path = (
            resolve_repo_path(args.json_output, label="json output")
            if args.json_output
            else None
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    try:
        suite = load_suite(args.suite)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if default_variants is None:
        result = evaluate_suite(suite)
    else:
        result = evaluate_suite(
            suite,
            variants=tuple(args.variants or default_variants),
        )

    print(format_report(result))
    if output_path:
        written = write_json_output(output_path, result)
        print(f"JSON output: {written}")

    return 0 if result["passed"] else 1
