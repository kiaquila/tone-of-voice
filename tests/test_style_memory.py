from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tone_of_voice.config import repo_root
from tone_of_voice.drafting import DraftRequest, load_reference_library
from tone_of_voice.style_memory import (
    StyleMemoryQuery,
    build_style_memory_index,
    load_style_memory_index,
    retrieve_style_memory,
    save_style_memory_index,
    style_memory_query_from_request,
)


class StyleMemoryIndexTest(unittest.TestCase):
    def test_builds_index_from_reference_library_and_voice_docs(self) -> None:
        root = repo_root()
        library = load_reference_library(root)

        index = build_style_memory_index(
            root=root,
            reference_entries=library.entries,
            feedback_dirs=[],
        )

        record_ids = {record.record_id for record in index.records}
        source_types = {record.source_type for record in index.records}

        self.assertIn("reference:REF-TG-102", record_ids)
        self.assertIn("reference_example", source_types)
        self.assertIn("stop_rule", source_types)
        self.assertIn("voice_snapshot", source_types)

    def test_saves_and_loads_index(self) -> None:
        root = repo_root()
        library = load_reference_library(root)
        index = build_style_memory_index(
            root=root,
            reference_entries=library.entries[:1],
            feedback_dirs=[],
        )

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "index.json"
            save_style_memory_index(index, path)
            loaded = load_style_memory_index(path)

        self.assertEqual(len(loaded.records), len(index.records))
        self.assertEqual(loaded.records[0].record_id, index.records[0].record_id)

    def test_includes_feedback_final_and_correction_records(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            feedback_root = Path(td) / "feedback"
            raw_dir = feedback_root / "raw"
            raw_dir.mkdir(parents=True)
            (raw_dir / "sample.json").write_text(
                json.dumps(
                    {
                        "id": "sample",
                        "created_at": "2026-05-08T10:00:00Z",
                        "platform": "telegram",
                        "request": {
                            "angle": "Share the human-in-the-loop bot experiment"
                        },
                        "source": {"draft_artifact_path": "drafts/sample.json"},
                        "classification": {
                            "post_type": "project_update",
                            "topics": ["bot", "feedback"],
                            "mood": ["practical"],
                            "tone_corrections": ["less_generic"],
                            "structural_notes": ["stronger opening"],
                        },
                        "final_text": "Проверила бот на себе: human-in-the-loop тут не лозунг, а спасательный круг для тона.",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            index = build_style_memory_index(
                root=repo_root(),
                reference_entries=[],
                feedback_dirs=[feedback_root],
            )

        record_ids = {record.record_id for record in index.records}
        self.assertIn("feedback:sample:final", record_ids)
        self.assertIn("feedback:sample:corrections", record_ids)

    def test_empty_feedback_dirs_disables_feedback_ingestion(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw_dir = root / "data" / "working" / "feedback" / "raw"
            raw_dir.mkdir(parents=True)
            (raw_dir / "sample.json").write_text(
                json.dumps(
                    {
                        "id": "local-only",
                        "platform": "telegram",
                        "request": {"angle": "Ignored local feedback"},
                        "final_text": "This should not enter deterministic eval indexes.",
                    }
                ),
                encoding="utf-8",
            )

            index_without_feedback = build_style_memory_index(
                root=root,
                reference_entries=[],
                feedback_dirs=[],
            )
            index_with_default_feedback = build_style_memory_index(
                root=root,
                reference_entries=[],
                feedback_dirs=None,
            )

        self.assertEqual(index_without_feedback.records, ())
        self.assertIn(
            "feedback:local-only:final",
            {record.record_id for record in index_with_default_feedback.records},
        )


class StyleMemoryRetrievalTest(unittest.TestCase):
    def test_retrieves_matching_reference_examples(self) -> None:
        root = repo_root()
        library = load_reference_library(root)
        index = build_style_memory_index(
            root=root,
            reference_entries=library.entries,
            feedback_dirs=[],
        )
        query = StyleMemoryQuery(
            text="multi-agent setup costs",
            platform="telegram",
            post_type="tool_breakdown",
            topics=("agents", "cost", "setup"),
            source_types=("reference_example",),
        )

        matches = retrieve_style_memory(index, query, limit=5)
        match_ids = [match.record.record_id for match in matches]

        self.assertGreaterEqual(len(matches), 3)
        self.assertEqual(match_ids[0], "reference:REF-TG-134")
        self.assertIn("reference:REF-TG-088", match_ids)

    def test_builds_query_from_draft_request(self) -> None:
        request = DraftRequest.from_mapping(
            {
                "platform": "telegram",
                "angle": "Share the first RAG experiment for the bot",
                "source_notes": "Compare heuristic and style-memory retrieval.",
                "topics": ["rag", "bot"],
                "post_type": "project_update",
                "mood": ["practical"],
            }
        )

        query = style_memory_query_from_request(request)

        self.assertEqual(query.platform, "telegram")
        self.assertEqual(query.post_type, "project_update")
        self.assertIn("style-memory retrieval", query.text)
        self.assertEqual(query.topics, ("rag", "bot"))


if __name__ == "__main__":
    unittest.main()
