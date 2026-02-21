"""
core/interfaces.py
==================
Abstract interfaces (ports) for the Clean Architecture.
Concrete implementations belong in the pipeline/ and app/storage/ layers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Extractor interface
# ---------------------------------------------------------------------------

class BaseExtractor(ABC):
    """
    Port for all web scrapers / data extractors.

    Each concrete extractor (Idealista, Fotocasa, …) must implement:
      - ``extract()``: Perform the scrape and return raw records.
    """

    @abstractmethod
    async def extract(
        self,
        url: str,
        max_pages: int = 1,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Extract raw property listings from a URL.

        Parameters
        ----------
        url:
            Starting URL for the scrape.
        max_pages:
            Maximum number of pagination pages to follow.
        filters:
            Optional dict of source-specific query filters.

        Returns
        -------
        List of raw property dictionaries.
        """
        ...

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Unique identifier for this data source, e.g. ``'idealista'``."""
        ...


# ---------------------------------------------------------------------------
# Repository interface
# ---------------------------------------------------------------------------

class BaseRepository(ABC):
    """
    Port for all data storage sinks.

    Concrete implementations may write to DuckDB, PostgreSQL, etc.
    """

    @abstractmethod
    def save(self, records: List[Dict[str, Any]], table_name: str) -> int:
        """
        Persist a list of records to the underlying store.

        Parameters
        ----------
        records:
            List of dicts to store.
        table_name:
            Target table / collection name.

        Returns
        -------
        Number of rows written.
        """
        ...

    @abstractmethod
    def query(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a read query against the underlying store.

        Parameters
        ----------
        sql:
            SQL query string.
        params:
            Optional bind parameters.

        Returns
        -------
        List of row dicts.
        """
        ...
