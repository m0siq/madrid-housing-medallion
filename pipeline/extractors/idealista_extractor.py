"""
pipeline/extractors/idealista_extractor.py
==========================================
Concrete scraper for Idealista.com property listings in Madrid.
Inherits all stealth / retry logic from PlaywrightBaseExtractor.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from playwright.async_api import Page

from core.logging_config import get_logger
from pipeline.extractors.base_extractor import PlaywrightBaseExtractor

log = get_logger(__name__)

# Default Idealista search URL for Madrid residential sale listings
DEFAULT_URL = "https://www.idealista.com/venta-viviendas/madrid/puente-de-vallecas/"


class IdealistaExtractor(PlaywrightBaseExtractor):
    """
    Scrapes property listings from Idealista Madrid.

    Each call to ``extract()`` returns dicts compatible with ``RawProperty``.
    """

    SOURCE = "idealista"

    @property
    def source_name(self) -> str:
        return self.SOURCE

    # ── Core parse logic ─────────────────────────────────────────────────────

    async def _parse_listings(self, page: Page) -> List[Dict[str, Any]]:
        """Extract listing cards from the current Idealista SERP page."""
        listings: List[Dict[str, Any]] = []
        scraped_at = datetime.utcnow().isoformat()
        scrape_date = datetime.utcnow().strftime("%Y-%m-%d")

        # Idealista renders listings as <article class="item"> elements
        cards = await page.query_selector_all("article.item")

        if not cards:
            log.warning("no_listings_found", source=self.SOURCE, url=page.url)
            return listings

        for card in cards:
            try:
                record = await self._parse_card(card, page.url, scraped_at, scrape_date)
                if record:
                    listings.append(record)
            except Exception as exc:  # noqa: BLE001
                log.warning("card_parse_error", source=self.SOURCE, error=str(exc))

        log.info("page_parsed", source=self.SOURCE, count=len(listings))
        return listings

    async def _parse_card(
        self,
        card: Any,
        page_url: str,
        scraped_at: str,
        scrape_date: str,
    ) -> Optional[Dict[str, Any]]:
        """Map a single article card to a raw property dict."""
        # ── URL ──────────────────────────────────────────────────────────────
        link_el = await card.query_selector("a.item-link")
        if not link_el:
            return None
        href = await link_el.get_attribute("href") or ""
        url = f"https://www.idealista.com{href}" if href.startswith("/") else href

        # ── Title ─────────────────────────────────────────────────────────────
        title = await self._text(card, "a.item-link") or "Sin título"

        # ── Price ─────────────────────────────────────────────────────────────
        raw_price = await self._text(card, "span.item-price") or ""

        # ── Area & rooms ──────────────────────────────────────────────────────
        raw_area = await self._text(card, "span.item-detail:nth-child(1)") or ""
        raw_rooms = await self._text(card, "span.item-detail:nth-child(2)")

        # ── Location (neighborhood / district) ───────────────────────────────
        location_text = await self._text(card, "span.item-detail-location") or ""
        neighborhood, district = self._split_location(location_text)

        return {
            "source": self.SOURCE,
            "url": url,
            "title": title.strip(),
            "raw_price": raw_price.strip(),
            "raw_area": raw_area.strip(),
            "raw_rooms": raw_rooms.strip() if raw_rooms else None,
            "neighborhood": neighborhood,
            "district": district,
            "latitude": None,
            "longitude": None,
            "scraped_at": scraped_at,
            "scrape_date": scrape_date,
        }

    # ── Pagination ────────────────────────────────────────────────────────────

    async def _get_next_page_url(self, page: Page) -> Optional[str]:
        """Click the 'siguiente' link and return the new URL, or None."""
        next_btn = await page.query_selector("a.icon-arrow-right-after")
        if next_btn:
            href = await next_btn.get_attribute("href")
            if href:
                return f"https://www.idealista.com{href}" if href.startswith("/") else href
        return None

    # ── Utilities ─────────────────────────────────────────────────────────────

    @staticmethod
    async def _text(element: Any, selector: str) -> Optional[str]:
        el = await element.query_selector(selector)
        return (await el.text_content()).strip() if el else None

    @staticmethod
    def _split_location(text: str) -> tuple[str, str]:
        """
        Split 'Barrio, Distrito' into (neighborhood, district).
        Falls back to ('Desconocido', 'Desconocido') if unparseable.
        """
        parts = [p.strip() for p in text.split(",")]
        neighborhood = parts[0] if len(parts) > 0 else "Desconocido"
        district = parts[1] if len(parts) > 1 else "Desconocido"
        return neighborhood, district
