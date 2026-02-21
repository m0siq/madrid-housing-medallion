"""
app/api/main.py
================
FastAPI application for MadridHousingScanner.

Endpoints
---------
GET /health     – Service health check.
GET /deals      – Top N housing deals ranked by Opportunity Index.
GET /stats      – Neighbourhood aggregation statistics.

Run::

    uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.api.schemas import DealsListResponse, DealResponse, HealthResponse
from core.config import settings
from core.logging_config import configure_logging, get_logger
from pipeline.storage.duckdb_repository import DuckDBRepository

# ── Bootstrap ─────────────────────────────────────────────────────────────────
configure_logging(level=settings.LOG_LEVEL, fmt="console")
log = get_logger(__name__)

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="MadridHousingScanner API",
    description=(
        "Real-time real estate analytics API for Madrid. "
        "Serves deals ranked by the Opportunity Index — a metric that compares "
        "each listing's price per m² against its neighbourhood historical average."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Dependency: shared repository ─────────────────────────────────────────────
_repo: Optional[DuckDBRepository] = None


def get_repository() -> DuckDBRepository:
    global _repo
    if _repo is None:
        _repo = DuckDBRepository()
    return _repo


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check() -> HealthResponse:
    """Service health check."""
    return HealthResponse()


@app.get("/deals", response_model=DealsListResponse, tags=["Deals"])
def get_top_deals(
    n: int = Query(
        default=10,
        ge=1,
        le=100,
        description="Number of top deals to return (max 100).",
    ),
    scrape_date: Optional[str] = Query(
        default=None,
        description="Filter by scrape date (YYYY-MM-DD). Defaults to latest available.",
    ),
    lat: Optional[float] = Query(
        default=None,
        description="Centre latitude for spatial radius search.",
    ),
    lon: Optional[float] = Query(
        default=None,
        description="Centre longitude for spatial radius search.",
    ),
    radius_km: float = Query(
        default=2.0,
        ge=0.1,
        le=50.0,
        description="Search radius in kilometres (used with lat/lon).",
    ),
) -> DealsListResponse:
    """
    Return the top N housing deals ranked by Opportunity Index.

    Optionally filter by a geographic radius using ``lat``, ``lon``, and
    ``radius_km`` parameters.

    The Opportunity Index is computed as:
    ``1 - (listing_price_per_sqm / neighbourhood_avg_price_per_sqm)``

    A **higher** value means the listing is proportionally cheaper than
    its neighbourhood average → a better deal.
    """
    repo = get_repository()
    try:
        if lat is not None and lon is not None:
            # Spatial search
            deals = repo.get_deals_within_radius(
                lat=lat, lon=lon, radius_km=radius_km, n=n
            )
        else:
            deals = repo.get_top_deals(n=n, scrape_date=scrape_date)
    except Exception as exc:
        log.error("deals_query_failed", error=str(exc))
        raise HTTPException(
            status_code=503,
            detail="Could not retrieve deals. Ensure the pipeline has run at least once.",
        ) from exc

    if not deals:
        raise HTTPException(
            status_code=404,
            detail="No deals found. Run the data pipeline first.",
        )

    date_used = deals[0].get("scrape_date") if deals else scrape_date
    if hasattr(date_used, "isoformat"):
        date_used = date_used.isoformat()
    return DealsListResponse(
        total=len(deals),
        scrape_date=date_used,
        deals=[DealResponse(**d) for d in deals],
    )


@app.get("/stats", tags=["Analytics"])
def get_neighbourhood_stats() -> dict:
    """
    Return price and Opportunity Index statistics aggregated per neighbourhood.
    Useful for the Streamlit choropleth dashboard.
    """
    repo = get_repository()
    try:
        stats = repo.get_neighborhood_stats()
    except Exception as exc:
        log.error("stats_query_failed", error=str(exc))
        raise HTTPException(
            status_code=503,
            detail="Could not retrieve neighbourhood stats.",
        ) from exc

    return {"total_neighbourhoods": len(stats), "data": stats}
