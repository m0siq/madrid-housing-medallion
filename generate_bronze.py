"""
generate_bronze.py
====================
Synthetic data generator for MadridHousingScanner.

Generates ~2000 realistic listings across all 21 Madrid districts
following Madrid 2026 market logic:

- Price is calculated as ``district_avg_price_sqm × area_sqm`` with
  a ±15 % random variance, anchored to the real district average.
- A small subset (~5 %) of listings are tagged as *opportunity* deals:
  their price is 5–15 % **below** the district average, and the
  ``opportunity_index`` column records the exact % discount.
- All other listings have ``opportunity_index = 0.0``.

Run::

    python generate_bronze.py
"""

import os
import random

import pandas as pd

from pipeline.geo.madrid_geodata import MADRID_DISTRICTS
from pipeline.geo.jitter import add_jitter


# ---------------------------------------------------------------------------
# District average price per m² (EUR) — sourced from MADRID_DISTRICTS.
# We build a local dict for fast lookup inside the loop.
# ---------------------------------------------------------------------------
DISTRICT_AVG: dict[str, float] = {
    name: data["avg_price_sqm"]
    for name, data in MADRID_DISTRICTS.items()
}


def generate_madrid_2026(n_listings: int = 2000) -> None:
    """Generate a synthetic Bronze CSV with *n_listings* across all Madrid.

    Pricing logic
    -------------
    For **normal** listings (95 % of records):
        price_per_sqm = district_avg × uniform(0.85, 1.15)

    For **opportunity** listings (≈5 % of records):
        price_per_sqm = district_avg × (1 - discount)
        where discount ∈ uniform(0.05, 0.15)  → 5–15 % below average
        opportunity_index = discount × 100    → stored as a % value
    """

    # ── Destination path ──────────────────────────────────────────────────
    folder_path = "data/bronze/source=synthetic/date=2026-02-21"
    file_path = f"{folder_path}/madrid_2026.csv"

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"📁 Folders created: {folder_path}")

    # ── Build flat list of (barrio, district, metadata) tuples ────────────
    barrio_pool: list[dict] = []
    for district_name, ddata in MADRID_DISTRICTS.items():
        for barrio_name, bdata in ddata["barrios"].items():
            barrio_pool.append({
                "barrio": barrio_name,
                "district": district_name,
                "lat": bdata["lat"],
                "lon": bdata["lon"],
            })

    # ── Pre-select opportunity indices (~5 % of total listings) ───────────
    n_opportunities = max(1, round(n_listings * 0.05))
    opportunity_indices: set[int] = set(
        random.sample(range(n_listings), k=n_opportunities)
    )

    # ── Title variety ─────────────────────────────────────────────────────
    title_styles = [
        "Piso en {barrio}",
        "Apartamento en {barrio}",
        "Ático en {barrio}",
        "Estudio en {barrio}",
        "Piso reformado en {barrio}",
        "Piso exterior en {barrio}",
        "Dúplex en {barrio}",
    ]

    # ── Generate listings ─────────────────────────────────────────────────
    data: list[dict] = []

    for i in range(n_listings):
        entry = random.choice(barrio_pool)
        barrio = entry["barrio"]
        district = entry["district"]

        # Area: 30–180 m²
        area_sqm = random.randint(30, 180)

        # District average price per m² (EUR/m²)
        district_avg = DISTRICT_AVG[district]

        # ── Price logic ───────────────────────────────────────────────────
        if i in opportunity_indices:
            # Opportunity: 5–15 % below district average
            discount = random.uniform(0.05, 0.15)
            price_per_sqm = round(district_avg * (1.0 - discount), 2)
            opportunity_index = round(discount * 100, 2)
        else:
            # Normal market: ±15 % variance around district average
            variance = random.uniform(-0.15, 0.15)
            price_per_sqm = round(district_avg * (1.0 + variance), 2)
            opportunity_index = 0.0

        price = int(price_per_sqm * area_sqm)

        # ── Rooms: correlated with area ───────────────────────────────────
        if area_sqm < 45:
            rooms = random.choice([0, 1])
        elif area_sqm < 70:
            rooms = random.choice([1, 2])
        elif area_sqm < 100:
            rooms = random.choice([2, 3])
        elif area_sqm < 140:
            rooms = random.choice([3, 4])
        else:
            rooms = random.choice([4, 5])

        bathrooms = max(1, rooms // 2)

        # ── Jittered coordinates ──────────────────────────────────────────
        lat, lon = add_jitter(entry["lat"], entry["lon"], radius_m=250)

        # ── Title ─────────────────────────────────────────────────────────
        title = random.choice(title_styles).format(barrio=barrio)

        data.append({
            "title": title,
            "price": price,
            "price_per_sqm": price_per_sqm,
            "area_sqm": area_sqm,
            "rooms": rooms,
            "bathrooms": bathrooms,
            "neighborhood": barrio,
            "district": district,
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "opportunity_index": opportunity_index,
            "scrape_date": "2026-02-21",
        })

    # ── Save ──────────────────────────────────────────────────────────────
    df = pd.DataFrame(data)
    df.to_csv(file_path, index=False)

    n_districts = df["district"].nunique()
    n_barrios = df["neighborhood"].nunique()
    n_opp = (df["opportunity_index"] > 0).sum()
    avg_psqm = df["price_per_sqm"].mean()

    print(f"✅ Generated {len(df)} listings across {n_districts} districts / {n_barrios} barrios")
    print(f"   💶 Avg price/m²: €{avg_psqm:,.0f}")
    print(f"   🏷️  Opportunity deals: {n_opp} ({n_opp / len(df) * 100:.1f} %)")
    print(f"   Saved to: {file_path}")


if __name__ == "__main__":
    generate_madrid_2026()