from __future__ import annotations

import unittest

from tone_of_voice.config import repo_root
from tone_of_voice.retrieval_experiments import (
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
        self.assertEqual(result["total_cases"], 3)
        self.assertIn(result["winner"], {"heuristic", "style_memory", "hybrid"})
        self.assertIn("style-memory-retrieval-seed", report)

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
