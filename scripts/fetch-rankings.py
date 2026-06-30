#!/usr/bin/env python3
"""
起点中文网排行榜爬虫

爬取起点移动版三大榜单（月票榜/畅销榜/阅读榜），输出为 JSON 文件。

使用方式:
    python3 scripts/fetch-rankings.py                    # 输出到 docs/rankings.json
    python3 scripts/fetch-rankings.py --output path.json # 自定义输出路径

依赖:
    pip install requests beautifulsoup4

数据来源:
    - 月票榜: https://m.qidian.com/rank/yuepiao/
    - 畅销榜: https://m.qidian.com/rank/hotsales/
    - 阅读榜: https://m.qidian.com/rank/readindex/
"""

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

import requests
from bs4 import BeautifulSoup

# ── 配置 ──────────────────────────────────────────────────────────────────────

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/16.0 Mobile/15E148 Safari/604.1"
)

HEADERS = {
    "User-Agent": MOBILE_UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

REQUEST_DELAY = 1.0  # 每次请求间隔（秒），避免触发反爬

RANKINGS = [
    {"type": "yuepiao", "name": "月票榜", "url": "https://m.qidian.com/rank/yuepiao/"},
    {"type": "hotsales", "name": "畅销榜", "url": "https://m.qidian.com/rank/hotsales/"},
    {"type": "readindex", "name": "阅读榜", "url": "https://m.qidian.com/rank/readindex/"},
]

# ── 数据模型 ───────────────────────────────────────────────────────────────────

@dataclass
class Book:
    """单本书的排行信息"""
    rank: int
    title: str
    author: str
    category: str
    coverURL: str
    bookURL: str
    description: str = ""
    badge: str = ""  # 月票数/畅销标签等辅助信息


@dataclass
class Ranking:
    """一种榜单"""
    type: str
    name: str
    books: list = field(default_factory=list)


@dataclass
class RankingsOutput:
    """最终输出结构"""
    updatedAt: str
    rankings: list = field(default_factory=list)


# ── 工具函数 ───────────────────────────────────────────────────────────────────

def safe_text(element) -> str:
    """安全提取元素的纯文本，去除多余空白"""
    if element is None:
        return ""
    return element.get_text(strip=True)


def resolve_url(href: str) -> str:
    """补全 URL（处理 // 协议相对路径 和 /path 绝对路径）"""
    if not href:
        return ""
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        return "https://m.qidian.com" + href
    return href


def extract_cover_url(img) -> str:
    """从 img 标签提取封面 URL（优先 data-src，其次 src）"""
    url = img.get("data-src") or img.get("src") or ""
    return resolve_url(url)


def fetch_soup(url: str) -> BeautifulSoup:
    """GET 请求页面并返回 BeautifulSoup 对象"""
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return BeautifulSoup(resp.text, "html.parser")


# ── 解析器 ─────────────────────────────────────────────────────────────────────

def parse_ranking_page(soup: BeautifulSoup, rank_type: str) -> list:
    """
    解析排行榜页面，提取书籍列表。

    起点移动版使用 CSS Module（类名 hash 每次构建会变），
    因此使用 CSS 属性选择器匹配 class 前缀来定位元素。
    """
    books = []
    items = soup.select("div.y-list__item")

    for item in items:
        # --- 封面 & 书籍链接 ---
        link = item.find("a", href=re.compile(r"/book/\d+"))
        if not link:
            continue

        img = link.find("img", attrs={"data-src": re.compile(r"bookcover", re.I)})
        if img is None:
            img = link.find("img", src=re.compile(r"bookcover", re.I))
        if img is None:
            continue

        cover_url = extract_cover_url(img)
        book_url = resolve_url(link.get("href", ""))

        # --- 右侧信息区 ---
        right = link.find("div", class_=lambda c: c and "_bookItemRight" in c)
        if not right:
            continue

        # --- 排名 ---
        rank_div = right.find("div", class_=lambda c: c and "_ranking" in c)
        rank = int(safe_text(rank_div)) if rank_div else 0

        # --- 书名 ---
        title_elem = right.find("h2", class_=lambda c: c and "_title" in c)
        title = safe_text(title_elem)

        if not title:
            continue

        # --- Badge（月票榜特有：如 "9.97万月票"） ---
        badge_div = right.find("div", class_=lambda c: c and "_bookTitleR" in c)
        badge = safe_text(badge_div) if badge_div else ""

        # --- 简介 ---
        desc_elem = right.find("p", class_=lambda c: c and "_bookDesc" in c)
        description = safe_text(desc_elem) if desc_elem else ""

        # --- 作者 / 分类 / 字数（格式：作者·分类·字数） ---
        author = ""
        category = ""
        sub_elem = right.find("p", class_=lambda c: c and "_subTitle" in c)
        if sub_elem:
            sub_text = sub_elem.get_text(strip=True)
            parts = [p.strip() for p in sub_text.split("·") if p.strip()]
            if len(parts) >= 1:
                author = parts[0]
            if len(parts) >= 2:
                category = parts[1]

        books.append(Book(
            rank=rank,
            title=title,
            author=author,
            category=category,
            coverURL=cover_url,
            bookURL=book_url,
            description=description,
            badge=badge,
        ))

    return books


def fetch_all_rankings() -> RankingsOutput:
    """依次抓取所有榜单，返回合并结果"""
    output = RankingsOutput(updatedAt=time.strftime("%Y-%m-%d"))

    for i, ranking_info in enumerate(RANKINGS):
        print(f"[{i + 1}/{len(RANKINGS)}] 正在抓取 {ranking_info['name']}...", flush=True)

        try:
            soup = fetch_soup(ranking_info["url"])
            books = parse_ranking_page(soup, ranking_info["type"])
            ranking = Ranking(type=ranking_info["type"], name=ranking_info["name"], books=books)
            output.rankings.append(ranking)
            print(f"  ✓ 获取到 {len(books)} 本书", flush=True)
        except Exception as e:
            print(f"  ✗ 失败: {e}", flush=True)
            output.rankings.append(Ranking(type=ranking_info["type"], name=ranking_info["name"], books=[]))

        # 请求间隔
        if i < len(RANKINGS) - 1:
            time.sleep(REQUEST_DELAY)

    return output


# ── JSON 输出 ──────────────────────────────────────────────────────────────────

def rankings_to_dict(output: RankingsOutput) -> dict:
    """将 RankingsOutput 序列化为可 JSON 序列化的 dict"""
    return {
        "updatedAt": output.updatedAt,
        "rankings": [
            {
                "type": r.type,
                "name": r.name,
                "books": [
                    {
                        "rank": b.rank,
                        "title": b.title,
                        "author": b.author,
                        "category": b.category,
                        "coverURL": b.coverURL,
                        "bookURL": b.bookURL,
                        "description": b.description,
                        "badge": b.badge,
                    }
                    for b in r.books
                ],
            }
            for r in output.rankings
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="起点中文网排行榜爬虫")
    parser.add_argument(
        "--output",
        default="docs/rankings.json",
        help="输出 JSON 路径（默认: docs/rankings.json）",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="每个榜单最多抓取多少本（默认 10）",
    )
    args = parser.parse_args()

    output_path = args.output

    print(f"起点排行榜爬虫 v1.0", flush=True)
    print(f"输出路径: {output_path}", flush=True)
    print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(f"{'=' * 40}", flush=True)

    output = fetch_all_rankings()

    # 如果有限制，截取
    if args.limit > 0:
        for ranking in output.rankings:
            ranking.books = ranking.books[: args.limit]

    # 转为 dict
    data = rankings_to_dict(output)

    # 写入文件
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 统计
    total_books = sum(len(r.books) for r in output.rankings)
    print(f"{'=' * 40}", flush=True)
    print(f"完成！共获取 {len(output.rankings)} 种榜单，{total_books} 本书", flush=True)
    for r in output.rankings:
        print(f"  {r.name}: {len(r.books)} 本", flush=True)
    print(f"已保存到: {output_path}", flush=True)


if __name__ == "__main__":
    main()
