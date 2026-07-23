"""
魔法大脑 - FastAPI Web 服务
===========================

对外暴露交通套利搜索能力。

端点:
  GET  /                 前端页面
  GET  /api/cities       可查城市列表
  GET  /api/search       搜索套利路径 + 省钱对比
  GET  /api/health       健康检查

运行:
  source .venv/bin/activate
  uvicorn api:app --reload --port 8000
"""

from __future__ import annotations
import json
from pathlib import Path
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine import load_graph, search, Weights
from engine.loader import get_baselines_for
from engine.arbitrage import compare_to_baseline

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

app = FastAPI(title="魔法大脑 Magic Brain", version="0.1.0")

# 启动时加载一次
_GRAPH, _BASELINES = load_graph(DATA_DIR)


# ---------- 数据模型 ----------

class SegmentOut(BaseModel):
    label: str
    mode: str
    price: float
    duration_min: int
    depart: str | None = None


class PathOut(BaseModel):
    segments: list[SegmentOut]
    total_price: float
    total_duration_min: int
    transfers: int
    duration_text: str


class BaselineOut(BaseModel):
    id: str
    name: str
    type: str
    price: float
    duration_min: int
    transfers: int


class SavingsOut(BaseModel):
    benchmark_id: str
    benchmark_name: str
    benchmark_price: float
    savings_price: float
    savings_ratio: float
    time_cost_min: int
    verdict: str


class SearchResponse(BaseModel):
    origin: str
    destination: str
    paths: list[PathOut]
    baselines: list[BaselineOut]
    savings: list[SavingsOut]


# ---------- 端点 ----------

@app.get("/api/health")
def health():
    return {"status": "ok", "nodes": len(_GRAPH.nodes), "edges": sum(len(v) for v in _GRAPH.adj.values())}


@app.get("/api/cities")
def cities():
    """可查城市 (有基准线路的城市对)。"""
    city_data = json.loads((DATA_DIR / "cities.json").read_text(encoding="utf-8"))
    pairs = set()
    for b in _BASELINES:
        pairs.add((b["__origin_code"], b["__dest_code"]))
    return {
        "cities": city_data["cities"],
        "queryable_pairs": [{"origin": o, "destination": d} for o, d in sorted(pairs)],
    }


@app.get("/api/search", response_model=SearchResponse)
def api_search(
    origin: str = Query(..., description="起点 code, 如 SHA"),
    destination: str = Query(..., description="终点 code, 如 HKG"),
    weight: str = Query("price", description="偏好: price/time/balanced"),
    top_k: int = Query(5, ge=1, le=20),
):
    if origin not in _GRAPH.nodes:
        return JSONResponse(status_code=404, content={"error": f"未知起点: {origin}"})
    if destination not in _GRAPH.nodes:
        return JSONResponse(status_code=404, content={"error": f"未知终点: {destination}"})

    w = {
        "price": Weights(price=1.0, time=0.02, transfer=30.0, comfort=15.0),
        "time": Weights(price=0.3, time=0.1, transfer=30.0, comfort=10.0),
        "balanced": Weights(price=0.7, time=0.05, transfer=25.0, comfort=12.0),
    }.get(weight, Weights())

    paths = search(_GRAPH, origin, destination, weights=w, top_k=top_k)
    matched_baselines = get_baselines_for(_BASELINES, origin, destination)

    path_outs = []
    for p in paths:
        segs = []
        for e in p.user_facing_edges():
            segs.append(SegmentOut(
                label=e.label or e.mode.value,
                mode=e.mode.value,
                price=e.price,
                duration_min=e.duration_min,
                depart=e.schedule_note,
            ))
        path_outs.append(PathOut(
            segments=segs,
            total_price=p.total_price,
            total_duration_min=p.total_duration_min,
            transfers=p.transfer_count,
            duration_text=_fmt(p.total_duration_min),
        ))

    base_outs = [BaselineOut(
        id=b.get("baseline_id", ""),
        name=b["name"],
        type=b["type"],
        price=b["total_price"],
        duration_min=b["total_duration_min"],
        transfers=b.get("transfers", 0),
    ) for b in matched_baselines]

    savings_outs = []
    cheapest = min(paths, key=lambda p: p.total_price) if paths else None
    if cheapest:
        for b in matched_baselines:
            rep = compare_to_baseline(
                path=cheapest,
                benchmark_id=b.get("baseline_id", ""),
                benchmark_name=b["name"],
                benchmark_price=b["total_price"],
                benchmark_duration_min=b["total_duration_min"],
            )
            savings_outs.append(SavingsOut(
                benchmark_id=rep.benchmark_id,
                benchmark_name=rep.benchmark_name,
                benchmark_price=rep.benchmark_price,
                savings_price=rep.savings_price,
                savings_ratio=rep.savings_ratio,
                time_cost_min=rep.time_cost_min,
                verdict=rep.verdict,
            ))

    return SearchResponse(
        origin=origin,
        destination=destination,
        paths=path_outs,
        baselines=base_outs,
        savings=savings_outs,
    )


@app.get("/", response_class=HTMLResponse)
def index():
    """临时前端, Stitch 设计稿回来后替换为旅行温暖风。"""
    html_file = ROOT / "web" / "index.html"
    if html_file.exists():
        return HTMLResponse(html_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>魔法大脑</h1><p>前端开发中, 访问 /docs 看 API</p>")


def _fmt(minutes: int) -> str:
    if minutes <= 0:
        return "0分"
    h, m = divmod(minutes, 60)
    parts = []
    if h:
        parts.append(f"{h}小时")
    if m:
        parts.append(f"{m}分")
    return "".join(parts)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
