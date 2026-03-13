import unittest

from app.services.summary_service import summarize_prices


class SummaryServiceTest(unittest.TestCase):
    def test_summarize_prices(self):
        summary = summarize_prices(
            "DDR5 6000 32G",
            "RAM",
            [
                {"price": 2000},
                {"price": 2500},
                {"price": 2200},
            ],
        )
        self.assertEqual(summary["sample_count"], 3)
        self.assertEqual(summary["avg_price"], 2233.33)
        self.assertEqual(summary["median_price"], 2200.0)
        self.assertEqual(summary["p25_price"], 2100.0)
        self.assertEqual(summary["p75_price"], 2350.0)

    def test_summarize_prices_empty(self):
        summary = summarize_prices("RTX 4060", "GPU", [])
        self.assertEqual(summary["sample_count"], 0)
        self.assertIsNone(summary["avg_price"])
        self.assertIsNone(summary["median_price"])


if __name__ == "__main__":
    unittest.main()
