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

# 主要城市 -> 机场三字码 (携程机票URL用)
AIRPORT_CODES = {
    "上海": "SHA", "北京": "BJS", "广州": "CAN", "深圳": "SZX", "成都": "CTU",
    "重庆": "CKG", "杭州": "HGH", "西安": "SIA", "武汉": "WUH", "南京": "NKG",
    "青岛": "TAO", "厦门": "XMN", "昆明": "KMG", "海口": "HAK", "三亚": "SYX",
    "长沙": "CSX", "郑州": "CGO", "天津": "TSN", "沈阳": "SHE", "大连": "DLC",
    "哈尔滨": "HRB", "济南": "TNA", "福州": "FOC", "南宁": "NNG", "贵阳": "KWE",
    "拉萨": "LXA", "兰州": "LHW", "乌鲁木齐": "URC", "呼和浩特": "HET",
    "银川": "INC", "西宁": "XNN", "石家庄": "SJW", "太原": "TYN", "合肥": "HFE",
    "南昌": "KHN", "长春": "CGQ", "香港": "HKG", "澳门": "MFM", "台北": "TPE",
    "宁波": "NGB", "温州": "WNZ", "无锡": "WUX", "烟台": "YNT", "威海": "WEH",
    "桂林": "KWL", "丽江": "LHG", "黄山": "TXN", "珠海": "ZUH", "汕头": "SWA",
}


def _get_chrome_path():
    chrome_paths = sorted(glob.glob(os.path.expanduser(
        "~/Library/Caches/ms-playwright/chromium-*/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
    )))
    return chrome_paths[-1] if chrome_paths else None


def fetch_train_fares(origin: str, destination: str, timeout_ms: int = 15000) -> list[dict]:
    """抓携程火车票页, 返回 [{train, depart, arrive, duration, seats:[{name,price}]}]。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return []
    url = f"https://trains.ctrip.com/webapp/train/list?ticketType=0&dStation={quote(origin)}&aStation={quote(destination)}"
    text = ""
    with sync_playwright() as p:
        launch_opts = {"headless": True}
        cp = _get_chrome_path()
        if cp:
            launch_opts["executable_path"] = cp
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


def fetch_all_fares(origin: str, destination: str) -> tuple[list[dict], dict | None]:
    """一个浏览器实例抓火车+飞机, 避免连续启动冲突。返回 (train_fares, flight_info)。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return ([], None)
    train_text = ""
    flight_text = ""
    with sync_playwright() as p:
        launch_opts = {"headless": True}
        cp = _get_chrome_path()
        if cp:
            launch_opts["executable_path"] = cp
        browser = p.chromium.launch(**launch_opts)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        )
        # 火车页
        try:
            train_url = f"https://trains.ctrip.com/webapp/train/list?ticketType=0&dStation={quote(origin)}&aStation={quote(destination)}"
            page.goto(train_url, timeout=15000, wait_until="domcontentloaded")
            page.wait_for_timeout(6000)
            train_text = page.inner_text("body")
        except Exception:
            train_text = ""
        # 飞机页 (同实例)
        o_code = AIRPORT_CODES.get(origin)
        d_code = AIRPORT_CODES.get(destination)
        if o_code and d_code:
            try:
                flight_url = f"https://flights.ctrip.com/online/list/oneway-{o_code.lower()}-{d_code.lower()}?depdate=2026-07-25"
                page.goto(flight_url, timeout=15000, wait_until="domcontentloaded")
                page.wait_for_timeout(5000)
                flight_text = page.inner_text("body")
            except Exception:
                flight_text = ""
        browser.close()
    # 解析
    train_fares = parse_ctrip_text(train_text) if train_text else []
    flight_info = None
    if flight_text:
        import re as _re
        prices = [int(x) for x in _re.findall(r"¥(\d{3,5})", flight_text) if 100 < int(x) < 9999]
        if prices:
            flight_info = {"price": min(prices), "source": f"携程机票 {origin}→{destination}"}
    return (train_fares, flight_info)


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
    duration_re = re.compile(r"^(\d{1,2})时(\d{1,2})分$")

    i = 0
    while i < len(lines):
        line = lines[i]
        m = train_re.match(line)
        if m:
            train_no = m.group(1)
            # 往前找出发时间和运行时长
            depart = ""
            duration_min = 0
            for j in range(max(0, i-5), i):
                if re.match(r"^\d{1,2}:\d{2}$", lines[j]):
                    depart = lines[j]
                dm = duration_re.match(lines[j])
                if dm:
                    duration_min = int(dm.group(1)) * 60 + int(dm.group(2))
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
                results.append({"train": train_no, "depart": depart, "duration_min": duration_min, "seats": seats})
        i += 1

    # 去重
    seen = {}
    for t in results:
        if t["train"] not in seen or len(t["seats"]) > len(seen[t["train"]]["seats"]):
            seen[t["train"]] = t
    return list(seen.values())[:8]


def fetch_flight_price(origin: str, destination: str, timeout_ms: int = 20000) -> dict | None:
    """抓携程机票页, 返回最低机票价 {price, airline_info}。"""
    o_code = AIRPORT_CODES.get(origin)
    d_code = AIRPORT_CODES.get(destination)
    if not o_code or not d_code:
        return None
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    chrome_paths = sorted(glob.glob(os.path.expanduser(
        "~/Library/Caches/ms-playwright/chromium-*/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
    )))
    url = f"https://flights.ctrip.com/online/list/oneway-{o_code.lower()}-{d_code.lower()}?depdate=2026-07-25"
    import re as _re
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
        return None
    prices = [int(x) for x in _re.findall(r"¥(\d{3,5})", text) if 100 < int(x) < 9999]
    if not prices:
        return None
    return {"price": min(prices), "source": f"携程机票 {origin}→{destination}"}


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
