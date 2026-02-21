"""
core/models.py
==============
Domain models for MadridHousingScanner.
These are pure data classes with no framework dependencies (Clean Architecture).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Bronze layer model – raw data exactly as scraped
# ---------------------------------------------------------------------------

class RawProperty(BaseModel):
    """Represents a single raw property listing as scraped from a source."""

    source: str = Field(..., description="Scraper source identifier, e.g. 'idealista'")
    url: str = Field(..., description="Full URL of the listing")
    title: str = Field(..., description="Listing title/headline")
    raw_price: str = Field(..., description="Price as raw string, e.g. '350.000 €'")
    raw_area: str = Field(..., description="Area as raw string, e.g. '85 m²'")
    raw_rooms: Optional[str] = Field(None, description="Rooms as raw string, e.g. '3 hab.'")
    neighborhood: Optional[str] = Field(None, description="Neighborhood / barrio name")
    district: Optional[str] = Field(None, description="District / distrito name")
    latitude: Optional[float] = Field(None, description="GPS latitude if available")
    longitude: Optional[float] = Field(None, description="GPS longitude if available")
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    scrape_date: str = Field(default="")  # YYYY-MM-DD partition key

    def model_post_init(self, __context: object) -> None:  # noqa: ANN001
        if not self.scrape_date:
            self.scrape_date = self.scraped_at.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Silver layer model – cleaned & typed
# ---------------------------------------------------------------------------

class CleanedProperty(BaseModel):
    """Represents a cleaned, validated property record (Silver layer)."""

    source: str
    url: str
    title: str
    price_eur: float = Field(..., ge=0, description="Price in EUR")
    area_sqm: float = Field(..., gt=0, description="Area in m²")
    rooms: Optional[int] = Field(None, ge=0)
    price_per_sqm: float = Field(..., ge=0, description="EUR per m²")
    neighborhood: str
    district: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    scraped_at: datetime
    scrape_date: str

    @field_validator("neighborhood", "district", mode="before")
    @classmethod
    def normalize_text(cls, v: str) -> str:
        return v.strip().title() if v else "Desconocido"


# ---------------------------------------------------------------------------
# Gold layer model – enriched deal with Opportunity Index
# ---------------------------------------------------------------------------

class Deal(BaseModel):
    """A property deal enriched with the Opportunity Index (Gold layer)."""

    source: str
    url: str
    title: str
    price_eur: float
    area_sqm: float
    rooms: Optional[int]
    price_per_sqm: float
    neighborhood: str
    district: str
    latitude: Optional[float]
    longitude: Optional[float]
    neighborhood_avg_price_per_sqm: float = Field(
        ..., description="Historical average price/m² for the neighborhood"
    )
    opportunity_index: float = Field(
        ...,
        description=(
            "1 - (listing_price_per_sqm / neighborhood_avg_price_per_sqm). "
            "Higher means a better deal relative to the neighborhood average."
        ),
    )
    rank: int = Field(..., description="Deal rank by opportunity_index (1 = best deal)")
    scrape_date: str
