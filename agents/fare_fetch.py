"""
魔法大脑 - 携程火车票抓取
========================

用 Playwright 渲染携程火车票页, 提取真实车次与票价。
页面结构: 车次号后跟 "座位类型 价格 预订/抢票" 序列。
"""

from __future__ import annotations
import os
import re
import glob
from urllib.parse import quote

SEAT_NAMES = ["硬座", "硬卧", "软卧", "二等座", "一等座", "商务座", "无座", "高级软卧", "动卧"]


def fetch_train_fares(origin: str, destination: str, timeout_ms: int = 15000) -> list[dict]:
    """抓携程火车票页, 返回 [{train, depart, arrive, duration, seats:[{name,price}]}]。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return []

    url = f"https://trains.ctrip.com/webapp/train/list?ticketType=0&dStation={quote(origin)}&aStation={quote(destination)}"
    chrome_paths = sorted(glob.glob(os.path.expanduser(
        "~/Library/Caches/ms-playwright/chromium-*/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
    )))
    text = ""
    with sync_playwright() as p:
        launch_opts = {"headless": True}
        if chrome_paths:
            launch_opts["executable_path"] = chrome_paths[-1]
        browser = p.chromium.launch(**launch_opts)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        )
        try:
            page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
            page.wait_for_timeout(6000)
            text = page.inner_text("body")
        except Exception:
            text = ""
        browser.close()

    if not text:
        return []

    return parse_ctrip_text(text)


def parse_ctrip_text(text: str) -> list[dict]:
    """解析携程渲染后的文本, 提取车次和票价。

    页面结构 (每车次块):
      HH:MM          <- 出发时间
      出发站
      XX时XX分        <- 运行时长
      车次号          <- K4916 / Z40 / G99 等
      HH:MM          <- 到达时间
      (+N)           <- 跨天
      到达站
      ...登录/余票...
      硬座            <- 座位名
      385.5          <- 价格
      预订/抢票
      硬卧
      649.5
      ...
    """
    results = []
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    train_re = re.compile(r"^([ZTKDGC]\d{1,5})$")
    price_re = re.compile(r"^\d{2,5}(\.\d)?$")

    i = 0
    while i < len(lines):
        line = lines[i]
        m = train_re.match(line)
        if m:
            train_no = m.group(1)
            # 往前找出发时间
            depart = ""
            for j in range(max(0, i-4), i):
                if re.match(r"^\d{1,2}:\d{2}$", lines[j]):
                    depart = lines[j]
            # 往后找座位和价格
            seats = []
            j = i + 1
            while j < len(lines) and j < i + 40:
                lj = lines[j]
                if lj in SEAT_NAMES:
                    # 下一个数字是价格
                    if j + 1 < len(lines) and price_re.match(lines[j+1]):
                        try:
                            price = float(lines[j+1])
                            if 5 < price < 10000:
                                seats.append({"name": lj, "price": price})
                                j += 2
                                continue
                        except ValueError:
                            pass
                # 遇到下一个车次就停
                if train_re.match(lj) and lj != train_no:
                    break
                j += 1
            if seats:
                results.append({"train": train_no, "depart": depart, "seats": seats})
        i += 1

    # 去重
    seen = {}
    for t in results:
        if t["train"] not in seen or len(t["seats"]) > len(seen[t["train"]]["seats"]):
            seen[t["train"]] = t
    return list(seen.values())[:8]


def fares_to_text(origin: str, destination: str, fares: list[dict]) -> str:
    """把抓取的票价转成文本。"""
    if not fares:
        return ""
    lines = [f"{origin}到{destination}的真实火车票价(来源携程实时):"]
    for t in fares:
        seat_str = " ".join(f"{s['name']}¥{s['price']}" for s in t["seats"])
        dep = t.get("depart", "")
        lines.append(f"{t['train']} {dep}出发 {seat_str}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    o, d = (sys.argv[1:3] if len(sys.argv) >= 3 else ("上海", "乌鲁木齐"))
    fares = fetch_train_fares(o, d)
    print(fares_to_text(o, d, fares))
