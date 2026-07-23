"""
魔法大脑 - 套利搜索引擎
=====================

核心算法: 多目标 Dijkstra 变种。

不同于传统最短路只看"距离", 这里每条边的成本是多维度的加权综合:
    cost(edge) = w_price * price + w_time * duration_min + w_transfer * transfer_cost

用户通过偏好权重控制侧重:
  - 价格敏感型: w_price 高 -> 优先找卧铺省钱方案
  - 时间敏感型: w_time 高  -> 优先直达飞机
  - 舒适型:     间接通过 comfort + transfer 体现

输出: top-K 条 Pareto 候选路径, 再与基准直达对比算省钱额。

为何不用标准最短路:
  真实出行是多目标权衡, 没有唯一最优解。
  我们给用户"菜单"(前几条不同 trade-off 的路), 而非"唯一答案"。
"""

from __future__ import annotations
import heapq
from dataclasses import dataclass, field
from typing import Optional
from .graph import TransportGraph, Edge, Mode, Comfort


@dataclass
class Weights:
    """多目标权重。默认偏价格敏感 (套利场景)。"""
    price: float = 1.0
    time: float = 0.02     # 分钟换算成元级别, 1分钟≈0.02元惩罚
    transfer: float = 30.0  # 每次换乘≈30元等价不爽
    comfort: float = 15.0   # 舒适度降一档≈15元等价不爽


@dataclass
class Path:
    """一条完整出行路径。"""
    edges: list[Edge]
    total_price: float = 0.0
    total_duration_min: int = 0
    transfers: int = 0
    max_comfort: int = Comfort.SEAT  # 路径中最差舒适度

    @property
    def origin(self) -> str:
        return self.edges[0].from_code if self.edges else ""

    @property
    def destination(self) -> str:
        return self.edges[-1].to_code if self.edges else ""

    def describe(self) -> str:
        """人类可读路径描述。"""
        if not self.edges:
            return "(空路径)"
        steps = []
        for e in self.edges:
            steps.append(f"{e.label or e.mode.value} {e.from_code}→{e.to_code} (¥{e.price:.0f}, {e.duration_min}min)")
        head = " ➜ ".join(steps)
        return f"{head}\n   合计 ¥{self.total_price:.0f} | {self.total_duration_min}min | {self.transfers}次换乘"


def edge_cost(e: Edge, w: Weights) -> float:
    """单条边的综合成本。"""
    return (
        w.price * e.price
        + w.time * e.duration_min
        + w.transfer * e.transfer_cost
        + w.comfort * e.comfort
    )


def search(
    graph: TransportGraph,
    origin: str,
    destination: str,
    weights: Optional[Weights] = None,
    top_k: int = 5,
    max_edges: int = 10,
) -> list[Path]:
    """
    多目标 Dijkstra, 返回 top_k 条综合成本最低的路径。

    参数:
      graph       交通图
      origin      起点节点 code
      destination 终点节点 code
      weights     偏好权重 (None=默认价格敏感)
      top_k       最多返回几条
      max_edges   路径最多几段 (防无限绕路)
    """
    w = weights or Weights()
    # 状态: (累计成本, 节点code, 已走边数, 路径边列表, 累计价格, 累计时间, 换乘数, 最差舒适度)
    # 用 list 而非 dataclass 进堆, 避免比较时 dataclass 报错
    start = (0.0, origin, 0, [], 0.0, 0, 0, 0)
    heap: list = [start]
    results: list[Path] = []
    seen_cost: dict[tuple[str, int], float] = {}

    while heap and len(results) < top_k:
        cost, node, n_edges, path_edges, tot_price, tot_time, transfers, worst_comf = heapq.heappop(heap)

        # 剪枝: 同节点同跳数已出现更优, 跳过
        key = (node, n_edges)
        if key in seen_cost and seen_cost[key] <= cost:
            continue
        seen_cost[key] = cost

        if node == destination and path_edges:
            p = Path(
                edges=list(path_edges),
                total_price=tot_price,
                total_duration_min=tot_time,
                transfers=transfers,
                max_comfort=worst_comf,
            )
            results.append(p)
            continue

        if n_edges >= max_edges:
            continue

        for e in graph.neighbors(node):
            new_cost = cost + edge_cost(e, w)
            new_path = path_edges + [e]
            new_transfers = transfers + e.transfer_cost
            heapq.heappush(heap, (
                new_cost, e.to_code, n_edges + 1, new_path,
                tot_price + e.price, tot_time + e.duration_min,
                new_transfers, max(worst_comf, e.comfort),
            ))

    return sorted(results, key=lambda p: (p.total_price, p.total_duration_min))
