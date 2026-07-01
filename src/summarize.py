"""AI 总结：把过滤后的新闻交给大模型，产出导语 + 编号快报。"""
from __future__ import annotations

import json

from .config import settings
from .fetch_news import NewsItem

DEFAULT_LEAD = "今日 AI 圈核心动态已打包，快报速览"

PROMPT_TMPL = """你是一名 AI 领域资讯编��。下面是今日抓取到的 AI 相关新闻（含标题、摘要、链接）。
请挑选最重要的 5-8 条，为每条生成一句话快报标题（主体+核心事件，不超过 30 字，中文）。

硬性规则：
1. 每条快报必须对应新闻列表中一条独立新闻的链接，且不同快报的链接必须各不相同，严禁两条快报共用同一个链接。
2. 若某条新闻是「聚合快讯/晚报」（一条里塞了多个不相关话题），只能整体概括为一条快报，禁止拆成多条；如果它包含的单个话题在列表其他条目里有独立链接，优先选用那条独立新闻。
3. 只使用新闻列表里真实出现过的链接，不得编造或复用。

严格只返回如下 JSON，不要额外文字：
{{
  "lead": "一句吸睛导语，营造'打包速览'氛围",
  "items": [
    {{"headline": "一句话快报标题", "link": "对应原文链接"}}
  ]
}}

新闻列表：
{news}
"""


def _build_news_block(items: list[NewsItem]) -> str:
    lines = []
    for i, it in enumerate(items, 1):
        summary = it.summary[:120] if it.summary else ""
        lines.append(f"{i}. 标题：{it.title}\n   摘要：{summary}\n   链接：{it.link}")
    return "\n".join(lines)


def _fallback(items: list[NewsItem]) -> dict:
    """无 API 或调用失败时的降级：直接用原标题。"""
    return {
        "lead": DEFAULT_LEAD,
        "items": [{"headline": it.title, "link": it.link} for it in items[:8]],
    }


def summarize(items: list[NewsItem]) -> dict:
    """返回 {"lead": str, "items": [{"headline", "link"}]}。"""
    if not items:
        return {"lead": "今日暂无 AI 相关更新", "items": []}

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)
        prompt = PROMPT_TMPL.format(news=_build_news_block(items))
        resp = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        content = resp.choices[0].message.content.strip()
        start, end = content.find("{"), content.rfind("}")
        if start != -1 and end != -1:
            content = content[start : end + 1]
        data = json.loads(content)
        lead = data.get("lead") or DEFAULT_LEAD
        out_items = []
        seen_links = set()
        for x in data.get("items", []):
            headline = x.get("headline", "").strip()
            link = x.get("link", "").strip()
            if not headline:
                continue
            # 兜底去重：同一链接只保留第一条，避免聚合快讯被拆成多条共用同一 URL
            if link and link in seen_links:
                continue
            if link:
                seen_links.add(link)
            out_items.append({"headline": headline, "link": link})
        if not out_items:
            return _fallback(items)
        return {"lead": lead, "items": out_items}
    except Exception as e:  # noqa: BLE001
        print(f"[summarize] 总结失败，降级为原标题: {e}")
        return _fallback(items)


if __name__ == "__main__":
    from .ai_filter import filter_ai
    from .fetch_news import fetch_all

    result = summarize(filter_ai(fetch_all()))
    print(result["lead"])
    for i, it in enumerate(result["items"], 1):
        print(f"{i}. {it['headline']}  ->  {it['link']}")