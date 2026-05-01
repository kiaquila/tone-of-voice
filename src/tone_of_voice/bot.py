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

from tone_of_voice.config import resolve_session_stem
from tone_of_voice.drafting import (
    DraftRequest,
    build_prompt_bundle,
    generate_with_anthropic_messages,
    write_draft_artifact,
)
from tone_of_voice.telegram_export import ensure_telegram_credentials


logger = logging.getLogger(__name__)


DEFAULT_BOT_OUTPUT_DIR = "data/working/bot"
DEFAULT_BOT_SESSION_NAME = "tone_of_voice_bot"
DEFAULT_DROP_STALE_SECONDS = 300
TELEGRAM_MESSAGE_LIMIT = 3900


@dataclass(frozen=True)
class DraftResult:
    draft: str | None
    artifact_path: str
    prompt_path: str
    backend: str


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

    def _session_path(self, chat_id: int) -> Path:
        return self.sessions_dir / f"chat-{chat_id}.json"


def _atomic_write_text(path: Path, data: str) -> None:
    tmp = path.with_name(f"{path.name}.{secrets.token_hex(4)}.tmp")
    tmp.write_text(data, encoding="utf-8")
    os.replace(tmp, path)


DraftGenerator = Callable[[DraftRequest], DraftResult]


class TelegramDraftAssistant:
    def __init__(
        self,
        *,
        store: BotStateStore,
        generator: DraftGenerator,
        allowed_chat_ids: set[int] | None = None,
        bot_username: str | None = None,
    ) -> None:
        self.store = store
        self.generator = generator
        self.allowed_chat_ids = allowed_chat_ids or set()
        self.bot_username = bot_username
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
            if command == "/cancel":
                self.store.clear(chat_id)
                return ("Current draft session cleared.",)
            if command:
                return (f"Unknown command: {command}\n\n{help_text()}",)

            session = self.store.load(chat_id)
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

        request = DraftRequest.from_mapping(
            {
                "platform": "telegram",
                "angle": idea,
                "source_notes": idea,
                "constraints": [
                    "Keep the first bot release human-in-the-loop.",
                    "Return publish-ready text without metadata.",
                ],
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
        if not instruction:
            return ("Send the revision instruction after /revise.",)

        session = self.store.load(chat_id)
        if not session or not session.draft:
            return ("No active draft yet. Send /draft followed by an idea first.",)

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
            "No auto-publish was triggered. Send /draft to start a new one.\n"
            f"Review history: {history_path}",
        )

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

    assistant = TelegramDraftAssistant(
        store=store,
        generator=generator,
        allowed_chat_ids=allowed_chat_ids,
        bot_username=bot_username,
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
                "Reply with /revise <instruction>, /approve, or /cancel.",
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
