"""主入口：fetch → filter → summarize → render → send → (archive)。"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.ai_filter import filter_ai
from src.config import settings
from src.fetch_news import fetch_all
from src.render import build_subject, render_html, render_text
from src.send_email import send_email
from src.summarize import summarize

ARCHIVE_DIR = Path(__file__).resolve().parent / "archive"


def _archive(subject: str, text_body: str) -> None:
    """把当日快报归档到 archive/YYYY-MM-DD.md。"""
    try:
        ARCHIVE_DIR.mkdir(exist_ok=True)
        bj = datetime.now(timezone.utc) + timedelta(hours=8)
        path = ARCHIVE_DIR / f"{bj.strftime('%Y-%m-%d')}.md"
        path.write_text(f"# {subject}\n\n{text_body}\n", encoding="utf-8")
        print(f"[archive] 已归档 {path.name}")
    except Exception as e:  # noqa: BLE001
        print(f"[archive] 归档失败（忽略）: {e}")


def main() -> int:
    settings.validate()

    print("=== 1. 抓取新闻 ===")
    news = fetch_all()

    print("=== 2. AI 相关性过滤 ===")
    ai_news = filter_ai(news)

    print("=== 3. AI 总结 ===")
    summary = summarize(ai_news)

    print("=== 4. 渲染邮件 ===")
    subject = build_subject(summary)
    text_body = render_text(summary)
    html_body = render_html(summary)
    print(text_body)

    print("=== 5. 发送邮件 ===")
    send_email(subject, text_body, html_body)

    _archive(subject, text_body)
    print("=== 完成 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())