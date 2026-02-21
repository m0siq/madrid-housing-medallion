"""
core/config.py
==============
Centralized configuration for MadridHousingScanner.
Uses pydantic-settings to load values from environment variables / .env file.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class Settings(BaseSettings):
    """Application-wide settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Data lake paths ──────────────────────────────────────────────────────
    DATA_DIR: Path = Path("data")
    BRONZE_DIR: Path = Path("data/bronze")
    SILVER_DIR: Path = Path("data/silver")
    GOLD_DIR: Path = Path("data/gold")

    # ── DuckDB ───────────────────────────────────────────────────────────────
    DUCKDB_PATH: Path = Path("data/madrid_housing.duckdb")

    # ── API ──────────────────────────────────────────────────────────────────
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    TOP_DEALS_LIMIT: int = 10

    # ── Scraper ──────────────────────────────────────────────────────────────
    SCRAPER_HEADLESS: bool = False
    SCRAPER_TIMEOUT_MS: int = 60_000
    SCRAPER_MAX_RETRIES: int = 3
    SCRAPER_DELAY_MIN_S: float = 2.0
    SCRAPER_DELAY_MAX_S: float = 5.0

    # ── Stealth / Anti-detection ─────────────────────────────────────────
    STEALTH_ENABLED: bool = True
    WARMUP_ENABLED: bool = True
    PROXY_URL: Optional[str] = None  # e.g. "http://user:pass@proxy.example.com:8080"

    # ── User-Agent rotation pool ─────────────────────────────────────────────
    USER_AGENTS: List[str] = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    ]

    # ── Spark ────────────────────────────────────────────────────────────────
    SPARK_APP_NAME: str = "MadridHousingScanner"
    SPARK_MASTER: str = "local[*]"

    # ── Logging ──────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # "json" | "console"

    @field_validator("BRONZE_DIR", "SILVER_DIR", "GOLD_DIR", "DATA_DIR", mode="before")
    @classmethod
    def expand_paths(cls, v: str | Path) -> Path:
        return Path(v)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

settings = Settings()
