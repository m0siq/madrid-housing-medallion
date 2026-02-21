"""
pipeline/extractors/base_extractor.py
======================================
Abstract Playwright-based extractor with:
  - Full stealth mode (fingerprint patching, human behavior, CDP masking)
  - Proxy support (residential / rotating)
  - User-Agent + viewport rotation
  - Cookie consent auto-dismissal
  - CAPTCHA / block-page detection with automatic back-off
  - Configurable retries with exponential back-off
  - Session warm-up for organic navigation patterns
  - Resource blocking (images, fonts) to reduce footprint
"""

from __future__ import annotations

import asyncio
import random
from abc import abstractmethod
from typing import Any, Dict, List, Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from core.config import settings
from core.interfaces import BaseExtractor
from core.logging_config import get_logger
from pipeline.extractors.stealth import (
    UA_POOL,
    apply_stealth_scripts,
    detect_blocking,
    dismiss_cookie_banners,
    get_random_ua,
    get_random_viewport,
    simulate_human_mouse,
    simulate_human_scroll,
    simulate_reading_pause,
    warm_up_session,
)

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# PlaywrightBaseExtractor
# ---------------------------------------------------------------------------

class PlaywrightBaseExtractor(BaseExtractor):
    """
    Concrete base for all Playwright-based scrapers.

    Handles browser lifecycle, stealth mode, human behavior simulation,
    proxy support, cookie consent, CAPTCHA detection, and retries.

    Subclasses override ``_parse_listings()`` and ``_get_next_page_url()``
    to implement source-specific CSS selector logic.
    """

    def __init__(self) -> None:
        # Use the large UA pool from stealth module, fallback to config
        self._user_agents: List[str] = UA_POOL if len(UA_POOL) > 10 else settings.USER_AGENTS
        self._headless: bool = settings.SCRAPER_HEADLESS
        self._timeout_ms: int = settings.SCRAPER_TIMEOUT_MS
        self._max_retries: int = settings.SCRAPER_MAX_RETRIES
        self._delay_min: float = settings.SCRAPER_DELAY_MIN_S
        self._delay_max: float = settings.SCRAPER_DELAY_MAX_S
        self._proxy_url: Optional[str] = settings.PROXY_URL
        self._stealth_enabled: bool = settings.STEALTH_ENABLED
        self._warmup_enabled: bool = settings.WARMUP_ENABLED

    # ── Public API ───────────────────────────────────────────────────────────

    async def extract(
        self,
        url: str,
        max_pages: int = 1,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Run the full scrape workflow across ``max_pages`` pages."""
        all_listings: List[Dict[str, Any]] = []
        current_url: Optional[str] = url

        async with async_playwright() as pw:
            browser, context = await self._create_browser(pw)
            try:
                page = await context.new_page()

                # ── Session warm-up ───────────────────────────────────────
                if self._warmup_enabled:
                    await warm_up_session(page)

                # ── Cookie consent (dismiss before scraping) ──────────────
                await page.goto(url, timeout=self._timeout_ms, wait_until="domcontentloaded")
                await asyncio.sleep(random.uniform(1.0, 2.5))
                await dismiss_cookie_banners(page)

                for page_num in range(1, max_pages + 1):
                    if not current_url:
                        break

                    log.info(
                        "scraping_page",
                        source=self.source_name,
                        page=page_num,
                        url=current_url,
                    )

                    listings = await self._scrape_with_retry(page, current_url)
                    all_listings.extend(listings)

                    # Human-like inter-page delay (randomized)
                    delay = random.uniform(self._delay_min, self._delay_max)
                    # Add extra jitter to avoid periodic patterns
                    delay += random.uniform(0, 1.5)
                    await asyncio.sleep(delay)

                    # Advance pagination
                    current_url = await self._get_next_page_url(page)

            finally:
                await context.close()
                await browser.close()

        log.info(
            "extraction_complete",
            source=self.source_name,
            total_listings=len(all_listings),
        )
        return all_listings

    # ── Internal helpers ─────────────────────────────────────────────────────

    async def _create_browser(self, pw: Playwright) -> tuple[Browser, BrowserContext]:
        """
        Launch a stealth-hardened Chromium browser with:
        - Random User-Agent from 50+ pool
        - Random viewport from common resolutions
        - Spanish locale + Madrid timezone + geolocation
        - Optional proxy support
        - Fingerprint masking scripts
        - Resource blocking (images, fonts, media)
        """
        user_agent = get_random_ua()
        viewport = get_random_viewport()

        # ── Launch args ───────────────────────────────────────────────────
        launch_args = [
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--disable-infobars",
            "--disable-background-networking",
            "--disable-default-apps",
            "--disable-extensions",
            "--disable-sync",
            "--disable-translate",
            "--metrics-recording-only",
            "--no-first-run",
            "--safebrowsing-disable-auto-update",
            f"--window-size={viewport['width']},{viewport['height']}",
        ]

        # ── Proxy config ──────────────────────────────────────────────────
        proxy_config = None
        if self._proxy_url:
            proxy_config = {"server": self._proxy_url}
            log.info("proxy_configured", server=self._proxy_url[:30] + "...")

        browser = await pw.chromium.launch(
            headless=self._headless,
            slow_mo=random.randint(50, 150) if not self._headless else 0,
            args=launch_args,
            proxy=proxy_config,
        )

        context = await browser.new_context(
            user_agent=user_agent,
            viewport=viewport,
            locale="es-ES",
            timezone_id="Europe/Madrid",
            geolocation={"latitude": 40.4168, "longitude": -3.7038},
            permissions=["geolocation"],
            color_scheme=random.choice(["light", "dark", "no-preference"]),
            java_script_enabled=True,
            has_touch=False,
            is_mobile=False,
        )

        # ── Apply stealth patches ─────────────────────────────────────────
        if self._stealth_enabled:
            await apply_stealth_scripts(context)

        # ── Block heavy resources (reduce bandwidth fingerprint) ──────────
        await context.route(
            "**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf,ico,mp4,webm,avi}",
            lambda route: route.abort(),
        )

        # ── Block known tracking/analytics scripts ────────────────────────
        tracking_patterns = [
            "**/google-analytics.com/**",
            "**/googletagmanager.com/**",
            "**/facebook.net/**",
            "**/doubleclick.net/**",
            "**/hotjar.com/**",
        ]
        for pattern in tracking_patterns:
            await context.route(pattern, lambda route: route.abort())

        log.info(
            "stealth_browser_created",
            user_agent=user_agent[:50] + "...",
            viewport=f"{viewport['width']}x{viewport['height']}",
            headless=self._headless,
            proxy=bool(self._proxy_url),
            stealth=self._stealth_enabled,
        )
        return browser, context

    async def _scrape_with_retry(
        self, page: Page, url: str
    ) -> List[Dict[str, Any]]:
        """Navigate to ``url`` and call ``_parse_listings()`` with retry logic."""
        last_error: Optional[Exception] = None
        for attempt in range(1, self._max_retries + 1):
            try:
                # Navigate
                await page.goto(url, timeout=self._timeout_ms, wait_until="domcontentloaded")
                await page.wait_for_load_state("networkidle", timeout=self._timeout_ms)

                # ── CAPTCHA / block detection ─────────────────────────────
                block_status = await detect_blocking(page)
                if block_status["blocked"]:
                    log.warning(
                        "blocking_detected",
                        source=self.source_name,
                        reason=block_status["reason"],
                        attempt=attempt,
                    )
                    # Exponential back-off with longer waits for blocks
                    wait = (2 ** attempt) * random.uniform(2, 5)
                    log.info("block_backoff", wait_seconds=round(wait, 1))
                    await asyncio.sleep(wait)
                    continue

                # ── Cookie consent (retry on each new page) ───────────────
                await dismiss_cookie_banners(page)

                # ── Human behavior simulation ─────────────────────────────
                if self._stealth_enabled:
                    await simulate_reading_pause(0.5, 1.5)
                    await simulate_human_mouse(page)
                    await simulate_human_scroll(page)
                    await simulate_reading_pause(0.5, 1.5)

                return await self._parse_listings(page)

            except Exception as exc:  # noqa: BLE001
                last_error = exc
                wait = 2 ** attempt + random.uniform(0, 2)
                log.warning(
                    "scrape_attempt_failed",
                    source=self.source_name,
                    attempt=attempt,
                    max_retries=self._max_retries,
                    url=url,
                    error=str(exc),
                    retry_in_s=round(wait, 1),
                )
                await asyncio.sleep(wait)

        log.error(
            "scrape_failed_permanently",
            source=self.source_name,
            url=url,
            error=str(last_error),
        )
        return []

    # ── Abstract methods for subclasses ─────────────────────────────────────

    @abstractmethod
    async def _parse_listings(self, page: Page) -> List[Dict[str, Any]]:
        """
        Parse property listing cards from the current Playwright ``page``.
        """
        ...

    @abstractmethod
    async def _get_next_page_url(self, page: Page) -> Optional[str]:
        """Return the URL of the next pagination page, or None if no more pages."""
        ...