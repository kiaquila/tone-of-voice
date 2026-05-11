from __future__ import annotations

import unittest

from tone_of_voice.config import repo_root
from tone_of_voice.generated_output_experiments import (
    choose_generated_output_winner,
    evaluate_generated_output_suite,
    format_generated_output_report,
    load_generated_output_suite,
    parse_generated_output_cases,
)


class GeneratedOutputExperimentSuiteTest(unittest.TestCase):
    def test_seed_suite_passes_and_selects_hybrid(self) -> None:
        result = evaluate_generated_output_suite(
            load_generated_output_suite(),
            root=repo_root(),
        )
        report = format_generated_output_report(result)

        self.assertTrue(result["passed"], report)
        self.assertEqual(result["total_cases"], 1)
        self.assertEqual(result["winner"], "hybrid")
        self.assertIn("generated-output-ab-seed", report)

        case = result["cases"][0]
        self.assertEqual(case["selected_variant"], "hybrid")
        self.assertEqual(case["best_by_edit_distance"], "hybrid")
        self.assertIn("llama_index", case["variants"])
        self.assertGreaterEqual(
            len(case["variants"]["hybrid"]["prompt"]["reference_ids"]),
            3,
        )
        tone_correction_counts = dict(result["common_tone_corrections"])
        self.assertGreaterEqual(tone_correction_counts.get("less_generic", 0), 2)

    def test_evaluates_subset_of_variants(self) -> None:
        suite = {
            "schema_version": 1,
            "name": "subset",
            "cases": [
                {
                    "id": "case",
                    "request": {
                        "platform": "telegram",
                        "angle": "MVP shipped",
                        "max_references": 3,
                    },
                    "final_text": "same text",
                    "selected_variant": "heuristic",
                    "variants": [
                        {
                            "strategy": "heuristic",
                            "draft_text": "same text",
                            "preference": "selected",
                        },
                        {
                            "strategy": "style_memory",
                            "draft_text": "different text",
                            "preference": "rejected",
                        },
                    ],
                }
            ],
        }

        result = evaluate_generated_output_suite(
            suite,
            root=repo_root(),
            variants=("heuristic", "style_memory"),
        )

        self.assertTrue(result["passed"], format_generated_output_report(result))
        self.assertEqual(result["winner"], "heuristic")
        self.assertEqual(set(result["aggregate"]), {"heuristic", "style_memory"})
        self.assertEqual(result["aggregate"]["heuristic"]["selected_count"], 1)
        self.assertEqual(result["aggregate"]["heuristic"]["best_by_edit_count"], 1)

    def test_suite_fails_on_metric_threshold(self) -> None:
        suite = {
            "schema_version": 1,
            "name": "strict",
            "cases": [
                {
                    "id": "too-different",
                    "request": {
                        "platform": "telegram",
                        "angle": "MVP shipped",
                        "max_references": 3,
                    },
                    "final_text": "a much longer final text",
                    "thresholds": {"max_word_percent_changed": 1},
                    "variants": [
                        {"strategy": "heuristic", "draft_text": "short"},
                        {"strategy": "style_memory", "draft_text": "short"},
                    ],
                }
            ],
        }

        result = evaluate_generated_output_suite(
            suite,
            root=repo_root(),
            variants=("heuristic", "style_memory"),
        )

        self.assertFalse(result["passed"])
        self.assertIn(
            "word_percent_changed",
            result["cases"][0]["variants"]["heuristic"]["failures"][0],
        )

    def test_parse_rejects_missing_selected_variant(self) -> None:
        suite = {
            "schema_version": 1,
            "cases": [
                {
                    "id": "bad-selected",
                    "request": {"platform": "telegram", "angle": "x"},
                    "final_text": "final",
                    "selected_variant": "hybrid",
                    "variants": [
                        {"strategy": "heuristic", "draft_text": "draft"},
                        {"strategy": "style_memory", "draft_text": "draft"},
                    ],
                }
            ],
        }

        with self.assertRaises(ValueError):
            parse_generated_output_cases(suite)

    def test_parse_requires_at_least_two_variants(self) -> None:
        suite = {
            "schema_version": 1,
            "cases": [
                {
                    "id": "one-variant",
                    "request": {"platform": "telegram", "angle": "x"},
                    "final_text": "final",
                    "variants": [
                        {"strategy": "heuristic", "draft_text": "draft"},
                    ],
                }
            ],
        }

        with self.assertRaises(ValueError):
            parse_generated_output_cases(suite)

    def test_choose_winner_returns_none_on_tie(self) -> None:
        aggregate = {
            "heuristic": {
                "passed": True,
                "selected_count": 1,
                "best_by_edit_count": 1,
                "median_word_percent_changed": 10.0,
                "median_char_percent_changed": 10.0,
            },
            "hybrid": {
                "passed": True,
                "selected_count": 1,
                "best_by_edit_count": 1,
                "median_word_percent_changed": 10.0,
                "median_char_percent_changed": 10.0,
            },
        }

        self.assertIsNone(choose_generated_output_winner(aggregate))


if __name__ == "__main__":
    unittest.main()
