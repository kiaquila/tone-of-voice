from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tone_of_voice.config import repo_root
from tone_of_voice.drafting import DraftRequest, build_prompt_bundle, load_reference_library
from tone_of_voice.llama_index_memory import (
    LLAMA_INDEX_MANIFEST,
    build_or_load_llama_index,
    retrieve_llama_index_style_memory,
)
from tone_of_voice.style_memory import (
    StyleMemoryQuery,
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


if __name__ == "__main__":
    unittest.main()
