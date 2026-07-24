"""
魔法大脑 - 多 Agent 流水线
==========================

4 个 Agent 协作完成出行省钱搜索:
  1. 意图理解 Agent  - 从自然语言解析起终点/偏好
  2. 任务规划 Agent  - 拆解执行步骤
  3. 工具调用 Agent  - 调搜索引擎 + 价格对比
  4. 结果解释 Agent  - 生成自然语言回复

每个 Agent 返回 AgentStep(思考摘要, 结果), 供 UI 展示思考过程。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from .llm import chat, chat_json, chat_with_search


@dataclass
class AgentStep:
    """单个 Agent 的执行步骤, 供 UI 展示。"""
    agent: str           # Agent 名称 (如 "意图理解")
    icon: str            # emoji 图标
    status: str          # "thinking" | "done" | "error"
    thought: str         # 思考内容摘要 (展示给用户)
    result: Any = None   # 结构化结果 (内部传递)
    sources: list = None # 联网搜索的数据来源 (title/url/snippet)


@dataclass
class PipelineResult:
    """整个 Agent 流水线的结果。"""
    steps: list[AgentStep] = field(default_factory=list)
    origin_code: str | None = None
    dest_code: str | None = None
    origin_name: str = ""
    dest_name: str = ""
    reply: str = ""          # 最终自然语言回复
    route: dict | None = None  # 路线卡数据 (同 /api/chat 的 route)
    live_alternatives: list = None  # 联网替代方案 (纯联网模式)


# 城市别名 (与 api.py 保持一致)
_CITY_ALIASES = {
    "上海": "SHA", "北京": "BJS", "广州": "CAN", "深圳": "SZX",
    "香港": "HKG", "澳门": "MFM", "厦门": "XMN", "三亚": "SYX",
    "海口": "HAK", "成都": "CTU", "重庆": "CKG", "西安": "SIA",
    "武汉": "WUH", "南京": "NKG", "杭州": "HGH", "青岛": "TAO",
    "昆明": "KMG", "哈尔滨": "HRB", "乌鲁木齐": "URC",
}

_CITY_NAMES = {v: k for k, v in _CITY_ALIASES.items()}


def _detect_cities(text: str) -> list[str]:
    """规则辅助: 预提取出现的城市 code。"""
    found = []
    for alias in sorted(_CITY_ALIASES, key=len, reverse=True):
        if alias in text:
            code = _CITY_ALIASES[alias]
            if code not in found:
                found.append(code)
    return found


def run_pipeline(user_message: str, search_fn) -> PipelineResult:
    """运行完整 Agent 流水线。

    search_fn: callable(origin_code, dest_code) -> dict, 返回搜索结果
              (与 /api/search 同结构: paths, baselines, savings)
    返回 PipelineResult 含所有步骤。
    """
    res = PipelineResult()

    # ===== Agent 1: 意图理解 =====
    s1 = AgentStep(agent="意图理解", icon="🧠", status="thinking",
                   thought="正在理解你的出行需求...")
    res.steps.append(s1)

    rule_cities = _detect_cities(user_message)
    intent = chat_json(
        system=(
            "你是出行意图理解助手。从用户消息提取: 出发城市、目的城市、偏好(省钱/时间/舒适)。"
            "严格只输出JSON: {\"origin\":\"城市名\",\"destination\":\"城市名\",\"preference\":\"省钱|时间|舒适\",\"note\":\"一句话观察\"}。"
            "城市必须是中国真实城市名(如上海/香港/北京/广州/深圳/三亚/澳门/厦门等)。"
            "若用户只说目的地没说起源地, 默认origin为上海。"
        ),
        user=user_message,
    )

    if intent and intent.get("origin") and intent.get("destination"):
        o_name = intent["origin"]
        d_name = intent["destination"]
        pref = intent.get("preference", "省钱")
        note = intent.get("note", "")
        # 映射到 code
        o_code = _CITY_ALIASES.get(o_name)
        d_code = _CITY_ALIASES.get(d_name)
        if o_code and d_code:
            s1.status = "done"
            s1.thought = f"识别到: {o_name} → {d_name}，{pref}优先。{('注意:'+note) if note else ''}"
            res.origin_code, res.dest_code = o_code, d_code
            res.origin_name, res.dest_name = o_name, d_name
        else:
            # 城市名不在本地别名表, 但仍继续 (纯联网模式, 不依赖本地数据)
            s1.status = "done"
            s1.thought = f"识别到: {o_name} → {d_name}，{pref}优先。将联网查询真实票价。"
            res.origin_code = o_code or o_name
            res.dest_code = d_code or d_name
            res.origin_name, res.dest_name = o_name, d_name
    else:
        # LLM 失败, 规则兜底
        if len(rule_cities) >= 2:
            s1.status = "done"
            s1.thought = f"识别到: {_CITY_NAMES[rule_cities[0]]} → {_CITY_NAMES[rule_cities[1]]}"
            res.origin_code, res.dest_code = rule_cities[0], rule_cities[1]
            res.origin_name = _CITY_NAMES[rule_cities[0]]
            res.dest_name = _CITY_NAMES[rule_cities[1]]
        elif len(rule_cities) == 1:
            s1.status = "done"
            res.dest_code = rule_cities[0]
            res.dest_name = _CITY_NAMES[rule_cities[0]]
            res.origin_code, res.origin_name = "SHA", "上海"
            s1.thought = f"识别到目的地 {_CITY_NAMES[rule_cities[0]]}，默认从上海出发。"
        else:
            s1.status = "error"
            s1.thought = "没能识别出出发地和目的地，请明确告知，例如「从上海去香港」。"
            return res

    # ===== Agent 2: 任务规划 =====
    s2 = AgentStep(agent="任务规划", icon="📋", status="thinking",
                   thought="正在拆解搜索步骤...")
    res.steps.append(s2)

    plan = chat(
        system=(
            "你是任务规划助手。用2-3句话简述出行省钱搜索的步骤。"
            "口语化, 不超过60字。例如: 先查直达基准价, 再找中转省钱方案, 最后对比省多少。"
        ),
        user=f"用户要从{res.origin_name}去{res.dest_name}",
        max_tokens=100,
    )
    s2.status = "done"
    s2.thought = plan or f"计划: 1.查{res.origin_name}→{res.dest_name}直达基准 2.搜中转省钱方案 3.对比省多少"

    # ===== Agent 3: 工具调用 (本地中转搜索 + 联网查直达票价) =====
    s3 = AgentStep(agent="工具调用", icon="🔧", status="thinking",
                   thought="正在调用路径搜索引擎 + 联网查询实时直达票价...")
    res.steps.append(s3)

    # 3a. 本地引擎搜中转方案
    search_result = search_fn(res.origin_code, res.dest_code)
    paths = search_result.get("paths", [])
    baselines = search_result.get("baselines", [])
    savings = search_result.get("savings", [])

    # 3b. 联网查真实直达票价 (GLM web_search)
    live_text, live_sources = chat_with_search(
        system=(
            "你是票价查询助手。联网查询中国两地之间的真实交通票价。"
            "返回: 直达高铁二等座票价、最便宜机票价、以及任意更便宜的中转走法。"
            "只给具体数字, 口语简短。"
        ),
        user=f"{res.origin_name}到{res.dest_name}的高铁二等座票价和最便宜机票分别是多少钱？有没有更便宜的中转方案？",
        max_tokens=400,
    )
    s3.sources = live_sources

    # 3c. 联网查结构化路线 (含车次/分段, 供纯联网模式渲染路线卡 + 详情)
    live_prices_text, _ = chat_with_search(
        system=(
            "你是路线查询助手。联网查询后输出严格JSON: "
            '{"cheapest_method":"最便宜走法名","cheapest_price":数字,"cheapest_duration":"耗时",'
            '"segments":[{"label":"段名含车次如G89二等座","mode":"flight|train_hsr|train_sleeper|train_seat|metro|bus|walk_border","price":数字,"duration_min":数字,"depart":"班次","from":"出发地","to":"到达地"}],'
            '"alternatives":[{"method":"方法含车次","price":数字,"segments":[同上]}]}。'
            "mode必选: flight/train_hsr/train_sleeper/train_seat/metro/bus/walk_border。只输出JSON。"
        ),
        user=f"联网查询 {res.origin_name}到{res.dest_name} 的真实交通方案(含车次、每段票价耗时), 输出含segments的结构化JSON。",
        max_tokens=700,
    )
    import json as _json
    parsed_prices = None
    try:
        start = live_prices_text.find("{"); end = live_prices_text.rfind("}")
        if start >= 0 and end > start:
            parsed_prices = _json.loads(live_prices_text[start:end+1])
    except Exception:
        parsed_prices = None

    if not paths and not live_text:
        s3.status = "error"
        s3.thought = f"搜索完成, 但暂时没有 {res.origin_name}→{res.dest_name} 的方案数据。"
        s4 = AgentStep(agent="结果解释", icon="💡", status="done",
                       thought=f"抱歉，暂无 {res.origin_name}→{res.dest_name} 的省钱方案数据。")
        res.steps.append(s4)
        res.reply = s4.thought
        return res

    # 构建工具调用摘要: 本地结果 + 联网结果
    local_summary = ""
    if paths:
        cheapest = min(paths, key=lambda p: p["total_price"])
        local_summary = f"本地引擎找到 {len(paths)} 条中转方案, 最优 ¥{int(cheapest['total_price'])}。"
    live_summary = f"联网查询到实时票价: {live_text[:100]}" if live_text and not live_text.startswith("[LLM_ERROR]") else ""
    s3.status = "done"
    s3.thought = (local_summary + " " + live_summary).strip() or "搜索完成。"

    # 找最省方案 (基于本地中转 vs 联网直达)
    cheapest = min(paths, key=lambda p: p["total_price"]) if paths else None
    best_saving = None
    for sv in savings:
        if sv["savings_price"] > 0:
            if not best_saving or sv["savings_price"] > best_saving["savings_price"]:
                best_saving = sv

    # ===== Agent 4: 结果解释 =====
    s4 = AgentStep(agent="结果解释", icon="💡", status="thinking",
                   thought="正在组织回复...")
    res.steps.append(s4)

    if cheapest and best_saving:
        first_seg_label = cheapest["segments"][0]["label"].split(" ")[0]
        time_diff = best_saving["time_cost_min"]
        if time_diff < 0:
            time_note = "反而更快"
        else:
            h = time_diff // 60
            time_note = f"多花约 {h} 小时" if h > 0 else f"多花 {time_diff} 分钟"

        # 融入联网查到的实时票价信息
        live_context = f" 联网查询到的实时票价参考: {live_text[:150]}" if live_text and not live_text.startswith("[LLM_ERROR]") else ""
        reply = chat(
            system=(
                "你是魔法大脑, 一个交通省钱助手。用简短口语化中文(60字内)告诉用户找到了省钱方案。"
                "自然融入省钱数字, 别像念稿。用第二人称'你'。可以提及联网查到的票价作为对比。"
            ),
            user=(
                f"用户要从{res.origin_name}去{res.dest_name}。本地方案: {first_seg_label}, "
                f"总价¥{int(cheapest['total_price'])}, 比{best_saving['benchmark_name']}"
                f"省¥{int(best_saving['savings_price'])}({int(best_saving['savings_ratio']*100)}%), {time_note}。"
                f"{live_context}"
                f"用一两句话告诉用户这个省钱方案, 可结合联网票价。"
            ),
            max_tokens=150,
        )
        s4.status = "done"
        s4.thought = reply or (
            f"已找到省钱方案: {first_seg_label} ¥{int(cheapest['total_price'])}, "
            f"比{best_saving['benchmark_name']}省¥{int(best_saving['savings_price'])}。"
        )
        s4.sources = live_sources
        res.reply = s4.thought
        # 路线卡
        first_seg = cheapest["segments"][0]
        res.route = {
            "title": first_seg["label"],
            "dept": (first_seg.get("depart") or "—").split(" ")[0][:5] or "—",
            "dept_name": res.origin_name,
            "arr": "次日" if cheapest["total_duration_min"] > 360 else "当日",
            "arr_name": res.dest_name,
            "price": int(cheapest["total_price"]),
            "duration": cheapest["duration_text"],
            "savings": int(best_saving["savings_price"]),
            "origin_code": res.origin_code,
            "dest_code": res.dest_code,
        }
    else:
        # 纯联网模式 (本地无该城市对中转数据): 用联网结构化价格渲染
        if parsed_prices and parsed_prices.get("cheapest_price"):
            cheap_price = int(parsed_prices["cheapest_price"])
            alts = parsed_prices.get("alternatives", [])
            # 找最贵的方案做"划线对比"基准
            all_prices = [cheap_price] + [int(a.get("price", 0)) for a in alts if a.get("price")]
            benchmark_price = max(all_prices) if len(all_prices) > 1 else (int(alts[0].get("price", cheap_price)) if alts else cheap_price)
            savings_amt = benchmark_price - cheap_price
            # 生成自然语言回复
            reply = chat(
                system="你是魔法大脑省钱助手。简短口语(50字内)告诉用户找到了省钱走法。用第二人称。",
                user=f"{res.origin_name}→{res.dest_name}, 最省走法:{parsed_prices.get('cheapest_method','')} ¥{cheap_price}, 对比其他方案最高¥{benchmark_price}, 省¥{savings_amt}。说一句话。",
                max_tokens=100,
            )
            s4.status = "done"
            s4.thought = reply or f"找到{res.origin_name}→{res.dest_name}省钱方案: ¥{cheap_price}, 比最贵方案省¥{savings_amt}。"
            res.reply = s4.thought
            res.route = {
                "title": parsed_prices.get("cheapest_method", f"{res.origin_name}→{res.dest_name}"),
                "dept": "—", "dept_name": res.origin_name,
                "arr": "—", "arr_name": res.dest_name,
                "price": cheap_price,
                "duration": parsed_prices.get("cheapest_duration", "—"),
                "savings": savings_amt,
                "origin_code": res.origin_code,
                "dest_code": res.dest_code,
                "segments": parsed_prices.get("segments", []),
            }
            # 构造替代方案 (供前端划线显示 + 详情)
            res.live_alternatives = alts
        elif live_text and not live_text.startswith("[LLM_ERROR]"):
            s4.status = "done"
            s4.thought = live_text[:200]
            res.reply = live_text
            res.route = {
                "title": f"{res.origin_name}→{res.dest_name}",
                "dept": "—", "dept_name": res.origin_name,
                "arr": "—", "arr_name": res.dest_name,
                "price": 0, "duration": "详见联网信息",
                "savings": 0,
                "origin_code": res.origin_code,
                "dest_code": res.dest_code,
            }
        else:
            s4.status = "done"
            s4.thought = f"{res.origin_name}→{res.dest_name} 暂时查询不到省钱方案, 建议直接走直达。"
            res.reply = s4.thought

    return res


def steps_to_json(res: PipelineResult) -> list[dict]:
    """把 AgentStep 列表转成前端可展示的 JSON。"""
    return [
        {
            "agent": s.agent, "icon": s.icon, "status": s.status, "thought": s.thought,
            "sources": s.sources or [],
        }
        for s in res.steps
    ]
