from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from telethon import TelegramClient, events

from tone_of_voice.config import resolve_session_stem
from tone_of_voice.drafting import (
    DraftRequest,
    build_prompt_bundle,
    generate_with_openai_responses,
    write_draft_artifact,
)
from tone_of_voice.telegram_export import ensure_telegram_credentials


DEFAULT_BOT_OUTPUT_DIR = "data/working/bot"
DEFAULT_BOT_SESSION_NAME = "tone_of_voice_bot"
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
        path.write_text(
            json.dumps(session.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return path

    def clear(self, chat_id: int) -> None:
        path = self._session_path(chat_id)
        if path.exists():
            path.unlink()

    def append_review_history(self, session: BotSession) -> Path:
        self.history_dir.mkdir(parents=True, exist_ok=True)
        stamp = compact_stamp()
        path = self.history_dir / f"{stamp}-chat-{session.chat_id}-event-{len(session.events)}.json"
        path.write_text(
            json.dumps(session.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return path

    def _session_path(self, chat_id: int) -> Path:
        return self.sessions_dir / f"chat-{chat_id}.json"


DraftGenerator = Callable[[DraftRequest], DraftResult]


class TelegramDraftAssistant:
    def __init__(
        self,
        *,
        store: BotStateStore,
        generator: DraftGenerator,
        allowed_chat_ids: set[int] | None = None,
    ) -> None:
        self.store = store
        self.generator = generator
        self.allowed_chat_ids = allowed_chat_ids or set()

    def handle_text(self, chat_id: int, text: str) -> tuple[str, ...]:
        clean = text.strip()
        if not clean:
            return ("Send /draft followed by the idea you want to turn into a post.",)

        if self.allowed_chat_ids and chat_id not in self.allowed_chat_ids:
            return ("This bot is not enabled for this chat.",)

        command, body = split_command(clean)

        if command in {"/start", "/help"}:
            return (help_text(),)
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
        result = self.generator(request)
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
        result = self.generator(request)
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
        self.store.save(session)
        history_path = self.store.append_review_history(session)
        return (
            "Approved for manual handoff.\n"
            "No auto-publish was triggered.\n"
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
            draft, response_data = generate_with_openai_responses(bundle, timeout=timeout)
            backend = "openai_responses"

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
    timeout: int = 120,
) -> None:
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
    assistant = TelegramDraftAssistant(
        store=store,
        generator=generator,
        allowed_chat_ids=allowed_chat_ids,
    )

    client = TelegramClient(session_stem, api_id, api_hash)

    @client.on(events.NewMessage(incoming=True))
    async def on_message(event: Any) -> None:
        text = event.raw_text or ""
        chat_id = int(event.chat_id)
        for message in assistant.handle_text(chat_id, text):
            for chunk in split_for_telegram(message):
                await event.respond(chunk)

    await client.start(bot_token=bot_token)
    print(f"Telegram bot running with session: {session_stem}")
    print(f"Bot state root: {output_root}")
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


def split_command(text: str) -> tuple[str | None, str]:
    if not text.startswith("/"):
        return None, text
    first, _, rest = text.partition(" ")
    command = first.split("@", 1)[0].lower()
    return command, rest.strip()


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
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
