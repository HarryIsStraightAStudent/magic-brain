"""
魔法大脑 - 引擎回归测试
=======================

固化核心行为, 防止回归:
  - 上海→香港卧铺方案 ¥567, 换乘 2 次
  - vs 高铁直达 ¥966 省 41%
  - 时长 13小时9分

用纯标准库 unittest, 不依赖 pytest 也能跑。
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import load_graph, search, Weights
from engine.arbitrage import compare_to_baseline
from engine.loader import get_baselines_for


class TestShanghaiHongKong(unittest.TestCase):
    """核心案例: 上海→香港 卧铺省钱。"""

    @classmethod
    def setUpClass(cls):
        cls.graph, cls.baselines = load_graph()
        cls.paths = search(cls.graph, "SHA", "HKG", weights=Weights(), top_k=5)

    def test_path_exists(self):
        self.assertTrue(len(self.paths) > 0, "应至少找到一条路径")

    def test_sleeper_price(self):
        """卧铺方案总价 ¥567 (D941 ¥507 + 港铁 ¥60)。"""
        cheapest = min(self.paths, key=lambda p: p.total_price)
        self.assertEqual(cheapest.total_price, 567)

    def test_transfer_count(self):
        """3 段真实交通 = 2 次换乘。"""
        p = self.paths[0]
        self.assertEqual(p.transfer_count, 2)

    def test_duration_13h09m(self):
        """总时长 789 分钟 = 13小时9分。"""
        p = self.paths[0]
        self.assertEqual(p.total_duration_min, 789)

    def test_hides_internal_codes(self):
        """美化输出: 不应出现内部 code STN::。"""
        desc = self.paths[0].describe()
        self.assertNotIn("STN::", desc)

    def test_savings_41pct_vs_hsr(self):
        """vs 高铁直达 ¥966, 省 41%。"""
        matched = get_baselines_for(self.baselines, "SHA", "HKG")
        hsr = [b for b in matched if b["type"] == "train_hsr_direct"][0]
        cheapest = min(self.paths, key=lambda p: p.total_price)
        rep = compare_to_baseline(
            path=cheapest,
            benchmark_id=hsr["baseline_id"],
            benchmark_name=hsr["name"],
            benchmark_price=hsr["total_price"],
            benchmark_duration_min=hsr["total_duration_min"],
        )
        self.assertAlmostEqual(rep.savings_price, 399)
        self.assertAlmostEqual(rep.savings_ratio, 399 / 966, places=2)


if __name__ == "__main__":
    unittest.main()
