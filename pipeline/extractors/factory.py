"""
pipeline/extractors/factory.py
================================
ExtractorFactory – Factory Pattern implementation.

Maintains a central registry of scraper classes keyed by source name.
New sources can be registered at runtime or via the REGISTRY constant.

Usage::

    from pipeline.extractors.factory import ExtractorFactory

    # Create an extractor by name
    extractor = ExtractorFactory.create("idealista")
    results = await extractor.extract(url="https://...", max_pages=3)

    # Register a custom extractor at runtime
    ExtractorFactory.register("custom_source", MyCustomExtractor)

    # List available sources
    sources = ExtractorFactory.available_sources()
"""

from __future__ import annotations

from typing import Dict, Type

from core.interfaces import BaseExtractor
from core.logging_config import get_logger

log = get_logger(__name__)

# Lazy imports inside register() to avoid circular imports at module level;
# the factory only imports a class when it's actually requested.
_REGISTRY: Dict[str, Type[BaseExtractor]] = {}


def _build_default_registry() -> Dict[str, Type[BaseExtractor]]:
    """Populate the default extractor registry on first access."""
    from pipeline.extractors.fotocasa_extractor import FotocasaExtractor
    from pipeline.extractors.idealista_extractor import IdealistaExtractor

    return {
        IdealistaExtractor.SOURCE: IdealistaExtractor,
        FotocasaExtractor.SOURCE: FotocasaExtractor,
    }


class ExtractorFactory:
    """
    Central factory for all web scraper extractors.

    Design decisions
    ----------------
    * **Registry pattern**: extractor classes are stored in a plain dict,
      making it trivial to add new sources without modifying this file.
    * **Lazy loading**: concrete extractor modules are imported on first
      use, so the heavy Playwright dependency is not pulled in unless needed.
    * **Validation**: raises ``ValueError`` for unknown source names with a
      helpful list of available options.
    """

    # Class-level registry; populated lazily on first call.
    _registry: Dict[str, Type[BaseExtractor]] = {}

    @classmethod
    def _ensure_registry(cls) -> None:
        """Initialise the registry if it has not been populated yet."""
        if not cls._registry:
            cls._registry = _build_default_registry()
            log.debug(
                "extractor_registry_initialised",
                sources=list(cls._registry.keys()),
            )

    # ── Public API ────────────────────────────────────────────────────────────

    @classmethod
    def create(cls, source: str) -> BaseExtractor:
        """
        Instantiate and return the extractor for the given ``source`` name.

        Parameters
        ----------
        source:
            Case-insensitive source identifier, e.g. ``"idealista"`` or
            ``"fotocasa"``.

        Returns
        -------
        A fully initialised ``BaseExtractor`` instance.

        Raises
        ------
        ValueError
            If ``source`` is not in the registry.

        Examples
        --------
        >>> extractor = ExtractorFactory.create("idealista")
        >>> type(extractor).__name__
        'IdealistaExtractor'
        """
        cls._ensure_registry()
        key = source.lower().strip()
        extractor_class = cls._registry.get(key)

        if extractor_class is None:
            available = cls.available_sources()
            log.error(
                "unknown_extractor_source",
                requested=source,
                available=available,
            )
            raise ValueError(
                f"Unknown extractor source: '{source}'. "
                f"Available sources: {available}. "
                "Use ExtractorFactory.register() to add new ones."
            )

        instance = extractor_class()
        log.info("extractor_created", source=key, cls=type(instance).__name__)
        return instance

    @classmethod
    def register(cls, source: str, extractor_class: Type[BaseExtractor]) -> None:
        """
        Register a new extractor class under the given ``source`` name.

        This allows extending the factory at runtime without modifying this file.

        Parameters
        ----------
        source:
            Unique source identifier (lowercased automatically).
        extractor_class:
            A concrete subclass of ``BaseExtractor``.

        Raises
        ------
        TypeError
            If ``extractor_class`` does not subclass ``BaseExtractor``.

        Examples
        --------
        >>> ExtractorFactory.register("pisos_com", PisosDotComExtractor)
        """
        cls._ensure_registry()
        if not (isinstance(extractor_class, type) and issubclass(extractor_class, BaseExtractor)):
            raise TypeError(
                f"{extractor_class!r} must be a subclass of BaseExtractor."
            )
        key = source.lower().strip()
        cls._registry[key] = extractor_class
        log.info("extractor_registered", source=key, cls=extractor_class.__name__)

    @classmethod
    def available_sources(cls) -> list[str]:
        """Return a sorted list of all registered source names."""
        cls._ensure_registry()
        return sorted(cls._registry.keys())
