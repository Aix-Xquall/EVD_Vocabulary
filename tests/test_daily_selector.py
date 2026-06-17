import unittest
from datetime import date

from daily_selector import select_daily_words


def entry(word, review_count, last_review_date, difficulty):
    return {
        "id": word,
        "word": word,
        "review_count": str(review_count),
        "last_review_date": last_review_date,
        "difficulty": str(difficulty),
    }


class DailySelectorTests(unittest.TestCase):
    def test_select_daily_words_prioritizes_low_review_old_date_high_difficulty(self):
        entries = [
            entry("newer", 0, "2026-06-10", 3),
            entry("older", 0, "2026-05-01", 3),
            entry("harder", 0, "2026-05-01", 5),
            entry("reviewed", 2, "2026-01-01", 5),
        ]

        selected = select_daily_words(entries, count=3, today=date(2026, 6, 17))

        self.assertEqual([item["word"] for item in selected], ["harder", "older", "newer"])

    def test_select_daily_words_treats_blank_last_review_as_oldest(self):
        entries = [
            entry("has-date", 0, "2020-01-01", 5),
            entry("blank-date", 0, "", 1),
        ]

        selected = select_daily_words(entries, count=1, today=date(2026, 6, 17))

        self.assertEqual(selected[0]["word"], "blank-date")


if __name__ == "__main__":
    unittest.main()
