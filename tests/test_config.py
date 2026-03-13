import os
import unittest
from pathlib import Path

from app.config import load_config


class ConfigTest(unittest.TestCase):
    def test_defaults(self):
        os.environ.pop("RIGEL_SERVICE_NAME", None)
        os.environ.pop("RIGEL_HTTP_PORT", None)
        os.environ.pop("RIGEL_GOOFISH_STATE_DIR", None)
        os.environ.pop("RIGEL_GOOFISH_ROOT_STATE_FILE", None)
        os.environ.pop("RIGEL_GOOFISH_HEADLESS", None)
        os.environ.pop("RIGEL_GOOFISH_SEARCH_TIMEOUT_MS", None)
        cfg = load_config()
        self.assertEqual(cfg.service_name, "rigel-goofish-collector")
        self.assertEqual(cfg.http_port, 8080)
        self.assertEqual(cfg.state_dir, Path("state"))
        self.assertEqual(cfg.root_state_file, Path("state/goofish_state.json"))
        self.assertTrue(cfg.run_headless)
        self.assertEqual(cfg.search_timeout_ms, 45000)
        self.assertEqual(cfg.browser_channel, "chromium")


if __name__ == "__main__":
    unittest.main()
