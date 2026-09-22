"""纵横中文网公开榜单页抓取（元数据 only）。

注意：iPhone UA 会 500，必须 DESKTOP_USER_AGENT。
榜单页 SSR：`https://www.zongheng.com/rank` 含多组 `section.zh-modules-rank-book`。
"""
from __future__ import annotations

import re
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from common import DESKTOP_USER_AGENT, empty_book, fetch

RANK_URL = "https://www.zongheng.com/rank"
_BOOK_ID_RE = re.compile(r"/detail/(\d+)")

# 页内单元末尾的热度单位 → 榜单 type/名称
_UNIT_HINTS = [
    ("月票", "zongheng_yuepiao", "纵横月票榜"),
    ("人气", "zongheng_renqi", "纵横人气榜"),
    ("点击", "zongheng_click", "纵横点击榜"),
    ("推荐", "zongheng_recommend", "纵横推荐榜"),
]


def _parse(html: str, limit: int = 20) -> List[dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("div.zh-modules-rank-book")
    if not items:
        return []

    # 按“单位词”拆成多组；无单位的归入 misc
    buckets: dict[str, dict] = {}
    order: List[str] = []

    def bucket_for(text: str) -> tuple[str, str]:
        # 单元文案形如「11622 月票」；仅部分 item 带单位，按关键字归类
        if "月票" in text:
            return "zongheng_yuepiao", "纵横月票榜"
        if "人气" in text:
            return "zongheng_renqi", "纵横人气榜"
        if "点击" in text:
            return "zongheng_click", "纵横点击榜"
        if "推荐" in text:
            return "zongheng_recommend", "纵横推荐榜"
        return "zongheng_hot", "纵横热榜"

    seen_global: set[str] = set()
    current_key = "zongheng_hot"
    current_name = "纵横热榜"
    for item in items:
        a = item.find("a", href=re.compile(r"/detail/\d+"))
        if not a:
            continue
        title_el = item.select_one(".book-rank--title-text, .bookeName")
        title = title_el.get_text(strip=True) if title_el else a.get_text(strip=True)
        href = urljoin("https://www.zongheng.com", a.get("href") or "")
        if not title or href in seen_global:
            continue
        m = _BOOK_ID_RE.search(href)
        source_id = m.group(1) if m else ""
        author_el = item.select_one(".auther, .author")
        author = author_el.get_text(strip=True) if author_el else ""
        unit_el = item.select_one(".rank-content-default__rank-text, .book-rank--hover-main")
        unit = unit_el.get_text(" ", strip=True) if unit_el else item.get_text(" ", strip=True)[:40]
        # 归入榜单：命中单位词则切换当前桶，否则沿用同组
        full_text = item.get_text(" ", strip=True)
        if any(k in full_text for k in ("月票", "人气", "点击", "推荐")):
            current_key, current_name = bucket_for(full_text)
        img = item.select_one("img")
        cover = ""
        if img:
            cover = img.get("data-src") or img.get("src") or ""
            if cover.startswith("//"):
                cover = "https:" + cover

        if current_key not in buckets:
            buckets[current_key] = {"type": current_key, "name": current_name, "books": []}
            order.append(current_key)
        rank = len(buckets[current_key]["books"]) + 1
        seen_global.add(href)
        buckets[current_key]["books"].append(
            empty_book(
                rank,
                title,
                author,
                coverURL=cover,
                bookURL=href,
                badge=unit,
                source="zongheng",
                sourceId=source_id,
            )
        )

    groups: List[dict] = []
    for key in order:
        books = buckets[key]["books"][:limit]
        if books:
            groups.append({"type": buckets[key]["type"], "name": buckets[key]["name"], "books": books})
    return groups


def scrape(limit: int = 20) -> List[dict]:
    try:
        html = fetch(RANK_URL, encoding="utf-8", user_agent=DESKTOP_USER_AGENT)
    except Exception as exc:  # noqa: BLE001
        print(f"[zongheng] fail rank: {exc}")
        return []
    if len(html) < 500:
        print(f"[zongheng] fail rank: short body {len(html)}B")
        return []
    groups = _parse(html, limit=limit)
    for g in groups:
        print(f"[zongheng] {g['type']}: {len(g['books'])}")
    if not groups:
        print("[zongheng] empty parse")
    return groups
