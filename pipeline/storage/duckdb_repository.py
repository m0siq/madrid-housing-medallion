"""
pipeline/storage/duckdb_repository.py
=======================================
DuckDBRepository – reads Gold Parquet into DuckDB for low-latency queries.

DuckDB can query Parquet files directly without loading them into memory,
making it ideal for analytical workloads on local data.

Usage::

    from pipeline.storage.duckdb_repository import DuckDBRepository

    repo = DuckDBRepository()
    repo.sync_gold_to_duckdb()            # import Gold Parquet → DuckDB table
    deals = repo.get_top_deals(n=10)      # query top deals
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb

from core.config import settings
from core.interfaces import BaseRepository
from core.logging_config import get_logger

log = get_logger(__name__)

# DuckDB table name for the Gold layer
GOLD_TABLE = "gold_listings"


class DuckDBRepository(BaseRepository):
    """
    Concrete repository backed by DuckDB.

    DuckDB is opened in file mode so data persists across runs.
    All public methods manage their own connection lifecycle.
    """

    def __init__(
        self,
        db_path: Path | None = None,
        gold_dir: Path | None = None,
    ) -> None:
        self._db_path = db_path or settings.DUCKDB_PATH
        self._gold_dir = gold_dir or settings.GOLD_DIR
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    # ── BaseRepository implementation ─────────────────────────────────────────

    def save(self, records: List[Dict[str, Any]], table_name: str) -> int:
        """
        Insert a list of dicts into a DuckDB table (creates table if missing).
        """
        if not records:
            return 0

        import pandas as pd

        df = pd.DataFrame(records)
        with duckdb.connect(str(self._db_path)) as con:
            # Create or replace (idempotent for pipeline re-runs)
            con.execute(
                f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM df"
            )
            row_count: int = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

        log.info("duckdb_saved", table=table_name, rows=row_count)
        return row_count

    def query(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute a raw SQL query and return results as a list of dicts."""
        with duckdb.connect(str(self._db_path)) as con:
            if params:
                result = con.execute(sql, list(params.values()))
            else:
                result = con.execute(sql)
            columns = [desc[0] for desc in result.description]
            rows = result.fetchall()

        return [dict(zip(columns, row)) for row in rows]

    # ── Domain-specific methods ───────────────────────────────────────────────

    def sync_gold_to_duckdb(self) -> int:
        """
        Read all Gold Parquet files and upsert them into the DuckDB table.

        DuckDB reads Parquet files natively using a glob pattern, so no
        intermediate DataFrame is needed.

        Returns
        -------
        Number of rows synced.
        """
        parquet_glob = str(self._gold_dir / "**" / "*.parquet")
        log.info("duckdb_sync_started", glob=parquet_glob)

        with duckdb.connect(str(self._db_path)) as con:
            con.execute(f"""
                CREATE OR REPLACE TABLE {GOLD_TABLE} AS
                SELECT *
                FROM read_parquet('{parquet_glob}', hive_partitioning=true)
            """)
            row_count: int = con.execute(
                f"SELECT COUNT(*) FROM {GOLD_TABLE}"
            ).fetchone()[0]

        log.info("duckdb_sync_complete", table=GOLD_TABLE, rows=row_count)
        return row_count

    def get_top_deals(self, n: int = 10, scrape_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Return the top ``n`` housing deals by Opportunity Index.

        Parameters
        ----------
        n:
            Maximum number of deals to return.
        scrape_date:
            Optional ``'YYYY-MM-DD'`` filter. If omitted, uses the latest available date.

        Returns
        -------
        List of deal dicts, ordered by ``opportunity_index`` descending.
        """
        date_filter = (
            f"AND scrape_date = '{scrape_date}'" if scrape_date
            else "AND scrape_date = (SELECT MAX(scrape_date) FROM gold_listings)"
        )

        sql = f"""
            SELECT
                source,
                url,
                title,
                price_eur,
                area_sqm,
                rooms,
                price_per_sqm,
                neighborhood,
                district,
                latitude,
                longitude,
                avg_neighborhood_price,
                opportunity_index,
                scrape_date
            FROM {GOLD_TABLE}
            WHERE opportunity_index > 0
              {date_filter}
            ORDER BY opportunity_index DESC
            LIMIT {n}
        """
        results = self.query(sql)
        log.info("top_deals_fetched", n=n, returned=len(results))
        return results

    def get_neighborhood_stats(self) -> List[Dict[str, Any]]:
        """
        Return aggregated statistics per neighbourhood for dashboard charts.
        """
        sql = f"""
            SELECT
                neighborhood,
                district,
                AVG(price_per_sqm)              AS avg_price_per_sqm,
                AVG(opportunity_index)           AS avg_opportunity_index,
                COUNT(*)                         AS listing_count,
                MIN(price_eur)                   AS min_price_eur,
                MAX(price_eur)                   AS max_price_eur,
                scrape_date
            FROM {GOLD_TABLE}
            WHERE scrape_date = (SELECT MAX(scrape_date) FROM {GOLD_TABLE})
            GROUP BY neighborhood, district, scrape_date
            ORDER BY avg_opportunity_index DESC
        """
        return self.query(sql)

    def get_deals_within_radius(
        self,
        lat: float,
        lon: float,
        radius_km: float = 2.0,
        n: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Find top deals within *radius_km* km of (*lat*, *lon*) using Haversine.

        Parameters
        ----------
        lat, lon : float
            Centre point coordinates.
        radius_km : float
            Search radius in kilometres.
        n : int
            Maximum results.

        Returns
        -------
        List of deal dicts with an extra ``distance_km`` field.
        """
        sql = f"""
            WITH distances AS (
                SELECT *,
                    6371 * ACOS(
                        LEAST(1.0,
                            COS(RADIANS({lat})) * COS(RADIANS(latitude))
                            * COS(RADIANS(longitude) - RADIANS({lon}))
                            + SIN(RADIANS({lat})) * SIN(RADIANS(latitude))
                        )
                    ) AS distance_km
                FROM {GOLD_TABLE}
                WHERE latitude IS NOT NULL
                  AND longitude IS NOT NULL
            )
            SELECT
                source, url, title, price_eur, area_sqm, rooms,
                price_per_sqm, neighborhood, district,
                latitude, longitude, avg_neighborhood_price,
                opportunity_index, scrape_date,
                ROUND(distance_km, 2) AS distance_km
            FROM distances
            WHERE distance_km <= {radius_km}
            ORDER BY opportunity_index DESC
            LIMIT {n}
        """
        results = self.query(sql)
        log.info("deals_within_radius", lat=lat, lon=lon, radius_km=radius_km, found=len(results))
        return results
