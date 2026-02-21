"""
pipeline/spark/session_manager.py
==================================
SparkSessionManager – Singleton Pattern.

Ensures only one SparkSession is created per process, shared across all
pipeline jobs. Thread-safe via a class-level lock.

Usage::

    from pipeline.spark.session_manager import SparkSessionManager

    spark = SparkSessionManager.get_session()
    df = spark.read.parquet("data/silver/")
"""

from __future__ import annotations

import threading

from pyspark.sql import SparkSession

from core.config import settings
from core.logging_config import get_logger

log = get_logger(__name__)


class SparkSessionManager:
    """
    Thread-safe Singleton that manages a single shared SparkSession.

    Design decisions
    ----------------
    * Uses a class-level ``threading.Lock`` (double-checked locking) so
      concurrent calls during startup do not create multiple sessions.
    * Reads configuration from ``core.config.settings`` so Spark parameters
      (app name, master URL) are centralised.
    * ``stop()`` is provided for test teardown; in production the session lives
      for the lifetime of the process.
    """

    _instance: SparkSession | None = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "SparkSessionManager":  # noqa: D102
        raise TypeError(
            "SparkSessionManager is a static utility class. "
            "Use SparkSessionManager.get_session() instead."
        )

    @classmethod
    def get_session(cls) -> SparkSession:
        """
        Return the shared SparkSession, creating it if it does not yet exist.

        Returns
        -------
        pyspark.sql.SparkSession
            The single active SparkSession for this process.
        """
        # Fast path – no lock needed once session exists
        if cls._instance is not None:
            return cls._instance

        with cls._lock:
            # Double-checked locking: verify again inside the lock
            if cls._instance is None:
                log.info(
                    "spark_session_creating",
                    app_name=settings.SPARK_APP_NAME,
                    master=settings.SPARK_MASTER,
                )
                cls._instance = (
                    SparkSession.builder
                    .appName(settings.SPARK_APP_NAME)
                    .master(settings.SPARK_MASTER)
                    # ── Parquet optimisations ─────────────────────────────────
                    .config("spark.sql.parquet.filterPushdown", "true")
                    .config("spark.sql.parquet.mergeSchema", "false")
                    # ── Performance ───────────────────────────────────────────
                    .config("spark.sql.shuffle.partitions", "8")
                    .config("spark.default.parallelism", "8")
                    # ── Logging noise reduction ───────────────────────────────
                    .config("spark.driver.extraJavaOptions", "-Dlog4j.logLevel=WARN")
                    .getOrCreate()
                )
                cls._instance.sparkContext.setLogLevel("WARN")
                log.info(
                    "spark_session_created",
                    app_id=cls._instance.sparkContext.applicationId,
                )

        return cls._instance

    @classmethod
    def stop(cls) -> None:
        """
        Stop the SparkSession and reset the singleton.

        Primarily used in tests and CI pipeline teardown. In production,
        let the session live for the lifetime of the process.
        """
        with cls._lock:
            if cls._instance is not None:
                log.info("spark_session_stopping")
                cls._instance.stop()
                cls._instance = None
                log.info("spark_session_stopped")
