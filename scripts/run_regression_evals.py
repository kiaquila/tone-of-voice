#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tone_of_voice.evals import (
    DEFAULT_EVAL_SUITE,
    evaluate_suite,
    format_eval_report,
    load_eval_suite,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the offline draft/final regression eval slice."
    )
    parser.add_argument(
        "--suite",
        default=DEFAULT_EVAL_SUITE,
        help=f"Eval suite JSON path. Defaults to {DEFAULT_EVAL_SUITE}.",
    )
    parser.add_argument(
        "--json-output",
        help="Optional path for structured JSON eval output.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = evaluate_suite(load_eval_suite(args.suite))

    if args.json_output:
        output_path = Path(args.json_output).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    print(format_eval_report(result))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
