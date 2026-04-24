from __future__ import annotations

import os
import unittest
from unittest import mock

from tone_of_voice.telegram_export import ensure_telegram_credentials


class EnsureTelegramCredentialsTest(unittest.TestCase):
    def test_missing_env_raises_runtime_error(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                ensure_telegram_credentials()
        self.assertIn("TELEGRAM_API_ID", str(ctx.exception))

    def test_non_integer_api_id_raises_runtime_error(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"TELEGRAM_API_ID": "not-a-number", "TELEGRAM_API_HASH": "abc"},
            clear=True,
        ):
            with self.assertRaises(RuntimeError) as ctx:
                ensure_telegram_credentials()
        self.assertIn("must be an integer", str(ctx.exception))

    def test_valid_credentials_returned(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"TELEGRAM_API_ID": "12345", "TELEGRAM_API_HASH": "secret"},
            clear=True,
        ):
            api_id, api_hash = ensure_telegram_credentials()
        self.assertEqual(api_id, 12345)
        self.assertEqual(api_hash, "secret")


if __name__ == "__main__":
    unittest.main()
