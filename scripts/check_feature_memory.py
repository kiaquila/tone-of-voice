#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
    "requirements-dev.txt",
    "pyproject.toml",
    "README.md",
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


def has_complete_feature_memory(
    feature_id: str,
    head_ref: str = "HEAD",
    *,
    use_worktree: bool = False,
) -> bool:
    required = ("spec.md", "plan.md", "tasks.md")
    if use_worktree:
        base = Path("specs") / feature_id
        return all((base / name).exists() for name in required)
    for name in required:
        result = subprocess.run(
            ["git", "cat-file", "-e", f"{head_ref}:specs/{feature_id}/{name}"],
            capture_output=True,
        )
        if result.returncode != 0:
            return False
    return True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify that PRs touching tracked product paths ship matching feature memory.",
    )
    parser.add_argument(
        "base_ref",
        nargs="?",
        default="origin/main",
        help="Base ref for the diff (defaults to origin/main).",
    )
    parser.add_argument(
        "head_ref",
        nargs="?",
        default="HEAD",
        help="Head ref for the diff (defaults to HEAD).",
    )
    parser.add_argument(
        "--worktree",
        action="store_true",
        help="Inspect the dirty worktree instead of a base...head diff.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    changed_files = (
        git_changed_files_in_worktree()
        if args.worktree
        else git_changed_files(args.base_ref, args.head_ref)
    )

    if not any(is_product_path(path) for path in changed_files):
        print("No tracked product or workflow paths changed; feature-memory guard passes.")
        return 0

    ids = feature_ids(changed_files)
    valid = next(
        (
            feature_id
            for feature_id in ids
            if has_complete_feature_memory(feature_id, args.head_ref, use_worktree=args.worktree)
        ),
        None,
    )
    if valid:
        print(f"Feature-memory guard passed via specs/{valid}/")
        return 0

    print("Tracked product or workflow paths changed without a complete feature-memory update.", file=sys.stderr)
    print("Add specs/<feature-id>/spec.md, plan.md, and tasks.md in the same PR.", file=sys.stderr)
    if ids:
        print("Observed specs folders:", file=sys.stderr)
        for feature_id in sorted(ids):
            status = (
                "complete"
                if has_complete_feature_memory(feature_id, args.head_ref, use_worktree=args.worktree)
                else "incomplete"
            )
            print(f"- {feature_id}: {status}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
