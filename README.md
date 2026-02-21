# 🏠 MadridHousingScanner

> **Real-time real estate analytics platform for Madrid.**  
> Scrapes property listings, processes them through a Medallion data lake, computes an *Opportunity Index*, and serves results via a FastAPI + Streamlit stack.

### 📡 Current Status: `Synthetic Mode`

| Component | Status |
|-----------|--------|
| **Medallion Pipeline** (Bronze → Silver → Gold) | ✅ Operational — 21 districts, ~120 barrios, 2000 listings |
| **FastAPI** (REST API + spatial queries) | ✅ Returns `200 OK` — Haversine radius search active |
| **Streamlit Dashboard** (fly-to map, filters) | ✅ Rendering markers across all Madrid |
| **Live Scraper** (Idealista / Fotocasa) | ⛔ Blocked — anti-bot detection on target sites |

> ⚠️ **Operational Note:** Until the scraper is stealth-hardened, the application runs on **Synthetic Mode** to demonstrate the full analytical capabilities of the dashboard and API.

---

## 📐 Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Scraper (Bronze)        Silver (Cleaned)      Gold (Enriched)       │
│  ┌────────────────┐      ┌───────────────┐     ┌─────────────────┐  │
│  │ Idealista      │ ───► │  PySpark      │ ──► │ Opportunity     │  │
│  │ Fotocasa       │      │  Cleaner      │     │ Index Job       │  │
│  │ (Playwright +  │      │               │     │ (Spark + Pandas │  │
│  │  Stealth)      │      └───────────────┘     │  Bridge)        │  │
│  └────────────────┘                            └────────┬────────┘  │
│                                                         │           │
│                                                         ▼           │
│                                                   ┌──────────┐      │
│                                                   │  DuckDB  │      │
│                                                   │  (gold_  │      │
│                                                   │ listings)│      │
│                                                   └────┬─────┘      │
└────────────────────────────────────────────────────────┼────────────┘
                                                         │
                         ┌───────────────────────────────┤
                         ▼                               ▼
                   ┌──────────┐                  ┌──────────────┐
                   │ FastAPI  │                  │  Streamlit   │
                   │ /deals   │                  │  Dashboard   │
                   └──────────┘                  └──────────────┘
```

### Architectural Patterns

| Pattern | Where applied |
|---------|--------------|
| **Clean Architecture** | `core/` → `pipeline/` → `app/` layers |
| **Factory Pattern** | `ExtractorFactory` for scrapers |
| **Medallion Architecture** | Bronze → Silver → Gold data layers |
| **Singleton Pattern** | `SparkSessionManager` for shared `SparkSession` |

---

## � Technical Changes & Improvements

> Key decisions made during the final integration phase to achieve a fully functional E2E system.

### Pipeline Orchestration

The main execution entry point was moved to **`main_pipeline_archive.py`**, which runs the full asynchronous E2E flow: **Bronze → Silver → Gold → DuckDB Sync** in a single script with proper Spark session lifecycle management.

### Windows Compatibility Layer

Replaced native Spark Parquet/Hadoop writers with a **Pandas-based bridge** (`.toPandas().to_csv()`) to bypass `winutils.exe` requirements and filesystem permission errors on Windows. The Hadoop filesystem implementation is also patched at runtime:

```python
spark._jsc.hadoopConfiguration().set(
    "fs.file.impl", "org.apache.hadoop.fs.RawLocalFileSystem"
)
```

### Storage Schema Unification

Renamed the primary DuckDB table to **`gold_listings`** to align with FastAPI SQL queries, ensuring seamless data serving from the analytical engine to the API layer.

### Gold Layer Schema Enrichment

The Gold layer merges computed metrics with Bronze source data. Key columns:

| Column | Source |
|--------|--------|
| `source` | `F.lit("synthetic_2026")` |
| `url` | Unique URL per listing via `monotonically_increasing_id()` |
| `price_eur` | Derived from `price` |
| `area_sqm` / `area_m2` | Derived from `sq_mt` |
| `rooms`, `bathrooms` | Realistic per-listing values from Bronze (1–5 rooms, 1–3 baths) |
| `district` | Real district from geodata lookup (21 Madrid districts) |
| `latitude`, `longitude` | Jittered barrio centroids (±200m gaussian scatter) |

### Feature Engineering

Calculated metrics are computed **inside the Spark pipeline** to offload computation from the backend:

```
price_per_sqm     = price / sq_mt
opportunity_index = (avg_neighbourhood_price - price) / avg_neighbourhood_price
```

### Madrid-Wide Expansion (21 Districts)

Expanded from 7 mock barrios to **all 21 Madrid districts** (~120 barrios) with accurate geodata:

| Component | Details |
|-----------|---------|
| `pipeline/geo/madrid_geodata.py` | Static geodata: coordinates, price ranges, district↔barrio mappings |
| `pipeline/geo/jitter.py` | Gaussian spatial scatter (±200m) to prevent marker stacking |
| `generate_bronze.py` | 2000 listings, per-barrio price distributions, varied rooms/titles |
| `duckdb_repository.py` | `get_deals_within_radius()` — Haversine SQL spatial queries |
| `GET /deals?lat=...&lon=...&radius_km=...` | Spatial proximity search on the API |
| Streamlit dashboard | District dropdown filter + fly-to map navigation |

### API & Schema Alignment

Resolved column name mismatches between the DuckDB table and the FastAPI Pydantic schemas:

| Issue | Resolution |
|-------|-----------|
| `district` column not found | ✅ Restored — now populated from geodata module |
| `rank` column not found | Removed from queries & schemas |
| `neighborhood_avg_price_per_sqm` | Renamed to `avg_neighborhood_price` |
| `scrape_date` returned as `datetime.date` | Added Pydantic `field_validator` for auto-coercion |
| No spatial filtering | ✅ Added `lat`, `lon`, `radius_km` params + Haversine query |

### API & UI Connectivity

Verified the 3-tier connection (**DuckDB → FastAPI → Streamlit**) and established the correct execution order:

```
1. python main_pipeline_archive.py   # Populate DuckDB
2. uvicorn app.api.main:app --reload  # Start API
3. streamlit run app/dashboard/streamlit_app.py  # Start Dashboard
```

---

## �📁 Project Structure

```
MadridHousingScanner/
├── core/                          # Domain models, interfaces, config
│   ├── config.py                  # Centralised settings (pydantic-settings)
│   ├── interfaces.py              # Abstract ports: BaseExtractor, BaseRepository
│   ├── logging_config.py          # Structured logging (structlog)
│   └── models.py                  # Pydantic models: RawProperty, CleanedProperty, Deal
│
├── pipeline/                      # Medallion data pipeline
│   ├── extractors/
│   │   ├── base_extractor.py      # Playwright base (stealth, UA rotation, retries)
│   │   ├── idealista_extractor.py # Idealista.com scraper
│   │   ├── fotocasa_extractor.py  # Fotocasa.es scraper
│   │   └── factory.py             # ⭐ ExtractorFactory (Factory Pattern)
│   ├── bronze/
│   │   └── ingestor.py            # Raw → Parquet (partitioned by source/date)
│   ├── silver/
│   │   └── cleaner.py             # PySpark: parse, dedup, normalise
│   ├── gold/
│   │   └── opportunity_index.py   # ⭐ PySpark Gold job (Opportunity Index)
│   ├── spark/
│   │   └── session_manager.py     # ⭐ SparkSessionManager (Singleton)
│   └── storage/
│       └── duckdb_repository.py   # DuckDB sink & queries (gold_listings table)
│
├── app/
│   ├── api/
│   │   ├── main.py                # FastAPI: /deals, /stats, /health
│   │   └── schemas.py             # Pydantic response models (with date coercion)
│   └── dashboard/
│       └── streamlit_app.py       # Interactive dashboard (Folium map + filters)
│
├── data/                          # ⚠️ gitignored – generated at runtime
│   ├── bronze/                    # Raw CSV (source=X/date=Y partitions)
│   ├── silver/                    # Cleaned CSV
│   ├── gold/                      # Enriched CSV (with Opportunity Index)
│   └── madrid_housing.duckdb      # Analytical database
│
├── main_pipeline_archive.py       # ⭐ E2E pipeline orchestrator (async)
├── .github/workflows/
│   └── main.yml                   # CI/CD: runs every 3h (scrape→spark→sync)
│
├── .env.example                   # Environment variable template
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.11+
- Java 17+ (required by PySpark)
- Git

### 2. Setup

```bash
# Clone and enter project
git clone <your-repo-url>
cd MadridHousingScanner

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium

# Configure environment
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux
```

### 3. Run the Pipeline

```bash
# Run the full pipeline (Bronze → Silver → Gold → DuckDB Sync)
python main_pipeline_archive.py
```

### 4. Start the API

```bash
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
# API docs: http://localhost:8000/docs
```

### 5. Launch the Dashboard

```bash
streamlit run app/dashboard/streamlit_app.py
# Open: http://localhost:8501
```

> **⚠️ Important:** Always run the pipeline (step 3) before starting the API. The API requires the `gold_listings` table to exist in DuckDB.

---

## 📊 Opportunity Index

The **Opportunity Index** measures how much cheaper a listing is relative to its neighbourhood average:

```
opportunity_index = (avg_neighbourhood_price - listing_price) / avg_neighbourhood_price
```

| Value | Interpretation |
|-------|---------------|
| `> 0` | Listing is **cheaper** than the average → good deal 🟢 |
| `= 0` | At the neighbourhood average |
| `< 0` | **More expensive** than the average 🔴 |

The index is computed inside the PySpark Gold job using aggregated neighbourhood averages.

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Service health check |
| `GET` | `/deals?n=10&scrape_date=2026-02-21` | Top N deals by Opportunity Index |
| `GET` | `/stats` | Neighbourhood aggregation stats |
| `GET` | `/docs` | Swagger UI |

### Example Response (`/deals?n=1`)

```json
{
  "total": 1,
  "scrape_date": "2026-02-21",
  "deals": [
    {
      "source": "synthetic_2026",
      "url": "https://www.idealista.com/",
      "title": "Piso en Salamanca",
      "price_eur": 180000,
      "area_sqm": 85,
      "rooms": 2,
      "price_per_sqm": 2117.65,
      "neighborhood": "Salamanca",
      "latitude": 40.4167,
      "longitude": -3.7033,
      "avg_neighborhood_price": 350000,
      "opportunity_index": 0.49,
      "scrape_date": "2026-02-21"
    }
  ]
}
```

---

## ⚙️ CI/CD

The GitHub Actions workflow (`.github/workflows/main.yml`) runs automatically **every 3 hours**:

```
🥉 Bronze Scrape → 🥈 Silver Clean → 🥇 Gold Opportunity Index → 🦆 DuckDB Sync
```

Trigger manually via **Actions → Run workflow** with optional `max_pages` and `sources` parameters.

---

## 🧩 Extending with New Sources

Register a new scraper in one step using the **ExtractorFactory**:

```python
from pipeline.extractors.factory import ExtractorFactory
from pipeline.extractors.base_extractor import PlaywrightBaseExtractor

class MilanunciosExtractor(PlaywrightBaseExtractor):
    SOURCE = "milanuncios"

    @property
    def source_name(self) -> str:
        return self.SOURCE

    async def _parse_listings(self, page): ...
    async def _get_next_page_url(self, page): ...

# Register at runtime – no existing files modified
ExtractorFactory.register("milanuncios", MilanunciosExtractor)
extractor = ExtractorFactory.create("milanuncios")
```

---

## 📦 Key Dependencies

| Package | Purpose |
|---------|---------|
| `playwright` + `playwright-stealth` | Stealth web scraping |
| `pyspark` | Silver/Gold pipeline (Medallion layers) |
| `duckdb` | Low-latency analytical queries |
| `fastapi` + `uvicorn` | REST API |
| `streamlit` + `folium` | Interactive dashboard |
| `pydantic-settings` | Typed configuration |
| `structlog` | Structured JSON logging |

---

## 🕷️ Scraper Status & Anti-Detection Roadmap

### Current Blocker

The live Idealista scraper is **failing in production** — the target site detects and blocks the headless browser via fingerprinting, CAPTCHAs, and IP rate limiting.

### Strategic Roadmap

| Priority | Strategy | Status |
|----------|----------|--------|
| 🔴 P0 | **Stealth Plugins** — Integrate `playwright-stealth` with realistic fingerprints, mouse movements, and viewport randomization | 🔲 Planned |
| 🔴 P0 | **Residential Proxies** — Rotate IPs through residential proxy pools (e.g., Bright Data, Oxylabs) to bypass IP-based rate limiting | 🔲 Planned |
| 🟡 P1 | **User-Agent Rotation** — Maintain a pool of 50+ real browser UA strings, randomize per session | 🔲 Planned |
| 🟡 P1 | **Request Throttling** — Randomized delays (2–8s), session warm-up, organic navigation patterns | 🔲 Planned |
| 🟢 P2 | **Official APIs / Alt Sources** — Evaluate Idealista API partnership, Fotocasa data feeds, or alternative portals (pisos.com, Habitaclia) for stable long-term access | 🔲 Research |

### Anti-Detection Techniques (Planned)

```python
# Example: Stealth-hardened Playwright session
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent=random.choice(UA_POOL),
        locale="es-ES",
        timezone_id="Europe/Madrid",
    )
    page = await context.new_page()
    await stealth_async(page)  # Patches navigator, webdriver, etc.
```

---

## 🗺️ Full Roadmap

```
✅ PHASE 1 — Synthetic Pipeline (COMPLETE)
   ├── Medallion Architecture (Bronze → Silver → Gold)
   ├── DuckDB analytical layer
   ├── FastAPI REST API
   └── Streamlit dashboard

✅ PHASE 2 — Madrid-Wide Expansion (COMPLETE)
   ├── 21 districts / ~120 barrios with real coordinates
   ├── Spatial jitter for marker scatter
   ├── Haversine spatial queries (GET /deals?lat=...&lon=...&radius_km=...)
   └── Interactive district filter + fly-to map

🔲 PHASE 3 — Stealth Scraping (IN PROGRESS)
   ├── playwright-stealth integration
   ├── Residential proxy rotation
   ├── User-Agent pool + throttling
   └── CAPTCHA handling strategy

🔲 PHASE 4 — Production Hardening
   ├── Docker containerization
   ├── Scheduled GitHub Actions pipeline
   ├── Alerting on scrape failures
   └── Historical price tracking
```

---

## 📄 License

MIT © MadridHousingScanner Team
