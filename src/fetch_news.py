"""抓取新闻：读取 sources.yaml，遍历 RSS 源，解析、过滤时间、去重。"""
from __future__ import annotations

import time
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import feedparser
import requests

from .config import load_sources

# 模拟浏览器 UA，避免部分站点拦截默认 python-requests / feedparser UA
_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
_HEADERS = {"User-Agent": _UA, "Accept": "application/rss+xml, application/xml, text/xml, */*"}


def _fetch_raw(url: str) -> bytes | None:
    """用 requests 拉取 RSS 原文；SSL 校验失败（如公司代理自签证书）时降级重试。"""
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=20)
        resp.raise_for_status()
        return resp.content
    except requests.exceptions.SSLError:
        # 公司网络常见：HTTPS 中间人代理导致自签证书链，降级为不校验重试
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                resp = requests.get(url, headers=_HEADERS, timeout=20, verify=False)
                resp.raise_for_status()
                return resp.content
        except Exception as e:  # noqa: BLE001
            print(f"[fetch] SSL 降级仍失败 {url}: {e}")
            return None
    except Exception as e:  # noqa: BLE001
        print(f"[fetch] 请求失败 {url}: {e}")
        return None


@dataclass
class NewsItem:
    title: str
    link: str
    summary: str
    source: str
    published: datetime | None = None
    needs_filter: bool = False
    # 过滤后由 ai_filter 标记是否与 AI 相关
    is_ai: bool = field(default=False)


def _parse_time(entry) -> datetime | None:
    """从 feed entry 中提取发布时间（UTC）。"""
    for key in ("published_parsed", "updated_parsed"):
        t = getattr(entry, key, None) or entry.get(key)
        if t:
            return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc)
    return None


def fetch_all() -> list[NewsItem]:
    """抓取所有源，返回去重、按时间过滤后的新闻列表。"""
    cfg = load_sources()
    sources = cfg.get("sources", [])
    max_items = int(cfg.get("max_items_per_source", 15))
    recent_hours = int(cfg.get("recent_hours", 24))

    cutoff = datetime.now(timezone.utc) - timedelta(hours=recent_hours)
    items: list[NewsItem] = []

    for src in sources:
        name = src.get("name", "未知来源")
        url = src.get("url", "")
        needs_filter = bool(src.get("needs_filter", False))
        if not url:
            continue
        raw = _fetch_raw(url)
        if raw is None:
            print(f"[fetch] {name}: 抓到 0 条（请求未成功）")
            continue
        try:
            feed = feedparser.parse(raw)
        except Exception as e:  # noqa: BLE001
            print(f"[fetch] 解析失败 {name}: {e}")
            continue

        count = 0
        for entry in feed.entries:
            if count >= max_items:
                break
            published = _parse_time(entry)
            # 有时间信息则按时间过滤；无时间信息则保留
            if published and published < cutoff:
                continue
            title = (entry.get("title") or "").strip()
            link = (entry.get("link") or "").strip()
            summary = (entry.get("summary") or "").strip()
            if not title or not link:
                continue
            items.append(
                NewsItem(
                    title=title,
                    link=link,
                    summary=summary,
                    source=name,
                    published=published,
                    needs_filter=needs_filter,
                )
            )
            count += 1
        print(f"[fetch] {name}: 抓到 {count} 条")

    return _dedup(items)


def _dedup(items: list[NewsItem]) -> list[NewsItem]:
    """按 link 去重。"""
    seen: set[str] = set()
    result: list[NewsItem] = []
    for it in items:
        if it.link in seen:
            continue
        seen.add(it.link)
        result.append(it)
    print(f"[fetch] 去重后共 {len(result)} 条")
    return result


if __name__ == "__main__":
    for i in fetch_all():
        print(f"- [{i.source}] {i.title}")