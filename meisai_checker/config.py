from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover - optional at runtime
    load_dotenv = None


@dataclass
class AppConfig:
    openai_api_key: str | None
    openai_base_url: str | None
    openai_model: str
    guidelines_dir: Path

    @staticmethod
    def load(cwd: Path | None = None) -> "AppConfig":
        if load_dotenv:
            load_dotenv()
        cwd = cwd or Path.cwd()
        return AppConfig(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_base_url=os.getenv("OPENAI_BASE_URL"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            guidelines_dir=Path(os.getenv("GUIDELINES_DIR", "guidelines")).resolve(),
        )

