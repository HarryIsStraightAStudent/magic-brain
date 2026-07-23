"""
魔法大脑 - 交通图谱模块
=====================

定义多模态交通网络的数据结构。

图模型:
  - 节点 (Node): 城市/枢纽站点, 如 "上海南", "深圳", "罗湖口岸"
  - 边 (Edge): 一段交通, 带多维度成本 (价格/时间/换乘次数/舒适度)

这是套利搜索的基础。边不只有"距离", 而是真实交通段:
  飞机 / 高铁 / 普速卧铺 / 地铁 / 步行过关 ...

每条边记录: 票价, 耗时, 班次约束, 舒适度等级。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Mode(str, Enum):
    """交通方式。str 基类便于 JSON 序列化。"""
    FLIGHT = "flight"
    HSR = "hsr"                       # 高铁
    TRAIN_SLEEPER = "train_sleeper"   # 普速卧铺
    TRAIN_SEAT = "train_seat"         # 普速座
    METRO = "metro"
    BUS = "bus"
    WALK_BORDER = "walk_border"       # 步行过关
    TAXI = "taxi"


class Comfort:
    """舒适度, 数值越小越舒适 (bed 最优, walk 最差)。"""
    BED = 0      # 卧铺/商务舱
    SEAT = 1     # 一二等座
    STAND = 2    # 站票
    WALK = 3     # 步行


@dataclass
class Node:
    """交通网络节点。"""
    code: str            # 唯一代码, 如 "SHA", "HKG-TST"
    name: str            # 显示名, 如 "上海", "尖沙咀"
    city: str            # 所属城市
    is_border: bool = False  # 是否口岸节点 (影响过关耗时)


@dataclass
class Edge:
    """
    交通网络边 = 一段可乘坐的交通。

    多维成本:
      price         票价 (元)
      duration_min  耗时 (分钟)
      comfort       舒适度等级
      transfer_cost 到此段视为换乘的额外惩罚 (默认 1, 直达段可设 0)

    时序约束 (W2 启用):
      schedule_note 可限制班次。
    """
    from_code: str
    to_code: str
    mode: Mode
    price: float
    duration_min: int
    comfort: int = Comfort.SEAT
    transfer_cost: int = 1            # 进入此段是否算一次换乘
    label: str = ""                   # 人类可读说明, 如 "D941 二等卧"
    schedule_note: Optional[str] = None  # 班次备注, 如 "每日 21:22 发车"


@dataclass
class TransportGraph:
    """多模态交通网络。邻接表表示。"""
    nodes: dict[str, Node] = field(default_factory=dict)
    adj: dict[str, list[Edge]] = field(default_factory=dict)

    def add_node(self, node: Node) -> None:
        self.nodes[node.code] = node
        self.adj.setdefault(node.code, [])

    def add_edge(self, edge: Edge) -> None:
        """加有向边。交通段是有方向的。"""
        assert edge.from_code in self.nodes, f"未知节点: {edge.from_code}"
        assert edge.to_code in self.nodes, f"未知节点: {edge.to_code}"
        self.adj[edge.from_code].append(edge)

    def neighbors(self, code: str) -> list[Edge]:
        return self.adj.get(code, [])
