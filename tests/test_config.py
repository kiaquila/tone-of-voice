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

    def test_warns_when_legacy_session_exists_without_explicit_name(self) -> None:
        import io
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            session_dir = Path(td)
            (session_dir / "legacy_session.session").touch()
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("TELEGRAM_SESSION_NAME", None)
                with mock.patch.object(config, "repo_root", return_value=session_dir):
                    captured = io.StringIO()
                    with mock.patch("sys.stderr", captured):
                        config.resolve_session_stem()
                    output = captured.getvalue()
        self.assertIn("legacy_session", output)
        self.assertIn("TELEGRAM_SESSION_NAME", output)

    def test_no_warning_when_explicit_name_is_provided(self) -> None:
        import io
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            session_dir = Path(td)
            (session_dir / "legacy_session.session").touch()
            with mock.patch.dict(
                os.environ, {"TELEGRAM_SESSION_NAME": "explicit"}, clear=False
            ):
                with mock.patch.object(config, "repo_root", return_value=session_dir):
                    captured = io.StringIO()
                    with mock.patch("sys.stderr", captured):
                        config.resolve_session_stem()
                    self.assertEqual(captured.getvalue(), "")


class LoadProjectEnvTest(unittest.TestCase):
    def test_explicit_missing_file_raises(self) -> None:
        # Use a path inside the allowed root (repo's parent tree) so the
        # security guard does not pre-empt the FileNotFoundError. This
        # test specifically exercises the "exists?" branch, not the
        # path-confinement branch (covered in test_cli_path_hardening.py).
        missing_path = config.repo_root() / "tests" / ".env.absent.does.not.exist"
        with self.assertRaises(FileNotFoundError):
            config.load_project_env(str(missing_path))

    def test_explicit_existing_file_loads(self) -> None:
        import tempfile

        # Place the env file inside the repo root, which is within the
        # allowed root (repo's parent tree). A temp dir under /var/folders
        # would be outside the allowed root and rejected by the new
        # security guard.
        with tempfile.TemporaryDirectory(dir=config.repo_root()) as td:
            env_file = Path(td) / "custom.env"
            env_file.write_text("TONE_OF_VOICE_TEST_FLAG=ok\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("TONE_OF_VOICE_TEST_FLAG", None)
                resolved = config.load_project_env(str(env_file))
                self.assertEqual(resolved, env_file.resolve())
                self.assertEqual(os.environ.get("TONE_OF_VOICE_TEST_FLAG"), "ok")

    def test_explicit_env_file_outside_allowed_root_raises(self) -> None:
        import tempfile

        # A path under /var/folders is outside both the repo and its
        # parent tree — must fail closed with ValueError, even if the
        # file itself exists.
        with tempfile.TemporaryDirectory() as td:
            outside_env = Path(td) / "external.env"
            outside_env.write_text(
                "TONE_OF_VOICE_TEST_FLAG=leaked\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError) as ctx:
                config.load_project_env(str(outside_env))
            self.assertIn("outside the allowed root", str(ctx.exception))


class DefaultEnvCandidatesTest(unittest.TestCase):
    def test_without_fallback_env_only_uses_repo_dot_env(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TONE_OF_VOICE_FALLBACK_ENV", None)
            candidates = config.default_env_candidates()
        self.assertEqual(candidates, [config.repo_root() / ".env"])

    def test_first_candidate_is_repo_dot_env(self) -> None:
        candidates = config.default_env_candidates()
        self.assertEqual(candidates[0], config.repo_root() / ".env")

    def test_fallback_env_var_overrides_default(self) -> None:
        # Pick an absolute path that lives under the allowed root
        # (repo's parent tree). The previous version of this test used
        # /tmp/alt.env, which is outside the new boundary applied to
        # absolute paths too (closes Codex P2).
        parent_env = (config.repo_root().parent / "alt.env").resolve()
        with mock.patch.dict(
            os.environ,
            {"TONE_OF_VOICE_FALLBACK_ENV": str(parent_env)},
            clear=False,
        ):
            candidates = config.default_env_candidates()
        self.assertIn(parent_env, candidates)

    def test_relative_traversal_outside_parent_raises(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"TONE_OF_VOICE_FALLBACK_ENV": "../../../../etc/passwd"},
            clear=False,
        ):
            with self.assertRaises(ValueError):
                config.default_env_candidates()

    def test_absolute_path_outside_allowed_root_raises(self) -> None:
        # The new boundary rejects absolute paths outside the parent
        # tree as well — without this guard, TONE_OF_VOICE_FALLBACK_ENV
        # could redirect dotenv loading to e.g. /tmp/malicious.env and
        # inject secrets into the CLIs.
        with mock.patch.dict(
            os.environ,
            {"TONE_OF_VOICE_FALLBACK_ENV": "/tmp/outside-allowed-root.env"},
            clear=False,
        ):
            with self.assertRaises(ValueError) as ctx:
                config.default_env_candidates()
            self.assertIn("outside the allowed root", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
