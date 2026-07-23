#!/usr/bin/env python3
"""
魔法大脑 - CLI 冒烟测试
=======================

W1 验收门:
  输入起点终点, 输出中转省钱方案 + 与直达基准的省钱对比。

用法:
  python3 cli.py
  python3 cli.py 上海 香港

不依赖第三方库, 纯标准库 + 本地引擎。
"""

from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine import load_graph, search, Weights
from engine.arbitrage import compare_to_baseline


# 城市名 -> code 的别名 (用户输入中文也行)
CITY_ALIAS = {
    "上海": "SHA", "shanghai": "SHA",
    "香港": "HKG", "hongkong": "HKG", "hong kong": "HKG",
    "北京": "BJS", "beijing": "BJS",
    "广州": "CAN", "guangzhou": "CAN",
    "深圳": "SZX", "shenzhen": "SZX",
    "澳门": "MFM", "macao": "MFM", "macau": "MFM",
    "厦门": "XMN", "xiamen": "XMN",
    "三亚": "SYX", "sanya": "SYX",
    "海口": "HAK", "haikou": "HAK",
    "昆明": "KMG", "kunming": "KMG",
    "成都": "CTU", "chengdu": "CTU",
    "重庆": "CKG", "chongqing": "CKG",
    "西安": "SIA", "xian": "SIA",
    "武汉": "WUH", "wuhan": "WUH",
    "南京": "NKG", "nanjing": "NKG",
    "杭州": "HGH", "hangzhou": "HGH",
    "青岛": "TAO", "qingdao": "TAO",
    "哈尔滨": "HRB", "harbin": "HRB",
    "乌鲁木齐": "URC", "urumqi": "URC",
}


def resolve(code_or_name: str) -> str:
    code_or_name = code_or_name.strip()
    if code_or_name in CITY_ALIAS:
        return CITY_ALIAS[code_or_name]
    return code_or_name.upper()


def main() -> None:
    print("=" * 60)
    print("  魔法大脑 Magic Brain — 交通套利搜索引擎")
    print("=" * 60)

    graph, baselines = load_graph()
    print(f"\n[数据] 图节点 {len(graph.nodes)} 个, 边 {sum(len(v) for v in graph.adj.values())} 条")
    print(f"[数据] 直达基准 {len(baselines)} 条")

    # 输入
    if len(sys.argv) >= 3:
        origin_in, dest_in = sys.argv[1], sys.argv[2]
    else:
        origin_in = input("\n起点 (如 上海): ").strip()
        dest_in = input("终点 (如 香港): ").strip()

    origin = resolve(origin_in)
    dest = resolve(dest_in)
    print(f"\n查询: {origin} → {dest}")

    if origin not in graph.nodes or dest not in graph.nodes:
        print(f"\n[!] 起点或终点不在图中。当前节点: {sorted(graph.nodes.keys())}")
        print("    (W1 只有上海→香港数据, 后续扩充)")
        sys.exit(1)

    # 搜索中转省钱路径
    paths = search(graph, origin, dest, weights=Weights(), top_k=5)
    if not paths:
        print("\n[!] 未找到 {origin}→{dest} 的路径。")
        sys.exit(1)

    print(f"\n找到 {len(paths)} 条候选路径:\n")
    for i, p in enumerate(paths, 1):
        print(f"--- 方案 {i} ---")
        print(p.describe())
        print()

    # 与直达基准对比
    print("=" * 60)
    print("  省钱对比 (vs 直达基准)")
    print("=" * 60)
    from engine.loader import get_baselines_for
    matched = get_baselines_for(baselines, origin, dest)
    if not matched:
        print(f"\n[!] 未找到 {origin}→{dest} 的直达基准, 跳过对比。")
    for b in matched:
        print(f"\n■ 基准: {b['name']} — ¥{b['total_price']} / {b['total_duration_min']}min / {b.get('transfers',0)}换乘")
        for i, p in enumerate(paths, 1):
            rep = compare_to_baseline(
                path=p,
                benchmark_id=b.get("baseline_id", ""),
                benchmark_name=b["name"],
                benchmark_price=b["total_price"],
                benchmark_duration_min=b["total_duration_min"],
            )
            print(f"  方案{i}: {rep.headline()}")
            print(f"          {rep.verdict}")
    print("\n" + "=" * 60)
    print("  魔法大脑 — 让每一程更省")
    print("=" * 60)


if __name__ == "__main__":
    main()
