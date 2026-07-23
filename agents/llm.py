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


def chat_with_search(system: str, user: str, max_tokens: int = 600) -> tuple[str, list[dict]]:
    """调用 GLM 并启用 web_search 工具, 联网查询。

    返回 (最终文本回复, 搜索结果摘要列表)。
    搜索结果含 title/url/content, 供展示数据来源。
    """
    if not API_KEY:
        return ("", [])
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
                "temperature": 0.4,
                "system": system,
                "messages": [{"role": "user", "content": user}],
                "tools": [{"type": "web_search_20250305", "name": "web_search"}],
            },
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        text_parts = []
        sources = []
        for block in data.get("content", []):
            btype = block.get("type")
            if btype == "text":
                text_parts.append(block["text"])
            elif btype == "tool_result":
                # 提取搜索结果摘要
                import json as _json
                raw = block.get("content", "")
                try:
                    results = _json.loads(raw) if isinstance(raw, str) else raw
                    if isinstance(results, list):
                        for item in results:
                            txt_blocks = item.get("text", [])
                            for tb in txt_blocks:
                                sources.append({
                                    "title": tb.get("title", ""),
                                    "url": tb.get("link", ""),
                                    "snippet": (tb.get("content") or "")[:200],
                                })
                except Exception:
                    pass
        return ("\n".join(text_parts).strip(), sources)
    except Exception as e:
        return (f"[LLM_ERROR] {e}", [])
