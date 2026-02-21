import asyncio
import sys
from pathlib import Path
import pandas as pd
import duckdb
from pyspark.sql import functions as F

# Project components
from pipeline.spark.session_manager import SparkSessionManager
from core.config import settings
from core.logging_config import configure_logging, get_logger

log = get_logger("main_pipeline")

async def run_full_pipeline():
    """Execute the full E2E flow: Bronze (CSV) -> Silver -> Gold -> DuckDB Sync"""
    
    configure_logging(level="INFO")
    log.info("pipeline_e2e_started", msg="Starting consistent processing for API/Dashboard")

    try:
        # --- STEP 1: BRONZE ---
        log.info("step_1_bronze_start")
        spark = SparkSessionManager.get_session()
        
        # Vital patch for Windows: avoids winutils.exe error
        spark._jsc.hadoopConfiguration().set("fs.file.impl", "org.apache.hadoop.fs.RawLocalFileSystem")
        
        path_bronze = "data/bronze/source=synthetic/date=2026-02-21/madrid_2026.csv"
        if not Path(path_bronze).exists():
            raise FileNotFoundError(f"Not found: {path_bronze}. Run generate_bronze.py first.")
        log.info("step_1_bronze_complete")

        # --- STEP 2: SILVER ---
        log.info("step_2_silver_start")
        df_spark = spark.read.csv(path_bronze, header=True, inferSchema=True)
        
        silver_folder = Path("data/silver")
        silver_folder.mkdir(parents=True, exist_ok=True)
        silver_file = silver_folder / "madrid_housing_clean.csv"
        
        # Bypass Hadoop using Pandas to write local CSV
        df_spark.toPandas().to_csv(silver_file, index=False)
        log.info("step_2_silver_complete")

        # --- STEP 3: GOLD (Final schema with calculated metrics) ---
        log.info("step_3_gold_start")
        
        df_silver = spark.read.csv(str(silver_file), header=True, inferSchema=True)
        
        # 1. Aggregation by neighbourhood
        avg_price_df = df_silver.groupBy("neighborhood").agg(
            F.avg("price").alias("avg_neighborhood_price")
        )
        
        # 2. Join and create all columns the API needs
        df_gold = df_silver.join(avg_price_df, "neighborhood")
        
        df_gold = (
            df_gold
            .withColumn(
                "opportunity_index",
                (F.col("avg_neighborhood_price") - F.col("price")) / F.col("avg_neighborhood_price")
            )
            .withColumn("price_eur", F.col("price"))
            .withColumn("area_sqm", F.col("sq_mt"))
            .withColumn("area_m2", F.col("sq_mt"))
            .withColumn("price_per_sqm", F.col("price") / F.col("sq_mt"))
            .withColumn("source", F.lit("synthetic_2026"))
            .withColumn("url", F.concat(
                F.lit("https://www.idealista.com/inmueble/"),
                F.monotonically_increasing_id().cast("string"),
                F.lit("/")
            ))
        )
        # NOTE: latitude, longitude, district, rooms, bathrooms
        # are already present from the Bronze CSV — no need to inject static values!
        
        # 3. Final save
        gold_file = "data/gold/opportunities.csv"
        Path("data/gold").mkdir(parents=True, exist_ok=True)
        df_gold.toPandas().to_csv(gold_file, index=False)
        log.info("step_3_gold_complete", path=gold_file)

        # --- STEP 4: STORAGE (Sync to DuckDB for FastAPI) ---
        log.info("step_4_storage_start")
        con = duckdb.connect(settings.DUCKDB_PATH)
        
        # Sync with the table name the API expects
        con.execute(f"CREATE OR REPLACE TABLE gold_listings AS SELECT * FROM read_csv_auto('{gold_file}')")
        
        # Verify district coverage
        districts = con.execute("SELECT DISTINCT district FROM gold_listings ORDER BY district").fetchall()
        count = con.execute("SELECT count(*) FROM gold_listings").fetchone()[0]
        con.close()
        log.info("step_4_storage_complete", synced_rows=count, districts=len(districts))

        print("\n" + "="*50)
        print("✅ PIPELINE COMPLETED SUCCESSFULLY")
        print(f"   Table: gold_listings")
        print(f"   Records: {count}")
        print(f"   Districts: {len(districts)}")
        for d in districts:
            print(f"     • {d[0]}")
        print("="*50 + "\n")

    except Exception as e:
        log.error("pipeline_failed", error=str(e))
        print(f"❌ Error during execution: {e}")
        sys.exit(1)
    finally:
        SparkSessionManager.stop()

if __name__ == "__main__":
    asyncio.run(run_full_pipeline())