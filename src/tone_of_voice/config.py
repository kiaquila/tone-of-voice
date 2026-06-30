from __future__ import annotations

import os
import sys
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

    raw = Path(fallback)
    fallback_path = raw.resolve() if raw.is_absolute() else (root / raw).resolve()

    # Confine the ambient fallback to the repo and its parent directory tree
    # regardless of whether it was supplied as absolute or relative. Unlike
    # explicit `--env-file`, this env var can be inherited silently by many
    # CLIs, so it must not point at arbitrary host paths.
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
        # Explicit env files are the documented credential-file exception:
        # callers may point at a private secrets path outside the repository.
        # Ambient fallback discovery remains confined in default_env_candidates().
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
    explicit_name = session_name or os.getenv("TELEGRAM_SESSION_NAME") or None
    name = explicit_name or "telegram_session"

    if session_dir:
        return str(Path(session_dir).expanduser().resolve() / name)

    target_dir = repo_root()
    resolved = target_dir / name

    # The previous default session stem was renamed during anonymization.
    # When the caller has not opted in to a specific name and the new
    # default file is missing, surface any pre-existing session files so an
    # operator carrying over an authenticated session learns to pin
    # TELEGRAM_SESSION_NAME instead of silently starting a fresh login.
    if explicit_name is None and not resolved.with_suffix(".session").exists():
        try:
            legacy = sorted(
                p for p in target_dir.glob("*.session") if p.stem != name
            )
        except OSError:
            legacy = []
        if legacy:
            stems = ", ".join(p.stem for p in legacy)
            print(
                f"warning: resolve_session_stem: default session "
                f"{resolved}.session does not exist; found other session "
                f"file(s) in {target_dir} ({stems}). Set "
                f"TELEGRAM_SESSION_NAME or pass --session-name to choose "
                f"one explicitly.",
                file=sys.stderr,
            )

    return str(resolved)
