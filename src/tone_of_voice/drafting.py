from __future__ import annotations

import json
import os
import re
import secrets
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tone_of_voice.config import repo_root
from tone_of_voice.style_memory import (
    DEFAULT_FEEDBACK_DIRS,
    STYLE_MEMORY_DOCS,
    StyleMemoryMatch,
    StyleMemoryQuery,
    build_style_memory_index,
    feedback_raw_dirs,
    normalize_token,
    retrieve_style_memory,
    style_memory_query_from_request,
    text_tokens,
)


ALLOWED_PLATFORMS = {"telegram", "threads", "linkedin"}
ALLOWED_RETRIEVAL_STRATEGIES = {"heuristic", "style_memory", "hybrid"}
# Source types eligible for the drafting prompt context. `feedback_final`
# (raw user final post text) is intentionally excluded so that previous final
# posts do not leak back into the prompt and cause self-imitation drift or
# unnecessary data flow to model providers.
PROMPT_CONTEXT_SOURCE_TYPES = (
    "reference_example",
    "voice_principle",
    "voice_snapshot",
    "platform_playbook",
    "stop_rule",
    "drafting_recipe",
    "feedback_correction",
)
DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_ANTHROPIC_MAX_TOKENS = 4096
ANTHROPIC_API_VERSION = "2023-06-01"
ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"

CONTEXT_DOCS = (
    "docs/00-principles.md",
    "docs/01-current-voice-snapshot.md",
    "docs/04-platform-adaptation.md",
    "docs/12-stop-list.md",
    "docs/13-drafting-recipes.md",
)

RECIPE_SHORTCUT_ALIASES = {
    "telegram_quick_reaction": ("quick_telegram_reaction",),
    "telegram_field_note_from_practice": ("quick_telegram_reaction",),
    "tool_or_setup_breakdown": ("tool_or_setup_breakdown",),
    "contrarian_product_take": ("contrarian_take",),
    "project_update_or_launch": ("project_update",),
    "threads_distillation": ("quick_telegram_reaction",),
    "linkedin_grounded_version": ("tool_or_setup_breakdown", "project_update"),
}

SYSTEM_INSTRUCTIONS = """You draft public posts for the author using only the provided voice memory.

Write in the target platform's packaging while preserving the same authorial identity.
Keep the draft human, situated, and first-person when the request allows it.
Do not copy reference examples mechanically.
Do not add generic marketing language, fake certainty, or a formal CTA unless requested.
Return only one near-finished post draft, with no analysis or title."""


@dataclass(frozen=True)
class DraftRequest:
    platform: str
    angle: str
    source_notes: str = ""
    constraints: tuple[str, ...] = ()
    call_to_action: str | None = None
    topics: tuple[str, ...] = ()
    post_type: str | None = None
    mood: tuple[str, ...] = ()
    recipe: str | None = None
    language: str = "ru"
    max_references: int = 5
    model: str | None = None
    retrieval_strategy: str | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "DraftRequest":
        platform = normalize_token(_required_text(data, "platform"))
        if platform not in ALLOWED_PLATFORMS:
            allowed = ", ".join(sorted(ALLOWED_PLATFORMS))
            raise ValueError(f"platform must be one of: {allowed}")

        angle = _required_text(data, "angle")
        max_references = int(data.get("max_references", 5))
        if not 3 <= max_references <= 5:
            raise ValueError("max_references must be between 3 and 5")

        post_type = _optional_token(data.get("post_type"))
        recipe = _optional_token(data.get("recipe"))
        retrieval_strategy = _optional_token(data.get("retrieval_strategy"))
        if (
            retrieval_strategy
            and retrieval_strategy not in ALLOWED_RETRIEVAL_STRATEGIES
        ):
            allowed = ", ".join(sorted(ALLOWED_RETRIEVAL_STRATEGIES))
            raise ValueError(f"retrieval_strategy must be one of: {allowed}")

        return cls(
            platform=platform,
            angle=angle,
            source_notes=_clean_text(data.get("source_notes") or ""),
            constraints=tuple(_listify(data.get("constraints"))),
            call_to_action=_clean_text(data.get("call_to_action"))
            if data.get("call_to_action")
            else None,
            topics=tuple(_listify(data.get("topics"), normalize_tokens=True)),
            post_type=post_type,
            mood=tuple(_listify(data.get("mood"), normalize_tokens=True)),
            recipe=recipe,
            language=_clean_text(data.get("language") or "ru"),
            max_references=max_references,
            model=_clean_text(data.get("model")) if data.get("model") else None,
            retrieval_strategy=retrieval_strategy,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReferenceEntry:
    ref_id: str
    title: str
    platform: str
    source: str
    published_at: str
    post_types: tuple[str, ...]
    moods: tuple[str, ...]
    depth: str
    topics: tuple[str, ...]
    best_for: str
    watch_out: str
    representative_text: str

    def to_prompt_block(self) -> str:
        lines = [
            f"### {self.ref_id} - {self.title}",
            f"- platform: {self.platform}",
            f"- post_type: {', '.join(self.post_types)}",
            f"- mood: {', '.join(self.moods)}",
            f"- depth: {self.depth}",
            f"- topics: {', '.join(self.topics)}",
            f"- best_for: {self.best_for}",
            f"- watch_out: {self.watch_out}",
            "",
            "Representative text:",
            self.representative_text,
        ]
        return "\n".join(lines).strip()

    def to_artifact(self) -> dict[str, Any]:
        data = asdict(self)
        data["post_types"] = list(self.post_types)
        data["moods"] = list(self.moods)
        data["topics"] = list(self.topics)
        return data


@dataclass(frozen=True)
class ReferenceLibrary:
    entries: tuple[ReferenceEntry, ...]
    shortcuts: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class PromptBundle:
    request: DraftRequest
    model: str
    prompt: str
    references: tuple[ReferenceEntry, ...]
    context_files: tuple[str, ...]
    retrieval_strategy: str = "heuristic"
    style_memory_matches: tuple[StyleMemoryMatch, ...] = ()
    system_instructions: str = SYSTEM_INSTRUCTIONS


def load_request_json(path: str) -> DraftRequest:
    request_path = Path(path).expanduser().resolve()
    with request_path.open(encoding="utf-8") as fh:
        return DraftRequest.from_mapping(json.load(fh))


def load_reference_library(root: Path | None = None) -> ReferenceLibrary:
    base = root or repo_root()
    path = base / "docs/10-reference-library.md"
    return parse_reference_library(path.read_text(encoding="utf-8"))


def parse_reference_library(markdown: str) -> ReferenceLibrary:
    entries: list[ReferenceEntry] = []
    shortcuts: dict[str, tuple[str, ...]] = {}
    current: dict[str, Any] | None = None
    representative_lines: list[str] = []
    collecting_representative = False
    in_shortcuts = False

    def finalize_current() -> None:
        nonlocal current, representative_lines, collecting_representative
        if not current:
            return
        fields = current["fields"]
        entries.append(
            ReferenceEntry(
                ref_id=current["ref_id"],
                title=current["title"],
                platform=normalize_token(fields.get("platform", "")),
                source=fields.get("source", ""),
                published_at=fields.get("published_at", ""),
                post_types=tuple(_split_tokens(fields.get("post_type", ""))),
                moods=tuple(_split_tokens(fields.get("mood", ""))),
                depth=normalize_token(fields.get("depth", "")),
                topics=tuple(_split_tokens(fields.get("topics", ""))),
                best_for=fields.get("best_for", ""),
                watch_out=fields.get("watch_out", ""),
                representative_text="\n".join(representative_lines).strip(),
            )
        )
        current = None
        representative_lines = []
        collecting_representative = False

    for line in markdown.splitlines():
        if line.startswith("## Retrieval Shortcuts"):
            finalize_current()
            in_shortcuts = True
            continue

        if in_shortcuts:
            shortcut_match = re.match(r"^- `([^`]+)`: (.+)$", line)
            if shortcut_match:
                refs = tuple(re.findall(r"REF-[A-Z]+-\d+", shortcut_match.group(2)))
                shortcuts[normalize_token(shortcut_match.group(1))] = refs
            continue

        heading = re.match(r"^### (REF-[A-Z]+-\d+) - (.+)$", line)
        if heading:
            finalize_current()
            current = {
                "ref_id": heading.group(1),
                "title": heading.group(2).strip(),
                "fields": {},
            }
            continue

        if current is None:
            continue

        if line.strip() == "Representative text:":
            collecting_representative = True
            continue

        if collecting_representative:
            if line.startswith(">"):
                representative_lines.append(line[1:].lstrip())
                continue
            if not line.strip():
                continue
            collecting_representative = False

        field = re.match(r"^- `([^`]+)`: (.*)$", line)
        if field:
            current["fields"][normalize_token(field.group(1))] = field.group(2).strip()

    finalize_current()
    return ReferenceLibrary(entries=tuple(entries), shortcuts=shortcuts)


def select_references(
    request: DraftRequest,
    library: ReferenceLibrary,
) -> tuple[ReferenceEntry, ...]:
    if not library.entries:
        return ()

    shortcut_ref_ids = _shortcut_ref_ids(request, library.shortcuts)
    query_tokens = set(
        text_tokens(
            " ".join(
                [
                    request.angle,
                    request.source_notes,
                    " ".join(request.constraints),
                    request.call_to_action or "",
                    " ".join(request.topics),
                    request.post_type or "",
                    " ".join(request.mood),
                ]
            )
        )
    )

    scored: list[tuple[int, str, ReferenceEntry]] = []
    for entry in library.entries:
        score = 0
        if entry.ref_id in shortcut_ref_ids:
            score += 50
        if entry.platform == request.platform:
            score += 10
        elif entry.platform == "telegram" and request.platform in {"threads", "linkedin"}:
            score += 3
        if request.post_type and request.post_type in entry.post_types:
            score += 10
        score += 5 * len(set(request.topics).intersection(entry.topics))
        score += 3 * len(set(request.mood).intersection(entry.moods))

        entry_tokens = set(
            text_tokens(
                " ".join(
                    [
                        entry.title,
                        entry.best_for,
                        entry.watch_out,
                        " ".join(entry.post_types),
                        " ".join(entry.topics),
                    ]
                )
            )
        )
        score += min(len(query_tokens.intersection(entry_tokens)), 5)
        scored.append((score, entry.ref_id, entry))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return tuple(item[2] for item in scored[: request.max_references])


def resolve_retrieval_strategy(request: DraftRequest) -> str:
    raw = (
        request.retrieval_strategy
        or os.getenv("TONE_OF_VOICE_RETRIEVAL_STRATEGY")
        or "heuristic"
    )
    strategy = normalize_token(raw)
    if strategy not in ALLOWED_RETRIEVAL_STRATEGIES:
        allowed = ", ".join(sorted(ALLOWED_RETRIEVAL_STRATEGIES))
        raise ValueError(f"retrieval_strategy must be one of: {allowed}")
    return strategy


def select_references_from_memory(
    request: DraftRequest,
    library: ReferenceLibrary,
    memory_matches: tuple[StyleMemoryMatch, ...],
    *,
    strategy: str,
) -> tuple[ReferenceEntry, ...]:
    by_id = {entry.ref_id: entry for entry in library.entries}
    heuristic = list(select_references(request, library))
    memory_refs = []
    for match in memory_matches:
        ref_id = str((match.record.metadata or {}).get("ref_id") or "").strip()
        if ref_id and ref_id in by_id:
            memory_refs.append(by_id[ref_id])

    if strategy == "style_memory":
        ordered = _unique_references(memory_refs + heuristic)
    elif strategy == "hybrid":
        ordered = _interleave_references(memory_refs, heuristic)
    else:
        ordered = heuristic
    return tuple(ordered[: request.max_references])


_STYLE_MEMORY_CACHE: dict[Any, Any] = {}


def _style_memory_cache_disabled() -> bool:
    raw = os.getenv("TONE_OF_VOICE_STYLE_MEMORY_CACHE", "").strip().lower()
    return raw == "disabled"


def _clear_style_memory_cache() -> None:
    """Clear the in-process style-memory index cache.

    Intended for tests so cached state does not leak between cases.
    """

    _STYLE_MEMORY_CACHE.clear()


def _style_memory_cache_fingerprint(
    base: Path,
    library: ReferenceLibrary,
) -> tuple[Any, ...]:
    doc_mtimes: list[float] = []
    for rel_path, *_rest in STYLE_MEMORY_DOCS:
        doc_path = base / rel_path
        try:
            doc_mtimes.append(doc_path.stat().st_mtime)
        except OSError:
            doc_mtimes.append(0.0)

    feedback_mtimes: list[float] = []
    feedback_paths: list[str] = []
    for raw_dir in feedback_raw_dirs(base, DEFAULT_FEEDBACK_DIRS):
        for path in sorted(raw_dir.glob("*.json")):
            feedback_paths.append(str(path))
            try:
                feedback_mtimes.append(path.stat().st_mtime)
            except OSError:
                feedback_mtimes.append(0.0)

    library_signature = tuple(entry.ref_id for entry in library.entries)

    return (
        str(base),
        tuple(rel_path for rel_path, *_ in STYLE_MEMORY_DOCS),
        tuple(doc_mtimes),
        tuple(feedback_paths),
        tuple(feedback_mtimes),
        library_signature,
    )


def _get_or_build_style_memory_index(
    base: Path,
    library: ReferenceLibrary,
):
    if _style_memory_cache_disabled():
        return build_style_memory_index(
            root=base,
            reference_entries=library.entries,
        )

    fingerprint = _style_memory_cache_fingerprint(base, library)
    cached = _STYLE_MEMORY_CACHE.get("entry")
    if cached is not None and cached[0] == fingerprint:
        return cached[1]

    index = build_style_memory_index(
        root=base,
        reference_entries=library.entries,
    )
    _STYLE_MEMORY_CACHE["entry"] = (fingerprint, index)
    return index


def build_prompt_bundle(
    request: DraftRequest,
    *,
    root: Path | None = None,
    model: str | None = None,
) -> PromptBundle:
    base = root or repo_root()
    library = load_reference_library(base)
    retrieval_strategy = resolve_retrieval_strategy(request)
    style_memory_matches: tuple[StyleMemoryMatch, ...] = ()
    if retrieval_strategy == "heuristic":
        references = select_references(request, library)
    else:
        style_index = _get_or_build_style_memory_index(base, library)
        prompt_context_query = style_memory_query_from_request(request)
        style_memory_matches = retrieve_style_memory(
            style_index,
            StyleMemoryQuery(
                text=prompt_context_query.text,
                platform=prompt_context_query.platform,
                post_type=prompt_context_query.post_type,
                topics=prompt_context_query.topics,
                mood=prompt_context_query.mood,
                source_types=PROMPT_CONTEXT_SOURCE_TYPES,
            ),
            limit=6,
        )
        reference_query = style_memory_query_from_request(request)
        reference_matches = retrieve_style_memory(
            style_index,
            StyleMemoryQuery(
                text=reference_query.text,
                platform=reference_query.platform,
                post_type=reference_query.post_type,
                topics=reference_query.topics,
                mood=reference_query.mood,
                source_types=("reference_example",),
            ),
            limit=request.max_references,
        )
        references = select_references_from_memory(
            request,
            library,
            reference_matches,
            strategy=retrieval_strategy,
        )
    context_blocks = []
    context_files = []

    for rel_path in CONTEXT_DOCS:
        path = base / rel_path
        context_files.append(rel_path)
        context_blocks.append(f"## {rel_path}\n\n{path.read_text(encoding='utf-8').strip()}")

    request_json = json.dumps(request.to_dict(), ensure_ascii=False, indent=2)
    reference_blocks = "\n\n".join(ref.to_prompt_block() for ref in references)
    style_memory_blocks = "\n\n".join(
        match.to_prompt_block() for match in style_memory_matches
    )

    prompt = "\n\n".join(
        [
            "# Task",
            "Draft one public post from the structured request.",
            "",
            "# Draft Request",
            request_json,
            "",
            "# Voice Memory",
            "\n\n".join(context_blocks),
            "",
            "# Selected Reference Examples",
            reference_blocks or "No references selected.",
            "",
            "# Retrieved Style Memory",
            (
                "\n\n".join(
                    [
                        f"Retrieval strategy: {retrieval_strategy}.",
                        (
                            "Use positive records as style evidence. "
                            "Use corrective records as guardrails. "
                            "Do not mention the retrieval system."
                        ),
                        style_memory_blocks or "No style-memory records selected.",
                    ]
                )
                if retrieval_strategy != "heuristic"
                else "Retrieval strategy: heuristic. No extra style-memory records selected."
            ),
            "",
            "# Output Contract",
            "- Return exactly one draft.",
            "- Use the request language unless the user explicitly asks otherwise.",
            "- Do not explain the rules.",
            "- Do not include a title, metadata, or commentary.",
        ]
    )

    selected_model = (
        model
        or request.model
        or os.getenv("TONE_OF_VOICE_ANTHROPIC_MODEL")
        or os.getenv("ANTHROPIC_MODEL")
        or DEFAULT_MODEL
    )
    return PromptBundle(
        request=request,
        model=selected_model,
        prompt=prompt,
        references=references,
        context_files=tuple(context_files),
        retrieval_strategy=retrieval_strategy,
        style_memory_matches=style_memory_matches,
    )


def generate_with_anthropic_messages(
    bundle: PromptBundle,
    *,
    api_key: str | None = None,
    timeout: int = 120,
    max_tokens: int | None = None,
) -> tuple[str, dict[str, Any]]:
    key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Re-run with --dry-run to inspect the prompt "
            "or export ANTHROPIC_API_KEY to generate a draft."
        )

    payload = {
        "model": bundle.model,
        "max_tokens": max_tokens or anthropic_max_tokens_from_env(),
        "system": bundle.system_instructions,
        "messages": [{"role": "user", "content": bundle.prompt}],
    }
    request = urllib.request.Request(
        ANTHROPIC_MESSAGES_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-api-key": key,
            "anthropic-version": ANTHROPIC_API_VERSION,
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Anthropic Messages API returned HTTP {exc.code}: {error_body}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Anthropic Messages API request failed: {exc}") from exc

    response_data = json.loads(body)
    return extract_anthropic_message_text(response_data), response_data


def extract_anthropic_message_text(response_data: dict[str, Any]) -> str:
    chunks: list[str] = []
    for item in response_data.get("content", []):
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if isinstance(text, str) and item.get("type") == "text":
            chunks.append(text)

    text = "\n".join(chunk.strip() for chunk in chunks if chunk.strip()).strip()
    if not text:
        raise RuntimeError("Anthropic response did not contain text content.")
    return text


def anthropic_max_tokens_from_env() -> int:
    raw = (
        os.getenv("TONE_OF_VOICE_ANTHROPIC_MAX_TOKENS")
        or os.getenv("ANTHROPIC_MAX_TOKENS")
        or ""
    ).strip()
    if not raw:
        return DEFAULT_ANTHROPIC_MAX_TOKENS

    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(
            f"ANTHROPIC_MAX_TOKENS must be an integer, got {raw!r}."
        ) from exc

    if value <= 0:
        raise RuntimeError("ANTHROPIC_MAX_TOKENS must be greater than zero.")
    return value


def write_draft_artifact(
    bundle: PromptBundle,
    *,
    output_dir: str | Path,
    draft: str | None,
    backend: str,
    response_data: dict[str, Any] | None = None,
) -> tuple[Path, Path, dict[str, Any]]:
    created_at = datetime.now(timezone.utc).replace(microsecond=0)
    artifact_id = _artifact_id(bundle.request, created_at)
    output_path = Path(output_dir).expanduser().resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    prompt_path = output_path / f"{artifact_id}.prompt.md"
    artifact_path = output_path / f"{artifact_id}.json"
    prompt_path.write_text(bundle.prompt + "\n", encoding="utf-8")

    artifact = {
        "id": artifact_id,
        "created_at": created_at.isoformat().replace("+00:00", "Z"),
        "backend": backend,
        "model": bundle.model,
        "request": bundle.request.to_dict(),
        "context_files": list(bundle.context_files),
        "retrieval_strategy": bundle.retrieval_strategy,
        "references": [reference.to_artifact() for reference in bundle.references],
        "style_memory_matches": [
            match.to_dict() for match in bundle.style_memory_matches
        ],
        "prompt_path": str(prompt_path),
        "draft": draft,
        "response_id": response_data.get("id") if response_data else None,
    }
    artifact_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return artifact_path, prompt_path, artifact


def _required_text(data: dict[str, Any], key: str) -> str:
    value = _clean_text(data.get(key))
    if not value:
        raise ValueError(f"{key} is required")
    return value


def _clean_text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _optional_token(value: Any) -> str | None:
    text = _clean_text(value)
    return normalize_token(text) if text else None


def _split_tokens(value: str) -> list[str]:
    return [normalize_token(part) for part in value.split(",") if part.strip()]


def _listify(value: Any, *, normalize_tokens: bool = False) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        values = [part.strip() for part in value.split(",")] if "," in value else [value.strip()]
    elif isinstance(value, (list, tuple)):
        values = [_clean_text(item) for item in value]
    else:
        values = [_clean_text(value)]
    values = [item for item in values if item]
    if normalize_tokens:
        return [normalize_token(item) for item in values]
    return values


def _shortcut_ref_ids(
    request: DraftRequest,
    shortcuts: dict[str, tuple[str, ...]],
) -> set[str]:
    shortcut_names: list[str] = []
    if request.recipe:
        shortcut_names.append(request.recipe)
        shortcut_names.extend(RECIPE_SHORTCUT_ALIASES.get(request.recipe, ()))
    if request.post_type:
        shortcut_names.append(request.post_type)
    if request.platform == "threads":
        shortcut_names.extend(RECIPE_SHORTCUT_ALIASES["threads_distillation"])
    if request.platform == "linkedin":
        shortcut_names.extend(RECIPE_SHORTCUT_ALIASES["linkedin_grounded_version"])

    refs: set[str] = set()
    for name in shortcut_names:
        refs.update(shortcuts.get(normalize_token(name), ()))
    return refs


def _unique_references(entries: list[ReferenceEntry]) -> list[ReferenceEntry]:
    seen: set[str] = set()
    unique = []
    for entry in entries:
        if entry.ref_id in seen:
            continue
        seen.add(entry.ref_id)
        unique.append(entry)
    return unique


def _interleave_references(
    primary: list[ReferenceEntry],
    secondary: list[ReferenceEntry],
) -> list[ReferenceEntry]:
    seen: set[str] = set()
    merged: list[ReferenceEntry] = []
    max_len = max(len(primary), len(secondary))
    for index in range(max_len):
        for group in (primary, secondary):
            if index >= len(group):
                continue
            entry = group[index]
            if entry.ref_id in seen:
                continue
            seen.add(entry.ref_id)
            merged.append(entry)
    return merged


def _artifact_id(request: DraftRequest, created_at: datetime) -> str:
    stamp = created_at.strftime("%Y%m%dT%H%M%SZ")
    slug = re.sub(r"[^a-z0-9]+", "-", request.angle.lower()).strip("-")[:40]
    if not slug:
        slug = "draft"
    suffix = secrets.token_hex(3)
    return f"{stamp}-{request.platform}-{slug}-{suffix}"
