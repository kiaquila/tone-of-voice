import unittest

from tone_of_voice.metrics import compute_corpus_metrics


class MetricsTestCase(unittest.TestCase):
    def test_compute_corpus_metrics_returns_expected_core_values(self) -> None:
        records = [
            {
                "published_at": "2026-04-20T10:00:00+00:00",
                "raw_text": "Сегодня тестирую новый сетап 😏\n\nВот ссылка https://example.com",
            },
            {
                "published_at": "2026-04-21T10:00:00+00:00",
                "raw_text": "А человеку остается быть источником смыслов",
            },
        ]

        metrics = compute_corpus_metrics(records, top_n=20)

        self.assertEqual(metrics["total_posts"], 2)
        self.assertEqual(metrics["date_range"]["first"], "2026-04-20T10:00:00+00:00")
        self.assertEqual(metrics["date_range"]["last"], "2026-04-21T10:00:00+00:00")
        self.assertEqual(metrics["signals"]["posts_with_links"], 1)
        self.assertEqual(metrics["signals"]["posts_with_emoji"], 1)
        self.assertEqual(metrics["top_starters"][0][0], "сегодня")
        self.assertTrue(
            any(token in {"источником", "смыслов", "человеку"} for token, _ in metrics["top_tokens"])
        )


if __name__ == "__main__":
    unittest.main()
