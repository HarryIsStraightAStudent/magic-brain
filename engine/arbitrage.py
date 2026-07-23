"""
魔法大脑 - 套利分析模块
=====================

把搜索引擎找到的中转路径, 与直达基准对比, 算出真实省钱额。

这是产品的"卖点发生器":
  "直达高铁 ¥966, 我们的方案 ¥567, 省 ¥399 (41%)"

benchmark = 直达基准 (飞机/高铁直达)
candidates = 引擎搜出的中转省钱路径
savings = benchmark - candidate
"""

from __future__ import annotations
from dataclasses import dataclass
from .search import Path


@dataclass
class SavingsReport:
    """单条省钱分析报告。"""
    path: Path
    benchmark_id: str
    benchmark_name: str
    benchmark_price: float
    benchmark_duration_min: int
    savings_price: float         # 省了多少钱
    savings_ratio: float         # 省了百分之几
    time_cost_min: int           # 多花多少时间 (负数=更快)
    verdict: str                 # 一句话评价

    def headline(self) -> str:
        """生成 demo 用的标题。"""
        sign = "快" if self.time_cost_min < 0 else "慢"
        mins = abs(self.time_cost_min)
        return (
            f"省 ¥{self.savings_price:.0f} ({self.savings_ratio*100:.0f}%), "
            f"代价: {sign} {mins}min"
        )


def compare_to_baseline(
    path: Path,
    benchmark_id: str,
    benchmark_name: str,
    benchmark_price: float,
    benchmark_duration_min: int,
) -> SavingsReport:
    """单条路径 vs 单条基准。"""
    saved = benchmark_price - path.total_price
    ratio = saved / benchmark_price if benchmark_price > 0 else 0.0
    time_diff = path.total_duration_min - benchmark_duration_min

    if saved <= 0:
        verdict = f"比{benchmark_name}贵 ¥{-saved:.0f}, 不推荐"
    elif time_diff <= 0:
        verdict = f"比{benchmark_name}又便宜又快, 闭眼选"
    else:
        verdict = (
            f"比{benchmark_name}省 ¥{saved:.0f} ({ratio*100:.0f}%), "
            f"多花 {time_diff}min, 看你取舍"
        )

    return SavingsReport(
        path=path,
        benchmark_id=benchmark_id,
        benchmark_name=benchmark_name,
        benchmark_price=benchmark_price,
        benchmark_duration_min=benchmark_duration_min,
        savings_price=saved,
        savings_ratio=ratio,
        time_cost_min=time_diff,
        verdict=verdict,
    )
