from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from tone_of_voice.config import repo_root


SCHEMA_VERSION = 1
DEFAULT_STYLE_INDEX_PATH = "data/working/style-memory/index.json"
DEFAULT_FEEDBACK_DIRS = (
    "data/working/feedback",
    "data/working/bot/feedback",
)

STYLE_MEMORY_DOCS = (
    ("docs/00-principles.md", "voice_principle", "positive", "general"),
    ("docs/01-current-voice-snapshot.md", "voice_snapshot", "positive", "general"),
    ("docs/04-platform-adaptation.md", "platform_playbook", "positive", "platform"),
    ("docs/12-stop-list.md", "stop_rule", "corrective", "general"),
    ("docs/13-drafting-recipes.md", "drafting_recipe", "positive", "platform"),
)


@dataclass(frozen=True)
class StyleMemoryRecord:
    record_id: str
    source_type: str
    title: str
    text: str
    source: str
    platform: str | None = None
    post_types: tuple[str, ...] = ()
    topics: tuple[str, ...] = ()
    mood: tuple[str, ...] = ()
    polarity: str = "neutral"
    scope: str = "general"
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["post_types"] = list(self.post_types)
        data["topics"] = list(self.topics)
        data["mood"] = list(self.mood)
        data["metadata"] = self.metadata or {}
        return data

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "StyleMemoryRecord":
        return cls(
            record_id=_required_text(data, "record_id"),
            source_type=_required_text(data, "source_type"),
            title=_required_text(data, "title"),
            text=_required_text(data, "text"),
            source=_required_text(data, "source"),
            platform=_optional_text(data.get("platform")),
            post_types=tuple(_normalize_token_list(data.get("post_types"))),
            topics=tuple(_normalize_token_list(data.get("topics"))),
            mood=tuple(_normalize_token_list(data.get("mood"))),
            polarity=_normalize_token(str(data.get("polarity") or "neutral")),
            scope=_normalize_token(str(data.get("scope") or "general")),
            metadata=data.get("metadata") if isinstance(data.get("metadata"), dict) else {},
        )

    def search_text(self) -> str:
        fields = [
            self.title,
            self.text,
            self.source_type,
            self.platform or "",
            " ".join(self.post_types),
            " ".join(self.topics),
            " ".join(self.mood),
            self.polarity,
            self.scope,
        ]
        if self.metadata:
            fields.extend(str(value) for value in self.metadata.values())
        return " ".join(fields)


@dataclass(frozen=True)
class StyleMemoryIndex:
    records: tuple[StyleMemoryRecord, ...]
    created_at: str
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        source_type_counts = Counter(record.source_type for record in self.records)
        platform_counts = Counter(record.platform or "general" for record in self.records)
        return {
            "schema_version": self.schema_version,
            "created_at": self.created_at,
            "stats": {
                "record_count": len(self.records),
                "source_type_counts": dict(sorted(source_type_counts.items())),
                "platform_counts": dict(sorted(platform_counts.items())),
                "vocabulary_size": len(index_vocabulary(self.records)),
            },
            "records": [record.to_dict() for record in self.records],
        }

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "StyleMemoryIndex":
        schema_version = int(data.get("schema_version") or 0)
        if schema_version != SCHEMA_VERSION:
            raise ValueError(f"unsupported style-memory schema_version: {schema_version}")
        records = tuple(
            StyleMemoryRecord.from_mapping(item)
            for item in data.get("records", [])
            if isinstance(item, dict)
        )
        return cls(
            schema_version=schema_version,
            created_at=_required_text(data, "created_at"),
            records=records,
        )


@dataclass(frozen=True)
class StyleMemoryQuery:
    text: str
    platform: str | None = None
    post_type: str | None = None
    topics: tuple[str, ...] = ()
    mood: tuple[str, ...] = ()
    source_types: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "StyleMemoryQuery":
        return cls(
            text=_required_text(data, "text"),
            platform=_optional_token(data.get("platform")),
            post_type=_optional_token(data.get("post_type")),
            topics=tuple(_normalize_token_list(data.get("topics"))),
            mood=tuple(_normalize_token_list(data.get("mood"))),
            source_types=tuple(_normalize_token_list(data.get("source_types"))),
        )

    def to_search_text(self) -> str:
        return " ".join(
            [
                self.text,
                self.platform or "",
                self.post_type or "",
                " ".join(self.topics),
                " ".join(self.mood),
            ]
        )


@dataclass(frozen=True)
class StyleMemoryMatch:
    record: StyleMemoryRecord
    score: float
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "record": self.record.to_dict(),
            "score": round(self.score, 4),
            "reasons": list(self.reasons),
        }

    def to_prompt_block(self) -> str:
        metadata = [
            f"- source_type: {self.record.source_type}",
            f"- polarity: {self.record.polarity}",
            f"- scope: {self.record.scope}",
            f"- source: {self.record.source}",
        ]
        if self.record.platform:
            metadata.append(f"- platform: {self.record.platform}")
        if self.record.post_types:
            metadata.append(f"- post_type: {', '.join(self.record.post_types)}")
        if self.record.topics:
            metadata.append(f"- topics: {', '.join(self.record.topics)}")
        if self.reasons:
            metadata.append(f"- retrieval_reasons: {', '.join(self.reasons)}")
        return "\n".join(
            [
                f"### {self.record.record_id} - {self.record.title}",
                *metadata,
                "",
                self.record.text.strip(),
            ]
        ).strip()


def build_style_memory_index(
    *,
    root: Path | None = None,
    reference_entries: Sequence[Any] = (),
    feedback_dirs: Sequence[str | Path] | None = None,
) -> StyleMemoryIndex:
    base = root or repo_root()
    records: list[StyleMemoryRecord] = []
    records.extend(records_from_reference_entries(reference_entries))
    records.extend(records_from_voice_docs(base))
    records.extend(records_from_feedback_dirs(base, feedback_dirs))
    deduped = dedupe_records(records)
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return StyleMemoryIndex(
        created_at=created_at.replace("+00:00", "Z"),
        records=tuple(deduped),
    )


def records_from_reference_entries(
    entries: Sequence[Any],
) -> list[StyleMemoryRecord]:
    records: list[StyleMemoryRecord] = []
    for entry in entries:
        ref_id = str(getattr(entry, "ref_id", "")).strip()
        if not ref_id:
            continue
        text_parts = [
            str(getattr(entry, "representative_text", "")).strip(),
            f"Best for: {getattr(entry, 'best_for', '')}".strip(),
            f"Watch out: {getattr(entry, 'watch_out', '')}".strip(),
        ]
        text = "\n".join(part for part in text_parts if part and part != "Best for:" and part != "Watch out:")
        if not text:
            continue
        records.append(
            StyleMemoryRecord(
                record_id=f"reference:{ref_id}",
                source_type="reference_example",
                title=str(getattr(entry, "title", ref_id)).strip() or ref_id,
                text=text,
                source=str(getattr(entry, "source", "")) or "docs/10-reference-library.md",
                platform=_optional_token(getattr(entry, "platform", None)),
                post_types=tuple(_normalize_token_list(getattr(entry, "post_types", ()))),
                topics=tuple(_normalize_token_list(getattr(entry, "topics", ()))),
                mood=tuple(_normalize_token_list(getattr(entry, "moods", ()))),
                polarity="positive",
                scope="platform",
                metadata={
                    "ref_id": ref_id,
                    "published_at": str(getattr(entry, "published_at", "")),
                },
            )
        )
    return records


def records_from_voice_docs(root: Path) -> list[StyleMemoryRecord]:
    records: list[StyleMemoryRecord] = []
    for rel_path, source_type, polarity, scope in STYLE_MEMORY_DOCS:
        path = root / rel_path
        if not path.exists():
            continue
        for index, chunk in enumerate(markdown_chunks(path.read_text(encoding="utf-8"))):
            text = chunk["text"].strip()
            if not text or len(_text_tokens(text)) < 8:
                continue
            record_id = f"doc:{rel_path}:{index + 1}"
            platform = platform_from_text(chunk["title"] + " " + text)
            records.append(
                StyleMemoryRecord(
                    record_id=record_id,
                    source_type=source_type,
                    title=chunk["title"],
                    text=text,
                    source=rel_path,
                    platform=platform,
                    polarity=polarity,
                    scope=scope,
                    metadata={"heading_level": chunk["level"]},
                )
            )
    return records


def records_from_feedback_dirs(
    root: Path,
    feedback_dirs: Sequence[str | Path] | None = None,
) -> list[StyleMemoryRecord]:
    dirs = DEFAULT_FEEDBACK_DIRS if feedback_dirs is None else feedback_dirs
    records: list[StyleMemoryRecord] = []
    for raw_dir in feedback_raw_dirs(root, dirs):
        for path in sorted(raw_dir.glob("*.json")):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            records.extend(records_from_feedback_record(record, source_path=path))
    return records


def records_from_feedback_record(
    record: dict[str, Any],
    *,
    source_path: Path,
) -> list[StyleMemoryRecord]:
    feedback_id = str(record.get("id") or source_path.stem).strip()
    platform = _optional_token(record.get("platform"))
    request = record.get("request") if isinstance(record.get("request"), dict) else {}
    classification = (
        record.get("classification") if isinstance(record.get("classification"), dict) else {}
    )
    topics = tuple(_normalize_token_list(classification.get("topics")))
    mood = tuple(_normalize_token_list(classification.get("mood")))
    post_type = _optional_token(classification.get("post_type"))
    source = str(source_path)
    source_data = record.get("source") if isinstance(record.get("source"), dict) else {}
    title_seed = str(request.get("angle") or feedback_id).strip()

    records: list[StyleMemoryRecord] = []
    final_text = str(record.get("final_text") or "").strip()
    if final_text:
        records.append(
            StyleMemoryRecord(
                record_id=f"feedback:{feedback_id}:final",
                source_type="feedback_final",
                title=f"Final version: {title_seed}",
                text=final_text,
                source=source,
                platform=platform,
                post_types=(post_type,) if post_type else (),
                topics=topics,
                mood=mood,
                polarity="positive",
                scope="platform",
                metadata={
                    "feedback_id": feedback_id,
                    "created_at": str(record.get("created_at") or ""),
                    "draft_artifact_path": str(source_data.get("draft_artifact_path") or ""),
                },
            )
        )

    corrections = _normalize_token_list(classification.get("tone_corrections"))
    structural_notes = _string_list(classification.get("structural_notes"))
    if corrections or structural_notes:
        text = "\n".join(
            [
                "Tone corrections: " + ", ".join(corrections),
                "Structural notes: " + "; ".join(structural_notes),
            ]
        ).strip()
        records.append(
            StyleMemoryRecord(
                record_id=f"feedback:{feedback_id}:corrections",
                source_type="feedback_correction",
                title=f"Correction signal: {title_seed}",
                text=text,
                source=source,
                platform=platform,
                post_types=(post_type,) if post_type else (),
                topics=topics,
                mood=mood,
                polarity="corrective",
                scope="platform",
                metadata={"feedback_id": feedback_id},
            )
        )

    return records


def feedback_raw_dirs(root: Path, dirs: Sequence[str | Path]) -> list[Path]:
    resolved = []
    for item in dirs:
        path = Path(item).expanduser()
        if not path.is_absolute():
            path = root / path
        raw_dir = path / "raw" if path.name != "raw" else path
        if raw_dir.exists():
            resolved.append(raw_dir)
    return resolved


def dedupe_records(records: Iterable[StyleMemoryRecord]) -> list[StyleMemoryRecord]:
    seen: set[str] = set()
    deduped = []
    for record in records:
        if record.record_id in seen:
            continue
        seen.add(record.record_id)
        deduped.append(record)
    return deduped


def save_style_memory_index(index: StyleMemoryIndex, path: str | Path) -> Path:
    output_path = Path(path).expanduser()
    if not output_path.is_absolute():
        output_path = repo_root() / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(index.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def load_style_memory_index(path: str | Path = DEFAULT_STYLE_INDEX_PATH) -> StyleMemoryIndex:
    index_path = Path(path).expanduser()
    if not index_path.is_absolute():
        index_path = repo_root() / index_path
    return StyleMemoryIndex.from_mapping(json.loads(index_path.read_text(encoding="utf-8")))


def retrieve_style_memory(
    index: StyleMemoryIndex,
    query: StyleMemoryQuery,
    *,
    limit: int = 8,
) -> tuple[StyleMemoryMatch, ...]:
    if limit <= 0:
        return ()
    candidates = [
        record
        for record in index.records
        if not query.source_types or record.source_type in query.source_types
    ]
    if not candidates:
        return ()

    idf = inverse_document_frequency(candidates)
    query_tokens = _token_counts(query.to_search_text())
    query_vector = weighted_vector(query_tokens, idf)

    matches = []
    for record in candidates:
        record_vector = weighted_vector(_token_counts(record.search_text()), idf)
        score = cosine_similarity(query_vector, record_vector) * 100
        reasons: list[str] = []

        if query.platform and record.platform == query.platform:
            score += 8
            reasons.append("platform")
        elif query.platform and record.platform is None:
            score += 2
            reasons.append("general")

        if query.post_type and query.post_type in record.post_types:
            score += 6
            reasons.append("post_type")
        topic_hits = sorted(set(query.topics).intersection(record.topics))
        if topic_hits:
            score += 4 * len(topic_hits)
            reasons.append("topics:" + ",".join(topic_hits))
        mood_hits = sorted(set(query.mood).intersection(record.mood))
        if mood_hits:
            score += 3 * len(mood_hits)
            reasons.append("mood:" + ",".join(mood_hits))
        if record.source_type == "feedback_final":
            score += 2
            reasons.append("feedback_final")
        elif record.source_type == "reference_example":
            score += 1
            reasons.append("reference_example")
        if record.polarity == "corrective":
            reasons.append("corrective_signal")

        if score > 0:
            matches.append(StyleMemoryMatch(record=record, score=score, reasons=tuple(reasons)))

    matches.sort(key=lambda item: (-item.score, item.record.record_id))
    return tuple(matches[:limit])


def style_memory_query_from_request(request: Any) -> StyleMemoryQuery:
    text_parts = [
        str(getattr(request, "angle", "")).strip(),
        str(getattr(request, "source_notes", "")).strip(),
        " ".join(str(item) for item in getattr(request, "constraints", ()) or ()),
        str(getattr(request, "call_to_action", "") or "").strip(),
    ]
    return StyleMemoryQuery(
        text="\n".join(part for part in text_parts if part),
        platform=_optional_token(getattr(request, "platform", None)),
        post_type=_optional_token(getattr(request, "post_type", None)),
        topics=tuple(_normalize_token_list(getattr(request, "topics", ()))),
        mood=tuple(_normalize_token_list(getattr(request, "mood", ()))),
    )


def index_vocabulary(records: Sequence[StyleMemoryRecord]) -> set[str]:
    vocabulary: set[str] = set()
    for record in records:
        vocabulary.update(_text_tokens(record.search_text()))
    return vocabulary


def inverse_document_frequency(records: Sequence[StyleMemoryRecord]) -> dict[str, float]:
    document_frequency: Counter[str] = Counter()
    for record in records:
        document_frequency.update(set(_text_tokens(record.search_text())))
    total = len(records)
    return {
        token: math.log((total + 1) / (count + 1)) + 1
        for token, count in document_frequency.items()
    }


def weighted_vector(
    token_counts: Counter[str],
    idf: dict[str, float],
) -> dict[str, float]:
    return {
        token: count * idf.get(token, 1.0)
        for token, count in token_counts.items()
    }


def cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(weight * right.get(token, 0.0) for token, weight in left.items())
    left_norm = math.sqrt(sum(weight * weight for weight in left.values()))
    right_norm = math.sqrt(sum(weight * weight for weight in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def markdown_chunks(markdown: str) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    current_title = "Document"
    current_level = 1
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_lines
        text = "\n".join(current_lines).strip()
        if text:
            chunks.append(
                {
                    "title": current_title,
                    "level": current_level,
                    "text": text,
                }
            )
        current_lines = []

    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            marker, _, title = stripped.partition(" ")
            if marker and all(char == "#" for char in marker):
                flush()
                current_title = title.strip() or "Untitled"
                current_level = len(marker)
                continue
        current_lines.append(line)
    flush()
    return chunks


def platform_from_text(text: str) -> str | None:
    tokens = _text_tokens(text)
    for platform in ("telegram", "threads", "linkedin"):
        if platform in tokens:
            return platform
    return None


def _token_counts(text: str) -> Counter[str]:
    return Counter(_text_tokens(text))


def _text_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    current: list[str] = []
    for char in text.casefold().replace("-", "_"):
        if char.isalnum() or char == "_":
            current.append(char)
        elif current:
            token = "".join(current).strip("_")
            if len(token) >= 3:
                tokens.append(token)
            current = []
    if current:
        token = "".join(current).strip("_")
        if len(token) >= 3:
            tokens.append(token)
    return tokens


def _required_text(data: dict[str, Any], key: str) -> str:
    value = _optional_text(data.get(key))
    if not value:
        raise ValueError(f"{key} is required")
    return value


def _optional_text(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _optional_token(value: Any) -> str | None:
    text = _optional_text(value)
    return _normalize_token(text) if text else None


def _normalize_token(value: str) -> str:
    return "_".join(part for part in value.strip().casefold().replace("-", " ").split())


def _normalize_token_list(value: Any) -> list[str]:
    return [_normalize_token(item) for item in _string_list(value)]


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw = value.split(",") if "," in value else [value]
    elif isinstance(value, (list, tuple, set)):
        raw = list(value)
    else:
        raw = [value]
    return [str(item).strip() for item in raw if str(item).strip()]
