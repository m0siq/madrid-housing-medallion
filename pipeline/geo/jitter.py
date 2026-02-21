"""
pipeline/geo/jitter.py
========================
Spatial jitter utility to scatter map markers around a centre point.

Adds gaussian random noise within a configurable radius to prevent
multiple listings from stacking on the exact same coordinate.

Usage::

    from pipeline.geo.jitter import add_jitter

    lat, lon = add_jitter(40.4169, -3.7035, radius_m=200)
"""

from __future__ import annotations

import math
import random


# Earth radius in metres (WGS-84 mean)
_EARTH_RADIUS_M = 6_371_000


def add_jitter(
    lat: float,
    lon: float,
    radius_m: float = 200,
) -> tuple[float, float]:
    """
    Return a new (lat, lon) displaced by gaussian noise within *radius_m* metres.

    Parameters
    ----------
    lat, lon : float
        Centre coordinates in decimal degrees.
    radius_m : float
        Standard-deviation radius in metres. ~68 % of points will fall
        within this distance; ~95 % within 2× this distance.

    Returns
    -------
    tuple[float, float]
        Jittered (latitude, longitude).
    """
    # Convert radius to degrees (approximate at Madrid's latitude)
    # 1 degree latitude  ≈ 111,320 m
    # 1 degree longitude ≈ 111,320 m × cos(lat)
    dlat_deg = radius_m / 111_320
    dlon_deg = radius_m / (111_320 * math.cos(math.radians(lat)))

    # Gaussian noise (most points within 1σ, rare outliers at 2–3σ)
    jitter_lat = random.gauss(0, dlat_deg)
    jitter_lon = random.gauss(0, dlon_deg)

    return (lat + jitter_lat, lon + jitter_lon)
