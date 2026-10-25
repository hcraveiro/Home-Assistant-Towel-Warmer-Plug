"""Boundary and regression tests for heating schedules."""
import unittest
from datetime import datetime, time
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "custom_components" / "towel_warmer_plug" / "schedule.py"
spec = spec_from_file_location("towel_schedule_boundaries", path)
module = module_from_spec(spec)
spec.loader.exec_module(module)


class BoundaryTests(unittest.TestCase):
    def active(self, day, hour, minute, days, windows):
        return module.is_in_schedule(datetime(2026, 10, day, hour, minute), days, windows)

    def test_exact_start_included(self):
        self.assertTrue(self.active(26, 8, 0, ["mon"], [("08:00:00", "09:00:00")]))

    def test_exact_end_excluded(self):
        self.assertFalse(self.active(26, 9, 0, ["mon"], [("08:00:00", "09:00:00")]))

    def test_before_start_excluded(self):
        self.assertFalse(self.active(26, 7, 59, ["mon"], [("08:00:00", "09:00:00")]))

    def test_multi_windows_gap(self):
        w = [("06:00:00", "08:00:00"), ("12:00:00", "14:00:00"), ("18:00:00", "21:00:00")]
        self.assertFalse(self.active(26, 10, 0, ["mon"], w))
        self.assertTrue(self.active(26, 13, 0, ["mon"], w))
        self.assertTrue(self.active(26, 20, 0, ["mon"], w))

    def test_overlapping_windows(self):
        w = [("08:00:00", "12:00:00"), ("10:00:00", "14:00:00")]
        self.assertTrue(self.active(26, 13, 0, ["mon"], w))

    def test_sunday_into_monday(self):
        self.assertTrue(self.active(26, 1, 0, ["sun"], [("22:00:00", "02:00:00")]))
        self.assertFalse(self.active(26, 3, 0, ["sun"], [("22:00:00", "02:00:00")]))

    def test_overnight_start_end_boundaries(self):
        w = [("22:00:00", "02:00:00")]
        self.assertTrue(self.active(26, 22, 0, ["mon"], w))
        self.assertFalse(self.active(27, 2, 0, ["mon"], w))

    def test_no_windows(self):
        self.assertFalse(self.active(26, 9, 0, ["mon"], []))

    def test_time_objects(self):
        self.assertTrue(self.active(26, 9, 0, ["mon"], [(time(8), time(10))]))

    def test_disabled_day(self):
        self.assertFalse(self.active(26, 9, 0, ["tue"], [("08:00:00", "10:00:00")]))

    def test_all_weekdays(self):
        days = list(module.WEEKDAYS)
        for day in range(26, 33):
            with self.subTest(day=day):
                self.assertTrue(self.active(day, 9, 0, days, [("08:00:00", "10:00:00")]))


if __name__ == "__main__":
    unittest.main()
