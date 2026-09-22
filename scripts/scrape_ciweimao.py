"""刺猬猫阅读公开书库/榜单抓取（元数据 only）。

www.ciweimao.com/rank 已 404；WAP 书库 `https://wap.ciweimao.com/book_list`
带「人气排序」书单，作为人气榜源（页内约 10 条，limit 截断）。
"""
from __future__ import annotations

import re
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from common import empty_book, fetch

RANK_URL = "https://wap.ciweimao.com/book_list"
_BOOK_ID_RE = re.compile(r"/book/(\d+)")


def _parse(html: str, limit: int = 20) -> List[dict]:
    soup = BeautifulSoup(html, "html.parser")
    books: List[dict] = []
    seen = set()
    for li in soup.select("li.book-item"):
        a = li.find("a", href=re.compile(r"/book/\d+"))
        if not a:
            continue
        href = urljoin("https://wap.ciweimao.com", a.get("href") or "")
        if href in seen:
            continue
        title_el = li.select_one("h3.title, .title")
        title = title_el.get_text(strip=True) if title_el else a.get_text(strip=True)
        # 去掉「14.4万」等子 span
        if title_el:
            for span in title_el.select("span"):
                span.decompose()
            title = title_el.get_text(strip=True)
        if not title:
            continue
        m = _BOOK_ID_RE.search(href)
        source_id = m.group(1) if m else ""
        author_el = li.select_one(".author")
        author_raw = author_el.get_text(" ", strip=True) if author_el else ""
        # 格式「作者 / 分类」
        author = author_raw.split("/")[0].strip() if author_raw else ""
        category = author_raw.split("/")[1].strip() if "/" in author_raw else ""
        img = li.select_one("img")
        cover = ""
        if img:
            cover = img.get("data-original") or img.get("data-src") or img.get("src") or ""
            if cover.startswith("//"):
                cover = "https:" + cover
        rank = len(books) + 1
        seen.add(href)
        books.append(
            empty_book(
                rank,
                title,
                author,
                category=category,
                coverURL=cover,
                bookURL=href,
                badge="",
                source="ciweimao",
                sourceId=source_id,
            )
        )
        if len(books) >= limit:
            break
    return books


def scrape(limit: int = 20) -> List[dict]:
    try:
        html = fetch(RANK_URL, encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        print(f"[ciweimao] fail book_list: {exc}")
        return []
    if len(html) < 500:
        print(f"[ciweimao] fail book_list: short body {len(html)}B")
        return []
    books = _parse(html, limit=limit)
    if books:
        print(f"[ciweimao] ciweimao_rank: {len(books)}")
        return [{"type": "ciweimao_rank", "name": "刺猬猫人气榜", "books": books}]
    print("[ciweimao] empty parse")
    return []
