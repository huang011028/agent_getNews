"""邮件渲染：将总结结果渲染为主题、纯文本、HTML。

输出格式（用户指定范式）：
    导语
    1.号快报
    2. ...
    —— 完整链接 ——
    [1] link
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


def _today_str() -> str:
    # 北京时间
    bj = datetime.now(timezone.utc) + timedelta(hours=8)
    return bj.strftime("%Y-%m-%d")


def build_subject(summary: dict) -> str:
    return f"每日 AI 速报 · {_today_str()}"


def render_text(summary: dict) -> str:
    """纯文本版。"""
    lead = summary.get("lead", "")
    items = summary.get("items", [])
    lines = [f"📮 {lead}", ""]
    for i, it in enumerate(items, 1):
        lines.append(f"{i}. {it['headline']}")
    if items:
        lines.append("")
        lines.append("—— 完整链接 ——")
        for i, it in enumerate(items, 1):
            lines.append(f"[{i}] {it['link']}")
    return "\n".join(lines)


def render_html(summary: dict) -> str:
    """HTML 版：编号加粗，链接可点击。"""
    lead = summary.get("lead", "")
    items = summary.get("items", [])

    briefs = "".join(
        f'<li style="margin:8px 0;line-height:1.6;">'
        f'<b>{i}.</b> {_esc(it["headline"])}</li>'
        for i, it in enumerate(items, 1)
    )
    links = "".join(
        f'<li style="margin:6px 0;word-break:break-all;">'
        f'[{i}] <a href="{_esc(it["link"])}" style="color:#1a73e8;">{_esc(it["link"])}</a></li>'
        for i, it in enumerate(items, 1)
    )

    link_block = (
        f'<hr style="border:none;border-top:1px solid #eee;margin:20px 0;">'
        f'<h3 style="color:#555;font-size:15px;">完整链接</h3>'
        f'<ul style="padding-left:20px;font-size:13px;color:#666;">{links}</ul>'
        if items
        else ""
    )

    return f"""\
<div style="max-width:640px;margin:0 auto;font-family:-apple-system,'PingFang SC',sans-serif;color:#222;">
  <h2 style="font-size:20px;">📮 {_esc(lead)}</h2>
  <ol style="padding-left:22px;font-size:15px;">{briefs}</ol>
  {link_block}
  <p style="color:#999;font-size:12px;margin-top:24px;">— 每日 AI 速报 · {_today_str()} · 自动生成 —</p>
</div>"""


def _esc(s: str) -> str:
    amp, lt, gt, quot = chr(38), chr(60), chr(62), chr(34)
    return (
        s.replace(amp, amp + "amp;")
        .replace(lt, amp + "lt;")
        .replace(gt, amp + "gt;")
        .replace(quot, amp + "quot;")
    )


if __name__ == "__main__":
    demo = {
        "lead": "今日 AI 圈核心动态已打包，快报速览",
        "items": [
            {"headline": "美团发布 LongCat-2.0 万亿参数大模型", "link": "https://example.com/1"},
            {"headline": "DeepSeek V4 高峰时段 API 价格翻倍", "link": "https://example.com/2"},
        ],
    }
    print(render_text(demo))