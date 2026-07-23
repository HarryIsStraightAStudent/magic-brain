"""
魔法大脑 - FastAPI Web 服务
===========================

对外暴露交通套利搜索能力。

端点:
  GET  /                 前端页面
  GET  /api/cities       可查城市列表
  GET  /api/search       搜索套利路径 + 省钱对比
  POST /api/chat         AI 对话 (意图解析 -> 搜索 -> 自然语言回复)
  GET  /api/health       健康检查

运行:
  source .venv/bin/activate
  uvicorn api:app --reload --port 8000
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

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


# ---------- AI 对话 ----------

# 城市/别名 -> code 映射 (意图解析用)
_CITY_ALIASES = {
    "上海": "SHA", "shanghai": "SHA",
    "北京": "BJS", "beijing": "BJS",
    "广州": "CAN", "guangzhou": "CAN",
    "深圳": "SZX", "shenzhen": "SZX",
    "香港": "HKG", "hongkong": "HKG", "hong kong": "HKG", "港": "HKG",
    "澳门": "MFM", "macao": "MFM", "macau": "MFM",
    "厦门": "XMN", "xiamen": "XMN",
    "三亚": "SYX", "sanya": "SYX",
    "海口": "HAK", "haikou": "HAK",
    "成都": "CTU", "chengdu": "CTU",
    "重庆": "CKG", "chongqing": "CKG",
    "西安": "SIA", "xian": "SIA",
    "武汉": "WUH", "wuhan": "WUH",
    "南京": "NKG", "nanjing": "NKG",
    "杭州": "HGH", "hangzhou": "HGH",
    "青岛": "TAO", "qingdao": "TAO",
    "昆明": "KMG", "kunming": "KMG",
    "哈尔滨": "HRB", "harbin": "HRB",
    "乌鲁木齐": "URC", "urumqi": "URC",
}


class ChatRequest(BaseModel):
    message: str


def _parse_intent(text: str) -> tuple[str | None, str | None]:
    """规则意图解析: 从自然语言中提取起终点 code。

    W2 接 GLM 后替换为 LLM 解析。当前用关键词匹配兜底。
    返回 (origin_code, dest_code), 未识别为 None。

    策略:
      1. 识别所有出现的城市
      2. 若有"从X""X出发""X去"等模式, X=origin
      3. 若有"去X""到X""往X"模式, X=dest
      4. 只识别到一个城市: 若是"去/到"语境则作 dest, origin 用默认(上海)
    """
    found_codes: list[str] = []
    lowered = text.lower()
    for alias in sorted(_CITY_ALIASES, key=len, reverse=True):
        if alias in text or alias in lowered:
            code = _CITY_ALIASES[alias]
            if code not in found_codes:
                found_codes.append(code)

    if not found_codes:
        return (None, None)

    # 模式匹配: 找每个城市周围的介词
    origin = dest = None
    for code in found_codes:
        # 反查这个 code 的中文别名, 在原文定位
        names = [a for a, c in _CITY_ALIASES.items() if c == code and not a.isascii()]
        name = names[0] if names else code
        if name in text:
            idx = text.index(name)
            before = text[max(0, idx-2):idx]
            after = text[idx+len(name):idx+len(name)+2]
            if any(w in before for w in ["从", "在", "自"]) or "出发" in after:
                origin = code
            if any(w in before for w in ["去", "到", "往", "飞"]) or any(w in after for w in ["怎么", "便宜"]):
                dest = code

    # 兜底: 按出现顺序
    if found_codes:
        if not origin and not dest:
            origin = found_codes[0]
            dest = found_codes[1] if len(found_codes) > 1 else None
        elif origin and not dest and len(found_codes) > 1:
            dest = found_codes[1]
        elif dest and not origin:
            # 识别到 dest 但缺 origin
            if len(found_codes) > 1:
                origin = found_codes[0]
            else:
                # 单城市 + "去/到"语境, 默认上海出发
                origin = "SHA"
        elif origin and dest and origin == dest and len(found_codes) > 1:
            dest = found_codes[1]

    return (origin, dest)


@app.post("/api/chat")
def chat(req: ChatRequest):
    """AI 对话端点。

    流程: 意图解析 -> 搜索 -> 自然语言回复。
    若有 GLM_API_KEY, 用 GLM 生成更自然的回复; 否则用模板兜底。
    """
    text = req.message.strip()
    origin, dest = _parse_intent(text)

    # 未识别起终点
    if not origin or not dest:
        return {
            "reply": "我需要知道你的<span class='text-[#006e2f] font-semibold'>出发地</span>和<span class='text-[#006e2f] font-semibold'>目的地</span>才能帮你找省钱路线。比如：「下周三从上海去香港，便宜点」",
            "route": None,
        }

    city_data = json.loads((DATA_DIR / "cities.json").read_text(encoding="utf-8"))
    o_name = city_data["cities"].get(origin, {}).get("name", origin)
    d_name = city_data["cities"].get(dest, {}).get("name", dest)

    # 搜索
    if origin not in _GRAPH.nodes or dest not in _GRAPH.nodes:
        return {"reply": f"抱歉，目前还没有 {o_name}→{d_name} 的线路数据，先用上方搜索框试试已支持的城市。", "route": None}

    paths = search(_GRAPH, origin, dest, weights=Weights(), top_k=5)
    matched = get_baselines_for(_BASELINES, origin, dest)
    if not paths or not matched:
        return {"reply": f"暂时没找到 {o_name}→{d_name} 的省钱方案。", "route": None}

    cheapest = min(paths, key=lambda p: p.total_price)
    best_saving = None
    for b in matched:
        if cheapest.total_price < b["total_price"]:
            rep = compare_to_baseline(
                path=cheapest, benchmark_id=b.get("baseline_id", ""),
                benchmark_name=b["name"], benchmark_price=b["total_price"],
                benchmark_duration_min=b["total_duration_min"])
            if not best_saving or rep.savings_price > best_saving.savings_price:
                best_saving = rep

    if not best_saving:
        return {"reply": f"{o_name}→{d_name} 暂无更便宜的中转方案。", "route": None}

    first_seg = cheapest.user_facing_edges()[0]
    time_note = "快" if best_saving.time_cost_min < 0 else f"多花约 {best_saving.time_cost_min // 60} 小时"

    # GLM 增强回复 (有 key 时)
    glm_reply = None
    if os.getenv("GLM_API_KEY"):
        try:
            glm_reply = _glm_reply(text, o_name, d_name, cheapest, best_saving, time_note)
        except Exception:
            glm_reply = None

    reply = glm_reply or (
        f"已为你找到 {o_name}→{d_name} 的省钱方案：坐 {first_seg.label}，"
        f"比 {best_saving.benchmark_name} <b>省 ¥{best_saving.savings_price:.0f} ({best_saving.savings_ratio*100:.0f}%)</b>，"
        f"{time_note}。点击下方查看完整路线 →"
    )

    return {
        "reply": reply,
        "route": {
            "title": first_seg.label,
            "dept": (first_seg.schedule_note or "—").split(" ")[0][:5] or "—",
            "dept_name": o_name,
            "arr": "次日" if cheapest.total_duration_min > 360 else "当日",
            "arr_name": d_name,
            "price": int(cheapest.total_price),
            "duration": _fmt(cheapest.total_duration_min),
            "savings": int(best_saving.savings_price),
        },
    }


def _glm_reply(user_msg, o_name, d_name, path, saving, time_note) -> str:
    """调 GLM 生成自然语言回复。有 GLM_API_KEY 时启用。"""
    from zhipuai import ZhipuAI
    client = ZhipuAI(api_key=os.environ["GLM_API_KEY"])
    sys_prompt = (
        "你是「魔法大脑」，一个交通套利助手。用简短、口语化的中文回复用户。"
        "把省钱数据自然融入，别像念稿。控制在 60 字以内。"
    )
    fact = (
        f"用户说:「{user_msg}」。已搜到 {o_name}→{d_name} 方案: "
        f"总价¥{path.total_price:.0f}, 比{saving.benchmark_name}省¥{saving.savings_price:.0f}"
        f"({saving.savings_ratio*100:.0f}%), {time_note}。"
    )
    resp = client.chat.completions.create(
        model=os.getenv("GLM_MODEL", "glm-4.5"),
        messages=[{"role": "system", "content": sys_prompt},
                  {"role": "user", "content": fact + "\n请用一句话告诉用户这个好消息。"}],
        max_tokens=120,
    )
    return resp.choices[0].message.content


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
