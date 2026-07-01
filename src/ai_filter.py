"""AI 相关性过滤：keyword / semantic / hybrid 三种策略。"""
from __future__ import annotations

import json

from .config import load_keywords, settings
from .fetch_news import NewsItem


def _match_keyword(text: str, includes: list[str], excludes: list[str]) -> bool:
    """关键词匹配（不区分大小写）。命中 include 且未命中 exclude。"""
    low = text.lower()
    if any(k.lower() in low for k in excludes):
        return False
    return any(k.lower() in low for k in includes)


def _semantic_batch(titles: list[str]) -> list[bool]:
    """用大模型批量判断标题是否属于 AI 领域，返回布尔列表。"""
    if not titles:
        return []
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)
        numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(titles))
        prompt = (
            "判断下列每条新闻标题是否属于人工智能/大模型/机器学习领域。"
            "只返回 JSON 数组，元素为 true/false，顺序与输入一致，不要多余文字。\n\n"
            f"{numbered}"
        )
        resp = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        content = resp.choices[0].message.content.strip()
        # 容错：截取第一个 [ 到最后一个 ]
        start, end = content.find("["), content.rfind("]")
        if start != -1 and end != -1:
            content = content[start : end + 1]
        result = json.loads(content)
        if isinstance(result, list) and len(result) == len(titles):
            return [bool(x) for x in result]
    except Exception as e:  # noqa: BLE001
        print(f"[filter] 语义判断失败，降级为全部保留: {e}")
    return [True] * len(titles)


def filter_ai(items: list[NewsItem]) -> list[NewsItem]:
    """按配置策略过滤出 AI 相关新闻。"""
    cfg = load_keywords()
    includes = cfg.get("include", [])
    excludes = cfg.get("exclude", [])
    strategy = cfg.get("strategy", "hybrid")

    result: list[NewsItem] = []

    if strategy == "keyword":
        for it in items:
            if _match_keyword(f"{it.title} {it.summary}", includes, excludes):
                it.is_ai = True
                result.append(it)

    elif strategy == "semantic":
        flags = _semantic_batch([it.title for it in items])
        for it, ok in zip(items, flags):
            if ok:
                it.is_ai = True
                result.append(it)

    else:  # hybrid：先关键词粗筛，未命中的再语义兜底
        matched: list[NewsItem] = []
        pending: list[NewsItem] = []
        for it in items:
            text = f"{it.title} {it.summary}"
            if _match_keyword(text, includes, excludes):
                it.is_ai = True
                matched.append(it)
            else:
                # 垂直源（needs_filter=False）默认信任；综合源才需语义兜底
                if it.needs_filter:
                    pending.append(it)
                else:
                    it.is_ai = True
                    matched.append(it)
        if pending:
            flags = _semantic_batch([it.title for it in pending])
            for it, ok in zip(pending, flags):
                if ok:
                    it.is_ai = True
                    matched.append(it)
        result = matched

    print(f"[filter] 策略={strategy} 过滤后 AI 相关 {len(result)}/{len(items)} 条")
    return result


if __name__ == "__main__":
    from .fetch_news import fetch_all

    for i in filter_ai(fetch_all()):
        print(f"- [{i.source}] {i.title}")