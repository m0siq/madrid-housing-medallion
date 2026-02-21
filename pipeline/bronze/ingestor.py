"""
pipeline/bronze/ingestor.py
============================
BronzeIngestor – persists raw scraper output as partitioned Parquet files.

Medallion Bronze Layer: raw data exactly as received from the scraper,
with minimal transformations (only schema enforcement via Pydantic).

Partition layout::

    data/bronze/
    └── source=idealista/
        └── date=2024-01-15/
            └── part-0000.parquet
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from core.config import settings
from core.logging_config import get_logger
from core.models import RawProperty

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# BronzeIngestor
# ---------------------------------------------------------------------------

class BronzeIngestor:
    """
    Receives raw dicts from extractors, validates them via ``RawProperty``,
    and writes partitioned Parquet files to the Bronze data lake layer.
    """

    def __init__(self, bronze_dir: Path | None = None) -> None:
        self._bronze_dir = bronze_dir or settings.BRONZE_DIR
        self._bronze_dir.mkdir(parents=True, exist_ok=True)

    # ── Public API ────────────────────────────────────────────────────────────

    def ingest(
        self,
        records: List[Dict[str, Any]],
        source: str,
        scrape_date: str | None = None,
    ) -> Path:
        """
        Validate and persist raw records to the Bronze Parquet layer.

        Parameters
        ----------
        records:
            List of raw dicts from ``BaseExtractor.extract()``.
        source:
            Source identifier used as partition key, e.g. ``"idealista"``.
        scrape_date:
            ISO date string ``"YYYY-MM-DD"`` for the partition.
            Defaults to today (UTC).

        Returns
        -------
        Path to the written Parquet file.
        """
        if not records:
            log.warning("bronze_ingest_skipped", source=source, reason="empty_records")
            raise ValueError(f"No records to ingest for source='{source}'.")

        date_str = scrape_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # ── Validate via Pydantic ─────────────────────────────────────────────
        validated: List[Dict[str, Any]] = []
        validation_errors = 0
        for raw in records:
            try:
                prop = RawProperty(**raw)
                row = prop.model_dump()
                row["scraped_at"] = row["scraped_at"].isoformat()
                validated.append(row)
            except Exception as exc:  # noqa: BLE001
                validation_errors += 1
                log.warning(
                    "bronze_validation_error",
                    source=source,
                    error=str(exc),
                    raw_record=raw,
                )

        if not validated:
            raise ValueError(
                f"All {len(records)} records failed validation for source='{source}'."
            )

        log.info(
            "bronze_validated",
            source=source,
            valid=len(validated),
            errors=validation_errors,
        )

        # ── Write Parquet ─────────────────────────────────────────────────────
        out_path = self._build_partition_path(source, date_str)
        out_path.mkdir(parents=True, exist_ok=True)

        df = pd.DataFrame(validated)
        table = pa.Table.from_pandas(df, preserve_index=False)

        file_path = out_path / "part-0000.parquet"
        pq.write_table(table, file_path, compression="snappy")

        log.info(
            "bronze_written",
            source=source,
            date=date_str,
            rows=len(validated),
            path=str(file_path),
        )
        return file_path

    def _build_partition_path(self, source: str, date_str: str) -> Path:
        """Return the Hive-partition directory path for a given source + date."""
        safe_source = re.sub(r"[^\w\-]", "_", source.lower())
        return self._bronze_dir / f"source={safe_source}" / f"date={date_str}"
