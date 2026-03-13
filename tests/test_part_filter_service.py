import unittest

from app.services.part_filter_service import is_valid_part_listing, reject_reason


class PartFilterServiceTest(unittest.TestCase):
    def test_rejects_wanted_posts(self):
        self.assertFalse(is_valid_part_listing("求购 RTX 4060 一张", "GPU"))
        self.assertEqual(reject_reason("求购 RTX 4060 一张", "GPU"), "wanted_post")

    def test_rejects_whole_pc_posts_for_non_case(self):
        self.assertFalse(is_valid_part_listing("5600 + 4060 游戏主机整机", "GPU"))
        self.assertEqual(reject_reason("5600 + 4060 游戏主机整机", "GPU"), "whole_pc")

    def test_rejects_broken_items(self):
        self.assertFalse(is_valid_part_listing("RTX 4060 坏卡 不亮", "GPU"))
        self.assertEqual(reject_reason("RTX 4060 坏卡 不亮", "GPU"), "broken_item")

    def test_rejects_cpu_mb_bundle(self):
        self.assertFalse(is_valid_part_listing("7500F 板U套装", "CPU"))
        self.assertEqual(reject_reason("7500F 板U套装", "CPU"), "bundle_listing")

    def test_rejects_gpu_mining_risk_listing(self):
        self.assertFalse(is_valid_part_listing("RTX 3070 矿卡 甩卖", "GPU"))
        self.assertEqual(reject_reason("RTX 3070 矿卡 甩卖", "GPU"), "gpu_risk_listing")

    def test_accepts_normal_part_listing(self):
        self.assertTrue(is_valid_part_listing("金士顿 DDR5 6000 32G 内存条", "RAM"))
        self.assertIsNone(reject_reason("金士顿 DDR5 6000 32G 内存条", "RAM"))

    def test_case_can_keep_case_related_titles(self):
        self.assertTrue(is_valid_part_listing("先马 机箱 台式机机箱", "CASE"))


if __name__ == "__main__":
    unittest.main()
