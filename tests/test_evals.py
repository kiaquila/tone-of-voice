from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tone_of_voice.config import repo_root
from tone_of_voice.evals import (
    evaluate_suite,
    format_eval_report,
    load_eval_suite,
    parse_eval_cases,
)


class EvalSuiteTest(unittest.TestCase):
    def test_seed_eval_suite_passes(self) -> None:
        result = evaluate_suite(load_eval_suite(), root=repo_root())
        report = format_eval_report(result)

        self.assertTrue(result["passed"])
        self.assertEqual(result["total_cases"], 1)
        self.assertIn("telegram-local-mvp-feedback-seed", report)
        self.assertGreaterEqual(
            len(result["cases"][0]["prompt"]["reference_ids"]),
            3,
        )

    def test_eval_suite_fails_on_metric_regression(self) -> None:
        suite = {
            "schema_version": 1,
            "name": "strict",
            "cases": [
                {
                    "id": "too-different",
                    "platform": "telegram",
                    "draft_text": "short",
                    "final_text": "a much longer final with a different structure",
                    "thresholds": {
                        "max_char_percent_changed": 1,
                        "max_word_percent_changed": 1,
                    },
                }
            ],
        }

        result = evaluate_suite(suite, root=repo_root())

        self.assertFalse(result["passed"])
        self.assertIn("char_percent_changed", result["cases"][0]["failures"][0])

    def test_eval_suite_fails_on_rule_regression(self) -> None:
        suite = {
            "schema_version": 1,
            "name": "rules",
            "cases": [
                {
                    "id": "generic-language",
                    "platform": "telegram",
                    "draft_text": "This will empower creators.",
                    "final_text": "This will empower creators.",
                    "draft_must_not_contain": ["empower"],
                }
            ],
        }

        result = evaluate_suite(suite, root=repo_root())

        self.assertFalse(result["passed"])
        self.assertIn("draft contains banned phrase", result["cases"][0]["failures"][0])

    def test_load_eval_suite_resolves_relative_paths_from_repo_root(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            suite_path = Path(td) / "suite.json"
            suite_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "name": "custom",
                        "cases": [
                            {
                                "id": "case",
                                "platform": "telegram",
                                "draft_text": "draft",
                                "final_text": "draft",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            parsed = parse_eval_cases(load_eval_suite(suite_path))

        self.assertEqual(parsed[0].case_id, "case")


if __name__ == "__main__":
    unittest.main()
