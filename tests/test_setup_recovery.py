"""Guard against regressions in setup error recovery."""
import ast
import unittest
from pathlib import Path


class SetupRecoveryTests(unittest.TestCase):
    def test_options_listener_is_registered_before_fallible_setup(self):
        file = Path(__file__).resolve().parents[1] / "custom_components" / "towel_warmer_plug" / "__init__.py"
        module = ast.parse(file.read_text(encoding="utf-8"))
        setup = next(
            node for node in module.body
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "async_setup_entry"
        )
        text = ast.get_source_segment(file.read_text(encoding="utf-8"), setup)
        self.assertLess(
            text.index("entry.add_update_listener(update_listener)"),
            text.index("if not data.get(CONF_POWER)"),
        )
        self.assertLess(
            text.index("entry.add_update_listener(update_listener)"),
            text.index("coordinator.async_config_entry_first_refresh()"),
        )


if __name__ == "__main__":
    unittest.main()
