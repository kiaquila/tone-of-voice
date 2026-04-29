from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
# NOTE: sys.path shim is intentional here — check_feature_memory.py is a
# standalone script, not an installed package module. This is the only
# remaining shim after the src-layout migration.
sys.path.insert(0, str(SCRIPTS_DIR))

import check_feature_memory as cfm


class IsProductPathTest(unittest.TestCase):
    def test_tracked_prefixes(self) -> None:
        self.assertTrue(cfm.is_product_path("src/tone_of_voice/foo.py"))
        self.assertTrue(cfm.is_product_path("scripts/build_telegram_metrics.py"))
        self.assertTrue(cfm.is_product_path("tests/test_metrics.py"))
        self.assertTrue(cfm.is_product_path(".github/workflows/pr-guard.yml"))
        self.assertTrue(cfm.is_product_path("evals/regression/step4-seed.json"))

    def test_tracked_files(self) -> None:
        self.assertTrue(cfm.is_product_path("requirements.txt"))
        self.assertTrue(cfm.is_product_path("requirements-dev.txt"))
        self.assertTrue(cfm.is_product_path("pyproject.toml"))
        self.assertTrue(cfm.is_product_path("README.md"))

    def test_untracked_paths(self) -> None:
        self.assertFalse(cfm.is_product_path("docs/05-roadmap.md"))
        self.assertFalse(cfm.is_product_path("AGENTS.md"))
        self.assertFalse(cfm.is_product_path("specs/001-x/spec.md"))


class FeatureIdsTest(unittest.TestCase):
    def test_extracts_feature_id_from_specs_path(self) -> None:
        ids = cfm.feature_ids(
            [
                "specs/001-telegram-foundation/spec.md",
                "specs/004-quality-fixes/plan.md",
                "src/tone_of_voice/metrics.py",
            ]
        )
        self.assertEqual(ids, {"001-telegram-foundation", "004-quality-fixes"})

    def test_ignores_non_specs_paths(self) -> None:
        self.assertEqual(cfm.feature_ids(["docs/05-roadmap.md", "src/foo.py"]), set())


class WorktreeChangedFilesTest(unittest.TestCase):
    def setUp(self) -> None:
        self._cwd = Path.cwd()

    def tearDown(self) -> None:
        os.chdir(self._cwd)

    @staticmethod
    def _git(*args: str) -> None:
        subprocess.run(["git", *args], check=True, capture_output=True)

    def test_includes_untracked_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            os.chdir(td)
            self._git("init", "-q", "-b", "main")
            self._git("config", "user.email", "test@example.com")
            self._git("config", "user.name", "Test")
            Path("README.md").write_text("before", encoding="utf-8")
            self._git("add", "README.md")
            self._git("commit", "-q", "-m", "fixture")

            Path("README.md").write_text("after", encoding="utf-8")
            Path("evals/regression").mkdir(parents=True)
            Path("evals/regression/new.json").write_text("{}", encoding="utf-8")

            self.assertEqual(
                cfm.git_changed_files_in_worktree(),
                ["README.md", "evals/regression/new.json"],
            )


class HasCompleteFeatureMemoryTest(unittest.TestCase):
    # WARNING: these tests use os.chdir and are NOT safe for parallel execution
    # (e.g., pytest-xdist). Run with a single worker when using parallelism.
    #
    # The function under test resolves files via `git cat-file -e <ref>:<path>`,
    # so each test must commit its fixture files into a temp git repo.

    def setUp(self) -> None:
        self._cwd = Path.cwd()

    def tearDown(self) -> None:
        os.chdir(self._cwd)

    @staticmethod
    def _git(*args: str) -> None:
        subprocess.run(["git", *args], check=True, capture_output=True)

    def _init_repo_with(self, files: dict[str, str]) -> None:
        self._git("init", "-q", "-b", "main")
        self._git("config", "user.email", "test@example.com")
        self._git("config", "user.name", "Test")
        for rel, body in files.items():
            path = Path(rel)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
        self._git("add", ".")
        self._git("commit", "-q", "-m", "fixture")

    def test_complete_when_all_three_files_exist(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            os.chdir(td)
            self._init_repo_with(
                {
                    "specs/099-demo/spec.md": "ok",
                    "specs/099-demo/plan.md": "ok",
                    "specs/099-demo/tasks.md": "ok",
                }
            )
            self.assertTrue(cfm.has_complete_feature_memory("099-demo"))

    def test_incomplete_when_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            os.chdir(td)
            self._init_repo_with({"specs/099-demo/spec.md": "ok"})
            self.assertFalse(cfm.has_complete_feature_memory("099-demo"))

    def test_worktree_mode_sees_uncommitted_files(self) -> None:
        # `--worktree` mode is meant to inspect dirty worktree state, so it
        # must succeed for files that exist on disk even when they are not
        # yet committed (or there is no git repo at all).
        with tempfile.TemporaryDirectory() as td:
            os.chdir(td)
            base = Path("specs/099-demo")
            base.mkdir(parents=True)
            for name in ("spec.md", "plan.md", "tasks.md"):
                (base / name).write_text("ok", encoding="utf-8")
            self.assertTrue(
                cfm.has_complete_feature_memory("099-demo", use_worktree=True)
            )

    def test_worktree_mode_incomplete_when_file_missing_on_disk(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            os.chdir(td)
            base = Path("specs/099-demo")
            base.mkdir(parents=True)
            (base / "spec.md").write_text("ok", encoding="utf-8")
            self.assertFalse(
                cfm.has_complete_feature_memory("099-demo", use_worktree=True)
            )


class ParseArgsTest(unittest.TestCase):
    def test_defaults(self) -> None:
        args = cfm.parse_args([])
        self.assertEqual(args.base_ref, "origin/main")
        self.assertEqual(args.head_ref, "HEAD")
        self.assertFalse(args.worktree)

    def test_worktree_flag_independent_of_position(self) -> None:
        args = cfm.parse_args(["--worktree", "main", "feature"])
        self.assertTrue(args.worktree)
        self.assertEqual(args.base_ref, "main")
        self.assertEqual(args.head_ref, "feature")

        args = cfm.parse_args(["main", "--worktree", "feature"])
        self.assertTrue(args.worktree)
        self.assertEqual(args.base_ref, "main")
        self.assertEqual(args.head_ref, "feature")


if __name__ == "__main__":
    unittest.main()
