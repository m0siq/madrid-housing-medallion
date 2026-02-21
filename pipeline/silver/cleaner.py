"""
pipeline/silver/cleaner.py
===========================
SilverCleaner – PySpark job for the Silver (cleaned) Medallion layer.

Reads Bronze Parquet → deduplicates → type-casts → normalises → writes Silver.

Transformations applied
-----------------------
1. **Type casting**: price/area strings → float, rooms → int.
2. **Derived column**: ``price_per_sqm = price_eur / area_sqm``.
3. **Deduplication**: on (url, scrape_date).
4. **Null filtering**: drop rows missing price or area.
5. **Text normalisation**: title/neighborhood/district capitalised.

Run directly::

    python -m pipeline.silver.cleaner
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import FloatType, IntegerType

from core.config import settings
from core.logging_config import configure_logging, get_logger
from pipeline.spark.session_manager import SparkSessionManager

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# UDF helpers (pure Python, no Spark deps)
# ---------------------------------------------------------------------------

def _parse_price(raw: str | None) -> float | None:
    """Extract numeric EUR value from a raw price string like '350.000 €'."""
    if not raw:
        return None
    cleaned = re.sub(r"[^\d,.]", "", raw).replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_area(raw: str | None) -> float | None:
    """Extract numeric m² value from a raw area string like '85 m²'."""
    if not raw:
        return None
    match = re.search(r"[\d,]+", raw)
    if match:
        try:
            return float(match.group().replace(",", "."))
        except ValueError:
            return None
    return None


def _parse_rooms(raw: str | None) -> int | None:
    """Extract integer room count from a raw string like '3 hab.'."""
    if not raw:
        return None
    match = re.search(r"\d+", raw)
    return int(match.group()) if match else None


# Register UDFs
_udf_parse_price = F.udf(_parse_price, FloatType())
_udf_parse_area = F.udf(_parse_area, FloatType())
_udf_parse_rooms = F.udf(_parse_rooms, IntegerType())


# ---------------------------------------------------------------------------
# SilverCleaner
# ---------------------------------------------------------------------------

class SilverCleaner:
    """
    PySpark job that transforms Bronze raw Parquet into a cleaned Silver dataset.
    """

    def __init__(
        self,
        bronze_dir: Path | None = None,
        silver_dir: Path | None = None,
    ) -> None:
        self._bronze_dir = bronze_dir or settings.BRONZE_DIR
        self._silver_dir = silver_dir or settings.SILVER_DIR
        self._spark = SparkSessionManager.get_session()

    # ── Public entry point ────────────────────────────────────────────────────

    def run(self) -> None:
        """Execute the full Bronze → Silver pipeline."""
        log.info("silver_job_started", bronze_dir=str(self._bronze_dir))

        raw_df = self._read_bronze()
        cleaned_df = self._transform(raw_df)
        count = self._write_silver(cleaned_df)

        log.info("silver_job_complete", rows_written=count)

    # ── Steps ─────────────────────────────────────────────────────────────────

    def _read_bronze(self) -> DataFrame:
        """Load all Bronze Parquet partitions into a Spark DataFrame."""
        path = str(self._bronze_dir)
        df = self._spark.read.parquet(path)
        log.info("bronze_loaded", rows=df.count(), path=path)
        return df

    def _transform(self, df: DataFrame) -> DataFrame:
        """Apply all cleansing and normalisation transformations."""

        # ── 1. Parse numeric fields from raw strings ──────────────────────────
        df = (
            df
            .withColumn("price_eur", _udf_parse_price(F.col("raw_price")).cast(FloatType()))
            .withColumn("area_sqm", _udf_parse_area(F.col("raw_area")).cast(FloatType()))
            .withColumn("rooms", _udf_parse_rooms(F.col("raw_rooms")).cast(IntegerType()))
        )

        # ── 2. Filter rows with valid price and area ──────────────────────────
        df = df.filter(
            F.col("price_eur").isNotNull()
            & F.col("area_sqm").isNotNull()
            & (F.col("price_eur") > 0)
            & (F.col("area_sqm") > 0)
        )

        # ── 3. Compute price per m² ───────────────────────────────────────────
        df = df.withColumn(
            "price_per_sqm",
            (F.col("price_eur") / F.col("area_sqm")).cast(FloatType()),
        )

        # ── 4. Normalise text fields ──────────────────────────────────────────
        for col_name in ("title", "neighborhood", "district"):
            df = df.withColumn(
                col_name,
                F.initcap(F.trim(F.coalesce(F.col(col_name), F.lit("Desconocido")))),
            )

        # ── 5. Deduplicate on (url, scrape_date) ─────────────────────────────
        before = df.count()
        df = df.dropDuplicates(["url", "scrape_date"])
        after = df.count()
        log.info("dedup_applied", removed=before - after, remaining=after)

        # ── 6. Select final Silver schema ─────────────────────────────────────
        df = df.select(
            "source",
            "url",
            "title",
            "price_eur",
            "area_sqm",
            "rooms",
            "price_per_sqm",
            "neighborhood",
            "district",
            "latitude",
            "longitude",
            "scraped_at",
            "scrape_date",
        )

        return df

    def _write_silver(self, df: DataFrame) -> int:
        """Persist cleaned DataFrame to the Silver layer as Parquet."""
        self._silver_dir.mkdir(parents=True, exist_ok=True)
        path = str(self._silver_dir)

        (
            df
            .repartition(1)
            .write
            .mode("overwrite")
            .partitionBy("source", "scrape_date")
            .parquet(path)
        )
        count = df.count()
        log.info("silver_written", path=path, rows=count)
        return count


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    configure_logging(level=settings.LOG_LEVEL, fmt=settings.LOG_FORMAT)
    try:
        SilverCleaner().run()
    except Exception as exc:
        log.exception("silver_job_failed", error=str(exc))
        sys.exit(1)
    finally:
        SparkSessionManager.stop()
