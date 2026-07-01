"""配置加载：读取 .env 环境变量与 YAML 配置文件。"""
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

# 项目根目录
ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT_DIR / "config"

# 加载 .env（本地开发用；GitHub Actions 走注入的环境变量）
load_dotenv(ROOT_DIR / ".env")


def _get(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


class Settings:
    """环境变量配置。"""

    # AI 模型（默认 DeepSeek V4 Pro，OpenAI 兼容接口）
    OPENAI_API_KEY = _get("OPENAI_API_KEY")
    OPENAI_BASE_URL = _get("OPENAI_BASE_URL", "https://api.deepseek.com")
    OPENAI_MODEL = _get("OPENAI_MODEL", "deepseek-v4-pro")

    # 邮件
    SMTP_HOST = _get("SMTP_HOST")
    SMTP_PORT = int(_get("SMTP_PORT", "465") or 465)
    SMTP_USER = _get("SMTP_USER")
    SMTP_PASS = _get("SMTP_PASS")
    MAIL_FROM_NAME = _get("MAIL_FROM_NAME", "每日AI速报")

    @property
    def mail_to_list(self) -> list[str]:
        raw = _get("MAIL_TO")
        return [x.strip() for x in raw.split(",") if x.strip()]

    def validate(self) -> None:
        """启动前校验关键配置是否齐全。"""
        missing = []
        if not self.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")
        for key in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS"):
            if not getattr(self, key):
                missing.append(key)
        if not self.mail_to_list:
            missing.append("MAIL_TO")
        if missing:
            raise RuntimeError(f"缺少必要配置: {', '.join(missing)}")


def load_yaml(filename: str) -> dict:
    """读取 config/ 下的 YAML 文件。"""
    path = CONFIG_DIR / filename
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_sources() -> dict:
    """加载新闻源配置。"""
    return load_yaml("sources.yaml")


def load_keywords() -> dict:
    """加载 AI 关键词与过滤策略配置。"""
    return load_yaml("keywords.yaml")


settings = Settings()