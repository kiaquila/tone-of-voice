from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tone_of_voice.config import repo_root
from tone_of_voice.drafting import (
    DraftRequest,
    build_prompt_bundle,
    extract_response_text,
    load_reference_library,
    select_references,
    write_draft_artifact,
)


class DraftRequestTest(unittest.TestCase):
    def test_from_mapping_normalizes_fields(self) -> None:
        request = DraftRequest.from_mapping(
            {
                "platform": "Telegram",
                "angle": "Explain the local drafting MVP",
                "constraints": "keep it compact",
                "topics": "agents, tone-of-voice",
                "post_type": "Project Update",
                "mood": ["Playful", "Product Minded"],
                "max_references": 3,
            }
        )

        self.assertEqual(request.platform, "telegram")
        self.assertEqual(request.constraints, ("keep it compact",))
        self.assertEqual(request.topics, ("agents", "tone_of_voice"))
        self.assertEqual(request.post_type, "project_update")
        self.assertEqual(request.mood, ("playful", "product_minded"))

    def test_requires_known_platform(self) -> None:
        with self.assertRaises(ValueError):
            DraftRequest.from_mapping({"platform": "newsletter", "angle": "x"})


class ReferenceLibraryTest(unittest.TestCase):
    def test_loads_reference_entries_and_shortcuts(self) -> None:
        library = load_reference_library(repo_root())
        ref_ids = {entry.ref_id for entry in library.entries}

        self.assertIn("REF-TG-102", ref_ids)
        self.assertIn("quick_telegram_reaction", library.shortcuts)

        ref_102 = next(entry for entry in library.entries if entry.ref_id == "REF-TG-102")
        self.assertIn("claude", ref_102.topics)
        self.assertIn("Claude Managed Agents", ref_102.representative_text)

    def test_select_references_prefers_matching_recipe_and_topics(self) -> None:
        library = load_reference_library(repo_root())
        request = DraftRequest.from_mapping(
            {
                "platform": "telegram",
                "angle": "Share how much the current multi-agent setup costs",
                "topics": ["agents", "cost", "setup"],
                "post_type": "tool_breakdown",
                "recipe": "tool_or_setup_breakdown",
                "max_references": 5,
            }
        )

        selected = select_references(request, library)
        selected_ids = [entry.ref_id for entry in selected]

        self.assertGreaterEqual(len(selected), 3)
        self.assertLessEqual(len(selected), 5)
        self.assertIn("REF-TG-134", selected_ids)
        self.assertIn("REF-TG-088", selected_ids)


class PromptBundleTest(unittest.TestCase):
    def test_build_prompt_bundle_includes_required_context(self) -> None:
        request = DraftRequest.from_mapping(
            {
                "platform": "linkedin",
                "angle": "Turn the local drafting MVP into a broader professional update",
                "source_notes": "The CLI now saves prompt artifacts and selected references.",
                "topics": ["tone_of_voice", "product"],
                "post_type": "project_update",
                "recipe": "linkedin_grounded_version",
            }
        )

        bundle = build_prompt_bundle(request, root=repo_root(), model="test-model")

        self.assertEqual(bundle.model, "test-model")
        self.assertIn("docs/01-current-voice-snapshot.md", bundle.prompt)
        self.assertIn("docs/12-stop-list.md", bundle.prompt)
        self.assertIn("Selected Reference Examples", bundle.prompt)
        self.assertIn(request.angle, bundle.prompt)
        self.assertGreaterEqual(len(bundle.references), 3)


class ResponseExtractionTest(unittest.TestCase):
    def test_extracts_direct_output_text(self) -> None:
        self.assertEqual(
            extract_response_text({"output_text": "  draft text  "}),
            "draft text",
        )

    def test_extracts_nested_output_text(self) -> None:
        response = {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": "first"},
                        {"type": "output_text", "text": "second"},
                    ],
                }
            ]
        }

        self.assertEqual(extract_response_text(response), "first\nsecond")


class ArtifactWritingTest(unittest.TestCase):
    def test_writes_prompt_and_json_artifact(self) -> None:
        request = DraftRequest.from_mapping(
            {
                "platform": "telegram",
                "angle": "MVP shipped",
                "topics": ["product"],
                "post_type": "project_update",
                "max_references": 3,
            }
        )
        bundle = build_prompt_bundle(request, root=repo_root(), model="test-model")

        with tempfile.TemporaryDirectory() as td:
            artifact_path, prompt_path, artifact = write_draft_artifact(
                bundle,
                output_dir=td,
                draft="draft body",
                backend="test",
                response_data={"id": "resp_test"},
            )

            self.assertTrue(artifact_path.exists())
            self.assertTrue(prompt_path.exists())
            data = json.loads(Path(artifact_path).read_text(encoding="utf-8"))
            self.assertEqual(data["draft"], "draft body")
            self.assertEqual(data["response_id"], "resp_test")
            self.assertEqual(artifact["model"], "test-model")


if __name__ == "__main__":
    unittest.main()
