from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import secrets
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit, urlunsplit

from tone_of_voice.config import resolve_session_stem
from tone_of_voice.drafting import (
    DraftRequest,
    build_prompt_bundle,
    generate_with_anthropic_messages,
    write_draft_artifact,
)
from tone_of_voice.feedback import (
    FeedbackInput,
    build_feedback_analysis,
    summarize_feedback,
    write_feedback_pair,
)
from tone_of_voice.telegram_export import ensure_telegram_credentials


logger = logging.getLogger(__name__)


DEFAULT_BOT_OUTPUT_DIR = "data/working/bot"
DEFAULT_BOT_SESSION_NAME = "tone_of_voice_bot"
DEFAULT_DROP_STALE_SECONDS = 300
TELEGRAM_MESSAGE_LIMIT = 3900
FEEDBACK_MEMORY_LIMIT = 3
STAT_TREND_WINDOW = 3


@dataclass(frozen=True)
class DraftResult:
    draft: str | None
    artifact_path: str
    prompt_path: str
    backend: str


@dataclass(frozen=True)
class ResolvedFinalText:
    text: str
    source_url: str | None = None
    published_at: str | None = None


@dataclass(frozen=True)
class FeedbackSourceMatch:
    raw_path: Path
    analysis_path: Path
    record: dict[str, Any]


@dataclass
class BotSession:
    chat_id: int
    platform: str
    angle: str
    source_notes: str = ""
    constraints: tuple[str, ...] = ()
    status: str = "drafted"
    draft: str | None = None
    draft_artifact_path: str | None = None
    prompt_path: str | None = None
    revision_count: int = 0
    created_at: str = field(default_factory=lambda: utc_now())
    updated_at: str = field(default_factory=lambda: utc_now())
    approved_at: str | None = None
    events: tuple[dict[str, Any], ...] = ()

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "BotSession":
        return cls(
            chat_id=int(data["chat_id"]),
            platform=str(data.get("platform") or "telegram"),
            angle=str(data["angle"]),
            source_notes=str(data.get("source_notes") or ""),
            constraints=tuple(str(item) for item in data.get("constraints", [])),
            status=str(data.get("status") or "drafted"),
            draft=data.get("draft"),
            draft_artifact_path=data.get("draft_artifact_path"),
            prompt_path=data.get("prompt_path"),
            revision_count=int(data.get("revision_count") or 0),
            created_at=str(data.get("created_at") or utc_now()),
            updated_at=str(data.get("updated_at") or utc_now()),
            approved_at=data.get("approved_at"),
            events=tuple(data.get("events", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["constraints"] = list(self.constraints)
        data["events"] = list(self.events)
        return data

    def record_event(self, event_type: str, **payload: Any) -> None:
        event = {"type": event_type, "created_at": utc_now(), **payload}
        self.events = (*self.events, event)
        self.updated_at = event["created_at"]


class BotStateStore:
    def __init__(self, root: str | Path = DEFAULT_BOT_OUTPUT_DIR) -> None:
        self.root = Path(root).expanduser().resolve()
        self.sessions_dir = self.root / "sessions"
        self.history_dir = self.root / "history"
        self.feedback_dir = self.root / "feedback"

    def load(self, chat_id: int) -> BotSession | None:
        path = self._session_path(chat_id)
        if not path.exists():
            return None
        return BotSession.from_mapping(json.loads(path.read_text(encoding="utf-8")))

    def save(self, session: BotSession) -> Path:
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        path = self._session_path(session.chat_id)
        _atomic_write_text(
            path,
            json.dumps(session.to_dict(), ensure_ascii=False, indent=2) + "\n",
        )
        return path

    def clear(self, chat_id: int) -> None:
        path = self._session_path(chat_id)
        if path.exists():
            path.unlink()

    def append_review_history(self, session: BotSession) -> Path:
        self.history_dir.mkdir(parents=True, exist_ok=True)
        stamp = compact_stamp()
        suffix = secrets.token_hex(3)
        path = (
            self.history_dir
            / f"{stamp}-chat-{session.chat_id}-event-{len(session.events)}-{suffix}.json"
        )
        _atomic_write_text(
            path,
            json.dumps(session.to_dict(), ensure_ascii=False, indent=2) + "\n",
        )
        return path

    def latest_review_history(self, chat_id: int) -> BotSession | None:
        if not self.history_dir.exists():
            return None

        pattern = f"*-chat-{chat_id}-event-*.json"
        for path in sorted(self.history_dir.glob(pattern), reverse=True):
            try:
                return BotSession.from_mapping(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
                logger.warning("Skipping unreadable bot history file %s: %s", path, exc)
        return None

    def feedback_exists_for_source(self, source_draft_artifact: str | None) -> bool:
        return self.feedback_record_for_source(source_draft_artifact) is not None

    def feedback_record_for_source(
        self,
        source_draft_artifact: str | None,
    ) -> FeedbackSourceMatch | None:
        if not source_draft_artifact:
            return None

        raw_dir = self.feedback_dir / "raw"
        if not raw_dir.exists():
            return None

        for path in raw_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("Skipping unreadable feedback raw file %s: %s", path, exc)
                continue
            source = data.get("source") or {}
            if source.get("draft_artifact_path") == source_draft_artifact:
                feedback_id = str(data.get("id") or path.stem)
                return FeedbackSourceMatch(
                    raw_path=path,
                    analysis_path=self.feedback_dir / "analysis" / f"{feedback_id}.json",
                    record=data,
                )
        return None

    def _session_path(self, chat_id: int) -> Path:
        return self.sessions_dir / f"chat-{chat_id}.json"


def _atomic_write_text(path: Path, data: str) -> None:
    tmp = path.with_name(f"{path.name}.{secrets.token_hex(4)}.tmp")
    tmp.write_text(data, encoding="utf-8")
    os.replace(tmp, path)


DraftGenerator = Callable[[DraftRequest], DraftResult]
FinalTextResolver = Callable[[str], ResolvedFinalText | None]


class TelegramDraftAssistant:
    def __init__(
        self,
        *,
        store: BotStateStore,
        generator: DraftGenerator,
        allowed_chat_ids: set[int] | None = None,
        bot_username: str | None = None,
        final_text_resolver: FinalTextResolver | None = None,
    ) -> None:
        self.store = store
        self.generator = generator
        self.allowed_chat_ids = allowed_chat_ids or set()
        self.bot_username = bot_username
        self.final_text_resolver = final_text_resolver
        self._chat_locks: dict[int, threading.Lock] = {}
        self._chat_locks_lock = threading.Lock()

    def _chat_lock(self, chat_id: int) -> threading.Lock:
        with self._chat_locks_lock:
            lock = self._chat_locks.get(chat_id)
            if lock is None:
                lock = threading.Lock()
                self._chat_locks[chat_id] = lock
            return lock

    def handle_text(self, chat_id: int, text: str) -> tuple[str, ...]:
        clean = text.strip()
        if not clean:
            return ("Send /draft followed by the idea you want to turn into a post.",)

        if self.allowed_chat_ids and chat_id not in self.allowed_chat_ids:
            return ("This bot is not enabled for this chat.",)

        command, body, addressed = split_command(clean, bot_username=self.bot_username)
        if command and not addressed:
            return ()

        if command in {"/start", "/help"}:
            return (help_text(),)

        with self._chat_lock(chat_id):
            if command == "/draft":
                return self._draft(chat_id, body)
            if command == "/revise":
                return self._revise(chat_id, body)
            if command == "/approve":
                return self._approve(chat_id)
            if command == "/status":
                return self._status(chat_id)
            if command == "/final":
                return self._final(chat_id, body)
            if command == "/stat":
                return self._stat(chat_id)
            if command == "/cancel":
                self.store.clear(chat_id)
                return ("Current draft session cleared.",)
            if command:
                return (f"Unknown command: {command}\n\n{help_text()}",)

            session = self.store.load(chat_id)
            if session and session.status == "awaiting_final_replace":
                return self._final(chat_id, clean, replace_requested=True)
            if session and session.status == "awaiting_final":
                return self._final(chat_id, clean)
            if session and session.status == "awaiting_revision":
                return self._revise(chat_id, clean)
            if session and session.draft:
                return self._revise(chat_id, clean)
            return self._draft(chat_id, clean)

    def _draft(self, chat_id: int, idea: str) -> tuple[str, ...]:
        idea = idea.strip()
        if not idea:
            return ("Send the idea after /draft, for example:\n/draft short note about the bot MVP",)

        existing = self.store.load(chat_id)
        if existing and existing.draft and existing.status != "approved":
            return (
                "You already have an active draft. Send /cancel to discard it, "
                "or /revise <instruction> to refine it.",
            )

        feedback_context = build_feedback_learning_context(
            self.store.feedback_dir,
            chat_id=chat_id,
        )
        source_notes = idea
        constraints = [
            "Keep the first bot release human-in-the-loop.",
            "Return publish-ready text without metadata.",
        ]
        if feedback_context:
            source_notes = "\n\n".join([idea, feedback_context])
            constraints.append(
                "Use the feedback memory as writing guidance, but do not mention the memory."
            )

        request = DraftRequest.from_mapping(
            {
                "platform": "telegram",
                "angle": idea,
                "source_notes": source_notes,
                "constraints": constraints,
                "max_references": 5,
            }
        )
        try:
            result = self.generator(request)
        except Exception as exc:  # noqa: BLE001 - surface failure to the user
            logger.exception("draft generation failed for chat_id=%s", chat_id)
            return (_format_generator_error("draft", exc),)
        session = BotSession(
            chat_id=chat_id,
            platform=request.platform,
            angle=request.angle,
            source_notes=request.source_notes,
            constraints=request.constraints,
            draft=result.draft,
            draft_artifact_path=result.artifact_path,
            prompt_path=result.prompt_path,
        )
        session.record_event("draft_created", backend=result.backend)
        self.store.save(session)
        return format_draft_response(result, intro="Draft ready.")

    def _revise(self, chat_id: int, instruction: str) -> tuple[str, ...]:
        instruction = instruction.strip()
        session = self.store.load(chat_id)
        if not session or not session.draft:
            return ("No active draft yet. Send /draft followed by an idea first.",)
        if not instruction:
            session.status = "awaiting_revision"
            session.record_event("revision_requested")
            self.store.save(session)
            return (
                "Send the revision instruction in the next message. "
                "Send /cancel to stop waiting for the revision.",
            )

        source_notes = "\n\n".join(
            part
            for part in (
                session.source_notes,
                "Previous draft:",
                session.draft,
                "Revision request:",
                instruction,
            )
            if part
        )
        request = DraftRequest.from_mapping(
            {
                "platform": session.platform,
                "angle": session.angle,
                "source_notes": source_notes,
                "constraints": [
                    *session.constraints,
                    f"Revise the previous draft according to: {instruction}",
                    "Return only the revised post text.",
                ],
                "max_references": 5,
            }
        )
        try:
            result = self.generator(request)
        except Exception as exc:  # noqa: BLE001 - surface failure to the user
            logger.exception("draft revision failed for chat_id=%s", chat_id)
            return (_format_generator_error("revision", exc),)
        session.draft = result.draft
        session.draft_artifact_path = result.artifact_path
        session.prompt_path = result.prompt_path
        session.revision_count += 1
        session.status = "revised"
        session.record_event("draft_revised", instruction=instruction, backend=result.backend)
        self.store.save(session)
        return format_draft_response(result, intro="Revised draft ready.")

    def _approve(self, chat_id: int) -> tuple[str, ...]:
        session = self.store.load(chat_id)
        if not session or not session.draft:
            return ("No active draft to approve.",)

        session.status = "approved"
        session.approved_at = utc_now()
        session.record_event("draft_approved")
        history_path = self.store.append_review_history(session)
        self.store.clear(chat_id)
        return (
            "Approved for manual handoff.\n"
            "No auto-publish was triggered. Send /final <text or Telegram link> after manual edits.\n"
            f"Review history: {history_path}",
        )

    def _final(
        self,
        chat_id: int,
        final_input: str,
        *,
        replace_requested: bool = False,
    ) -> tuple[str, ...]:
        session = self._final_target_session(chat_id)
        if not session or not session.draft:
            return ("No draft to finalize. Send /draft first, then /final <final text>.",)

        replace_requested, final_input = parse_final_input_options(
            final_input,
            replace_requested=replace_requested,
        )
        existing_feedback = self.store.feedback_record_for_source(session.draft_artifact_path)
        if existing_feedback and not replace_requested:
            return (
                "Feedback for this draft was already captured. "
                "Send /final --replace <text or Telegram link> to overwrite it, "
                "or /stat to inspect learning progress.",
            )
        if replace_requested and not existing_feedback:
            return (
                "No existing feedback for this draft to replace. "
                "Send /final <text or Telegram link> to capture it first.",
            )

        if not final_input:
            session.status = "awaiting_final_replace" if replace_requested else "awaiting_final"
            session.record_event("final_requested", replace=replace_requested)
            self.store.save(session)
            prompt = (
                "Send the replacement final post text or a Telegram post link in the next message. "
                if replace_requested
                else "Send the final post text or a Telegram post link in the next message. "
            )
            return (
                prompt
                + "Send /cancel to stop waiting for the final.",
            )

        record_id = None
        created_at = None
        if existing_feedback:
            record_id = str(existing_feedback.record.get("id") or existing_feedback.raw_path.stem)
            created_at = parse_feedback_created_at(existing_feedback.record)

        resolved, error = self._resolve_final_input(final_input)
        if error:
            return (error,)
        if not resolved or not resolved.text.strip():
            return ("Final text is empty. Send /final followed by the final post text.",)

        feedback = FeedbackInput.from_mapping(
            {
                "platform": session.platform,
                "draft_text": session.draft,
                "approved_draft_text": session.draft,
                "final_text": resolved.text,
                "source_draft_artifact": session.draft_artifact_path,
                "request": session_to_feedback_request(session),
                "published_url": resolved.source_url,
                "published_at": resolved.published_at,
                "notes": f"Captured from Telegram bot chat {chat_id}.",
            }
        )
        raw_path, analysis_path, _record, analysis = write_feedback_pair(
            feedback,
            output_dir=self.store.feedback_dir,
            created_at=created_at,
            record_id=record_id,
        )

        session.status = "finalized"
        event_type = "final_replaced" if replace_requested else "final_captured"
        session.record_event(
            event_type,
            feedback_analysis_path=str(analysis_path),
            feedback_raw_path=str(raw_path),
            published_url=resolved.source_url,
        )
        self.store.append_review_history(session)
        self.store.clear(chat_id)

        metrics = analysis["comparisons"]["draft_to_final"]
        fit_score = fit_score_from_metrics(metrics)
        return (
            "\n".join(
                [
                    "Feedback replaced." if replace_requested else "Feedback captured.",
                    f"Fit score: {fit_score}/100",
                    (
                        "Draft-to-final: "
                        f"{metrics['char_percent_changed']}% chars changed, "
                        f"{metrics['word_percent_changed']}% words changed."
                    ),
                    f"Learning signal: {learning_signal_text(self.store.feedback_dir, chat_id=chat_id)}",
                    "No auto-publish was triggered.",
                ]
            ),
        )

    def _stat(self, chat_id: int) -> tuple[str, ...]:
        raw_records = load_feedback_raw_records(self.store.feedback_dir, chat_id=chat_id)
        analyses = [build_feedback_analysis(record) for record in raw_records]
        if not analyses:
            return (
                "No feedback stats yet. Capture a final with /final <text or Telegram link> first.",
            )

        summary = summarize_feedback(analyses, recent_limit=3)
        scored = scored_feedback_records(analyses)
        latest = scored[-1]
        latest_score = latest["fit_score"]
        current_window = scored[-STAT_TREND_WINDOW:]
        previous_window = scored[-(STAT_TREND_WINDOW * 2) : -STAT_TREND_WINDOW]
        current_average = round_average(item["fit_score"] for item in current_window)
        trend = format_score_trend(current_window, previous_window)
        metrics = summary["metrics"]
        corrections = ", ".join(
            correction for correction, _count in summary["tone_corrections"][:3]
        )
        corrections = corrections or "none yet"

        return (
            "\n".join(
                [
                    "Feedback stats",
                    f"Pairs: {summary['total_pairs']}",
                    f"Latest fit score: {latest_score}/100",
                    f"Rolling fit, last {len(current_window)}: {current_average}/100",
                    f"Trend: {trend}",
                    f"Median word changes: {metrics['median_word_percent_changed']}%",
                    f"Median char changes: {metrics['median_char_percent_changed']}%",
                    f"Common corrections: {corrections}",
                    f"Learning signal: {learning_signal_text(self.store.feedback_dir, chat_id=chat_id)}",
                ]
            ),
        )

    def _final_target_session(self, chat_id: int) -> BotSession | None:
        session = self.store.load(chat_id)
        if session and session.draft:
            return session
        return self.store.latest_review_history(chat_id)

    def _resolve_final_input(self, final_input: str) -> tuple[ResolvedFinalText | None, str | None]:
        standalone_link = parse_standalone_telegram_post_link(final_input)
        if standalone_link and self.final_text_resolver:
            try:
                resolved = self.final_text_resolver(final_input)
            except Exception as exc:  # noqa: BLE001 - user-facing bot recovery path
                logger.exception("final text resolver failed")
                return (
                    None,
                    (
                        "I could not read that Telegram post link: "
                        f"{type(exc).__name__}: {exc}\n"
                        "Paste the final text after /final instead."
                    ),
                )
            if resolved:
                return resolved, None

        if standalone_link:
            return (
                None,
                "I found a Telegram post link but this bot instance cannot fetch it. "
                "Paste the final text after /final instead.",
            )
        return ResolvedFinalText(text=final_input), None

    def _status(self, chat_id: int) -> tuple[str, ...]:
        session = self.store.load(chat_id)
        if not session:
            return ("No active draft session.",)
        return (
            "\n".join(
                [
                    f"Status: {session.status}",
                    f"Angle: {session.angle}",
                    f"Revisions: {session.revision_count}",
                    f"Artifact: {session.draft_artifact_path or 'not written'}",
                ]
            ),
        )


def make_draft_generator(
    *,
    draft_output_dir: str | Path,
    dry_run: bool = False,
    model: str | None = None,
    timeout: int = 120,
) -> DraftGenerator:
    def generate(request: DraftRequest) -> DraftResult:
        bundle = build_prompt_bundle(request, model=model)
        draft = None
        response_data = None
        backend = "prompt_only"
        if not dry_run:
            draft, response_data = generate_with_anthropic_messages(
                bundle,
                timeout=timeout,
            )
            backend = "anthropic_messages"

        artifact_path, prompt_path, _artifact = write_draft_artifact(
            bundle,
            output_dir=draft_output_dir,
            draft=draft,
            backend=backend,
            response_data=response_data,
        )
        return DraftResult(
            draft=draft,
            artifact_path=str(artifact_path),
            prompt_path=str(prompt_path),
            backend=backend,
        )

    return generate


async def run_telegram_bot(
    *,
    bot_token: str,
    output_dir: str | Path = DEFAULT_BOT_OUTPUT_DIR,
    session_name: str = DEFAULT_BOT_SESSION_NAME,
    session_dir: str | None = None,
    dry_run: bool = False,
    model: str | None = None,
    allowed_chat_ids: set[int] | None = None,
    allow_public: bool = False,
    timeout: int = 120,
    drop_stale_seconds: int | None = DEFAULT_DROP_STALE_SECONDS,
) -> None:
    from telethon import TelegramClient, events

    if not allowed_chat_ids and not allow_public:
        raise RuntimeError(
            "Refusing to start without an allowlist. Pass --allowed-chat-id, set "
            "TONE_OF_VOICE_BOT_ALLOWED_CHAT_IDS, or pass --allow-public to opt out explicitly."
        )

    api_id, api_hash = ensure_telegram_credentials()
    session_stem = resolve_session_stem(session_name=session_name, session_dir=session_dir)
    output_root = Path(output_dir).expanduser().resolve()
    store = BotStateStore(output_root)
    generator = make_draft_generator(
        draft_output_dir=output_root / "drafts",
        dry_run=dry_run,
        model=model,
        timeout=timeout,
    )

    client = TelegramClient(session_stem, api_id, api_hash, sequential_updates=True)
    await client.start(bot_token=bot_token)
    me = await client.get_me()
    bot_username = getattr(me, "username", None)
    loop = asyncio.get_running_loop()

    def final_text_resolver(raw_input: str) -> ResolvedFinalText | None:
        if not parse_standalone_telegram_post_link(raw_input):
            return None
        future = asyncio.run_coroutine_threadsafe(
            resolve_telegram_post_text(client, raw_input),
            loop,
        )
        return future.result(timeout=timeout)

    assistant = TelegramDraftAssistant(
        store=store,
        generator=generator,
        allowed_chat_ids=allowed_chat_ids,
        bot_username=bot_username,
        final_text_resolver=final_text_resolver,
    )
    stale_cutoff = startup_stale_cutoff(drop_stale_seconds)

    if allow_public and not allowed_chat_ids:
        logger.warning(
            "Telegram bot started in --allow-public mode; any chat that finds @%s will be served.",
            bot_username or "<unknown>",
        )

    @client.on(events.NewMessage(incoming=True))
    async def on_message(event: Any) -> None:
        text = event.raw_text or ""
        chat_id = int(event.chat_id)
        message_date = getattr(getattr(event, "message", None), "date", None)
        if should_ignore_stale_message(message_date, stale_cutoff):
            logger.info(
                "Ignoring stale Telegram message chat_id=%s message_date=%s cutoff=%s",
                chat_id,
                message_date,
                stale_cutoff,
            )
            return
        replies = await asyncio.to_thread(assistant.handle_text, chat_id, text)
        for message in replies:
            for chunk in split_for_telegram(message):
                await event.respond(chunk)

    print(f"Telegram bot running with session: {session_stem}")
    print(f"Bot state root: {output_root}")
    if stale_cutoff:
        print(f"Ignoring messages older than: {stale_cutoff.isoformat()}")
    await client.run_until_disconnected()


def bot_token_from_env() -> str:
    token = (
        os.getenv("TONE_OF_VOICE_TELEGRAM_BOT_TOKEN")
        or os.getenv("TELEGRAM_BOT_TOKEN")
        or ""
    ).strip()
    if not token:
        raise RuntimeError(
            "Missing TONE_OF_VOICE_TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN."
        )
    return token


def allowed_chat_ids_from_env(extra: list[int] | None = None) -> set[int]:
    values = set(extra or [])
    raw = os.getenv("TONE_OF_VOICE_BOT_ALLOWED_CHAT_IDS", "")
    for part in raw.split(","):
        item = part.strip()
        if item:
            values.add(int(item))
    return values


@dataclass(frozen=True)
class TelegramPostLink:
    entity: str | int
    message_id: int
    url: str
    is_private_channel_link: bool = False


def parse_telegram_post_link(text: str) -> TelegramPostLink | None:
    for raw_token in re.findall(r"https?://[^\s<>()]+", text):
        token = raw_token.rstrip(".,;:!?)]}")
        parsed = urlsplit(token)
        host = parsed.netloc.lower()
        if host not in {"t.me", "www.t.me", "telegram.me", "www.telegram.me"}:
            continue

        parts = [part for part in parsed.path.split("/") if part]
        if parts and parts[0] == "s":
            parts = parts[1:]
        if len(parts) < 2:
            continue

        if parts[0] == "c" and len(parts) >= 3:
            canonical_parts = parts[:4] if len(parts) >= 4 else parts[:3]
            try:
                channel_id = int(parts[1])
                message_id = int(canonical_parts[-1])
            except ValueError:
                continue
            return TelegramPostLink(
                entity=channel_id,
                message_id=message_id,
                url=_canonical_telegram_url(canonical_parts),
                is_private_channel_link=True,
            )

        channel = parts[0]
        canonical_parts = parts[:3] if len(parts) >= 3 else parts[:2]
        try:
            message_id = int(canonical_parts[-1])
        except ValueError:
            continue
        if not re.fullmatch(r"[A-Za-z0-9_]+", channel):
            continue
        return TelegramPostLink(
            entity=channel,
            message_id=message_id,
            url=_canonical_telegram_url(canonical_parts),
        )
    return None


def parse_standalone_telegram_post_link(text: str) -> TelegramPostLink | None:
    clean = text.strip()
    tokens = re.findall(r"https?://[^\s<>()]+", clean)
    if len(tokens) != 1:
        return None

    token = tokens[0].rstrip(".,;:!?)]}")
    if clean != token:
        return None
    return parse_telegram_post_link(clean)


async def resolve_telegram_post_text(client: Any, text: str) -> ResolvedFinalText | None:
    link = parse_standalone_telegram_post_link(text)
    if not link:
        return None

    entity: Any = link.entity
    if link.is_private_channel_link:
        from telethon.tl.types import PeerChannel

        entity = PeerChannel(int(link.entity))

    message = await client.get_messages(entity, ids=link.message_id)
    if not message:
        raise ValueError("Telegram post was not found or is not visible to the bot")

    final_text = (
        getattr(message, "raw_text", None)
        or getattr(message, "message", None)
        or ""
    ).strip()
    if not final_text:
        raise ValueError("Telegram post has no text")

    published_at = None
    message_date = getattr(message, "date", None)
    if isinstance(message_date, datetime):
        published_at = message_date.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    return ResolvedFinalText(
        text=final_text,
        source_url=link.url,
        published_at=published_at,
    )


def session_to_feedback_request(session: BotSession) -> dict[str, Any]:
    return {
        "platform": session.platform,
        "chat_id": session.chat_id,
        "angle": session.angle,
        "source_notes": session.source_notes,
        "constraints": list(session.constraints),
    }


def parse_final_input_options(
    final_input: str,
    *,
    replace_requested: bool = False,
) -> tuple[bool, str]:
    clean = final_input.strip()
    if clean == "--replace":
        return True, ""
    if clean.startswith("--replace "):
        return True, clean[len("--replace ") :].strip()
    return replace_requested, clean


def parse_feedback_created_at(record: dict[str, Any]) -> datetime | None:
    raw = str(record.get("created_at") or "").strip()
    if not raw:
        return None
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def build_feedback_learning_context(
    feedback_dir: str | Path,
    *,
    chat_id: int,
    limit: int = FEEDBACK_MEMORY_LIMIT,
) -> str:
    records = load_feedback_raw_records(feedback_dir, chat_id=chat_id)
    if not records:
        return ""

    snippets = []
    for record in records[-limit:]:
        final = str(record.get("final_text") or "").strip()
        if not final:
            continue
        metrics = build_feedback_analysis(record)["comparisons"]["draft_to_final"]
        angle = ((record.get("request") or {}).get("angle") or "").strip()
        snippets.append(
            "\n".join(
                part
                for part in (
                    f"- Previous angle: {angle}" if angle else "- Previous final:",
                    (
                        "  Draft-to-final delta: "
                        f"{metrics['word_percent_changed']}% words, "
                        f"{metrics['char_percent_changed']}% chars changed."
                    ),
                    f"  Final voice sample: {truncate_for_prompt(final)}",
                )
                if part
            )
        )

    if not snippets:
        return ""

    return "\n\n".join(
        [
            "Feedback memory from the author's accepted final versions:",
            *snippets,
        ]
    )


def load_feedback_raw_records(
    feedback_dir: str | Path,
    *,
    chat_id: int | None = None,
) -> list[dict[str, Any]]:
    raw_dir = Path(feedback_dir).expanduser().resolve() / "raw"
    if not raw_dir.exists():
        return []

    records: list[dict[str, Any]] = []
    for path in sorted(raw_dir.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Skipping unreadable feedback raw file %s: %s", path, exc)
            continue

        if chat_id is not None and feedback_record_chat_id(record) != chat_id:
            continue
        records.append(record)

    records.sort(key=lambda item: str(item.get("created_at") or ""))
    return records


def feedback_record_chat_id(record: dict[str, Any]) -> int | None:
    request = record.get("request") or {}
    value = request.get("chat_id")
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def learning_signal_text(feedback_dir: str | Path, *, chat_id: int) -> str:
    records = load_feedback_raw_records(feedback_dir, chat_id=chat_id)
    analyses = [build_feedback_analysis(record) for record in records]
    pair_count = len(analyses)
    if pair_count == 0:
        return "memory empty; future drafts have no captured finals yet."

    memory_count = min(len(records), FEEDBACK_MEMORY_LIMIT)
    scored = scored_feedback_records(analyses)
    trend = ""
    if len(scored) >= 2:
        delta = scored[-1]["fit_score"] - scored[-2]["fit_score"]
        sign = "+" if delta > 0 else ""
        trend = f"; latest score delta {sign}{delta}"
    return (
        f"memory enabled; {pair_count} final pair(s) captured; "
        f"next drafts use {memory_count} recent final sample(s){trend}."
    )


def scored_feedback_records(analyses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored = []
    for analysis in analyses:
        metrics = analysis["comparisons"]["draft_to_final"]
        scored.append(
            {
                "feedback_id": analysis["feedback_id"],
                "created_at": str(analysis.get("created_at") or ""),
                "fit_score": fit_score_from_metrics(metrics),
            }
        )
    scored.sort(key=lambda item: item["created_at"])
    return scored


def fit_score_from_metrics(metrics: dict[str, Any]) -> int:
    char_change = float(metrics.get("char_percent_changed") or 0)
    word_change = float(metrics.get("word_percent_changed") or 0)
    weighted_change = (char_change * 0.4) + (word_change * 0.6)
    return max(0, min(100, round(100 - weighted_change)))


def round_average(values: Any) -> int:
    numbers = [int(value) for value in values]
    if not numbers:
        return 0
    return round(sum(numbers) / len(numbers))


def format_score_trend(
    current_window: list[dict[str, Any]],
    previous_window: list[dict[str, Any]],
) -> str:
    if not previous_window:
        if len(current_window) < 2:
            return "need at least 2 captured finals"
        delta = current_window[-1]["fit_score"] - current_window[-2]["fit_score"]
        sign = "+" if delta > 0 else ""
        return f"{sign}{delta} vs previous final"

    current = round_average(item["fit_score"] for item in current_window)
    previous = round_average(item["fit_score"] for item in previous_window)
    delta = current - previous
    sign = "+" if delta > 0 else ""
    return f"{sign}{delta} vs previous {len(previous_window)}"


def truncate_for_prompt(text: str, limit: int = 700) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3].rstrip() + "..."


def _canonical_telegram_url(parts: list[str]) -> str:
    return urlunsplit(("https", "t.me", "/" + "/".join(parts), "", ""))


def split_command(
    text: str, *, bot_username: str | None = None
) -> tuple[str | None, str, bool]:
    if not text.startswith("/"):
        return None, text, True
    parts = text.split(None, 1)
    first = parts[0]
    rest = parts[1].strip() if len(parts) > 1 else ""
    base, _, mention = first.partition("@")
    command = base.lower()
    if mention and bot_username and mention.lower() != bot_username.lower():
        return command, rest, False
    return command, rest, True


def startup_stale_cutoff(
    drop_stale_seconds: int | None,
    *,
    now: datetime | None = None,
) -> datetime | None:
    if drop_stale_seconds is None or drop_stale_seconds < 0:
        return None
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc) - timedelta(seconds=drop_stale_seconds)


def should_ignore_stale_message(
    message_date: Any,
    stale_cutoff: datetime | None,
) -> bool:
    if stale_cutoff is None or not isinstance(message_date, datetime):
        return False
    if message_date.tzinfo is None:
        normalized = message_date.replace(tzinfo=timezone.utc)
    else:
        normalized = message_date.astimezone(timezone.utc)
    return normalized < stale_cutoff


def format_draft_response(result: DraftResult, *, intro: str) -> tuple[str, ...]:
    if result.draft:
        message = "\n\n".join(
            [
                intro,
                result.draft,
                (
                    "Reply with /revise <instruction>, /approve, "
                    "/final <text or Telegram link>, /final --replace <text or link>, "
                    "or /cancel."
                ),
            ]
        )
    else:
        message = "\n".join(
            [
                f"{intro} Dry run only; prompt artifact was written.",
                f"Artifact: {result.artifact_path}",
                f"Prompt: {result.prompt_path}",
                "Run without --dry-run on the host to call the model.",
            ]
        )
    return tuple(split_for_telegram(message))


def split_for_telegram(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> tuple[str, ...]:
    if len(text) <= limit:
        return (text,)

    chunks: list[str] = []
    current = ""
    for paragraph in re.split(r"(\n\n+)", text):
        if len(current) + len(paragraph) <= limit:
            current += paragraph
            continue
        if current:
            chunks.append(current.strip())
            current = ""
        while len(paragraph) > limit:
            chunks.append(paragraph[:limit].strip())
            paragraph = paragraph[limit:]
        current = paragraph
    if current.strip():
        chunks.append(current.strip())
    return tuple(chunks)


def help_text() -> str:
    return "\n".join(
        [
            "Commands:",
            "/draft <idea> - create a Telegram draft",
            "/revise <instruction> - revise the active draft",
            "/approve - save approval history for manual handoff",
            "/final <text or Telegram link> - capture the final version for feedback learning",
            "/final --replace <text or Telegram link> - overwrite the captured final for this draft",
            "/stat - show feedback score trend and learning signal",
            "/status - show the active session",
            "/cancel - clear the active session",
        ]
    )


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def compact_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _format_generator_error(action: str, exc: Exception) -> str:
    return (
        f"Sorry, the {action} call failed: {type(exc).__name__}: {exc}\n"
        "Try again, or run the bot with --dry-run to isolate prompt assembly from the model call."
    )
