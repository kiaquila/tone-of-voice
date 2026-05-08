from __future__ import annotations

import argparse
import importlib.util
import sys
import unittest
from pathlib import Path


def _load_query_script():
    repo = Path(__file__).resolve().parents[1]
    script_path = repo / "scripts" / "query_style_memory.py"
    spec = importlib.util.spec_from_file_location("query_style_memory_script", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("query_style_memory_script", module)
    spec.loader.exec_module(module)
    return module


class BuildQueryNormalizationTest(unittest.TestCase):
    def test_request_mode_overrides_are_normalized(self) -> None:
        script = _load_query_script()
        repo = Path(__file__).resolve().parents[1]

        request_path = repo / "examples" / "draft-request.telegram.json"
        if not request_path.exists():
            self.skipTest("missing examples/draft-request.telegram.json")

        args = argparse.Namespace(
            query=None,
            request=str(request_path),
            platform="Telegram",
            post_type="Tool Breakdown",
            topics=["Multi Agent"],
            mood=["Practical"],
            source_types=["Reference-Example"],
        )

        query = script.build_query(args)

        self.assertEqual(query.platform, "telegram")
        self.assertEqual(query.post_type, "tool_breakdown")
        self.assertIn("multi_agent", query.topics)
        self.assertIn("practical", query.mood)
        self.assertIn("reference_example", query.source_types)


if __name__ == "__main__":
    unittest.main()
