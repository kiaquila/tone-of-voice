from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tone_of_voice.bot import (
    BotStateStore,
    DraftResult,
    ResolvedFinalText,
    TelegramDraftAssistant,
    allowed_chat_ids_from_env,
    compact_stamp,
    parse_standalone_telegram_post_link,
    parse_telegram_post_link,
    run_telegram_bot,
    should_ignore_stale_message,
    split_command,
    split_for_telegram,
    startup_stale_cutoff,
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

    def test_split_command_bare_command_is_addressed_to_us(self) -> None:
        self.assertEqual(
            split_command("/draft foo", bot_username="my_bot"),
            ("/draft", "foo", True),
        )

    def test_split_command_handles_arbitrary_whitespace(self) -> None:
        self.assertEqual(split_command("/draft\nidea body"), ("/draft", "idea body", True))
        self.assertEqual(split_command("/revise\tshorter please"), ("/revise", "shorter please", True))

    def test_splits_long_messages(self) -> None:
        chunks = split_for_telegram("x" * 8200, limit=3900)
        self.assertEqual(len(chunks), 3)
        self.assertTrue(all(len(chunk) <= 3900 for chunk in chunks))

    def test_parse_telegram_post_link_handles_public_and_private_links(self) -> None:
        public = parse_telegram_post_link("final: https://t.me/channel_name/123?single")
        self.assertIsNotNone(public)
        assert public is not None
        self.assertEqual(public.entity, "channel_name")
        self.assertEqual(public.message_id, 123)
        self.assertEqual(public.url, "https://t.me/channel_name/123")

        threaded_public = parse_telegram_post_link("https://t.me/channel_name/42/123")
        self.assertIsNotNone(threaded_public)
        assert threaded_public is not None
        self.assertEqual(threaded_public.entity, "channel_name")
        self.assertEqual(threaded_public.message_id, 123)
        self.assertEqual(threaded_public.url, "https://t.me/channel_name/42/123")

        private = parse_telegram_post_link("https://t.me/c/1234567890/77")
        self.assertIsNotNone(private)
        assert private is not None
        self.assertEqual(private.entity, 1234567890)
        self.assertEqual(private.message_id, 77)
        self.assertTrue(private.is_private_channel_link)

        threaded_private = parse_telegram_post_link("https://t.me/c/1234567890/42/77")
        self.assertIsNotNone(threaded_private)
        assert threaded_private is not None
        self.assertEqual(threaded_private.entity, 1234567890)
        self.assertEqual(threaded_private.message_id, 77)
        self.assertEqual(threaded_private.url, "https://t.me/c/1234567890/42/77")

    def test_standalone_telegram_link_requires_no_surrounding_text(self) -> None:
        self.assertIsNotNone(parse_standalone_telegram_post_link("https://t.me/channel_name/123"))
        self.assertIsNone(
            parse_standalone_telegram_post_link("final text https://t.me/channel_name/123")
        )


class CompactStampTest(unittest.TestCase):
    def test_compact_stamp_includes_microseconds(self) -> None:
        stamp = compact_stamp()
        self.assertRegex(stamp, r"^\d{8}T\d{6}\d{6}Z$")


class StaleMessageTest(unittest.TestCase):
    def test_startup_stale_cutoff_uses_configured_grace_window(self) -> None:
        now = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)
        self.assertEqual(
            startup_stale_cutoff(300, now=now),
            datetime(2026, 5, 1, 11, 55, tzinfo=timezone.utc),
        )

    def test_startup_stale_cutoff_can_be_disabled(self) -> None:
        self.assertIsNone(startup_stale_cutoff(-1))
        self.assertIsNone(startup_stale_cutoff(None))

    def test_should_ignore_messages_older_than_cutoff(self) -> None:
        cutoff = datetime(2026, 5, 1, 11, 55, tzinfo=timezone.utc)

        self.assertTrue(
            should_ignore_stale_message(
                datetime(2026, 5, 1, 11, 54, 59, tzinfo=timezone.utc),
                cutoff,
            )
        )
        self.assertFalse(
            should_ignore_stale_message(
                datetime(2026, 5, 1, 11, 55, tzinfo=timezone.utc),
                cutoff,
            )
        )
        self.assertFalse(
            should_ignore_stale_message(
                datetime(2026, 5, 1, 11, 56, tzinfo=timezone.utc),
                cutoff,
            )
        )

    def test_should_ignore_stale_message_handles_naive_datetimes(self) -> None:
        cutoff = datetime(2026, 5, 1, 11, 55, tzinfo=timezone.utc)
        self.assertTrue(
            should_ignore_stale_message(datetime(2026, 5, 1, 11, 54), cutoff)
        )

    def test_should_ignore_stale_message_ignores_unknown_dates(self) -> None:
        cutoff = datetime(2026, 5, 1, 11, 55, tzinfo=timezone.utc)
        self.assertFalse(should_ignore_stale_message(None, cutoff))
        self.assertFalse(should_ignore_stale_message("2026-05-01", cutoff))


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

    def test_concurrent_drafts_for_same_chat_are_serialized(self) -> None:
        import threading
        import time

        with tempfile.TemporaryDirectory() as td:
            store = BotStateStore(td)
            generator_calls: list[str] = []
            generator_calls_lock = threading.Lock()

            def slow_generator(request: DraftRequest) -> DraftResult:
                time.sleep(0.05)
                with generator_calls_lock:
                    generator_calls.append(request.angle)
                return fake_generator(request)

            assistant = TelegramDraftAssistant(store=store, generator=slow_generator)

            t1_result: list[tuple[str, ...]] = []
            t2_result: list[tuple[str, ...]] = []
            t1 = threading.Thread(
                target=lambda: t1_result.append(assistant.handle_text(1, "/draft first"))
            )
            t2 = threading.Thread(
                target=lambda: t2_result.append(assistant.handle_text(1, "/draft second"))
            )
            t1.start()
            t2.start()
            t1.join(timeout=5)
            t2.join(timeout=5)

            self.assertFalse(t1.is_alive())
            self.assertFalse(t2.is_alive())

            replies = [t1_result[0], t2_result[0]]
            blocked = [r for r in replies if any("active draft" in part for part in r)]
            accepted = [r for r in replies if r not in blocked]
            self.assertEqual(len(blocked), 1)
            self.assertEqual(len(accepted), 1)
            self.assertEqual(len(generator_calls), 1)

    def test_approve_clears_session_so_next_draft_starts_fresh(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            store = BotStateStore(td)
            assistant = TelegramDraftAssistant(store=store, generator=fake_generator)
            assistant.handle_text(1, "/draft first idea")
            assistant.handle_text(1, "/approve")

            self.assertIsNone(store.load(1))
            self.assertEqual(
                assistant.handle_text(1, "/status"),
                ("No active draft session.",),
            )

            replies = assistant.handle_text(1, "/draft second idea")
            joined = "\n".join(replies)
            self.assertIn("draft for second idea", joined)
            self.assertNotIn("active draft", joined)

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

    def test_final_captures_active_draft_feedback_and_clears_session(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            store = BotStateStore(td)
            assistant = TelegramDraftAssistant(store=store, generator=fake_generator)
            assistant.handle_text(1, "/draft bot MVP")

            replies = assistant.handle_text(1, "/final final bot MVP with more life")
            joined = "\n".join(replies)

            self.assertIn("Feedback captured", joined)
            self.assertIn("Fit score:", joined)
            self.assertIn("Learning signal:", joined)
            self.assertIsNone(store.load(1))
            raw_files = list((store.feedback_dir / "raw").glob("*.json"))
            analysis_files = list((store.feedback_dir / "analysis").glob("*.json"))
            self.assertEqual(len(raw_files), 1)
            self.assertEqual(len(analysis_files), 1)
            record = json.loads(raw_files[0].read_text(encoding="utf-8"))
            self.assertEqual(record["final_text"], "final bot MVP with more life")
            self.assertEqual(record["approved_draft_text"], "draft for bot MVP")

    def test_final_can_capture_after_approval_history(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            store = BotStateStore(td)
            assistant = TelegramDraftAssistant(store=store, generator=fake_generator)
            assistant.handle_text(1, "/draft handoff")
            assistant.handle_text(1, "/approve")

            replies = assistant.handle_text(1, "/final final handoff text")

            self.assertIn("Feedback captured", "\n".join(replies))
            self.assertEqual(len(list((store.feedback_dir / "raw").glob("*.json"))), 1)

    def test_final_without_body_waits_for_next_message(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            store = BotStateStore(td)
            assistant = TelegramDraftAssistant(store=store, generator=fake_generator)
            assistant.handle_text(1, "/draft waiting final")

            prompt = "\n".join(assistant.handle_text(1, "/final"))
            self.assertIn("next message", prompt)
            session = store.load(1)
            self.assertIsNotNone(session)
            assert session is not None
            self.assertEqual(session.status, "awaiting_final")

            replies = assistant.handle_text(1, "final text after waiting")

            self.assertIn("Feedback captured", "\n".join(replies))
            self.assertIsNone(store.load(1))

    def test_final_uses_telegram_link_resolver(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            store = BotStateStore(td)

            def resolver(raw_input: str) -> ResolvedFinalText | None:
                if raw_input == "https://t.me/channel_name/123":
                    return ResolvedFinalText(
                        text="final text from channel",
                        source_url=raw_input,
                        published_at="2026-05-01T12:00:00Z",
                    )
                return None

            assistant = TelegramDraftAssistant(
                store=store,
                generator=fake_generator,
                final_text_resolver=resolver,
            )
            assistant.handle_text(1, "/draft link final")

            replies = assistant.handle_text(1, "/final https://t.me/channel_name/123")

            self.assertIn("Feedback captured", "\n".join(replies))
            raw_file = next((store.feedback_dir / "raw").glob("*.json"))
            record = json.loads(raw_file.read_text(encoding="utf-8"))
            self.assertEqual(record["final_text"], "final text from channel")
            self.assertEqual(record["published"]["url"], "https://t.me/channel_name/123")

    def test_final_link_without_resolver_requests_manual_text(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            assistant = TelegramDraftAssistant(store=BotStateStore(td), generator=fake_generator)
            assistant.handle_text(1, "/draft link final")

            replies = assistant.handle_text(1, "/final https://t.me/channel_name/123")

            self.assertIn("cannot fetch", "\n".join(replies))

    def test_final_with_embedded_telegram_link_keeps_pasted_text(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            store = BotStateStore(td)

            def resolver(_raw_input: str) -> ResolvedFinalText | None:
                return ResolvedFinalText(text="linked post text", source_url="https://t.me/channel_name/123")

            assistant = TelegramDraftAssistant(
                store=store,
                generator=fake_generator,
                final_text_resolver=resolver,
            )
            assistant.handle_text(1, "/draft embedded link")
            final_text = "final text with source https://t.me/channel_name/123"

            replies = assistant.handle_text(1, f"/final {final_text}")

            self.assertIn("Feedback captured", "\n".join(replies))
            raw_file = next((store.feedback_dir / "raw").glob("*.json"))
            record = json.loads(raw_file.read_text(encoding="utf-8"))
            self.assertEqual(record["final_text"], final_text)
            self.assertIsNone(record["published"]["url"])

    def test_final_duplicate_guard_blocks_same_draft_twice(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            assistant = TelegramDraftAssistant(store=BotStateStore(td), generator=fake_generator)
            assistant.handle_text(1, "/draft duplicate")
            assistant.handle_text(1, "/final final text")

            replies = assistant.handle_text(1, "/final final text again")

            self.assertIn("already captured", "\n".join(replies))

    def test_stat_reports_score_trend_and_learning_signal(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            store = BotStateStore(td)

            def unique_generator(request: DraftRequest) -> DraftResult:
                artifact_name = request.angle.replace(" ", "-")
                return DraftResult(
                    draft=f"draft for {request.angle}",
                    artifact_path=f"/tmp/{artifact_name}.json",
                    prompt_path=f"/tmp/{artifact_name}.prompt.md",
                    backend="fake",
                )

            assistant = TelegramDraftAssistant(store=store, generator=unique_generator)
            assistant.handle_text(1, "/draft first")
            assistant.handle_text(1, "/final completely rewritten final with extra context")
            assistant.handle_text(1, "/draft second")
            assistant.handle_text(1, "/final draft for second")

            stat = "\n".join(assistant.handle_text(1, "/stat"))

            self.assertIn("Feedback stats", stat)
            self.assertIn("Pairs: 2", stat)
            self.assertIn("Latest fit score:", stat)
            self.assertIn("Trend:", stat)
            self.assertIn("Learning signal: memory enabled", stat)

    def test_stat_is_scoped_to_the_requesting_chat(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            store = BotStateStore(td)
            calls = {"n": 0}

            def unique_generator(request: DraftRequest) -> DraftResult:
                calls["n"] += 1
                artifact_name = f"{request.angle.replace(' ', '-')}-{calls['n']}"
                return DraftResult(
                    draft=f"draft for {request.angle}",
                    artifact_path=f"/tmp/{artifact_name}.json",
                    prompt_path=f"/tmp/{artifact_name}.prompt.md",
                    backend="fake",
                )

            assistant = TelegramDraftAssistant(store=store, generator=unique_generator)
            assistant.handle_text(1, "/draft chat one")
            assistant.handle_text(1, "/final final one")
            assistant.handle_text(2, "/draft chat two")
            assistant.handle_text(2, "/final final two")

            chat_one_stat = "\n".join(assistant.handle_text(1, "/stat"))
            chat_two_stat = "\n".join(assistant.handle_text(2, "/stat"))

            self.assertIn("Pairs: 1", chat_one_stat)
            self.assertIn("Pairs: 1", chat_two_stat)

    def test_stat_without_feedback_is_clear(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            assistant = TelegramDraftAssistant(store=BotStateStore(td), generator=fake_generator)

            self.assertIn("No feedback stats yet", "\n".join(assistant.handle_text(1, "/stat")))

    def test_new_draft_includes_feedback_memory_after_final_capture(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            store = BotStateStore(td)
            requests: list[DraftRequest] = []

            def recording_generator(request: DraftRequest) -> DraftResult:
                requests.append(request)
                return DraftResult(
                    draft=f"draft for {request.angle}",
                    artifact_path=f"/tmp/{len(requests)}.json",
                    prompt_path=f"/tmp/{len(requests)}.prompt.md",
                    backend="fake",
                )

            assistant = TelegramDraftAssistant(store=store, generator=recording_generator)
            assistant.handle_text(1, "/draft first")
            assistant.handle_text(1, "/final final text with author flavor")
            assistant.handle_text(2, "/draft other chat")
            assistant.handle_text(2, "/final other chat final text")
            assistant.handle_text(1, "/draft second")

            self.assertIn("Feedback memory", requests[-1].source_notes)
            self.assertIn("final text with author flavor", requests[-1].source_notes)
            self.assertNotIn("other chat final text", requests[-1].source_notes)


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
