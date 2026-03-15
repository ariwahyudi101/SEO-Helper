from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    db_path: Path
    openai_api_key: str | None
    deepseek_api_key: str | None
    openai_model: str
    deepseek_model: str
    request_timeout: float


DEFAULT_DB = Path(os.getenv("SEO_AUDIT_DB_PATH", "seo_audit.db"))


def load_settings() -> Settings:
    return Settings(
        db_path=Path(os.getenv("SEO_AUDIT_DB_PATH", str(DEFAULT_DB))),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        request_timeout=float(os.getenv("SEO_AUDIT_TIMEOUT", "15")),
    )
