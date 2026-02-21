"""
pipeline/gold/opportunity_index.py
====================================
GoldOpportunityJob – PySpark Gold layer.

Reads the Silver dataset, computes the **Opportunity Index** per listing,
ranks deals, and writes the Gold Parquet output for downstream consumption.

Opportunity Index formula
--------------------------
    opportunity_index = 1 - (listing_price_per_sqm / neighborhood_avg_price_per_sqm)

Interpretation:
  * ``> 0``: listing is cheaper than the neighbourhood average → good deal.
  * ``= 0``: listing is at the neighbourhood average.
  * ``< 0``: listing is more expensive than the neighbourhood average.

A higher positive value indicates a better deal.

Run directly::

    python -m pipeline.gold.opportunity_index
"""

from __future__ import annotations

import sys
from pathlib import Path

from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F
from pyspark.sql.types import FloatType, IntegerType

from core.config import settings
from core.logging_config import configure_logging, get_logger
from pipeline.spark.session_manager import SparkSessionManager

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# GoldOpportunityJob
# ---------------------------------------------------------------------------

class GoldOpportunityJob:
    """
    PySpark job that computes the Opportunity Index and produces the Gold layer.

    Steps
    -----
    1. Load Silver Parquet.
    2. Compute ``neighborhood_avg_price_per_sqm`` using a Window function
       partitioned by ``neighborhood`` + ``scrape_date``.
    3. Compute ``opportunity_index`` for each listing.
    4. Rank listings by ``opportunity_index`` (descending, per scrape date).
    5. Write Gold Parquet partitioned by ``scrape_date``.
    """

    def __init__(
        self,
        silver_dir: Path | None = None,
        gold_dir: Path | None = None,
    ) -> None:
        self._silver_dir = silver_dir or settings.SILVER_DIR
        self._gold_dir = gold_dir or settings.GOLD_DIR
        self._spark = SparkSessionManager.get_session()

    # ── Public entry point ────────────────────────────────────────────────────

    def run(self) -> None:
        """Execute the full Silver → Gold pipeline."""
        log.info("gold_job_started", silver_dir=str(self._silver_dir))

        silver_df = self._read_silver()
        gold_df = self._compute_opportunity_index(silver_df)
        count = self._write_gold(gold_df)

        log.info("gold_job_complete", rows_written=count)

    # ── Steps ─────────────────────────────────────────────────────────────────

    def _read_silver(self) -> DataFrame:
        """Load all Silver Parquet partitions."""
        path = str(self._silver_dir)
        df = self.spark.read.csv("data/silver/madrid_housing_clean.csv", header=True, inferSchema=True)
        row_count = df.count()
        log.info("silver_loaded", rows=row_count, path=path)

        if row_count == 0:
            raise ValueError("Silver dataset is empty. Run the Silver cleaner first.")

        return df

    def _compute_opportunity_index(self, df: DataFrame) -> DataFrame:
        """
        Enrich each listing with neighbourhood stats and Opportunity Index.

        Window function details
        -----------------------
        * **Partition**: ``neighborhood``, ``scrape_date`` — ensures that
          the average is computed within the same neighbourhood and on the
          same scraping day, making it a fair comparison.
        * **Statistic**: ``avg(price_per_sqm)`` — mean price per m² for all
          listings in that neighbourhood on that day.
        """

        # ── Step 1: Neighbourhood average via Window ──────────────────────────
        neighbourhood_window = Window.partitionBy("neighborhood", "scrape_date")

        df = df.withColumn(
            "neighborhood_avg_price_per_sqm",
            F.avg(F.col("price_per_sqm")).over(neighbourhood_window).cast(FloatType()),
        )

        # ── Step 2: Opportunity Index ──────────────────────────────────────────
        #   opportunity_index = 1 - (listing / avg)
        #   Clamp to [-1, 1] to handle extreme outliers.
        df = df.withColumn(
            "opportunity_index",
            F.greatest(
                F.lit(-1.0).cast(FloatType()),
                F.least(
                    F.lit(1.0).cast(FloatType()),
                    (
                        F.lit(1.0)
                        - (F.col("price_per_sqm") / F.col("neighborhood_avg_price_per_sqm"))
                    ).cast(FloatType()),
                ),
            ),
        )

        # ── Step 3: Global rank by opportunity_index per scrape_date ──────────
        rank_window = Window.partitionBy("scrape_date").orderBy(
            F.desc("opportunity_index")
        )
        df = df.withColumn(
            "rank",
            F.rank().over(rank_window).cast(IntegerType()),
        )

        # ── Step 4: Filter out neighbourhoods with only 1 listing ────────────
        #   (can't compute a meaningful average from a single data point)
        neighbourhood_count_window = Window.partitionBy("neighborhood", "scrape_date")
        df = df.withColumn(
            "_listing_count_in_neighbourhood",
            F.count("*").over(neighbourhood_count_window),
        )
        df = df.filter(F.col("_listing_count_in_neighbourhood") > 1)
        df = df.drop("_listing_count_in_neighbourhood")

        # ── Step 5: Select and order final Gold schema ────────────────────────
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
            "neighborhood_avg_price_per_sqm",
            "opportunity_index",
            "rank",
            "scrape_date",
        ).orderBy("scrape_date", "rank")

        row_count = df.count()
        log.info("opportunity_index_computed", rows=row_count)
        return df

    def _write_gold(self, df: DataFrame) -> int:
        """Persist the Gold DataFrame as Parquet partitioned by scrape_date."""
        self._gold_dir.mkdir(parents=True, exist_ok=True)
        path = str(self._gold_dir)

        (
            df
            .repartition(1)
            .write
            .mode("overwrite")
            .partitionBy("scrape_date")
            .parquet(path)
        )
        count = df.count()
        log.info("gold_written", path=path, rows=count)
        return count


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    configure_logging(level=settings.LOG_LEVEL, fmt=settings.LOG_FORMAT)
    try:
        GoldOpportunityJob().run()
    except Exception as exc:
        log.exception("gold_job_failed", error=str(exc))
        sys.exit(1)
    finally:
        SparkSessionManager.stop()
