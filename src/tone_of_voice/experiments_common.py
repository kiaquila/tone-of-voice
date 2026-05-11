from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tone_of_voice.config import repo_root


SCHEMA_VERSION = 1


def resolve_repo_path(
    path: str | Path,
    *,
    root: Path | None = None,
    label: str = "path",
) -> Path:
    base = (root or repo_root()).resolve()
    raw_path = Path(path).expanduser()
    candidate = raw_path if raw_path.is_absolute() else base / raw_path
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise ValueError(f"{label} must stay inside the repository: {path}") from exc
    return resolved


def load_json_suite(
    path: str | Path,
    *,
    root: Path | None = None,
    label: str = "suite",
) -> dict[str, Any]:
    suite_path = resolve_repo_path(path, root=root, label=label)
    return json.loads(suite_path.read_text(encoding="utf-8"))


def write_json_output(
    path: str | Path,
    result: dict[str, Any],
    *,
    root: Path | None = None,
) -> Path:
    output_path = resolve_repo_path(path, root=root, label="json output")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def required_mapping(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} is required")
    return value


def required_text(data: dict[str, Any], key: str) -> str:
    value = optional_text(data.get(key))
    if not value:
        raise ValueError(f"{key} is required")
    return value


def optional_text(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def string_list(
    value: Any,
    *,
    default: tuple[str, ...] = (),
) -> list[str]:
    if value is None:
        return list(default)
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple)):
        values = list(value)
    else:
        values = [value]
    return [str(item).strip() for item in values if str(item).strip()]
