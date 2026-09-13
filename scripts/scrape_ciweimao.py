"""刺猬猫阅读公开榜单页抓取（元数据 only）。"""
from __future__ import annotations

import re
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from common import empty_book, fetch

RANK_PAGES = [
    {
        "type": "ciweimao_rank",
        "name": "刺猬猫推荐榜",
        "url": "https://www.ciweimao.com/rank",
    },
]

_BOOK_ID_RE = re.compile(r"/book-detail/(\d+)|/book/(\d+)")


def _parse(html: str, limit: int = 20) -> List[dict]:
    soup = BeautifulSoup(html, "html.parser")
    books: List[dict] = []
    rows = soup.select(".rank-book-list li, .book-list li, .rank-list li, li.book-item")
    if not rows:
        rows = soup.select("li")
    seen = set()
    rank = 0
    for row in rows:
        a = row.select_one("a[href*='book']")
        if not a:
            continue
        title = a.get_text(strip=True)
        href = urljoin("https://www.ciweimao.com", a.get("href") or "")
        if not title or len(title) > 80 or href in seen:
            continue
        m = _BOOK_ID_RE.search(href)
        source_id = (m.group(1) or m.group(2)) if m else ""
        author_el = row.select_one(".author a, .author, .writer")
        author = author_el.get_text(strip=True) if author_el else ""
        img = row.select_one("img")
        cover = ""
        if img:
            cover = img.get("src") or img.get("data-src") or ""
            if cover.startswith("//"):
                cover = "https:" + cover
        rank += 1
        seen.add(href)
        books.append(
            empty_book(
                rank,
                title,
                author,
                coverURL=cover,
                bookURL=href,
                source="ciweimao",
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
            books = _parse(html, limit=limit)
        except Exception as exc:  # noqa: BLE001
            print(f"[ciweimao] fail {page['type']}: {exc}")
            continue
        if books:
            groups.append({"type": page["type"], "name": page["name"], "books": books})
            print(f"[ciweimao] {page['type']}: {len(books)}")
    return groups
