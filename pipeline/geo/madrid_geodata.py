"""
pipeline/geo/madrid_geodata.py
================================
Static geodata for all 21 Madrid districts and their barrios.

Coordinates sourced from OpenStreetMap barrio centroids.
Price ranges are realistic estimates for 2026 (EUR/m²).

Usage::

    from pipeline.geo.madrid_geodata import get_coords, get_district, MADRID_DISTRICTS

    lat, lon = get_coords("Sol")            # (40.4169, -3.7035)
    district = get_district("Sol")          # "Centro"
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Master geodata: 21 districts × barrios
# ---------------------------------------------------------------------------
# Format: district -> {center, avg_price_sqm, barrios: {name -> {lat, lon, price_range}}}

MADRID_DISTRICTS: Dict[str, dict] = {
    # ── 1. Centro ──────────────────────────────────────────────────────────
    "Centro": {
        "lat": 40.4155, "lon": -3.7074, "avg_price_sqm": 5500,
        "barrios": {
            "Sol":             {"lat": 40.4169, "lon": -3.7035, "price_range": (4800, 6200)},
            "Cortes":          {"lat": 40.4145, "lon": -3.6975, "price_range": (5000, 6500)},
            "Embajadores":     {"lat": 40.4080, "lon": -3.7060, "price_range": (3800, 5200)},
            "Justicia":        {"lat": 40.4245, "lon": -3.6975, "price_range": (5200, 6800)},
            "Universidad":     {"lat": 40.4260, "lon": -3.7100, "price_range": (4500, 5800)},
            "Palacio":         {"lat": 40.4140, "lon": -3.7140, "price_range": (4800, 6000)},
        },
    },

    # ── 2. Arganzuela ─────────────────────────────────────────────────────
    "Arganzuela": {
        "lat": 40.3950, "lon": -3.6940, "avg_price_sqm": 4200,
        "barrios": {
            "Acacias":         {"lat": 40.4020, "lon": -3.7050, "price_range": (3800, 4800)},
            "Chopera":         {"lat": 40.3950, "lon": -3.6940, "price_range": (3600, 4600)},
            "Legazpi":         {"lat": 40.3900, "lon": -3.6950, "price_range": (3500, 4500)},
            "Delicias":        {"lat": 40.3980, "lon": -3.6920, "price_range": (3700, 4700)},
            "Palos de Moguer": {"lat": 40.4010, "lon": -3.6870, "price_range": (3600, 4600)},
            "Atocha":          {"lat": 40.4050, "lon": -3.6900, "price_range": (4000, 5000)},
            "Imperial":        {"lat": 40.4060, "lon": -3.7120, "price_range": (3500, 4500)},
        },
    },

    # ── 3. Retiro ─────────────────────────────────────────────────────────
    "Retiro": {
        "lat": 40.4090, "lon": -3.6770, "avg_price_sqm": 6200,
        "barrios": {
            "Pacífico":        {"lat": 40.4020, "lon": -3.6730, "price_range": (5000, 6500)},
            "Adelfas":         {"lat": 40.4000, "lon": -3.6680, "price_range": (4800, 6200)},
            "Estrella":        {"lat": 40.4080, "lon": -3.6740, "price_range": (5500, 7000)},
            "Ibiza":           {"lat": 40.4200, "lon": -3.6770, "price_range": (5800, 7200)},
            "Jerónimos":       {"lat": 40.4130, "lon": -3.6870, "price_range": (6500, 8500)},
            "Niño Jesús":      {"lat": 40.4100, "lon": -3.6780, "price_range": (6000, 7800)},
        },
    },

    # ── 4. Salamanca ──────────────────────────────────────────────────────
    "Salamanca": {
        "lat": 40.4310, "lon": -3.6820, "avg_price_sqm": 7500,
        "barrios": {
            "Recoletos":       {"lat": 40.4250, "lon": -3.6880, "price_range": (7000, 9500)},
            "Goya":            {"lat": 40.4260, "lon": -3.6740, "price_range": (6500, 8500)},
            "Castellana":      {"lat": 40.4380, "lon": -3.6870, "price_range": (7500, 10000)},
            "Lista":           {"lat": 40.4310, "lon": -3.6720, "price_range": (6000, 8000)},
            "Fuente del Berro":{"lat": 40.4250, "lon": -3.6680, "price_range": (5500, 7500)},
            "Guindalera":      {"lat": 40.4340, "lon": -3.6700, "price_range": (5000, 7000)},
        },
    },

    # ── 5. Chamartín ──────────────────────────────────────────────────────
    "Chamartín": {
        "lat": 40.4620, "lon": -3.6770, "avg_price_sqm": 6500,
        "barrios": {
            "El Viso":         {"lat": 40.4450, "lon": -3.6880, "price_range": (7000, 9000)},
            "Prosperidad":     {"lat": 40.4420, "lon": -3.6720, "price_range": (5000, 6500)},
            "Ciudad Jardín":   {"lat": 40.4500, "lon": -3.6700, "price_range": (5200, 6800)},
            "Hispanoamérica":  {"lat": 40.4570, "lon": -3.6750, "price_range": (5500, 7500)},
            "Nueva España":    {"lat": 40.4650, "lon": -3.6800, "price_range": (5000, 6500)},
            "Castilla":        {"lat": 40.4720, "lon": -3.6870, "price_range": (4800, 6200)},
        },
    },

    # ── 6. Tetuán ─────────────────────────────────────────────────────────
    "Tetuán": {
        "lat": 40.4600, "lon": -3.7000, "avg_price_sqm": 4200,
        "barrios": {
            "Bellas Vistas":   {"lat": 40.4530, "lon": -3.7060, "price_range": (3500, 4500)},
            "Cuatro Caminos":  {"lat": 40.4480, "lon": -3.7050, "price_range": (4000, 5200)},
            "Castillejos":     {"lat": 40.4520, "lon": -3.6950, "price_range": (3800, 5000)},
            "Almenara":        {"lat": 40.4620, "lon": -3.7000, "price_range": (3200, 4200)},
            "Valdeacederas":   {"lat": 40.4650, "lon": -3.7020, "price_range": (3000, 4000)},
            "Berruguete":      {"lat": 40.4580, "lon": -3.7030, "price_range": (3200, 4200)},
        },
    },

    # ── 7. Chamberí ───────────────────────────────────────────────────────
    "Chamberí": {
        "lat": 40.4350, "lon": -3.7070, "avg_price_sqm": 6000,
        "barrios": {
            "Gaztambide":      {"lat": 40.4340, "lon": -3.7130, "price_range": (5000, 6500)},
            "Arapiles":        {"lat": 40.4320, "lon": -3.7060, "price_range": (5200, 6800)},
            "Trafalgar":       {"lat": 40.4310, "lon": -3.7010, "price_range": (5500, 7000)},
            "Almagro":         {"lat": 40.4330, "lon": -3.6950, "price_range": (6000, 7800)},
            "Ríos Rosas":      {"lat": 40.4400, "lon": -3.7020, "price_range": (4800, 6200)},
            "Vallehermoso":    {"lat": 40.4390, "lon": -3.7130, "price_range": (4500, 5800)},
        },
    },

    # ── 8. Fuencarral-El Pardo ────────────────────────────────────────────
    "Fuencarral-El Pardo": {
        "lat": 40.5100, "lon": -3.7300, "avg_price_sqm": 3800,
        "barrios": {
            "El Pardo":        {"lat": 40.5230, "lon": -3.7700, "price_range": (3000, 4200)},
            "Fuentelarreina":  {"lat": 40.4950, "lon": -3.7350, "price_range": (3500, 4800)},
            "Peñagrande":      {"lat": 40.4800, "lon": -3.7250, "price_range": (3200, 4200)},
            "El Pilar":        {"lat": 40.4750, "lon": -3.7100, "price_range": (3500, 4500)},
            "La Paz":          {"lat": 40.4900, "lon": -3.7050, "price_range": (3000, 4000)},
            "Mirasierra":      {"lat": 40.4980, "lon": -3.7200, "price_range": (4000, 5500)},
        },
    },

    # ── 9. Moncloa-Aravaca ────────────────────────────────────────────────
    "Moncloa-Aravaca": {
        "lat": 40.4350, "lon": -3.7350, "avg_price_sqm": 5200,
        "barrios": {
            "Casa de Campo":   {"lat": 40.4200, "lon": -3.7500, "price_range": (4000, 5200)},
            "Argüelles":       {"lat": 40.4300, "lon": -3.7180, "price_range": (5000, 6500)},
            "Ciudad Universitaria": {"lat": 40.4470, "lon": -3.7300, "price_range": (4500, 5800)},
            "Valdezarza":      {"lat": 40.4580, "lon": -3.7280, "price_range": (3800, 5000)},
            "Valdemarín":      {"lat": 40.4550, "lon": -3.7650, "price_range": (5500, 7500)},
            "Aravaca":         {"lat": 40.4500, "lon": -3.7800, "price_range": (5000, 7000)},
        },
    },

    # ── 10. Latina ────────────────────────────────────────────────────────
    "Latina": {
        "lat": 40.4020, "lon": -3.7450, "avg_price_sqm": 2800,
        "barrios": {
            "Los Cármenes":    {"lat": 40.3950, "lon": -3.7400, "price_range": (2200, 3200)},
            "Puerta del Ángel":{"lat": 40.4050, "lon": -3.7300, "price_range": (2800, 3800)},
            "Lucero":          {"lat": 40.3920, "lon": -3.7350, "price_range": (2200, 3000)},
            "Aluche":          {"lat": 40.3850, "lon": -3.7550, "price_range": (2400, 3200)},
            "Campamento":      {"lat": 40.3830, "lon": -3.7650, "price_range": (2000, 2800)},
            "Cuatro Vientos":  {"lat": 40.3700, "lon": -3.7850, "price_range": (2000, 2600)},
            "Las Águilas":     {"lat": 40.3880, "lon": -3.7450, "price_range": (2400, 3200)},
        },
    },

    # ── 11. Carabanchel ───────────────────────────────────────────────────
    "Carabanchel": {
        "lat": 40.3830, "lon": -3.7350, "avg_price_sqm": 2400,
        "barrios": {
            "Comillas":        {"lat": 40.3950, "lon": -3.7200, "price_range": (2500, 3300)},
            "Opañel":          {"lat": 40.3900, "lon": -3.7150, "price_range": (2200, 3000)},
            "San Isidro":      {"lat": 40.3980, "lon": -3.7250, "price_range": (2000, 2800)},
            "Vista Alegre":    {"lat": 40.3860, "lon": -3.7250, "price_range": (2000, 2800)},
            "Puerta Bonita":   {"lat": 40.3820, "lon": -3.7180, "price_range": (2000, 2600)},
            "Buenavista":      {"lat": 40.3750, "lon": -3.7350, "price_range": (2200, 2800)},
            "Abrantes":        {"lat": 40.3700, "lon": -3.7300, "price_range": (1800, 2500)},
        },
    },

    # ── 12. Usera ─────────────────────────────────────────────────────────
    "Usera": {
        "lat": 40.3820, "lon": -3.7050, "avg_price_sqm": 2200,
        "barrios": {
            "Orcasitas":       {"lat": 40.3700, "lon": -3.7000, "price_range": (1600, 2300)},
            "Orcasur":         {"lat": 40.3650, "lon": -3.6950, "price_range": (1500, 2200)},
            "San Fermín":      {"lat": 40.3600, "lon": -3.6900, "price_range": (1500, 2100)},
            "Almendrales":     {"lat": 40.3850, "lon": -3.7000, "price_range": (1800, 2600)},
            "Moscardó":        {"lat": 40.3900, "lon": -3.7050, "price_range": (1900, 2700)},
            "Pradolongo":      {"lat": 40.3780, "lon": -3.7020, "price_range": (1700, 2400)},
            "Zofío":           {"lat": 40.3830, "lon": -3.7100, "price_range": (1800, 2500)},
        },
    },

    # ── 13. Puente de Vallecas ────────────────────────────────────────────
    "Puente de Vallecas": {
        "lat": 40.3920, "lon": -3.6600, "avg_price_sqm": 2400,
        "barrios": {
            "Entrevías":       {"lat": 40.3900, "lon": -3.6650, "price_range": (1800, 2500)},
            "San Diego":       {"lat": 40.3950, "lon": -3.6700, "price_range": (2000, 2800)},
            "Palomeras Bajas": {"lat": 40.3850, "lon": -3.6550, "price_range": (1600, 2400)},
            "Palomeras Sureste": {"lat": 40.3820, "lon": -3.6500, "price_range": (1500, 2200)},
            "Numancia":        {"lat": 40.3980, "lon": -3.6680, "price_range": (2200, 2800)},
            "Portazgo":        {"lat": 40.3880, "lon": -3.6580, "price_range": (1800, 2500)},
        },
    },

    # ── 14. Moratalaz ─────────────────────────────────────────────────────
    "Moratalaz": {
        "lat": 40.4070, "lon": -3.6450, "avg_price_sqm": 2800,
        "barrios": {
            "Pavones":         {"lat": 40.4050, "lon": -3.6400, "price_range": (2400, 3200)},
            "Horcajo":         {"lat": 40.4020, "lon": -3.6380, "price_range": (2200, 3000)},
            "Marroquina":      {"lat": 40.4080, "lon": -3.6480, "price_range": (2500, 3200)},
            "Media Legua":     {"lat": 40.4100, "lon": -3.6520, "price_range": (2600, 3400)},
            "Fontarrón":       {"lat": 40.4000, "lon": -3.6350, "price_range": (2200, 2800)},
            "Vinateros":       {"lat": 40.4090, "lon": -3.6460, "price_range": (2500, 3200)},
        },
    },

    # ── 15. Ciudad Lineal ─────────────────────────────────────────────────
    "Ciudad Lineal": {
        "lat": 40.4450, "lon": -3.6500, "avg_price_sqm": 3800,
        "barrios": {
            "Ventas":          {"lat": 40.4320, "lon": -3.6630, "price_range": (3500, 4500)},
            "Pueblo Nuevo":    {"lat": 40.4350, "lon": -3.6520, "price_range": (3200, 4200)},
            "Quintana":        {"lat": 40.4380, "lon": -3.6580, "price_range": (3000, 4000)},
            "Concepción":      {"lat": 40.4400, "lon": -3.6600, "price_range": (3300, 4300)},
            "San Pascual":     {"lat": 40.4420, "lon": -3.6500, "price_range": (3500, 4500)},
            "San Juan Bautista":{"lat": 40.4480, "lon": -3.6550, "price_range": (3200, 4200)},
            "Colina":          {"lat": 40.4530, "lon": -3.6450, "price_range": (3000, 3800)},
            "Atalaya":         {"lat": 40.4560, "lon": -3.6400, "price_range": (2800, 3600)},
            "Costillares":     {"lat": 40.4600, "lon": -3.6500, "price_range": (3200, 4000)},
        },
    },

    # ── 16. Hortaleza ─────────────────────────────────────────────────────
    "Hortaleza": {
        "lat": 40.4700, "lon": -3.6400, "avg_price_sqm": 3800,
        "barrios": {
            "Palomas":         {"lat": 40.4650, "lon": -3.6450, "price_range": (3200, 4200)},
            "Piovera":         {"lat": 40.4700, "lon": -3.6300, "price_range": (5000, 7000)},
            "Canillas":        {"lat": 40.4600, "lon": -3.6380, "price_range": (3500, 4500)},
            "Pinar del Rey":   {"lat": 40.4680, "lon": -3.6500, "price_range": (3000, 4000)},
            "Apóstol Santiago":{"lat": 40.4750, "lon": -3.6350, "price_range": (3200, 4200)},
            "Valdefuentes":    {"lat": 40.4850, "lon": -3.6250, "price_range": (3500, 4500)},
        },
    },

    # ── 17. Villaverde ────────────────────────────────────────────────────
    "Villaverde": {
        "lat": 40.3500, "lon": -3.6950, "avg_price_sqm": 1800,
        "barrios": {
            "San Cristóbal":   {"lat": 40.3650, "lon": -3.6950, "price_range": (1500, 2200)},
            "Butarque":        {"lat": 40.3480, "lon": -3.7000, "price_range": (1400, 2000)},
            "Los Rosales":     {"lat": 40.3550, "lon": -3.6900, "price_range": (1400, 2000)},
            "Los Ángeles":     {"lat": 40.3600, "lon": -3.6850, "price_range": (1500, 2100)},
            "San Andrés":      {"lat": 40.3520, "lon": -3.7050, "price_range": (1300, 1900)},
        },
    },

    # ── 18. Villa de Vallecas ─────────────────────────────────────────────
    "Villa de Vallecas": {
        "lat": 40.3750, "lon": -3.6200, "avg_price_sqm": 2200,
        "barrios": {
            "Casco Histórico de Vallecas": {"lat": 40.3800, "lon": -3.6250, "price_range": (2000, 2800)},
            "Santa Eugenia":   {"lat": 40.3850, "lon": -3.6100, "price_range": (1800, 2500)},
            "Ensanche de Vallecas": {"lat": 40.3700, "lon": -3.6150, "price_range": (2200, 3000)},
        },
    },

    # ── 19. Vicálvaro ─────────────────────────────────────────────────────
    "Vicálvaro": {
        "lat": 40.4050, "lon": -3.6080, "avg_price_sqm": 2400,
        "barrios": {
            "Casco Histórico de Vicálvaro": {"lat": 40.4050, "lon": -3.6080, "price_range": (2000, 2800)},
            "Valdebernardo":   {"lat": 40.4000, "lon": -3.6200, "price_range": (2200, 3000)},
            "Valderribas":     {"lat": 40.3980, "lon": -3.6120, "price_range": (2000, 2800)},
            "El Cañaveral":    {"lat": 40.4050, "lon": -3.5900, "price_range": (2500, 3200)},
        },
    },

    # ── 20. San Blas-Canillejas ───────────────────────────────────────────
    "San Blas-Canillejas": {
        "lat": 40.4350, "lon": -3.6150, "avg_price_sqm": 2800,
        "barrios": {
            "Simancas":        {"lat": 40.4320, "lon": -3.6250, "price_range": (2500, 3300)},
            "Hellín":          {"lat": 40.4300, "lon": -3.6200, "price_range": (2400, 3200)},
            "Amposta":         {"lat": 40.4280, "lon": -3.6150, "price_range": (2400, 3000)},
            "Arcos":           {"lat": 40.4350, "lon": -3.6100, "price_range": (2200, 2800)},
            "Canillejas":      {"lat": 40.4400, "lon": -3.6080, "price_range": (2500, 3200)},
            "Rejas":           {"lat": 40.4450, "lon": -3.6000, "price_range": (2500, 3300)},
            "Salvador":        {"lat": 40.4350, "lon": -3.6200, "price_range": (2400, 3000)},
        },
    },

    # ── 21. Barajas ───────────────────────────────────────────────────────
    "Barajas": {
        "lat": 40.4700, "lon": -3.5800, "avg_price_sqm": 3200,
        "barrios": {
            "Alameda de Osuna":{"lat": 40.4580, "lon": -3.5900, "price_range": (3200, 4500)},
            "Aeropuerto":      {"lat": 40.4720, "lon": -3.5600, "price_range": (2800, 3800)},
            "Casco Histórico de Barajas": {"lat": 40.4750, "lon": -3.5790, "price_range": (2500, 3500)},
            "Timón":           {"lat": 40.4650, "lon": -3.5850, "price_range": (3000, 4000)},
            "Corralejos":      {"lat": 40.4800, "lon": -3.5750, "price_range": (2800, 3800)},
        },
    },
}


# ---------------------------------------------------------------------------
# Lookup caches (built once at import time)
# ---------------------------------------------------------------------------

_BARRIO_TO_DISTRICT: Dict[str, str] = {}
_BARRIO_TO_COORDS: Dict[str, Tuple[float, float]] = {}
_BARRIO_TO_PRICE_RANGE: Dict[str, Tuple[int, int]] = {}

for _district, _ddata in MADRID_DISTRICTS.items():
    for _barrio, _bdata in _ddata["barrios"].items():
        key = _barrio.lower()
        _BARRIO_TO_DISTRICT[key] = _district
        _BARRIO_TO_COORDS[key] = (_bdata["lat"], _bdata["lon"])
        _BARRIO_TO_PRICE_RANGE[key] = _bdata["price_range"]


# Also map the district name itself (e.g. "Salamanca" is both a district and a barrio name)
for _district, _ddata in MADRID_DISTRICTS.items():
    key = _district.lower()
    if key not in _BARRIO_TO_DISTRICT:
        _BARRIO_TO_DISTRICT[key] = _district
        _BARRIO_TO_COORDS[key] = (_ddata["lat"], _ddata["lon"])
        _BARRIO_TO_PRICE_RANGE[key] = (
            int(_ddata["avg_price_sqm"] * 0.85),
            int(_ddata["avg_price_sqm"] * 1.15),
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_district(neighborhood: str) -> Optional[str]:
    """Return the district name for a given neighbourhood (case-insensitive)."""
    return _BARRIO_TO_DISTRICT.get(neighborhood.lower())


def get_coords(neighborhood: str) -> Optional[Tuple[float, float]]:
    """Return (latitude, longitude) for a neighbourhood centroid."""
    return _BARRIO_TO_COORDS.get(neighborhood.lower())


def get_price_range(neighborhood: str) -> Optional[Tuple[int, int]]:
    """Return the (min, max) price-per-sqm range for a neighbourhood."""
    return _BARRIO_TO_PRICE_RANGE.get(neighborhood.lower())


def get_all_barrios() -> List[str]:
    """Return a flat list of all known barrio names."""
    result = []
    for ddata in MADRID_DISTRICTS.values():
        result.extend(ddata["barrios"].keys())
    return result


def get_all_districts() -> List[str]:
    """Return a list of all 21 district names."""
    return list(MADRID_DISTRICTS.keys())


def get_district_center(district: str) -> Optional[Tuple[float, float]]:
    """Return (latitude, longitude) of a district's center point."""
    ddata = MADRID_DISTRICTS.get(district)
    if ddata:
        return (ddata["lat"], ddata["lon"])
    return None
