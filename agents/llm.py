"""
魔法大脑 - GLM 客户端封装
========================

通过 Anthropic 兼容端点调用智谱 GLM-4.7。
统一封装, 供各 Agent 使用。
"""

from __future__ import annotations
import os
import httpx

# 加载 .env
from pathlib import Path
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

API_KEY = os.getenv("GLM_API_KEY", "")
BASE_URL = os.getenv("GLM_BASE_URL", "https://open.bigmodel.cn/api/anthropic")
MODEL = os.getenv("GLM_MODEL", "GLM-4.7")


def chat(system: str, user: str, max_tokens: int = 300, temperature: float = 0.7) -> str:
    """调用 GLM, 返回纯文本回复。

    Anthropic 兼容格式: /v1/messages, x-api-key 认证。
    """
    if not API_KEY:
        return ""
    try:
        r = httpx.post(
            f"{BASE_URL}/v1/messages",
            headers={
                "x-api-key": API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": MODEL,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
            timeout=40,
        )
        r.raise_for_status()
        data = r.json()
        # 提取文本
        for block in data.get("content", []):
            if block.get("type") == "text":
                return block["text"].strip()
        return ""
    except Exception as e:
        return f"[LLM_ERROR] {e}"


def chat_json(system: str, user: str, max_tokens: int = 400) -> dict | None:
    """调用 GLM 并解析 JSON 输出。要求 system 指示输出 JSON。"""
    raw = chat(system, user, max_tokens=max_tokens, temperature=0.3)
    if not raw or raw.startswith("[LLM_ERROR]"):
        return None
    # 容错: 去掉 markdown 代码块
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
    # 找第一个 { 和最后一个 }
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        import json
        try:
            return json.loads(raw[start:end+1])
        except Exception:
            return None
    return None


def web_search(query: str, max_results: int = 5) -> list[dict]:
    """用 DuckDuckGo (ddgs) 联网搜索, 免费、无 key、无日限。

    返回 [{title, url, snippet}]。
    """
    try:
        from ddgs import DDGS
        results = []
        for r in DDGS().text(query, max_results=max_results):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("href") or r.get("link") or r.get("url", ""),
                "snippet": (r.get("body") or r.get("content") or "")[:300],
            })
        return results
    except Exception:
        return []


def chat_with_search(system: str, user: str, max_tokens: int = 600) -> tuple[str, list[dict]]:
    """搜索 + GLM 解析的两步联网 (不耗 GLM web_search 额度)。

    1. 用 user 作为搜索词, DuckDuckGo 搜索
    2. 把搜索摘要喂给 GLM, 按 system 指示解析

    返回 (GLM 解析文本, 搜索来源列表)。
    """
    sources = web_search(user, max_results=5)
    if not sources:
        return ("", [])
    # 拼接搜索摘要
    search_context = "\n\n".join(
        f"【来源{i+1}】{s['title']}\n{s['snippet']}" for i, s in enumerate(sources)
    )
    prompt = f"基于以下联网搜索结果回答:\n\n{search_context}\n\n{user}"
    reply = chat(system, prompt, max_tokens=max_tokens, temperature=0.4)
    return (reply, sources)
