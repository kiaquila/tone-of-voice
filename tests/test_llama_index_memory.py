from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tone_of_voice.config import repo_root
from tone_of_voice.drafting import DraftRequest, build_prompt_bundle, load_reference_library
from tone_of_voice.llama_index_memory import (
    LLAMA_INDEX_MANIFEST,
    LLAMA_INDEX_PERSISTED_FILES,
    build_or_load_llama_index,
    metadata_filters_for_query,
    retrieve_llama_index_style_memory,
)
from tone_of_voice.style_memory import (
    StyleMemoryIndex,
    StyleMemoryQuery,
    StyleMemoryRecord,
    build_style_memory_index,
    style_memory_query_from_request,
)


class LlamaIndexStyleMemoryTest(unittest.TestCase):
    def test_builds_persistent_llama_index(self) -> None:
        root = repo_root()
        library = load_reference_library(root)
        style_index = build_style_memory_index(
            root=root,
            reference_entries=library.entries[:3],
            feedback_dirs=[],
        )

        with tempfile.TemporaryDirectory() as td:
            persist_dir = Path(td) / "llama-index"
            first = build_or_load_llama_index(style_index, persist_dir=persist_dir)
            second = build_or_load_llama_index(style_index, persist_dir=persist_dir)
            manifest = json.loads(
                (persist_dir / LLAMA_INDEX_MANIFEST).read_text(encoding="utf-8")
            )

        self.assertEqual(first.fingerprint, second.fingerprint)
        self.assertEqual(manifest["record_count"], len(style_index.records))

    def test_retrieves_reference_examples_with_metadata_filter(self) -> None:
        root = repo_root()
        library = load_reference_library(root)
        style_index = build_style_memory_index(
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

        with tempfile.TemporaryDirectory() as td:
            matches = retrieve_llama_index_style_memory(
                style_index,
                query,
                limit=5,
                persist_dir=Path(td) / "llama-index",
                root=root,
            )

        self.assertGreaterEqual(len(matches), 3)
        self.assertTrue(
            all(match.record.source_type == "reference_example" for match in matches)
        )
        self.assertIn("reference:REF-TG-134", {match.record.record_id for match in matches})

    def test_prompt_bundle_can_use_llama_index_strategy(self) -> None:
        request = DraftRequest.from_mapping(
            {
                "platform": "telegram",
                "angle": "Share how much the current multi-agent setup costs",
                "topics": ["agents", "cost", "setup"],
                "post_type": "tool_breakdown",
                "retrieval_strategy": "llama_index",
                "max_references": 5,
            }
        )

        bundle = build_prompt_bundle(request, root=repo_root(), model="test-model")

        self.assertEqual(bundle.retrieval_strategy, "llama_index")
        self.assertGreaterEqual(len(bundle.references), 3)
        self.assertGreaterEqual(len(bundle.style_memory_matches), 3)
        self.assertIn("Retrieval strategy: llama_index.", bundle.prompt)

    def test_query_from_request_can_retrieve_llama_index_matches(self) -> None:
        root = repo_root()
        library = load_reference_library(root)
        style_index = build_style_memory_index(
            root=root,
            reference_entries=library.entries,
            feedback_dirs=[],
        )
        request = DraftRequest.from_mapping(
            {
                "platform": "telegram",
                "angle": "Explain why I dropped one AI review tool after testing it",
                "topics": ["ai_review", "tools", "ai_workflow"],
                "post_type": "field_note",
                "mood": ["practical", "amused"],
            }
        )
        query = style_memory_query_from_request(request)

        with tempfile.TemporaryDirectory() as td:
            matches = retrieve_llama_index_style_memory(
                style_index,
                query,
                limit=5,
                persist_dir=Path(td) / "llama-index",
                root=root,
            )

        self.assertTrue(matches)
        self.assertTrue(any("llama_index_vector" in match.reasons for match in matches))

    def test_rebuild_when_records_change(self) -> None:
        root = repo_root()
        library = load_reference_library(root)
        first_index = build_style_memory_index(
            root=root,
            reference_entries=library.entries[:2],
            feedback_dirs=[],
        )
        second_index = build_style_memory_index(
            root=root,
            reference_entries=library.entries[:4],
            feedback_dirs=[],
        )

        with tempfile.TemporaryDirectory() as td:
            persist_dir = Path(td) / "llama-index"
            first = build_or_load_llama_index(first_index, persist_dir=persist_dir)
            second = build_or_load_llama_index(second_index, persist_dir=persist_dir)
            manifest = json.loads(
                (persist_dir / LLAMA_INDEX_MANIFEST).read_text(encoding="utf-8")
            )

        self.assertNotEqual(first.fingerprint, second.fingerprint)
        self.assertEqual(manifest["fingerprint"], second.fingerprint)
        self.assertEqual(manifest["record_count"], len(second_index.records))

    def test_rebuild_when_persisted_storage_is_missing(self) -> None:
        root = repo_root()
        library = load_reference_library(root)
        style_index = build_style_memory_index(
            root=root,
            reference_entries=library.entries[:3],
            feedback_dirs=[],
        )

        with tempfile.TemporaryDirectory() as td:
            persist_dir = Path(td) / "llama-index"
            first = build_or_load_llama_index(style_index, persist_dir=persist_dir)
            for filename in LLAMA_INDEX_PERSISTED_FILES:
                target = persist_dir / filename
                if target.exists():
                    target.unlink()
            second = build_or_load_llama_index(style_index, persist_dir=persist_dir)

            self.assertEqual(first.fingerprint, second.fingerprint)
            for filename in LLAMA_INDEX_PERSISTED_FILES:
                self.assertTrue(
                    (persist_dir / filename).is_file(),
                    f"expected {filename} to be re-created on rebuild",
                )

    def test_metadata_filter_supports_multiple_source_types(self) -> None:
        records = (
            StyleMemoryRecord(
                record_id="REF-X",
                source_type="reference_example",
                title="Reference",
                text="reference example text about agents and cost",
                source="docs/10-reference-library.md#REF-X",
                platform="telegram",
                topics=("agents", "cost"),
            ),
            StyleMemoryRecord(
                record_id="VOICE-X",
                source_type="voice_principle",
                title="Voice",
                text="voice principle about cost honesty and agents",
                source="docs/00-principles.md#VOICE-X",
                topics=("agents", "cost"),
            ),
            StyleMemoryRecord(
                record_id="STOP-X",
                source_type="stop_rule",
                title="Stop",
                text="stop list rule about agents",
                source="docs/12-stop-list.md#STOP-X",
                topics=("agents",),
            ),
        )
        style_index = StyleMemoryIndex(records=records, created_at="1970-01-01T00:00:00Z")
        query = StyleMemoryQuery(
            text="agents cost",
            topics=("agents", "cost"),
            source_types=("reference_example", "voice_principle"),
        )

        filters = metadata_filters_for_query(query)
        self.assertIsNotNone(filters)
        # Multi-value branch must use a single IN-style filter rather than
        # silently falling through to the EQ branch.
        self.assertEqual(len(filters.filters), 1)
        self.assertEqual(filters.filters[0].key, "source_type")
        self.assertEqual(
            sorted(filters.filters[0].value),
            ["reference_example", "voice_principle"],
        )

        with tempfile.TemporaryDirectory() as td:
            matches = retrieve_llama_index_style_memory(
                style_index,
                query,
                limit=5,
                persist_dir=Path(td) / "llama-index",
            )

        self.assertTrue(matches)
        retrieved_types = {match.record.source_type for match in matches}
        self.assertTrue(retrieved_types.issubset({"reference_example", "voice_principle"}))
        self.assertNotIn("stop_rule", retrieved_types)

    def test_tie_break_is_deterministic_by_record_id(self) -> None:
        # Two records with identical content embed to the same vector and earn
        # identical heuristic bonuses; the secondary sort by record_id must
        # produce a stable order so retrieval rankings are reproducible.
        twin_text = "duplicate content about agents and cost"
        records = (
            StyleMemoryRecord(
                record_id="REF-B",
                source_type="reference_example",
                title="Twin",
                text=twin_text,
                source="docs/10-reference-library.md#REF-B",
                platform="telegram",
                topics=("agents", "cost"),
            ),
            StyleMemoryRecord(
                record_id="REF-A",
                source_type="reference_example",
                title="Twin",
                text=twin_text,
                source="docs/10-reference-library.md#REF-A",
                platform="telegram",
                topics=("agents", "cost"),
            ),
        )
        style_index = StyleMemoryIndex(records=records, created_at="1970-01-01T00:00:00Z")
        query = StyleMemoryQuery(
            text="agents cost",
            platform="telegram",
            topics=("agents", "cost"),
            source_types=("reference_example",),
        )

        with tempfile.TemporaryDirectory() as td:
            matches = retrieve_llama_index_style_memory(
                style_index,
                query,
                limit=5,
                persist_dir=Path(td) / "llama-index",
            )

        self.assertEqual([match.record.record_id for match in matches], ["REF-A", "REF-B"])
        self.assertAlmostEqual(matches[0].score, matches[1].score)


if __name__ == "__main__":
    unittest.main()
