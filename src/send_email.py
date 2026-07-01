"""邮件发送：通过 SMTP 发送多部分（纯文本 + HTML）邮件。"""
from __future__ import annotations

import smtplib
import ssl
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from .config import settings


def _relaxed_context() -> ssl.SSLContext:
    """降级 SSL context：不校验证书。用于公司代�自签证书导致校验失败时兜底。"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _do_send(host: str, port: int, to_list: list[str], msg_str: str, context: ssl.SSLContext) -> None:
    """按端口选择 SSL(465) 或 STARTTLS 发送。"""
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=context) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.sendmail(settings.SMTP_USER, to_list, msg_str)
    else:
        with smtplib.SMTP(host, port) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.sendmail(settings.SMTP_USER, to_list, msg_str)


def send_email(subject: str, text_body: str, html_body: str) -> None:
    """发送邮件到 MAIL_TO 列表中的所有收件人。"""
    to_list = settings.mail_to_list
    if not to_list:
        raise RuntimeError("未配置收件人 MAIL_TO")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = formataddr((settings.MAIL_FROM_NAME, settings.SMTP_USER))
    msg["To"] = ", ".join(to_list)

    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    port = settings.SMTP_PORT
    host = settings.SMTP_HOST
    msg_str = msg.as_string()

    try:
        _do_send(host, port, to_list, msg_str, ssl.create_default_context())
    except ssl.SSLCertVerificationError:
        # 公司网络代理自签证书导致校验失败，降级为不校验证书重试
        print("[email] SSL 证书校验失败，降级为不校验证书重试（公司代理环境）")
        _do_send(host, port, to_list, msg_str, _relaxed_context())

    print(f"[email] 已发送至 {', '.join(to_list)}")


if __name__ == "__main__":
    settings.validate()
    send_email(
        subject="测试邮件 · 每日 AI 速报",
        text_body="这是一封测试纯文本邮件。",
        html_body="<b>这是一封测试 HTML 邮件。</b>",
    )