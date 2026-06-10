from __future__ import annotations

import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any

import httpx

TRACKED_SYMBOLS = {
    "GOOGL": ("GOOGL", "Google"),
    "NVDA": ("NVDA", "NVIDIA"),
    "AVGO": ("AVGO", "Broadcom"),
}

REDDIT_SUBREDDITS = "stocks+investing+wallstreetbets+StockMarket"
REDDIT_USER_AGENT = os.environ.get(
    "REDDIT_USER_AGENT",
    "web:stock-tracker:1.0 (by /u/krun2010qq; contact:289149668@qq.com)",
)

MAX_NEWS_ITEMS = 10
CACHE_TTL_SECONDS = 120
_news_cache: dict[str, Any] = {"expires_at": 0.0, "data": []}

HEADERS = {
    "User-Agent": REDDIT_USER_AGENT,
    "Accept": "application/atom+xml,application/xml,text/xml,*/*",
}

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


def _clean_text(text: str) -> str:
    cleaned = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _entry_id(entry: ET.Element) -> str:
    entry_id = entry.findtext("atom:id", default="", namespaces=ATOM_NS)
    link = entry.find("atom:link", ATOM_NS)
    href = link.attrib.get("href") if link is not None else ""
    return entry_id or href


def _entry_publisher(entry: ET.Element) -> str:
    author = entry.find("atom:author/atom:name", ATOM_NS)
    if author is not None and author.text:
        return author.text.strip()

    link = entry.find("atom:link", ATOM_NS)
    href = link.attrib.get("href", "") if link is not None else ""
    if "/r/" in href:
        subreddit = href.split("/r/")[1].split("/")[0]
        return f"r/{subreddit}"
    return "Reddit"


def _parse_reddit_rss(xml_text: str, symbol: str) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_text)
    posts: list[dict[str, Any]] = []

    for entry in root.findall("atom:entry", ATOM_NS):
        title = (entry.findtext("atom:title", default="", namespaces=ATOM_NS) or "Untitled").strip()
        link = entry.find("atom:link", ATOM_NS)
        url = link.attrib.get("href", "") if link is not None else ""
        published = (
            entry.findtext("atom:updated", default="", namespaces=ATOM_NS)
            or entry.findtext("atom:published", default="", namespaces=ATOM_NS)
            or ""
        ).strip()

        summary = _clean_text(
            (entry.findtext("atom:content", default="", namespaces=ATOM_NS) or "")
            or (entry.findtext("atom:summary", default="", namespaces=ATOM_NS) or "")
        )
        if len(summary) > 220:
            summary = summary[:217] + "..."

        posts.append(
            {
                "id": _entry_id(entry),
                "symbol": symbol,
                "title": title,
                "summary": summary or "Reddit 讨论帖",
                "url": url,
                "publisher": _entry_publisher(entry),
                "published_at": published,
                "score": None,
                "comments": None,
                "thumbnail": None,
            }
        )

    return posts


def _fetch_reddit_posts(symbol: str, keywords: tuple[str, ...], client: httpx.Client) -> list[dict[str, Any]]:
    url = f"https://www.reddit.com/r/{REDDIT_SUBREDDITS}/search.rss"
    query = " OR ".join(keywords)
    params = {
        "q": query,
        "restrict_sr": "1",
        "sort": "new",
        "t": "month",
    }
    response = client.get(url, params=params)
    response.raise_for_status()
    return _parse_reddit_rss(response.text, symbol)


def get_reddit_news(limit: int = MAX_NEWS_ITEMS) -> list[dict[str, Any]]:
    limit = max(1, min(limit, MAX_NEWS_ITEMS))
    now = time.time()
    if _news_cache["data"] and now < _news_cache["expires_at"]:
        return _news_cache["data"][:limit]

    collected: dict[str, dict[str, Any]] = {}

    with httpx.Client(timeout=20.0, headers=HEADERS, follow_redirects=True) as client:
        for index, (symbol, keywords) in enumerate(TRACKED_SYMBOLS.items()):
            if index > 0:
                time.sleep(0.4)
            try:
                posts = _fetch_reddit_posts(symbol, keywords, client)
            except Exception:
                continue

            for post in posts:
                post_id = post.get("id") or post.get("url")
                if post_id:
                    collected[post_id] = post

    news = sorted(
        collected.values(),
        key=lambda item: item.get("published_at") or "",
        reverse=True,
    )[:limit]

    _news_cache["data"] = news
    _news_cache["expires_at"] = now + CACHE_TTL_SECONDS
    return news
