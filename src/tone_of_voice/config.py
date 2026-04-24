from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_env_candidates() -> list[Path]:
    root = repo_root()
    return [
        root / ".env",
        root.parent / "vb-influencer" / ".env",
    ]


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
    name = session_name or os.getenv("TELEGRAM_SESSION_NAME", "vb_influencer_session")

    if session_dir:
        return str(Path(session_dir).expanduser().resolve() / name)

    root = repo_root()
    sibling_repo = root.parent / "vb-influencer"
    sibling_session = sibling_repo / f"{name}.session"
    if sibling_session.exists():
        return str(sibling_repo / name)

    return str(root / name)
