import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

import study_calendar


class StudyCalendarTests(unittest.TestCase):
    def test_default_date_uses_taipei_day_at_scheduled_utc_time(self):
        scheduled_utc = datetime(2026, 10, 4, 22, 30, tzinfo=timezone.utc)
        self.assertEqual(study_calendar.today_in_taipei(scheduled_utc), date(2026, 10, 5))

    def test_weekends_are_rest_days_even_without_calendar_data(self):
        with patch.object(study_calendar, "HOLIDAY_DIR", Path("missing")):
            self.assertFalse(study_calendar.is_study_day(date(2026, 10, 3)))
            self.assertFalse(study_calendar.is_study_day(date(2026, 10, 4)))

    def test_official_holidays_and_following_workdays(self):
        self.assertFalse(study_calendar.is_study_day(date(2026, 10, 9)))
        self.assertFalse(study_calendar.is_study_day(date(2026, 10, 26)))
        self.assertTrue(study_calendar.is_study_day(date(2026, 10, 12)))
        self.assertFalse(study_calendar.is_study_day(date(2027, 2, 9)))
        self.assertTrue(study_calendar.is_study_day(date(2027, 2, 11)))

    def test_missing_calendar_fails_closed_on_a_weekday(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(study_calendar, "HOLIDAY_DIR", Path(temp_dir)):
                with self.assertRaises(FileNotFoundError):
                    study_calendar.is_study_day(date(2026, 10, 5))


if __name__ == "__main__":
    unittest.main()
