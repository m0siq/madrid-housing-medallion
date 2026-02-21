"""
main_pipeline_scrapping.py
===========================
Live scraping pipeline: Idealista → Bronze → Silver → Gold → DuckDB.

Uses the stealth-hardened extractor. Rotates through multiple Madrid
district URLs to build a city-wide dataset progressively.

Run::

    python main_pipeline_scrapping.py
"""

import asyncio
import random
import sys
from pathlib import Path

# Medallion architecture components
from pipeline.extractors.factory import ExtractorFactory
from pipeline.bronze.ingestor import BronzeIngestor
from pipeline.silver.cleaner import SilverCleaner
from pipeline.gold.opportunity_index import GoldOpportunityJob
from pipeline.storage.duckdb_repository import DuckDBRepository

# Config & Logging
from core.config import settings
from core.logging_config import configure_logging, get_logger
from pipeline.spark.session_manager import SparkSessionManager

log = get_logger("main_pipeline_scrapping")

# ---------------------------------------------------------------------------
# Madrid district URLs for Idealista
# ---------------------------------------------------------------------------
# Scraping rotates across districts to avoid hammering a single URL.
# Each run picks a random subset to avoid patterns.

IDEALISTA_DISTRICT_URLS = [
    "https://www.idealista.com/venta-viviendas/madrid/centro/",
    "https://www.idealista.com/venta-viviendas/madrid/arganzuela/",
    "https://www.idealista.com/venta-viviendas/madrid/retiro/",
    "https://www.idealista.com/venta-viviendas/madrid/salamanca/",
    "https://www.idealista.com/venta-viviendas/madrid/chamartin/",
    "https://www.idealista.com/venta-viviendas/madrid/tetuan/",
    "https://www.idealista.com/venta-viviendas/madrid/chamberi/",
    "https://www.idealista.com/venta-viviendas/madrid/fuencarral/",
    "https://www.idealista.com/venta-viviendas/madrid/moncloa/",
    "https://www.idealista.com/venta-viviendas/madrid/latina/",
    "https://www.idealista.com/venta-viviendas/madrid/carabanchel/",
    "https://www.idealista.com/venta-viviendas/madrid/usera/",
    "https://www.idealista.com/venta-viviendas/madrid/puente-de-vallecas/",
    "https://www.idealista.com/venta-viviendas/madrid/moratalaz/",
    "https://www.idealista.com/venta-viviendas/madrid/ciudad-lineal/",
    "https://www.idealista.com/venta-viviendas/madrid/hortaleza/",
    "https://www.idealista.com/venta-viviendas/madrid/villaverde/",
    "https://www.idealista.com/venta-viviendas/madrid/villa-de-vallecas/",
    "https://www.idealista.com/venta-viviendas/madrid/vicalvaro/",
    "https://www.idealista.com/venta-viviendas/madrid/san-blas/",
    "https://www.idealista.com/venta-viviendas/madrid/barajas/",
]


async def run_full_pipeline():
    """Execute the full E2E flow: Scrape → Bronze → Silver → Gold → DuckDB Sync"""

    configure_logging(level="INFO")
    log.info("pipeline_e2e_started", msg="Starting stealth scraping pipeline")

    try:
        # --- STEP 1: BRONZE (Live Stealth Scraping) ---
        log.info("step_1_bronze_start")
        ingestor = BronzeIngestor()
        extractor = ExtractorFactory.create("idealista")

        # Randomly pick 3-5 districts per run to avoid patterns
        n_districts = random.randint(3, 5)
        target_urls = random.sample(IDEALISTA_DISTRICT_URLS, n_districts)

        log.info(
            "scraping_districts",
            count=n_districts,
            districts=[u.split("/")[-2] for u in target_urls],
        )

        all_records = []
        for i, url in enumerate(target_urls, 1):
            district_slug = url.split("/")[-2]
            log.info("scraping_district", district=district_slug, progress=f"{i}/{n_districts}")

            records = await extractor.extract(url, max_pages=2)
            all_records.extend(records)

            # Inter-district delay (longer, more human-like)
            if i < n_districts:
                inter_delay = random.uniform(8, 20)
                log.info("inter_district_delay", seconds=round(inter_delay, 1))
                await asyncio.sleep(inter_delay)

        if not all_records:
            log.warning(
                "no_records_scraped",
                msg="No records obtained from any district. "
                    "The scraper may be blocked. Check logs for CAPTCHA/block warnings.",
            )
            raise ValueError("No records obtained. Pipeline stopped.")

        ingestor.ingest(all_records, source="idealista")
        log.info("step_1_bronze_complete", count=len(all_records), districts=n_districts)

        # --- STEP 2: SILVER (Cleaning with PySpark) ---
        log.info("step_2_silver_start")
        SilverCleaner().run()
        log.info("step_2_silver_complete")

        # --- STEP 3: GOLD (Opportunity Index with PySpark) ---
        log.info("step_3_gold_start")
        GoldOpportunityJob().run()
        log.info("step_3_gold_complete")

        # --- STEP 4: STORAGE (DuckDB sync for FastAPI) ---
        log.info("step_4_storage_start")
        repo = DuckDBRepository()
        count = repo.sync_gold_to_duckdb()
        log.info("step_4_storage_complete", synced_rows=count)

        print("\n" + "=" * 50)
        print("✅ LIVE SCRAPING PIPELINE COMPLETED")
        print(f"   Districts scraped: {n_districts}")
        print(f"   Records ingested: {len(all_records)}")
        print(f"   DuckDB rows synced: {count}")
        print("=" * 50 + "\n")

    except Exception as e:
        log.error("pipeline_failed", error=str(e))
        print(f"❌ Error during execution: {e}")
        sys.exit(1)
    finally:
        SparkSessionManager.stop()


if __name__ == "__main__":
    asyncio.run(run_full_pipeline())