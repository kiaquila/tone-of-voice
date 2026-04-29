from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tone_of_voice.feedback import (
    FeedbackInput,
    build_feedback_analysis,
    build_feedback_record,
    compute_revision_metrics,
    format_feedback_summary_markdown,
    levenshtein_distance,
    load_feedback_analyses,
    summarize_feedback,
    write_feedback_pair,
)


class RevisionMetricsTest(unittest.TestCase):
    def test_levenshtein_distance_handles_strings_and_tokens(self) -> None:
        self.assertEqual(levenshtein_distance("draft", "graft"), 1)
        self.assertEqual(
            levenshtein_distance(["one", "solid", "draft"], ["one", "final", "draft"]),
            1,
        )

    def test_compute_revision_metrics_returns_edit_percentages(self) -> None:
        metrics = compute_revision_metrics("hello world", "hello brave world!")

        self.assertGreater(metrics["char_edit_distance"], 0)
        self.assertEqual(metrics["before_words"], 2)
        self.assertEqual(metrics["after_words"], 3)
        self.assertEqual(metrics["exclamation_delta"], 1)
        self.assertGreater(metrics["word_percent_changed"], 0)


class FeedbackCaptureTest(unittest.TestCase):
    def test_feedback_input_can_use_draft_artifact_context(self) -> None:
        feedback = FeedbackInput.from_mapping(
            {
                "final_text": "final text",
                "tone_corrections": ["Less Generic", "stronger-hook"],
            },
            draft_artifact={
                "draft": "draft text",
                "request": {
                    "platform": "Telegram",
                    "angle": "Ship the MVP",
                    "post_type": "Project Update",
                    "topics": ["tone_of_voice"],
                },
            },
            source_draft_artifact="draft.json",
        )

        self.assertEqual(feedback.platform, "telegram")
        self.assertEqual(feedback.draft_text, "draft text")
        self.assertEqual(feedback.post_type, "project_update")
        self.assertEqual(feedback.topics, ("tone_of_voice",))
        self.assertEqual(feedback.tone_corrections, ("less_generic", "stronger_hook"))

    def test_write_feedback_pair_separates_raw_record_and_analysis(self) -> None:
        feedback = FeedbackInput.from_mapping(
            {
                "platform": "telegram",
                "draft_text": "draft",
                "edited_text": "edited draft",
                "final_text": "final draft 😄",
                "post_type": "project_update",
                "tone_corrections": ["add_human_wink"],
            }
        )
        created_at = datetime(2026, 4, 29, 12, 0, tzinfo=timezone.utc)

        with tempfile.TemporaryDirectory() as td:
            raw_path, analysis_path, record, analysis = write_feedback_pair(
                feedback,
                output_dir=td,
                created_at=created_at,
                record_id="feedback-test",
            )

            self.assertTrue(raw_path.exists())
            self.assertTrue(analysis_path.exists())
            self.assertEqual(record["id"], "feedback-test")
            self.assertIn("draft_to_final", analysis["comparisons"])
            self.assertIn("draft_to_edited", analysis["comparisons"])
            self.assertEqual(
                json.loads(raw_path.read_text(encoding="utf-8"))["final_text"],
                "final draft 😄",
            )
            self.assertEqual(
                json.loads(analysis_path.read_text(encoding="utf-8"))["feedback_id"],
                "feedback-test",
            )


class FeedbackSummaryTest(unittest.TestCase):
    def test_summarize_feedback_aggregates_metrics_and_corrections(self) -> None:
        records = []
        for record_id, correction in [
            ("feedback-1", "stronger_hook"),
            ("feedback-2", "stronger_hook"),
            ("feedback-3", "less_generic"),
        ]:
            record = build_feedback_record(
                FeedbackInput.from_mapping(
                    {
                        "platform": "telegram",
                        "draft_text": "draft text",
                        "final_text": "final text with more life",
                        "post_type": "project_update",
                        "tone_corrections": [correction],
                    }
                ),
                created_at=datetime(2026, 4, 29, 12, 0, tzinfo=timezone.utc),
                record_id=record_id,
            )
            records.append(build_feedback_analysis(record))

        summary = summarize_feedback(records)
        markdown = format_feedback_summary_markdown(summary)

        self.assertEqual(summary["total_pairs"], 3)
        self.assertEqual(summary["tone_corrections"][0], ("stronger_hook", 2))
        self.assertIn("Average character percent changed", markdown)

    def test_load_feedback_analyses_returns_empty_when_storage_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            missing = Path(td) / "feedback"
            self.assertEqual(load_feedback_analyses(missing), [])


if __name__ == "__main__":
    unittest.main()
