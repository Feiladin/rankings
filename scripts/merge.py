"""合并各站榜单，写入 docs/rankings.json。

用法：
  python scripts/merge.py           # 真实抓取
  python scripts/merge.py --dry-run # 只打印不写文件
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import dedup_key  # noqa: E402
import scrape_ciweimao  # noqa: E402
import scrape_qidian  # noqa: E402
import scrape_zongheng  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "rankings.json"
MAX_PER_LIST = 20


def dedupe_group(group: dict) -> dict:
    seen: Dict[str, dict] = {}
    ordered: List[dict] = []
    for book in group.get("books", []):
        key = dedup_key(
            book.get("source", ""),
            book.get("title", ""),
            book.get("author", ""),
        )
        if key in seen:
            continue
        seen[key] = book
        ordered.append(book)
    ordered = ordered[:MAX_PER_LIST]
    for i, book in enumerate(ordered, start=1):
        book["rank"] = i
    out = dict(group)
    out["books"] = ordered
    return out


def collect() -> List[dict]:
    groups: List[dict] = []
    for module in (scrape_qidian, scrape_zongheng, scrape_ciweimao):
        try:
            groups.extend(module.scrape(limit=MAX_PER_LIST))
        except Exception as exc:  # noqa: BLE001
            print(f"[merge] module {module.__name__} failed: {exc}")
    by_type: Dict[str, dict] = {}
    for g in groups:
        t = g.get("type") or ""
        if not t or not g.get("books"):
            continue
        if t not in by_type:
            by_type[t] = dedupe_group(g)
    return list(by_type.values())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rankings = collect()
    if not rankings:
        print("[merge] no rankings collected, keep previous file")
        # 已有产物则不视为失败，避免 Actions 红叉
        return 0 if OUTPUT.exists() else 1

    payload = {
        "updatedAt": dt.date.today().isoformat(),
        "rankings": rankings,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.dry_run:
        print(text)
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(text + "\n", encoding="utf-8")
    print(f"[merge] wrote {OUTPUT} groups={len(rankings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
