"""榜单抓取公共工具：UA、请求、规范化。"""
from __future__ import annotations

import time
import unicodedata
from typing import Optional

import requests

USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)

# 纵横对 iPhone UA 直接 500，必须用桌面 UA
DESKTOP_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

_session = requests.Session()
_session.headers.update(
    {
        "User-Agent": USER_AGENT,
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
)

_last_fetch_ts = 0.0


def fetch(
    url: str,
    timeout: int = 15,
    encoding: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> str:
    """GET 页面文本；站间限速 ≥1s。"""
    global _last_fetch_ts
    wait = 1.0 - (time.time() - _last_fetch_ts)
    if wait > 0:
        time.sleep(wait)
    headers = {"User-Agent": user_agent} if user_agent else {}
    resp = _session.get(url, timeout=timeout, headers=headers)
    _last_fetch_ts = time.time()
    resp.raise_for_status()
    if encoding:
        resp.encoding = encoding
    return resp.text


def normalize_text(text: str) -> str:
    """trim + 全角转半角 + lower，用于去重键。"""
    t = (text or "").strip()
    t = unicodedata.normalize("NFKC", t)
    return t.lower()


def dedup_key(source: str, title: str, author: str) -> str:
    return f"{source}|{normalize_text(title)}|{normalize_text(author)}"


def empty_book(rank: int, title: str, author: str = "", **kwargs) -> dict:
    return {
        "rank": rank,
        "title": title.strip(),
        "author": (author or "").strip(),
        "category": kwargs.get("category", ""),
        "coverURL": kwargs.get("coverURL", ""),
        "bookURL": kwargs.get("bookURL", ""),
        "description": kwargs.get("description", ""),
        "badge": kwargs.get("badge", ""),
        "source": kwargs.get("source", ""),
        "sourceId": kwargs.get("sourceId", ""),
    }
