from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from tone_of_voice import drafting as drafting_module
from tone_of_voice import style_memory as style_memory_module
from tone_of_voice.config import repo_root
from tone_of_voice.drafting import (
    DraftRequest,
    anthropic_max_tokens_from_env,
    build_prompt_bundle,
    extract_anthropic_message_text,
    generate_with_anthropic_messages,
    load_reference_library,
    normalize_token,
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

    def test_accepts_retrieval_strategy(self) -> None:
        request = DraftRequest.from_mapping(
            {
                "platform": "telegram",
                "angle": "RAG shipped",
                "retrieval_strategy": "Style Memory",
            }
        )

        self.assertEqual(request.retrieval_strategy, "style_memory")

    def test_rejects_unknown_retrieval_strategy(self) -> None:
        with self.assertRaises(ValueError):
            DraftRequest.from_mapping(
                {
                    "platform": "telegram",
                    "angle": "RAG shipped",
                    "retrieval_strategy": "random",
                }
            )


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

    def test_build_prompt_bundle_reads_anthropic_model_env(self) -> None:
        import os
        from unittest import mock

        request = DraftRequest.from_mapping(
            {"platform": "telegram", "angle": "MVP shipped", "max_references": 3}
        )

        with mock.patch.dict(
            os.environ,
            {
                "ANTHROPIC_MODEL": "claude-haiku-4-5",
                "TONE_OF_VOICE_ANTHROPIC_MODEL": "claude-sonnet-4-6",
            },
        ):
            bundle = build_prompt_bundle(request, root=repo_root())

        self.assertEqual(bundle.model, "claude-sonnet-4-6")

    def test_build_prompt_bundle_can_use_style_memory_strategy(self) -> None:
        request = DraftRequest.from_mapping(
            {
                "platform": "telegram",
                "angle": "Share how much the current multi-agent setup costs",
                "topics": ["agents", "cost", "setup"],
                "post_type": "tool_breakdown",
                "retrieval_strategy": "style_memory",
                "max_references": 5,
            }
        )

        bundle = build_prompt_bundle(request, root=repo_root(), model="test-model")

        self.assertEqual(bundle.retrieval_strategy, "style_memory")
        self.assertGreaterEqual(len(bundle.style_memory_matches), 3)
        self.assertIn("Retrieved Style Memory", bundle.prompt)
        self.assertEqual(bundle.references[0].ref_id, "REF-TG-134")


class ResponseExtractionTest(unittest.TestCase):
    def test_extracts_anthropic_text_content(self) -> None:
        self.assertEqual(
            extract_anthropic_message_text(
                {"content": [{"type": "text", "text": "  draft text  "}]}
            ),
            "draft text",
        )

    def test_extracts_multiple_anthropic_text_blocks(self) -> None:
        response = {
            "content": [
                {"type": "text", "text": "first"},
                {"type": "text", "text": "second"},
            ]
        }

        self.assertEqual(extract_anthropic_message_text(response), "first\nsecond")

    def test_generate_requires_anthropic_api_key(self) -> None:
        import os
        from unittest import mock

        request = DraftRequest.from_mapping(
            {"platform": "telegram", "angle": "MVP shipped", "max_references": 3}
        )
        bundle = build_prompt_bundle(request, root=repo_root(), model="test-model")

        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError) as cm:
                generate_with_anthropic_messages(bundle)
        self.assertIn("ANTHROPIC_API_KEY", str(cm.exception))

    def test_generate_posts_anthropic_messages_payload(self) -> None:
        import os
        from unittest import mock

        request = DraftRequest.from_mapping(
            {"platform": "telegram", "angle": "MVP shipped", "max_references": 3}
        )
        bundle = build_prompt_bundle(request, root=repo_root(), model="test-model")
        captured: dict[str, object] = {}

        class FakeResponse:
            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *_args: object) -> None:
                return None

            def read(self) -> bytes:
                return json.dumps(
                    {"id": "msg_test", "content": [{"type": "text", "text": "draft"}]}
                ).encode("utf-8")

        def fake_urlopen(req: object, timeout: int) -> FakeResponse:
            captured["timeout"] = timeout
            captured["payload"] = json.loads(req.data.decode("utf-8"))  # type: ignore[attr-defined]
            captured["api_key"] = req.get_header("X-api-key")  # type: ignore[attr-defined]
            captured["version"] = req.get_header("Anthropic-version")  # type: ignore[attr-defined]
            return FakeResponse()

        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch("urllib.request.urlopen", fake_urlopen):
                draft, response = generate_with_anthropic_messages(
                    bundle,
                    api_key="sk-test",
                    timeout=7,
                    max_tokens=123,
                )

        self.assertEqual(draft, "draft")
        self.assertEqual(response["id"], "msg_test")
        self.assertEqual(captured["timeout"], 7)
        self.assertEqual(captured["api_key"], "sk-test")
        self.assertEqual(captured["version"], "2023-06-01")
        self.assertEqual(
            captured["payload"],
            {
                "model": "test-model",
                "max_tokens": 123,
                "system": bundle.system_instructions,
                "messages": [{"role": "user", "content": bundle.prompt}],
            },
        )

    def test_anthropic_max_tokens_reads_tone_of_voice_env_first(self) -> None:
        import os
        from unittest import mock

        with mock.patch.dict(
            os.environ,
            {
                "ANTHROPIC_MAX_TOKENS": "100",
                "TONE_OF_VOICE_ANTHROPIC_MAX_TOKENS": "200",
            },
        ):
            self.assertEqual(anthropic_max_tokens_from_env(), 200)


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
            self.assertEqual(data["retrieval_strategy"], "heuristic")
            self.assertEqual(data["style_memory_matches"], [])
            self.assertEqual(artifact["model"], "test-model")

    def test_consecutive_writes_do_not_collide(self) -> None:
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
            first_artifact_path, first_prompt_path, first = write_draft_artifact(
                bundle, output_dir=td, draft="first", backend="test"
            )
            second_artifact_path, second_prompt_path, second = write_draft_artifact(
                bundle, output_dir=td, draft="second", backend="test"
            )

            self.assertNotEqual(first["id"], second["id"])
            self.assertNotEqual(first_artifact_path, second_artifact_path)
            self.assertNotEqual(first_prompt_path, second_prompt_path)
            self.assertTrue(first_artifact_path.exists())
            self.assertTrue(second_artifact_path.exists())
            self.assertTrue(first_prompt_path.exists())
            self.assertTrue(second_prompt_path.exists())
            self.assertEqual(
                json.loads(first_artifact_path.read_text(encoding="utf-8"))["draft"],
                "first",
            )
            self.assertEqual(
                json.loads(second_artifact_path.read_text(encoding="utf-8"))["draft"],
                "second",
            )


class PromptContextPrivacyTest(unittest.TestCase):
    def setUp(self) -> None:
        drafting_module._clear_style_memory_cache()

    def tearDown(self) -> None:
        drafting_module._clear_style_memory_cache()

    def test_prompt_context_excludes_feedback_final(self) -> None:
        sentinel = "SECRET-FEEDBACK-FINAL-LEAK-CHECK"
        with tempfile.TemporaryDirectory() as td:
            workdir = Path(td)
            for rel_path in (
                "docs/00-principles.md",
                "docs/01-current-voice-snapshot.md",
                "docs/04-platform-adaptation.md",
                "docs/10-reference-library.md",
                "docs/12-stop-list.md",
                "docs/13-drafting-recipes.md",
            ):
                source = repo_root() / rel_path
                target = workdir / rel_path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)

            feedback_dir = workdir / "data/working/feedback/raw"
            feedback_dir.mkdir(parents=True, exist_ok=True)
            (feedback_dir / "sample.json").write_text(
                json.dumps(
                    {
                        "id": "sample",
                        "platform": "telegram",
                        "request": {
                            "platform": "telegram",
                            "angle": "leak check angle",
                        },
                        "classification": {},
                        "final_text": sentinel,
                    }
                ),
                encoding="utf-8",
            )

            request = DraftRequest.from_mapping(
                {
                    "platform": "telegram",
                    "angle": "Share how much the current multi-agent setup costs",
                    "topics": ["agents", "cost", "setup"],
                    "post_type": "tool_breakdown",
                    "retrieval_strategy": "style_memory",
                    "max_references": 5,
                }
            )

            bundle = build_prompt_bundle(
                request,
                root=workdir,
                model="test-model",
            )

            self.assertNotIn(sentinel, bundle.prompt)


class StyleMemoryCacheTest(unittest.TestCase):
    def setUp(self) -> None:
        drafting_module._clear_style_memory_cache()

    def tearDown(self) -> None:
        drafting_module._clear_style_memory_cache()

    def test_build_prompt_bundle_caches_style_memory_index(self) -> None:
        request = DraftRequest.from_mapping(
            {
                "platform": "telegram",
                "angle": "Share how much the current multi-agent setup costs",
                "topics": ["agents", "cost", "setup"],
                "post_type": "tool_breakdown",
                "retrieval_strategy": "style_memory",
                "max_references": 5,
            }
        )

        call_counter = {"count": 0}
        original_builder = drafting_module.build_style_memory_index

        def counting_builder(*args, **kwargs):
            call_counter["count"] += 1
            return original_builder(*args, **kwargs)

        try:
            drafting_module.build_style_memory_index = counting_builder
            build_prompt_bundle(request, root=repo_root(), model="test-model")
            first_count = call_counter["count"]
            build_prompt_bundle(request, root=repo_root(), model="test-model")
            second_count = call_counter["count"]
        finally:
            drafting_module.build_style_memory_index = original_builder

        self.assertEqual(first_count, 1)
        self.assertEqual(second_count, 1)

    def test_cache_invalidates_when_reference_library_content_changes(self) -> None:
        request = DraftRequest.from_mapping(
            {
                "platform": "telegram",
                "angle": "Share how much the current multi-agent setup costs",
                "topics": ["agents", "cost", "setup"],
                "post_type": "tool_breakdown",
                "retrieval_strategy": "style_memory",
                "max_references": 5,
            }
        )

        with tempfile.TemporaryDirectory() as td:
            workdir = Path(td)
            for rel_path in (
                "docs/00-principles.md",
                "docs/01-current-voice-snapshot.md",
                "docs/04-platform-adaptation.md",
                "docs/10-reference-library.md",
                "docs/12-stop-list.md",
                "docs/13-drafting-recipes.md",
            ):
                source = repo_root() / rel_path
                target = workdir / rel_path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)

            call_counter = {"count": 0}
            original_builder = drafting_module.build_style_memory_index

            def counting_builder(*args, **kwargs):
                call_counter["count"] += 1
                return original_builder(*args, **kwargs)

            try:
                drafting_module.build_style_memory_index = counting_builder
                build_prompt_bundle(request, root=workdir, model="test-model")
                self.assertEqual(call_counter["count"], 1)

                library_path = workdir / "docs/10-reference-library.md"
                original_mtime = library_path.stat().st_mtime
                original_text = library_path.read_text(encoding="utf-8")
                library_path.write_text(
                    original_text + "\n<!-- updated -->\n", encoding="utf-8"
                )
                os.utime(library_path, (original_mtime, original_mtime))

                build_prompt_bundle(request, root=workdir, model="test-model")
                self.assertEqual(
                    call_counter["count"],
                    2,
                    "cache must rebuild when content changes even without an mtime bump",
                )
            finally:
                drafting_module.build_style_memory_index = original_builder


class UnifiedTokenizerTest(unittest.TestCase):
    def test_unified_normalize_token_consistent_across_modules(self) -> None:
        self.assertIs(drafting_module.normalize_token, style_memory_module.normalize_token)
        self.assertEqual(normalize_token("Tone of Voice"), "tone_of_voice")


if __name__ == "__main__":
    unittest.main()
