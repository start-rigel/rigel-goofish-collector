import tempfile
import unittest
from pathlib import Path

from app.services.login_state_service import LoginStateService


class LoginStateServiceTest(unittest.TestCase):
    def test_save_list_delete_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir) / "state"
            root_state = state_dir / "goofish_state.json"
            service = LoginStateService(state_dir, root_state)

            saved = service.save_state('{"cookies": []}')
            self.assertTrue(saved.is_root)
            self.assertEqual(saved.name, "goofish_state.json")

            items = service.list_state_files()
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].name, "goofish_state.json")

            deleted = service.delete_state("goofish_state.json")
            self.assertTrue(deleted)
            self.assertEqual(service.list_state_files(), [])

    def test_runtime_plan_prefers_root_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir) / "state"
            root_state = state_dir / "goofish_state.json"
            service = LoginStateService(state_dir, root_state)
            service.save_state('{"cookies": []}')
            plan = service.resolve_runtime_plan(strategy=None, account_state_file=None)
            self.assertEqual(plan["strategy"], "auto")
            self.assertTrue(plan["prefer_root_state"])

    def test_promote_state_to_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir) / "state"
            root_state = state_dir / "goofish_state.json"
            service = LoginStateService(state_dir, root_state)
            service.save_state('{"cookies": [1]}', "acc_1.json")

            saved = service.promote_to_root("acc_1.json")
            self.assertTrue(saved.is_root)
            self.assertEqual(saved.name, "goofish_state.json")
            self.assertEqual(root_state.read_text(encoding="utf-8"), '{"cookies": [1]}')


if __name__ == "__main__":
    unittest.main()
