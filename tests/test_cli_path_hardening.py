from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tone_of_voice.config import repo_root


class CliPathHardeningTest(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, *args],
            cwd=repo_root(),
            text=True,
            capture_output=True,
            check=False,
        )

    def assert_path_error(
        self,
        result: subprocess.CompletedProcess[str],
        label: str,
    ) -> None:
        self.assertEqual(result.returncode, 2, result.stderr or result.stdout)
        self.assertIn(f"{label} must stay inside the repository", result.stderr)

    def test_draft_post_rejects_absolute_output_outside_repo(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            outside_output = Path(td) / "drafts"

            result = self.run_cli(
                "scripts/draft_post.py",
                "examples/draft-request.telegram.json",
                "--dry-run",
                "--output-dir",
                str(outside_output),
            )

            self.assert_path_error(result, "output dir")
            self.assertFalse(outside_output.exists())

    def test_build_style_memory_rejects_parent_output_escape(self) -> None:
        result = self.run_cli(
            "scripts/build_style_memory_index.py",
            "--output",
            "../outside-style-index.json",
        )

        self.assert_path_error(result, "style-memory output")

    def test_query_style_memory_rejects_request_symlink_escape(self) -> None:
        with tempfile.TemporaryDirectory(dir=repo_root()) as inside_dir:
            with tempfile.TemporaryDirectory() as outside_dir:
                outside = Path(outside_dir)
                request_path = outside / "request.json"
                request_path.write_text(
                    json.dumps(
                        {
                            "platform": "telegram",
                            "angle": "This request lives outside the repo",
                        }
                    ),
                    encoding="utf-8",
                )
                escape = Path(inside_dir) / "escape"
                os.symlink(outside, escape, target_is_directory=True)

                result = self.run_cli(
                    "scripts/query_style_memory.py",
                    "--request",
                    str(escape / "request.json"),
                    "--build",
                )

            self.assert_path_error(result, "draft request")

    def test_load_project_env_rejects_env_file_outside_allowed_root(self) -> None:
        # --env-file must be confined to the repo and its parent tree
        # (where the sibling vb-influencer repo lives). A path under
        # /tmp escapes both — load_project_env must refuse to load it.
        from tone_of_voice.config import load_project_env

        with tempfile.TemporaryDirectory() as td:
            outside_env = Path(td) / "malicious.env"
            outside_env.write_text("ANTHROPIC_API_KEY=stolen\n", encoding="utf-8")

            with self.assertRaises(ValueError) as ctx:
                load_project_env(str(outside_env))

            self.assertIn("--env-file resolved to", str(ctx.exception))
            self.assertIn("outside the allowed root", str(ctx.exception))

    def test_load_project_env_accepts_env_file_inside_repo(self) -> None:
        # A legitimate --env-file inside the repo loads without error.
        from tone_of_voice.config import load_project_env

        with tempfile.TemporaryDirectory(dir=repo_root()) as inside_dir:
            inside_env = Path(inside_dir) / "local.env"
            inside_env.write_text(
                "TONE_OF_VOICE_TEST_ENV_VAR=loaded\n",
                encoding="utf-8",
            )
            try:
                result = load_project_env(str(inside_env))
            finally:
                os.environ.pop("TONE_OF_VOICE_TEST_ENV_VAR", None)

            self.assertEqual(result, inside_env.resolve())

    def test_capture_feedback_rejects_embedded_artifact_outside_repo(self) -> None:
        with tempfile.TemporaryDirectory(dir=repo_root()) as inside_dir:
            with tempfile.TemporaryDirectory() as outside_dir:
                outside_artifact = Path(outside_dir) / "draft.json"
                outside_artifact.write_text(
                    json.dumps(
                        {
                            "draft": "draft text",
                            "request": {"platform": "telegram"},
                        }
                    ),
                    encoding="utf-8",
                )
                feedback_input = Path(inside_dir) / "feedback.json"
                feedback_input.write_text(
                    json.dumps(
                        {
                            "source_draft_artifact": str(outside_artifact),
                            "final_text": "final text",
                        }
                    ),
                    encoding="utf-8",
                )
                output_dir = Path(inside_dir) / "feedback-output"

                result = self.run_cli(
                    "scripts/capture_feedback.py",
                    str(feedback_input),
                    "--output-dir",
                    str(output_dir),
                )

            self.assert_path_error(result, "draft artifact")
            self.assertFalse(output_dir.exists())


if __name__ == "__main__":
    unittest.main()
