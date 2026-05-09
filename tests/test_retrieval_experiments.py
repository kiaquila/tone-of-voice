from __future__ import annotations

import unittest

from tone_of_voice.config import repo_root
from tone_of_voice.retrieval_experiments import (
    choose_winner,
    evaluate_retrieval_suite,
    format_retrieval_report,
    load_retrieval_suite,
    parse_retrieval_cases,
    retrieval_metrics,
)


class RetrievalExperimentSuiteTest(unittest.TestCase):
    def test_seed_suite_passes_for_default_variants(self) -> None:
        result = evaluate_retrieval_suite(load_retrieval_suite(), root=repo_root())
        report = format_retrieval_report(result)

        self.assertTrue(result["passed"], report)
        self.assertEqual(result["total_cases"], 4)
        self.assertIn(
            result["winner"],
            {"heuristic", "style_memory", "hybrid", "llama_index", None},
        )
        self.assertIn("style-memory-retrieval-seed", report)

    def test_seed_suite_metrics_are_not_all_identical(self) -> None:
        result = evaluate_retrieval_suite(load_retrieval_suite(), root=repo_root())
        aggregate = result["aggregate"]
        metric_tuples = {
            (item["mean_recall_at_k"], item["mean_mrr"])
            for item in aggregate.values()
        }
        # If every variant produces the same (recall@k, mrr), the suite
        # provides no signal and any retrieval regression would silently pass.
        self.assertGreater(len(metric_tuples), 1, format_retrieval_report(result))

    def test_seed_suite_separates_style_memory_from_hybrid(self) -> None:
        result = evaluate_retrieval_suite(load_retrieval_suite(), root=repo_root())
        aggregate = result["aggregate"]

        self.assertNotEqual(
            (
                aggregate["style_memory"]["mean_recall_at_k"],
                aggregate["style_memory"]["mean_precision_at_k"],
            ),
            (
                aggregate["hybrid"]["mean_recall_at_k"],
                aggregate["hybrid"]["mean_precision_at_k"],
            ),
            format_retrieval_report(result),
        )

    def test_choose_winner_returns_none_when_all_tied(self) -> None:
        aggregate = {
            "heuristic": {
                "passed": True,
                "mean_recall_at_k": 1.0,
                "mean_mrr": 1.0,
                "mean_precision_at_k": 0.5,
            },
            "style_memory": {
                "passed": True,
                "mean_recall_at_k": 1.0,
                "mean_mrr": 1.0,
                "mean_precision_at_k": 0.5,
            },
            "hybrid": {
                "passed": True,
                "mean_recall_at_k": 1.0,
                "mean_mrr": 1.0,
                "mean_precision_at_k": 0.5,
            },
        }
        self.assertIsNone(choose_winner(aggregate))

    def test_choose_winner_returns_none_when_top_variants_tie(self) -> None:
        aggregate = {
            "heuristic": {
                "passed": True,
                "mean_recall_at_k": 0.83,
                "mean_mrr": 1.0,
                "mean_precision_at_k": 0.55,
            },
            "style_memory": {
                "passed": True,
                "mean_recall_at_k": 1.0,
                "mean_mrr": 1.0,
                "mean_precision_at_k": 0.66,
            },
            "hybrid": {
                "passed": True,
                "mean_recall_at_k": 1.0,
                "mean_mrr": 1.0,
                "mean_precision_at_k": 0.66,
            },
        }
        self.assertIsNone(choose_winner(aggregate))

    def test_choose_winner_picks_best_variant_when_not_tied(self) -> None:
        aggregate = {
            "heuristic": {
                "passed": True,
                "mean_recall_at_k": 0.83,
                "mean_mrr": 1.0,
                "mean_precision_at_k": 0.55,
            },
            "style_memory": {
                "passed": True,
                "mean_recall_at_k": 1.0,
                "mean_mrr": 1.0,
                "mean_precision_at_k": 0.66,
            },
        }
        self.assertEqual(choose_winner(aggregate), "style_memory")

    def test_parse_requires_expected_records(self) -> None:
        suite = {
            "schema_version": 1,
            "cases": [
                {
                    "id": "missing-expected",
                    "request": {
                        "platform": "telegram",
                        "angle": "x",
                    },
                }
            ],
        }

        with self.assertRaises(ValueError):
            parse_retrieval_cases(suite)

    def test_retrieval_metrics_include_precision_recall_and_mrr(self) -> None:
        metrics = retrieval_metrics(
            ["reference:REF-TG-120", "reference:REF-TG-084"],
            ["reference:REF-TG-102", "reference:REF-TG-120"],
            k=2,
        )

        self.assertEqual(metrics["precision_at_k"], 0.5)
        self.assertEqual(metrics["recall_at_k"], 0.5)
        self.assertEqual(metrics["mrr"], 1.0)
        self.assertEqual(metrics["first_hit_rank"], 1)


if __name__ == "__main__":
    unittest.main()
