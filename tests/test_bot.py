from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from tone_of_voice.bot import (
    BotStateStore,
    DraftResult,
    TelegramDraftAssistant,
    allowed_chat_ids_from_env,
    compact_stamp,
    run_telegram_bot,
    split_command,
    split_for_telegram,
)
from tone_of_voice.drafting import DraftRequest


def fake_generator(request: DraftRequest) -> DraftResult:
    return DraftResult(
        draft=f"draft for {request.angle}",
        artifact_path="/tmp/artifact.json",
        prompt_path="/tmp/prompt.md",
        backend="fake",
    )


def dry_run_generator(request: DraftRequest) -> DraftResult:
    return DraftResult(
        draft=None,
        artifact_path="/tmp/dry.json",
        prompt_path="/tmp/dry.prompt.md",
        backend="prompt_only",
    )


def boom_generator(_request: DraftRequest) -> DraftResult:
    raise RuntimeError("upstream boom")


class BotCommandTest(unittest.TestCase):
    def test_split_command_handles_bot_mentions(self) -> None:
        self.assertEqual(split_command("/draft@my_bot hello"), ("/draft", "hello", True))
        self.assertEqual(split_command("plain idea"), (None, "plain idea", True))

    def test_split_command_addressed_to_other_bot_is_not_addressed(self) -> None:
        self.assertEqual(
            split_command("/draft@otherbot foo", bot_username="my_bot"),
            ("/draft", "foo", False),
        )

    def test_split_command_addressed_to_us_is_addressed(self) -> None:
        self.assertEqual(
            split_command("/DRAFT@My_Bot foo", bot_username="my_bot"),
            ("/draft", "foo", True),
        )

    def test_splits_long_messages(self) -> None:
        chunks = split_for_telegram("x" * 8200, limit=3900)
        self.assertEqual(len(chunks), 3)
        self.assertTrue(all(len(chunk) <= 3900 for chunk in chunks))


class CompactStampTest(unittest.TestCase):
    def test_compact_stamp_includes_microseconds(self) -> None:
        stamp = compact_stamp()
        self.assertRegex(stamp, r"^\d{8}T\d{6}\d{6}Z$")


class BotStateStoreTest(unittest.TestCase):
    def test_saves_loads_and_clears_session(self) -> None:
        from tone_of_voice.bot import BotSession

        with tempfile.TemporaryDirectory() as td:
            store = BotStateStore(td)
            session = BotSession(chat_id=42, platform="telegram", angle="ship it")
            path = store.save(session)

            self.assertTrue(path.exists())
            loaded = store.load(42)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.angle, "ship it")

            store.clear(42)
            self.assertIsNone(store.load(42))

    def test_save_does_not_leave_temp_files(self) -> None:
        from tone_of_voice.bot import BotSession

        with tempfile.TemporaryDirectory() as td:
            store = BotStateStore(td)
            store.save(BotSession(chat_id=42, platform="telegram", angle="ship it"))
            leftovers = list(store.sessions_dir.glob("*.tmp"))
            self.assertEqual(leftovers, [])

    def test_writes_review_history(self) -> None:
        from tone_of_voice.bot import BotSession

        with tempfile.TemporaryDirectory() as td:
            store = BotStateStore(td)
            session = BotSession(
                chat_id=42,
                platform="telegram",
                angle="ship it",
                draft="draft body",
            )
            path = store.append_review_history(session)

            data = json.loads(Path(path).read_text(encoding="utf-8"))
            self.assertEqual(data["draft"], "draft body")
            self.assertRegex(path.name, r"^\d{8}T\d+Z-chat-42-event-0-[0-9a-f]{6}\.json$")


class TelegramDraftAssistantTest(unittest.TestCase):
    def test_draft_revise_and_approve_flow(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            assistant = TelegramDraftAssistant(
                store=BotStateStore(td),
                generator=fake_generator,
                allowed_chat_ids={7},
            )

            draft_reply = "\n".join(assistant.handle_text(7, "/draft bot MVP"))
            self.assertIn("draft for bot MVP", draft_reply)

            revise_reply = "\n".join(assistant.handle_text(7, "/revise shorter"))
            self.assertIn("Revised draft ready", revise_reply)

            status_reply = "\n".join(assistant.handle_text(7, "/status"))
            self.assertIn("Revisions: 1", status_reply)

            approve_reply = "\n".join(assistant.handle_text(7, "/approve"))
            self.assertIn("No auto-publish was triggered", approve_reply)

    def test_rejects_unallowed_chat(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            assistant = TelegramDraftAssistant(
                store=BotStateStore(td),
                generator=fake_generator,
                allowed_chat_ids={7},
            )

            self.assertEqual(
                assistant.handle_text(8, "/draft nope"),
                ("This bot is not enabled for this chat.",),
            )

    def test_unknown_command_returns_help(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            assistant = TelegramDraftAssistant(
                store=BotStateStore(td),
                generator=fake_generator,
            )
            replies = assistant.handle_text(1, "/wat is going on")
            joined = "\n".join(replies)
            self.assertIn("Unknown command: /wat", joined)
            self.assertIn("/draft", joined)

    def test_status_without_session(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            assistant = TelegramDraftAssistant(
                store=BotStateStore(td),
                generator=fake_generator,
            )
            self.assertEqual(
                assistant.handle_text(1, "/status"),
                ("No active draft session.",),
            )

    def test_free_text_with_active_draft_revises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            assistant = TelegramDraftAssistant(
                store=BotStateStore(td),
                generator=fake_generator,
            )
            assistant.handle_text(1, "/draft initial idea")
            replies = assistant.handle_text(1, "make it shorter")
            self.assertTrue(any("Revised draft ready" in r for r in replies))

    def test_overwrite_guard_blocks_second_draft(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            assistant = TelegramDraftAssistant(
                store=BotStateStore(td),
                generator=fake_generator,
            )
            assistant.handle_text(1, "/draft first idea")
            replies = assistant.handle_text(1, "/draft second idea")
            joined = "\n".join(replies)
            self.assertIn("active draft", joined)
            self.assertIn("/cancel", joined)

    def test_cross_bot_mention_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            assistant = TelegramDraftAssistant(
                store=BotStateStore(td),
                generator=fake_generator,
                bot_username="my_bot",
            )
            self.assertEqual(
                assistant.handle_text(1, "/draft@otherbot do not respond"),
                (),
            )

    def test_dry_run_response_surfaces_artifact_paths(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            assistant = TelegramDraftAssistant(
                store=BotStateStore(td),
                generator=dry_run_generator,
            )
            replies = assistant.handle_text(1, "/draft something")
            joined = "\n".join(replies)
            self.assertIn("Dry run only", joined)
            self.assertIn("Artifact: /tmp/dry.json", joined)
            self.assertIn("Prompt: /tmp/dry.prompt.md", joined)

    def test_generator_exception_is_surfaced_and_session_not_saved(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            store = BotStateStore(td)
            assistant = TelegramDraftAssistant(
                store=store,
                generator=boom_generator,
            )
            replies = assistant.handle_text(1, "/draft trigger boom")
            joined = "\n".join(replies)
            self.assertIn("RuntimeError", joined)
            self.assertIn("upstream boom", joined)
            self.assertIsNone(store.load(1))

    def test_revise_generator_exception_preserves_prior_draft(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            store = BotStateStore(td)
            calls = {"n": 0}

            def flaky(request: DraftRequest) -> DraftResult:
                calls["n"] += 1
                if calls["n"] == 1:
                    return fake_generator(request)
                raise RuntimeError("revise boom")

            assistant = TelegramDraftAssistant(store=store, generator=flaky)
            assistant.handle_text(1, "/draft good idea")
            before = store.load(1)
            assistant.handle_text(1, "/revise tighter")
            after = store.load(1)

            self.assertIsNotNone(before)
            self.assertIsNotNone(after)
            self.assertEqual(before.draft, after.draft)
            self.assertEqual(after.revision_count, 0)


class BotEnvTest(unittest.TestCase):
    def test_allowed_chat_ids_from_env_and_cli_values(self) -> None:
        import os
        from unittest import mock

        with mock.patch.dict(os.environ, {"TONE_OF_VOICE_BOT_ALLOWED_CHAT_IDS": "1, 2"}):
            self.assertEqual(allowed_chat_ids_from_env([3]), {1, 2, 3})


class RunBotPreflightTest(unittest.TestCase):
    def test_run_telegram_bot_refuses_without_allowlist(self) -> None:
        async def go() -> None:
            await run_telegram_bot(bot_token="dummy", allowed_chat_ids=set())

        with self.assertRaises(RuntimeError) as cm:
            asyncio.run(go())
        self.assertIn("allowlist", str(cm.exception).lower())


if __name__ == "__main__":
    unittest.main()
