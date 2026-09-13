"""起点中文网公开榜单页抓取（元数据 only）。"""
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
        "url": "https://www.qidian.com/rank/yuepiao",
    },
    {
        "type": "qidian_hotsales",
        "name": "起点畅销榜",
        "url": "https://www.qidian.com/rank/hotsales",
    },
    {
        "type": "qidian_newbook",
        "name": "起点新书榜",
        "url": "https://www.qidian.com/rank/newauthor",
    },
]

_BOOK_ID_RE = re.compile(r"/book/(\d+)")


def _parse_rank_page(html: str, page: dict, limit: int = 20) -> List[dict]:
    soup = BeautifulSoup(html, "html.parser")
    books: List[dict] = []
    rows = soup.select("div.book-list ul li, .rank-list li, .book-img-text ul li")
    if not rows:
        rows = soup.select("[data-rank], .book-mid-info")

    seen = set()
    rank = 0
    for row in rows:
        a = row.select_one("a[href*='/book/'], h2 a, h4 a, .book-name a")
        if not a:
            continue
        title = a.get_text(strip=True)
        href = urljoin("https://www.qidian.com", a.get("href") or "")
        if not title or href in seen:
            continue
        m = _BOOK_ID_RE.search(href)
        source_id = m.group(1) if m else ""
        author_el = row.select_one(".author a, .name a, .author")
        author = author_el.get_text(strip=True) if author_el else ""
        cat_el = row.select_one(".category, .type")
        category = cat_el.get_text(strip=True) if cat_el else ""
        img = row.select_one("img")
        cover = ""
        if img:
            cover = img.get("src") or img.get("data-src") or ""
            if cover.startswith("//"):
                cover = "https:" + cover
        badge_el = row.select_one(".total, .update, .score, .num")
        badge = badge_el.get_text(strip=True) if badge_el else ""

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
            books = _parse_rank_page(html, page, limit=limit)
        except Exception as exc:  # noqa: BLE001
            print(f"[qidian] fail {page['type']}: {exc}")
            continue
        if books:
            groups.append({"type": page["type"], "name": page["name"], "books": books})
            print(f"[qidian] {page['type']}: {len(books)}")
    return groups
