from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest import mock

from tone_of_voice import config


class ResolveSessionStemTest(unittest.TestCase):
    def test_explicit_session_dir_wins(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TELEGRAM_SESSION_NAME", None)
            stem = config.resolve_session_stem(
                session_name="alpha",
                session_dir="/tmp/sessions",
            )
        self.assertEqual(stem, str(Path("/tmp/sessions/alpha").resolve()))

    def test_falls_back_to_repo_root(self) -> None:
        with mock.patch.dict(os.environ, {"TELEGRAM_SESSION_NAME": "betagamma"}, clear=False):
            stem = config.resolve_session_stem()
        self.assertTrue(stem.endswith("betagamma"))


class LoadProjectEnvTest(unittest.TestCase):
    def test_explicit_missing_file_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            config.load_project_env("/nonexistent/path/.env.absent")

    def test_explicit_existing_file_loads(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            env_file = Path(td) / "custom.env"
            env_file.write_text("TONE_OF_VOICE_TEST_FLAG=ok\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("TONE_OF_VOICE_TEST_FLAG", None)
                resolved = config.load_project_env(str(env_file))
                self.assertEqual(resolved, env_file.resolve())
                self.assertEqual(os.environ.get("TONE_OF_VOICE_TEST_FLAG"), "ok")


class DefaultEnvCandidatesTest(unittest.TestCase):
    def test_first_candidate_is_repo_dot_env(self) -> None:
        candidates = config.default_env_candidates()
        self.assertEqual(candidates[0], config.repo_root() / ".env")

    def test_fallback_env_var_overrides_default(self) -> None:
        with mock.patch.dict(
            os.environ, {"TONE_OF_VOICE_FALLBACK_ENV": "/tmp/alt.env"}, clear=False
        ):
            candidates = config.default_env_candidates()
        self.assertIn(Path("/tmp/alt.env"), candidates)


if __name__ == "__main__":
    unittest.main()
