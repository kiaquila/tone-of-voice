from __future__ import annotations

import json
import re
import secrets
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Sequence

from tone_of_voice.config import repo_root
from tone_of_voice.drafting import ALLOWED_PLATFORMS
from tone_of_voice.metrics import EMOJI_PATTERN


SCHEMA_VERSION = 1
DEFAULT_FEEDBACK_DIR = "data/working/feedback"


@dataclass(frozen=True)
class FeedbackInput:
    platform: str
    draft_text: str
    final_text: str
    edited_text: str | None = None
    approved_draft_text: str | None = None
    source_draft_artifact: str | None = None
    request: dict[str, Any] | None = None
    post_type: str | None = None
    topics: tuple[str, ...] = ()
    mood: tuple[str, ...] = ()
    tone_corrections: tuple[str, ...] = ()
    structural_notes: tuple[str, ...] = ()
    notes: str | None = None
    published_url: str | None = None
    published_at: str | None = None

    @classmethod
    def from_mapping(
        cls,
        data: dict[str, Any],
        *,
        draft_artifact: dict[str, Any] | None = None,
        source_draft_artifact: str | None = None,
    ) -> "FeedbackInput":
        request = _dict_or_none(data.get("request"))
        artifact_request = _dict_or_none(draft_artifact.get("request")) if draft_artifact else None
        if artifact_request:
            request = {**artifact_request, **(request or {})}

        platform = _normalize_token(
            _first_text(
                data.get("platform"),
                request.get("platform") if request else None,
            )
        )
        if platform not in ALLOWED_PLATFORMS:
            allowed = ", ".join(sorted(ALLOWED_PLATFORMS))
            raise ValueError(f"platform must be one of: {allowed}")

        draft_text = _first_text(
            data.get("draft_text"),
            data.get("draft"),
            draft_artifact.get("draft") if draft_artifact else None,
        )
        if not draft_text:
            raise ValueError("draft_text is required unless source_draft_artifact contains draft")

        final_text = _first_text(data.get("final_text"), data.get("published_text"))
        if not final_text:
            raise ValueError("final_text is required")

        post_type = _optional_token(
            _first_text(data.get("post_type"), request.get("post_type") if request else None)
        )

        source_path = _first_text(
            source_draft_artifact,
            data.get("source_draft_artifact"),
        )

        return cls(
            platform=platform,
            draft_text=draft_text,
            final_text=final_text,
            edited_text=_optional_text(data.get("edited_text")),
            approved_draft_text=_optional_text(data.get("approved_draft_text")),
            source_draft_artifact=source_path or None,
            request=request,
            post_type=post_type,
            topics=tuple(
                _listify(
                    data.get("topics", request.get("topics") if request else ()),
                    normalize_tokens=True,
                )
            ),
            mood=tuple(
                _listify(
                    data.get("mood", request.get("mood") if request else ()),
                    normalize_tokens=True,
                )
            ),
            tone_corrections=tuple(
                _listify(data.get("tone_corrections"), normalize_tokens=True)
            ),
            structural_notes=tuple(_listify(data.get("structural_notes"))),
            notes=_optional_text(data.get("notes")),
            published_url=_optional_text(data.get("published_url")),
            published_at=_optional_text(data.get("published_at")),
        )


def load_feedback_input(
    path: str | Path,
    *,
    source_draft_artifact: str | Path | None = None,
) -> FeedbackInput:
    input_path = Path(path).expanduser().resolve()
    data = json.loads(input_path.read_text(encoding="utf-8"))
    artifact_path = _resolve_artifact_path(
        source_draft_artifact,
        data.get("source_draft_artifact"),
        base_dir=input_path.parent,
    )
    artifact = load_draft_artifact(artifact_path) if artifact_path else None
    return FeedbackInput.from_mapping(
        data,
        draft_artifact=artifact,
        source_draft_artifact=str(artifact_path) if artifact_path else None,
    )


def load_draft_artifact(path: str | Path) -> dict[str, Any]:
    artifact_path = Path(path).expanduser().resolve()
    return json.loads(artifact_path.read_text(encoding="utf-8"))


def build_feedback_record(
    feedback: FeedbackInput,
    *,
    created_at: datetime | None = None,
    record_id: str | None = None,
) -> dict[str, Any]:
    captured_at = (created_at or datetime.now(timezone.utc)).replace(microsecond=0)
    feedback_id = record_id or _feedback_id(feedback, captured_at)

    return {
        "schema_version": SCHEMA_VERSION,
        "id": feedback_id,
        "created_at": _format_utc(captured_at),
        "platform": feedback.platform,
        "source": {
            "draft_artifact_path": feedback.source_draft_artifact,
        },
        "request": feedback.request,
        "draft_text": feedback.draft_text,
        "approved_draft_text": feedback.approved_draft_text,
        "edited_text": feedback.edited_text,
        "final_text": feedback.final_text,
        "published": {
            "url": feedback.published_url,
            "published_at": feedback.published_at,
        },
        "classification": {
            "post_type": feedback.post_type,
            "topics": list(feedback.topics),
            "mood": list(feedback.mood),
            "tone_corrections": list(feedback.tone_corrections),
            "structural_notes": list(feedback.structural_notes),
        },
        "notes": feedback.notes,
    }


def build_feedback_analysis(record: dict[str, Any]) -> dict[str, Any]:
    comparisons: dict[str, Any] = {
        "draft_to_final": compute_revision_metrics(
            record["draft_text"],
            record["final_text"],
        )
    }
    if record.get("edited_text"):
        comparisons["draft_to_edited"] = compute_revision_metrics(
            record["draft_text"],
            record["edited_text"],
        )
        comparisons["edited_to_final"] = compute_revision_metrics(
            record["edited_text"],
            record["final_text"],
        )

    classification = record.get("classification") or {}
    return {
        "schema_version": SCHEMA_VERSION,
        "feedback_id": record["id"],
        "created_at": record["created_at"],
        "platform": record["platform"],
        "post_type": classification.get("post_type"),
        "topics": classification.get("topics") or [],
        "tone_corrections": classification.get("tone_corrections") or [],
        "structural_notes": classification.get("structural_notes") or [],
        "comparisons": comparisons,
    }


def write_feedback_pair(
    feedback: FeedbackInput,
    *,
    output_dir: str | Path = DEFAULT_FEEDBACK_DIR,
    created_at: datetime | None = None,
    record_id: str | None = None,
) -> tuple[Path, Path, dict[str, Any], dict[str, Any]]:
    record = build_feedback_record(
        feedback,
        created_at=created_at,
        record_id=record_id,
    )
    analysis = build_feedback_analysis(record)

    output_path = Path(output_dir).expanduser().resolve()
    raw_dir = output_path / "raw"
    analysis_dir = output_path / "analysis"
    raw_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir.mkdir(parents=True, exist_ok=True)

    raw_path = raw_dir / f"{record['id']}.json"
    analysis_path = analysis_dir / f"{record['id']}.json"
    raw_path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    analysis_path.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return raw_path, analysis_path, record, analysis


def compute_revision_metrics(before: str, after: str) -> dict[str, Any]:
    before_words = _word_tokens(before)
    after_words = _word_tokens(after)
    char_distance = levenshtein_distance(before, after)
    word_distance = levenshtein_distance(before_words, after_words)

    before_lines = _line_count(before)
    after_lines = _line_count(after)
    before_emoji = len(EMOJI_PATTERN.findall(before))
    after_emoji = len(EMOJI_PATTERN.findall(after))

    return {
        "before_chars": len(before),
        "after_chars": len(after),
        "char_delta": len(after) - len(before),
        "char_edit_distance": char_distance,
        "char_percent_changed": _percent_changed(char_distance, len(before), len(after)),
        "before_words": len(before_words),
        "after_words": len(after_words),
        "word_delta": len(after_words) - len(before_words),
        "word_edit_distance": word_distance,
        "word_percent_changed": _percent_changed(
            word_distance,
            len(before_words),
            len(after_words),
        ),
        "before_lines": before_lines,
        "after_lines": after_lines,
        "line_delta": after_lines - before_lines,
        "emoji_delta": after_emoji - before_emoji,
        "question_delta": after.count("?") - before.count("?"),
        "exclamation_delta": after.count("!") - before.count("!"),
    }


def levenshtein_distance(a: Sequence[Any], b: Sequence[Any]) -> int:
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)

    previous = list(range(len(b) + 1))
    for i, item_a in enumerate(a, start=1):
        current = [i]
        for j, item_b in enumerate(b, start=1):
            cost = 0 if item_a == item_b else 1
            current.append(
                min(
                    previous[j] + 1,
                    current[j - 1] + 1,
                    previous[j - 1] + cost,
                )
            )
        previous = current
    return previous[-1]


def load_feedback_analyses(feedback_dir: str | Path = DEFAULT_FEEDBACK_DIR) -> list[dict[str, Any]]:
    base = Path(feedback_dir).expanduser().resolve()
    analysis_dir = base / "analysis"
    if not analysis_dir.exists():
        return []
    analyses = []
    for path in sorted(analysis_dir.glob("*.json")):
        analyses.append(json.loads(path.read_text(encoding="utf-8")))
    return analyses


def summarize_feedback(
    analyses: list[dict[str, Any]],
    *,
    recent_limit: int = 10,
) -> dict[str, Any]:
    correction_counter: Counter[str] = Counter()
    platform_counter: Counter[str] = Counter()
    post_type_counter: Counter[str] = Counter()
    char_percentages: list[float] = []
    word_percentages: list[float] = []
    char_distances: list[int] = []
    word_distances: list[int] = []
    recent_records: list[dict[str, Any]] = []

    for analysis in analyses:
        platform_counter[analysis.get("platform") or "unknown"] += 1
        if analysis.get("post_type"):
            post_type_counter[analysis["post_type"]] += 1
        correction_counter.update(analysis.get("tone_corrections") or [])

        metrics = analysis["comparisons"]["draft_to_final"]
        char_percentages.append(metrics["char_percent_changed"])
        word_percentages.append(metrics["word_percent_changed"])
        char_distances.append(metrics["char_edit_distance"])
        word_distances.append(metrics["word_edit_distance"])
        recent_records.append(
            {
                "feedback_id": analysis["feedback_id"],
                "created_at": analysis["created_at"],
                "platform": analysis.get("platform"),
                "post_type": analysis.get("post_type"),
                "char_percent_changed": metrics["char_percent_changed"],
                "word_percent_changed": metrics["word_percent_changed"],
                "tone_corrections": analysis.get("tone_corrections") or [],
            }
        )

    recent_records.sort(key=lambda item: item["created_at"], reverse=True)
    created_values = [item["created_at"] for item in recent_records if item.get("created_at")]

    return {
        "total_pairs": len(analyses),
        "date_range": {
            "first": min(created_values) if created_values else None,
            "last": max(created_values) if created_values else None,
        },
        "platforms": dict(sorted(platform_counter.items())),
        "post_types": dict(sorted(post_type_counter.items())),
        "metrics": {
            "average_char_percent_changed": _mean(char_percentages),
            "median_char_percent_changed": _median(char_percentages),
            "average_word_percent_changed": _mean(word_percentages),
            "median_word_percent_changed": _median(word_percentages),
            "median_char_edit_distance": _median(char_distances),
            "median_word_edit_distance": _median(word_distances),
        },
        "tone_corrections": correction_counter.most_common(),
        "recent_records": recent_records[:recent_limit],
    }


def format_feedback_summary_markdown(summary: dict[str, Any]) -> str:
    metrics = summary["metrics"]
    lines = [
        "# Feedback Metrics",
        "",
        "## Corpus Snapshot",
        "",
        f"- Total draft/final pairs: {summary['total_pairs']}",
        f"- Date range: {summary['date_range']['first']} to {summary['date_range']['last']}",
        f"- Platforms: {_format_counter(summary['platforms'])}",
        f"- Post types: {_format_counter(summary['post_types'])}",
        "",
        "## Draft To Final Change",
        "",
        f"- Average character percent changed: {metrics['average_char_percent_changed']}",
        f"- Median character percent changed: {metrics['median_char_percent_changed']}",
        f"- Average word percent changed: {metrics['average_word_percent_changed']}",
        f"- Median word percent changed: {metrics['median_word_percent_changed']}",
        f"- Median character edit distance: {metrics['median_char_edit_distance']}",
        f"- Median word edit distance: {metrics['median_word_edit_distance']}",
        "",
        "## Common Tone Corrections",
        "",
    ]

    if summary["tone_corrections"]:
        lines.extend(
            f"- `{correction}` - {count}"
            for correction, count in summary["tone_corrections"]
        )
    else:
        lines.append("- None recorded yet.")

    lines.extend(["", "## Recent Records", ""])
    if summary["recent_records"]:
        for item in summary["recent_records"]:
            corrections = ", ".join(item["tone_corrections"]) or "no correction tags"
            lines.append(
                "- "
                f"`{item['feedback_id']}` "
                f"({item['platform']}, {item.get('post_type') or 'unknown'}): "
                f"{item['char_percent_changed']}% chars changed, "
                f"{item['word_percent_changed']}% words changed; "
                f"{corrections}"
            )
    else:
        lines.append("- No feedback records found.")

    lines.append("")
    return "\n".join(lines)


def read_feedback_input_from_stdin(
    *,
    source_draft_artifact: str | Path | None = None,
) -> FeedbackInput:
    import sys

    data = json.load(sys.stdin)
    artifact_path = source_draft_artifact or data.get("source_draft_artifact")
    artifact = load_draft_artifact(artifact_path) if artifact_path else None
    return FeedbackInput.from_mapping(
        data,
        draft_artifact=artifact,
        source_draft_artifact=str(artifact_path) if artifact_path else None,
    )


def repo_feedback_dir(root: Path | None = None) -> Path:
    return (root or repo_root()) / DEFAULT_FEEDBACK_DIR


def _word_tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-zА-Яа-яЁё0-9_]+", text.lower())


def _line_count(text: str) -> int:
    return 0 if not text else text.count("\n") + 1


def _percent_changed(distance: int, before_len: int, after_len: int) -> float:
    denominator = max(before_len, after_len)
    if denominator == 0:
        return 0.0
    return round((distance / denominator) * 100, 1)


def _mean(values: list[float] | list[int]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 1)


def _median(values: list[float] | list[int]) -> float:
    if not values:
        return 0.0
    return round(float(median(values)), 1)


def _first_text(*values: Any) -> str:
    for value in values:
        text = _optional_text(value)
        if text:
            return text
    return ""


def _optional_text(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _dict_or_none(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _resolve_artifact_path(
    explicit: str | Path | None,
    embedded: Any,
    *,
    base_dir: Path,
) -> Path | None:
    if explicit is not None:
        return Path(explicit).expanduser()
    if not embedded:
        return None
    embedded_path = Path(str(embedded)).expanduser()
    if embedded_path.is_absolute():
        return embedded_path
    return base_dir / embedded_path


def _normalize_token(value: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[\s\-]+", "_", value.strip().lower())).strip("_")


def _optional_token(value: Any) -> str | None:
    text = _optional_text(value)
    return _normalize_token(text) if text else None


def _listify(value: Any, *, normalize_tokens: bool = False) -> list[str]:
    if value is None:
        values: list[str] = []
    elif isinstance(value, str):
        values = [part.strip() for part in value.split(",")] if "," in value else [value.strip()]
    elif isinstance(value, (list, tuple)):
        values = [str(item).strip() for item in value if str(item).strip()]
    else:
        values = [str(value).strip()]
    values = [item for item in values if item]
    if normalize_tokens:
        return [_normalize_token(item) for item in values]
    return values


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _feedback_id(feedback: FeedbackInput, created_at: datetime) -> str:
    stamp = created_at.strftime("%Y%m%dT%H%M%SZ")
    seed = feedback.post_type or (feedback.request or {}).get("angle") or "feedback"
    slug = re.sub(r"[^a-z0-9]+", "-", str(seed).lower()).strip("-")[:40]
    if not slug:
        slug = "feedback"
    return f"{stamp}-{feedback.platform}-{slug}-{secrets.token_hex(3)}"


def _format_counter(values: dict[str, int]) -> str:
    if not values:
        return "none"
    return ", ".join(f"{key}={value}" for key, value in values.items())
