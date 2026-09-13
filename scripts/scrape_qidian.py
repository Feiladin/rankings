"""起点中文网移动端公开榜单页抓取（元数据 only）。

PC www.qidian.com/rank 易被 WAF 拦截；移动端 m.qidian.com/rank/<key> 结构稳定。
"""
from __future__ import annotations

import re
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from common import empty_book, fetch

RANK_PAGES = [
    {
        "type": "qidian_yuepiao",
        "name": "起点月票榜",
        "url": "https://m.qidian.com/rank/yuepiao",
    },
    {
        "type": "qidian_hotsales",
        "name": "起点畅销榜",
        "url": "https://m.qidian.com/rank/hotsales",
    },
    {
        "type": "qidian_newbook",
        "name": "起点新书榜",
        "url": "https://m.qidian.com/rank/newauthor",
    },
]

_BOOK_ID_RE = re.compile(r"/book/(\d+)")


def _parse_rank_page(html: str, limit: int = 20) -> List[dict]:
    soup = BeautifulSoup(html, "html.parser")
    books: List[dict] = []
    # CSS Module 类名带 hash，用属性包含匹配
    items = soup.select("a[class*='bookItem']")
    seen = set()
    rank = 0
    for item in items:
        title_el = item.find("h2")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        href = urljoin("https://m.qidian.com", item.get("href") or "")
        if not title or href in seen:
            continue
        m = _BOOK_ID_RE.search(href)
        source_id = m.group(1) if m else ""
        badge_el = item.select_one("[class*='bookTitleR']")
        badge = badge_el.get_text(strip=True) if badge_el else ""
        # 作者 · 分类 · 字数
        author = ""
        category = ""
        for node in item.find_all(["p", "div", "span"]):
            text = node.get_text(" ", strip=True)
            if "·" in text and len(text) < 50:
                parts = [p.strip() for p in text.split("·")]
                if parts:
                    author = parts[0]
                if len(parts) > 1:
                    category = parts[1]
                break
        img = item.select_one("img")
        cover = ""
        if img:
            # 优先 data-src（真实封面）；src 常是站内统一占位图
            cover = img.get("data-src") or img.get("data-original") or img.get("src") or ""
            if cover.startswith("//"):
                cover = "https:" + cover

        rank += 1
        seen.add(href)
        books.append(
            empty_book(
                rank,
                title,
                author,
                category=category,
                coverURL=cover,
                bookURL=href,
                badge=badge,
                source="qidian",
                sourceId=source_id,
            )
        )
        if rank >= limit:
            break
    return books


def scrape(limit: int = 20) -> List[dict]:
    groups: List[dict] = []
    for page in RANK_PAGES:
        try:
            html = fetch(page["url"], encoding="utf-8")
            if len(html) < 500:
                print(f"[qidian] fail {page['type']}: short body ({len(html)}B) possible WAF")
                continue
            books = _parse_rank_page(html, limit=limit)
        except Exception as exc:  # noqa: BLE001
            print(f"[qidian] fail {page['type']}: {exc}")
            continue
        if books:
            groups.append({"type": page["type"], "name": page["name"], "books": books})
            print(f"[qidian] {page['type']}: {len(books)}")
        else:
            print(f"[qidian] empty parse {page['type']}")
    return groups
