from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_env_candidates() -> list[Path]:
    root = repo_root()
    candidates = [root / ".env"]

    fallback = (os.getenv("TONE_OF_VOICE_FALLBACK_ENV") or "").strip()
    if not fallback:
        return candidates

    if Path(fallback).is_absolute():
        fallback_path = Path(fallback)
    else:
        fallback_path = (root / fallback).resolve()

    # Confine *relative* paths to the parent directory tree to prevent traversal
    # (e.g. "../../etc/passwd"). Absolute paths are accepted as explicitly configured.
    if not Path(fallback).is_absolute():
        allowed_root = root.parent.resolve()
        if not fallback_path.is_relative_to(allowed_root):
            raise ValueError(
                f"TONE_OF_VOICE_FALLBACK_ENV resolved to {fallback_path}, "
                f"which is outside the allowed root {allowed_root}"
            )

    if fallback_path != (root / ".env").resolve():
        candidates.append(fallback_path)

    return candidates


def load_project_env(explicit_env_file: str | None = None) -> Path | None:
    if explicit_env_file:
        env_path = Path(explicit_env_file).expanduser().resolve()
        if not env_path.exists():
            raise FileNotFoundError(f"Env file not found: {env_path}")
        load_dotenv(env_path, override=False)
        return env_path

    for candidate in default_env_candidates():
        if candidate.exists():
            load_dotenv(candidate, override=False)
            return candidate

    return None


def resolve_session_stem(
    session_name: str | None = None,
    session_dir: str | None = None,
) -> str:
    name = session_name or os.getenv("TELEGRAM_SESSION_NAME", "telegram_session")

    if session_dir:
        return str(Path(session_dir).expanduser().resolve() / name)

    return str(repo_root() / name)
