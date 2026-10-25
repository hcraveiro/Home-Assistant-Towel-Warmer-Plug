"""Tests for backwards-compatible towel warmer settings."""
import sys
import types
import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "custom_components" / "towel_warmer_plug"
package = types.ModuleType("towel_warmer_plug")
package.__path__ = [str(BASE)]
sys.modules.setdefault("towel_warmer_plug", package)
spec = spec_from_file_location("towel_warmer_plug.models", BASE / "models.py")
module = module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
TowelWarmerConfig = module.TowelWarmerConfig
merge_entry_settings = module.merge_entry_settings


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.old_data = {
            "name": "WC Towel Warmer",
            "switch_entity": "switch.warmer",
            "power_sensor": "sensor.warmer_power",
            "start_time": "07:30:00",
            "end_time": "09:15:00",
        }

    def test_existing_configuration_keeps_original_window_and_all_days(self):
        config = TowelWarmerConfig.from_dict(self.old_data)
        self.assertEqual(config.time_windows, [("07:30:00", "09:15:00")])
        self.assertEqual(config.weekdays, ["mon", "tue", "wed", "thu", "fri", "sat", "sun"])

    def test_null_legacy_power_sensor_does_not_override_original(self):
        original = {**self.old_data, "power_sensor": "sensor.warmer_power"}
        options = {"power_sensor": None, "start_time": "11:00:00", "end_time": "12:00:00"}
        merged = merge_entry_settings(original, options)
        self.assertEqual(merged["power_sensor"], "sensor.warmer_power")
        self.assertEqual(TowelWarmerConfig.from_dict(merged).time_windows, [("11:00:00", "12:00:00")])

    def test_missing_power_sensor_requires_reconfiguration(self):
        old = dict(self.old_data)
        old.pop("power_sensor")
        merged = merge_entry_settings(old, {"power_sensor": None})
        self.assertNotIn("power_sensor", merged)
        fixed = merge_entry_settings(merged, {"power_sensor": "sensor.fixed_power"})
        self.assertEqual(TowelWarmerConfig.from_dict(fixed).power_sensor, "sensor.fixed_power")

    def test_valid_options_take_precedence(self):
        merged = merge_entry_settings(self.old_data, {"power_sensor": "sensor.new_power"})
        self.assertEqual(merged["power_sensor"], "sensor.new_power")

    def test_old_options_override_old_data(self):
        options = {"start_time": "06:00:00", "end_time": "08:00:00"}
        config = TowelWarmerConfig.from_dict({**self.old_data, **options})
        self.assertEqual(config.time_windows, [("06:00:00", "08:00:00")])

    def test_new_options_replace_old_window_without_duplicating_it(self):
        options = {
            "weekdays": ["mon", "wed", "fri"],
            "time_windows": [
                {"start": "06:30:00", "end": "08:00:00"},
                {"start": "18:00:00", "end": "20:00:00"},
            ],
        }
        config = TowelWarmerConfig.from_dict({**self.old_data, **options})
        self.assertEqual(config.weekdays, ["mon", "wed", "fri"])
        self.assertEqual(config.time_windows, [
            ("06:30:00", "08:00:00"),
            ("18:00:00", "20:00:00"),
        ])


if __name__ == "__main__":
    unittest.main()
