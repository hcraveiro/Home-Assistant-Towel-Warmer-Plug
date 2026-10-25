"""Regression tests for weekly and multi-window scheduling."""
import unittest
from datetime import datetime
from custom_components.towel_warmer_plug.schedule import is_in_schedule


class ScheduleTests(unittest.TestCase):
    def check(self, day, hour, days, windows):
        return is_in_schedule(datetime(2026, 10, day, hour), days, windows)

    def test_weekday_selection(self):
        self.assertTrue(self.check(26, 9, ["mon"], [("08:00:00", "10:00:00")]))
        self.assertFalse(self.check(27, 9, ["mon"], [("08:00:00", "10:00:00")]))

    def test_multiple_windows(self):
        windows = [("06:00:00", "08:00:00"), ("18:00:00", "20:00:00")]
        self.assertTrue(self.check(26, 7, ["mon"], windows))
        self.assertTrue(self.check(26, 19, ["mon"], windows))
        self.assertFalse(self.check(26, 12, ["mon"], windows))

    def test_overnight_window_uses_start_day(self):
        windows = [("22:00:00", "02:00:00")]
        self.assertTrue(self.check(26, 23, ["mon"], windows))
        self.assertTrue(self.check(27, 1, ["mon"], windows))
        self.assertFalse(self.check(27, 23, ["mon"], windows))

    def test_empty_days_disables_schedule(self):
        self.assertFalse(self.check(26, 12, [], [("09:00:00", "20:00:00")]))


if __name__ == "__main__":
    unittest.main()
