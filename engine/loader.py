"""
魔法大脑 - 数据加载器
====================

把 data/ 下的真实线路 JSON 灌进交通图。

数据分两类:
  data/routes/    中转省钱路径 (含多 segment)
  data/baselines/ 直达基准 (飞机/高铁直达)

设计原则:
  - 每条 route 的 origin/destination code 作为"城市级根节点"
    (如 SHA=上海, HKG=香港), 用户查询城市对即可
  - segments 里的站点作为内部节点, 通过 0 成本衔接边串起来
  - 这样一套图支持"城市对查询"和"站到站查询"
"""

from __future__ import annotations
import json
from pathlib import Path
from .graph import TransportGraph, Node, Edge, Mode, Comfort

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


# segment type -> (Mode, Comfort) 映射
_SEGMENT_MAP = {
    "flight_direct":     (Mode.FLIGHT,        Comfort.SEAT),
    "flight":            (Mode.FLIGHT,        Comfort.SEAT),
    "train_hsr":         (Mode.HSR,           Comfort.SEAT),
    "train_hsr_direct":  (Mode.HSR,           Comfort.SEAT),
    "train_sleeper":     (Mode.TRAIN_SLEEPER, Comfort.BED),
    "train_seat":        (Mode.TRAIN_SEAT,    Comfort.SEAT),
    "metro":             (Mode.METRO,         Comfort.SEAT),
    "bus":               (Mode.BUS,           Comfort.SEAT),
    "walk_border":       (Mode.WALK_BORDER,   Comfort.WALK),
    "taxi":              (Mode.TAXI,          Comfort.SEAT),
}


def _ensure_node(graph: TransportGraph, code: str, name: str, city: str, is_border: bool = False) -> None:
    """节点不存在则创建。已存在且传入 is_border=True 则升级标记。"""
    if code in graph.nodes:
        if is_border:
            graph.nodes[code].is_border = True
        return
    graph.add_node(Node(code=code, name=name, city=city, is_border=is_border or "口岸" in name))


def _seg_code(seg: dict, suffix: str) -> str:
    """segment 站点的内部 code。加前缀避免与城市根 code 冲突。"""
    name = seg.get("from") if suffix == "from" else seg.get("to")
    return f"STN::{name}" if name else ""


def load_graph(data_dir: Path = DATA_DIR) -> tuple[TransportGraph, list[dict]]:
    """
    扫描 data/, 返回 (graph, baselines)。
    """
    graph = TransportGraph()
    baselines: list[dict] = []

    routes_dir = data_dir / "routes"
    if routes_dir.exists():
        for f in sorted(routes_dir.glob("*.json")):
            route = json.loads(f.read_text(encoding="utf-8"))
            _load_route(graph, route)

    base_dir = data_dir / "baselines"
    if base_dir.exists():
        for f in sorted(base_dir.glob("*.json")):
            doc = json.loads(f.read_text(encoding="utf-8"))
            doc["__origin_code"] = doc["origin"]["code"]
            doc["__dest_code"] = doc["destination"]["code"]
            for b in doc.get("baselines", []):
                b["__origin_code"] = doc["origin"]["code"]
                b["__dest_code"] = doc["destination"]["code"]
                baselines.append(b)

    return graph, baselines


def _load_route(graph: TransportGraph, route: dict) -> None:
    """把一条 route (多 segment) 拆成边链加入图。

    结构:  origin_city_root -> [seg1_from -> seg1_to -> seg2_from -> ... ] -> dest_city_root
    城市根节点用 origin/destination 的 code (如 SHA/HKG)。
    """
    origin = route["origin"]
    dest = route["destination"]

    _ensure_node(graph, origin["code"], origin.get("station", origin["city"]), origin["city"])
    _ensure_node(graph, dest["code"], dest.get("station", dest["city"]), dest["city"])

    segments = route.get("segments", [])
    if not segments:
        return

    prev_code = origin["code"]
    for seg in segments:
        mode_str = seg["type"]
        mode, comfort = _SEGMENT_MAP.get(mode_str, (Mode.METRO, Comfort.SEAT))

        from_name = seg.get("from", "")
        to_name = seg.get("to", "")
        from_code = f"STN::{from_name}"
        to_code = f"STN::{to_name}"

        if from_name:
            _ensure_node(graph, from_code, from_name, origin["city"])
        if to_name:
            _ensure_node(graph, to_code, to_name, dest["city"])

        # prev -> seg.from (若不是同一个, 用 0 成本衔接)
        used_from = from_code if from_name else prev_code
        if prev_code != used_from:
            graph.add_edge(Edge(
                from_code=prev_code, to_code=used_from,
                mode=Mode.WALK_BORDER, price=0, duration_min=0,
                comfort=Comfort.WALK, transfer_cost=0, label="出发衔接",
            ))

        label_parts = [s for s in [seg.get("train_no", ""), seg.get("seat", "")] if s]
        label = " ".join(label_parts) + (f" {from_name}→{to_name}" if from_name and to_name else "")
        label = label.strip()

        graph.add_edge(Edge(
            from_code=used_from, to_code=to_code,
            mode=mode, price=seg["price"], duration_min=seg["duration_min"],
            comfort=comfort, transfer_cost=1,
            label=label, schedule_note=seg.get("depart"),
        ))
        prev_code = to_code

    # 末段 -> dest_city_root
    if prev_code != dest["code"]:
        graph.add_edge(Edge(
            from_code=prev_code, to_code=dest["code"],
            mode=Mode.WALK_BORDER, price=0, duration_min=0,
            comfort=Comfort.WALK, transfer_cost=0, label="抵达衔接",
        ))


def get_baselines_for(baselines: list[dict], origin_code: str, dest_code: str) -> list[dict]:
    """按城市 code 筛选基准。"""
    out = []
    for b in baselines:
        if b.get("__origin_code") == origin_code and b.get("__dest_code") == dest_code:
            out.append(b)
    return out
