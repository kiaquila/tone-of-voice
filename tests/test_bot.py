from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tone_of_voice.bot import (
    BotStateStore,
    DraftResult,
    TelegramDraftAssistant,
    allowed_chat_ids_from_env,
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


class BotCommandTest(unittest.TestCase):
    def test_split_command_handles_bot_mentions(self) -> None:
        self.assertEqual(split_command("/draft@my_bot hello"), ("/draft", "hello"))
        self.assertEqual(split_command("plain idea"), (None, "plain idea"))

    def test_splits_long_messages(self) -> None:
        chunks = split_for_telegram("x" * 8200, limit=3900)
        self.assertEqual(len(chunks), 3)
        self.assertTrue(all(len(chunk) <= 3900 for chunk in chunks))


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


class BotEnvTest(unittest.TestCase):
    def test_allowed_chat_ids_from_env_and_cli_values(self) -> None:
        import os
        from unittest import mock

        with mock.patch.dict(os.environ, {"TONE_OF_VOICE_BOT_ALLOWED_CHAT_IDS": "1, 2"}):
            self.assertEqual(allowed_chat_ids_from_env([3]), {1, 2, 3})


if __name__ == "__main__":
    unittest.main()
