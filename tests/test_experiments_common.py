from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tone_of_voice.config import repo_root
from tone_of_voice.experiments_common import (
    load_json_suite,
    resolve_repo_path,
    write_json_output,
)


class ExperimentsCommonTest(unittest.TestCase):
    def test_resolve_repo_path_rejects_parent_escape(self) -> None:
        with self.assertRaises(ValueError):
            resolve_repo_path("../outside.json", root=repo_root(), label="suite")

    def test_resolve_repo_path_allows_repo_local_absolute_path(self) -> None:
        root = repo_root()
        path = resolve_repo_path(
            root / "evals/regression/step4-seed.json",
            root=root,
            label="suite",
        )

        self.assertEqual(path, (root / "evals/regression/step4-seed.json").resolve())

    def test_json_helpers_stay_inside_repo(self) -> None:
        root = repo_root()
        with tempfile.TemporaryDirectory(dir=root) as tmp_dir:
            output_path = Path(tmp_dir) / "result.json"

            written = write_json_output(output_path, {"passed": True}, root=root)
            loaded = load_json_suite(written, root=root, label="result")

        self.assertEqual(loaded, {"passed": True})

    def test_write_json_output_rejects_parent_escape(self) -> None:
        with self.assertRaises(ValueError):
            write_json_output("../outside.json", {"passed": True}, root=repo_root())


if __name__ == "__main__":
    unittest.main()
