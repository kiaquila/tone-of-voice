#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PRODUCT_PREFIXES = (
    "src/",
    "scripts/",
    "tests/",
    ".github/workflows/",
)
PRODUCT_FILES = {
    "requirements.txt",
}


def git_changed_files(base_ref: str, head_ref: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base_ref}...{head_ref}"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def git_changed_files_in_worktree() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def is_product_path(path: str) -> bool:
    return path in PRODUCT_FILES or path.startswith(PRODUCT_PREFIXES)


def feature_ids(changed_files: list[str]) -> set[str]:
    ids: set[str] = set()
    for path in changed_files:
        parts = Path(path).parts
        if len(parts) >= 3 and parts[0] == "specs":
            ids.add(parts[1])
    return ids


def has_complete_feature_memory(feature_id: str) -> bool:
    base = Path("specs") / feature_id
    required = ("spec.md", "plan.md", "tasks.md")
    return all((base / name).exists() for name in required)


def main() -> int:
    inspect_worktree = "--worktree" in sys.argv
    args = [arg for arg in sys.argv[1:] if arg != "--worktree"]
    base_ref = args[0] if len(args) > 0 else "origin/main"
    head_ref = args[1] if len(args) > 1 else "HEAD"
    changed_files = (
        git_changed_files_in_worktree()
        if inspect_worktree
        else git_changed_files(base_ref, head_ref)
    )

    if not any(is_product_path(path) for path in changed_files):
        print("No tracked product or workflow paths changed; feature-memory guard passes.")
        return 0

    ids = feature_ids(changed_files)
    valid = next((feature_id for feature_id in ids if has_complete_feature_memory(feature_id)), None)
    if valid:
        print(f"Feature-memory guard passed via specs/{valid}/")
        return 0

    print("Tracked product or workflow paths changed without a complete feature-memory update.", file=sys.stderr)
    print("Add specs/<feature-id>/spec.md, plan.md, and tasks.md in the same PR.", file=sys.stderr)
    if ids:
        print("Observed specs folders:", file=sys.stderr)
        for feature_id in sorted(ids):
            status = "complete" if has_complete_feature_memory(feature_id) else "incomplete"
            print(f"- {feature_id}: {status}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
