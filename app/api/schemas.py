"""
app/api/schemas.py
==================
Pydantic schemas for the FastAPI response models.
"""

from __future__ import annotations

import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class DealResponse(BaseModel):
    """A single housing deal with its Opportunity Index."""

    source: str = Field(..., description="Data source identifier, e.g. 'idealista'")
    url: str = Field(..., description="Full URL of the listing")
    title: str = Field(..., description="Listing title")
    price_eur: float = Field(..., description="Listing price in EUR")
    area_sqm: float = Field(..., description="Area in m²")
    rooms: Optional[int] = Field(None, description="Number of rooms")
    price_per_sqm: float = Field(..., description="Price per m²")
    neighborhood: str = Field(..., description="Neighbourhood / barrio")
    district: Optional[str] = Field(None, description="District / distrito")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    avg_neighborhood_price: float = Field(
        ..., description="Average price for the neighbourhood"
    )
    opportunity_index: float = Field(
        ...,
        description=(
            "Opportunity Index: 1 - (listing_price / avg_neighbourhood_price). "
            "Higher = better deal."
        ),
    )
    scrape_date: str = Field(..., description="Date the listing was scraped (YYYY-MM-DD)")
    distance_km: Optional[float] = Field(None, description="Distance from search centre (km)")

    @field_validator("scrape_date", mode="before")
    @classmethod
    def _coerce_date(cls, v: object) -> str:
        if isinstance(v, datetime.date):
            return v.isoformat()
        return v  # type: ignore[return-value]

    class Config:
        from_attributes = True


class DealsListResponse(BaseModel):
    """Envelope for the /deals endpoint."""

    total: int = Field(..., description="Number of deals returned")
    scrape_date: Optional[str] = Field(None, description="Data date used")
    deals: List[DealResponse]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str = "1.0.0"
    service: str = "MadridHousingScanner API"
