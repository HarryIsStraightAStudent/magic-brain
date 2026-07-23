"""魔法大脑 - 套利路径引擎包。"""
from .graph import TransportGraph, Node, Edge, Mode, Comfort
from .search import search, Weights, Path
from .arbitrage import SavingsReport, compare_to_baseline
from .loader import load_graph, get_baselines_for

__all__ = [
    "TransportGraph", "Node", "Edge", "Mode", "Comfort",
    "search", "Weights", "Path",
    "SavingsReport", "compare_to_baseline",
    "load_graph", "get_baselines_for",
]
