"""
app/dashboard/streamlit_app.py
================================
Streamlit interactive dashboard for MadridHousingScanner.

Features
--------
* Sidebar filters: district, max price, min area, number of rooms.
* Dynamic "fly-to" map: re-centres on the selected district.
* Folium map: markers for top deal listings coloured by Opportunity Index.
* Sortable data table of top deals.
* Bar chart: average price per m² by neighbourhood.
* KPI row: best deal, average price, total listings.

Run::

    streamlit run app/dashboard/streamlit_app.py
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import folium
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import st_folium

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MadridHousingScanner",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Constants ─────────────────────────────────────────────────────────────────
try:
    API_BASE = st.secrets.get("API_URL", "http://localhost:8000")
except Exception:
    API_BASE = "http://localhost:8000"
MADRID_CENTER = [40.4168, -3.7038]

# District centres for fly-to (same as geodata module)
DISTRICT_CENTERS: Dict[str, Dict[str, float]] = {
    "Centro":              {"lat": 40.4155, "lon": -3.7074},
    "Arganzuela":          {"lat": 40.3950, "lon": -3.6940},
    "Retiro":              {"lat": 40.4090, "lon": -3.6770},
    "Salamanca":           {"lat": 40.4310, "lon": -3.6820},
    "Chamartín":           {"lat": 40.4620, "lon": -3.6770},
    "Tetuán":              {"lat": 40.4600, "lon": -3.7000},
    "Chamberí":            {"lat": 40.4350, "lon": -3.7070},
    "Fuencarral-El Pardo": {"lat": 40.5100, "lon": -3.7300},
    "Moncloa-Aravaca":     {"lat": 40.4350, "lon": -3.7350},
    "Latina":              {"lat": 40.4020, "lon": -3.7450},
    "Carabanchel":         {"lat": 40.3830, "lon": -3.7350},
    "Usera":               {"lat": 40.3820, "lon": -3.7050},
    "Puente de Vallecas":  {"lat": 40.3920, "lon": -3.6600},
    "Moratalaz":           {"lat": 40.4070, "lon": -3.6450},
    "Ciudad Lineal":       {"lat": 40.4450, "lon": -3.6500},
    "Hortaleza":           {"lat": 40.4700, "lon": -3.6400},
    "Villaverde":          {"lat": 40.3500, "lon": -3.6950},
    "Villa de Vallecas":   {"lat": 40.3750, "lon": -3.6200},
    "Vicálvaro":           {"lat": 40.4050, "lon": -3.6080},
    "San Blas-Canillejas": {"lat": 40.4350, "lon": -3.6150},
    "Barajas":             {"lat": 40.4700, "lon": -3.5800},
}


# ── Data fetching ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)  # cache 5 minutes
def fetch_deals(n: int = 50, scrape_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch deals from the FastAPI backend."""
    params: Dict[str, Any] = {"n": n}
    if scrape_date:
        params["scrape_date"] = scrape_date
    try:
        resp = requests.get(f"{API_BASE}/deals", params=params, timeout=10)
        resp.raise_for_status()
        return resp.json().get("deals", [])
    except Exception as exc:
        st.error(f"⚠️ Could not connect to the API: {exc}")
        return []


@st.cache_data(ttl=300)
def fetch_stats() -> List[Dict[str, Any]]:
    """Fetch neighbourhood stats from the FastAPI backend."""
    try:
        resp = requests.get(f"{API_BASE}/stats", timeout=10)
        resp.raise_for_status()
        return resp.json().get("data", [])
    except Exception:
        return []


# ── Colour helpers ────────────────────────────────────────────────────────────

def opportunity_to_color(index: float) -> str:
    """Map an Opportunity Index value to a hex colour (red → green)."""
    clamped = max(0.0, min(1.0, index))
    r = int(255 * (1 - clamped))
    g = int(200 * clamped)
    return f"#{r:02x}{g:02x}50"


# ── UI ────────────────────────────────────────────────────────────────────────

def render_sidebar() -> Dict[str, Any]:
    """Render sidebar filters and return selected values."""
    st.sidebar.title("🏠 MadridHousingScanner")
    st.sidebar.markdown("---")

    filters: Dict[str, Any] = {}

    # ── District filter (fly-to) ──────────────────────────────────────────
    district_options = ["All Districts"] + sorted(DISTRICT_CENTERS.keys())
    filters["district"] = st.sidebar.selectbox(
        "📍 District", options=district_options, index=0
    )

    filters["n_deals"] = st.sidebar.slider(
        "Number of deals to load", min_value=10, max_value=100, value=50, step=10
    )
    filters["max_price"] = st.sidebar.number_input(
        "Max price (€)", min_value=50_000, max_value=2_000_000,
        value=600_000, step=10_000
    )
    filters["min_area"] = st.sidebar.number_input(
        "Min area (m²)", min_value=20, max_value=300, value=40, step=5
    )
    filters["min_rooms"] = st.sidebar.selectbox(
        "Min rooms", options=[0, 1, 2, 3, 4, 5], index=0
    )
    st.sidebar.markdown("---")
    st.sidebar.caption("Data refreshes every 5 minutes from the API.")
    return filters


def apply_filters(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    """Apply sidebar filters to the deals DataFrame."""
    df = df[df["price_eur"] <= filters["max_price"]]
    df = df[df["area_sqm"] >= filters["min_area"]]
    if filters["min_rooms"] > 0:
        df = df[df["rooms"].fillna(0) >= filters["min_rooms"]]
    if filters["district"] != "All Districts":
        df = df[df["district"] == filters["district"]]
    return df


def render_kpis(df: pd.DataFrame) -> None:
    """Render top KPI metrics row."""
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🏆 Best Opportunity Index", f"{df['opportunity_index'].max():.2%}")
    with col2:
        st.metric("💶 Avg Price", f"€{df['price_eur'].mean():,.0f}")
    with col3:
        st.metric("📐 Avg Price/m²", f"€{df['price_per_sqm'].mean():,.0f}")
    with col4:
        st.metric("📋 Total Listings", len(df))


def render_map(df: pd.DataFrame, selected_district: str) -> None:
    """Render the Folium map with deal markers and fly-to support."""
    st.subheader("🗺️ Deal Map – Madrid")

    # ── Fly-to logic ──────────────────────────────────────────────────────
    if selected_district != "All Districts" and selected_district in DISTRICT_CENTERS:
        center = [
            DISTRICT_CENTERS[selected_district]["lat"],
            DISTRICT_CENTERS[selected_district]["lon"],
        ]
        zoom = 14
    else:
        center = MADRID_CENTER
        zoom = 12

    m = folium.Map(location=center, zoom_start=zoom, tiles="CartoDB positron")

    mappable = df.dropna(subset=["latitude", "longitude"])

    for _, row in mappable.iterrows():
        color = opportunity_to_color(row["opportunity_index"])
        district_label = row.get("district", "")
        popup_html = f"""
        <b>{row['title'][:60]}</b><br/>
        💶 <b>€{row['price_eur']:,.0f}</b> ({row['area_sqm']:.0f} m²)<br/>
        📊 Opportunity: <b>{row['opportunity_index']:.2%}</b><br/>
        📍 {row['neighborhood']}, {district_label}<br/>
        <a href="{row['url']}" target="_blank">View listing →</a>
        """
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=8 + row["opportunity_index"] * 10,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.85,
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=f"€{row['price_eur']:,.0f} | OI: {row['opportunity_index']:.2%}",
        ).add_to(m)

    st_folium(m, width="100%", height=480)

    if mappable.empty:
        st.info("ℹ️ No listings with GPS coordinates. Map will populate once the live scraper runs.")


def render_deals_table(df: pd.DataFrame) -> None:
    """Render a formatted, sortable data table."""
    st.subheader("🏅 Top Housing Deals")
    display_cols = [
        "title", "price_eur", "area_sqm", "rooms",
        "price_per_sqm", "neighborhood", "district",
        "opportunity_index", "source",
    ]
    # Only include columns that exist
    display_cols = [c for c in display_cols if c in df.columns]
    display_df = df[display_cols].copy()
    display_df["price_eur"] = display_df["price_eur"].map("€{:,.0f}".format)
    display_df["price_per_sqm"] = display_df["price_per_sqm"].map("€{:,.0f}".format)
    display_df["opportunity_index"] = display_df["opportunity_index"].map("{:.2%}".format)

    # Dynamic header mapping
    header_map = {
        "title": "Title", "price_eur": "Price (€)", "area_sqm": "Area (m²)",
        "rooms": "Rooms", "price_per_sqm": "Price/m²",
        "neighborhood": "Neighbourhood", "district": "District",
        "opportunity_index": "Opportunity Index", "source": "Source",
    }
    display_df.columns = [header_map.get(c, c) for c in display_df.columns]
    st.dataframe(display_df, use_container_width=True, hide_index=True)


def render_bar_chart(df: pd.DataFrame) -> None:
    """Render avg price/m² by neighbourhood chart."""
    st.subheader("📊 Avg Price/m² by Neighbourhood")
    chart_df = (
        df.groupby("neighborhood")["price_per_sqm"]
        .mean()
        .sort_values(ascending=False)
        .head(20)
        .reset_index()
    )
    chart_df.columns = ["Neighbourhood", "Avg Price/m²"]
    st.bar_chart(chart_df.set_index("Neighbourhood"))


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    filters = render_sidebar()

    st.title("🏠 MadridHousingScanner")
    st.caption("Real-time real estate opportunity analytics for Madrid · Data refreshes every 3 hours.")
    st.markdown("---")

    with st.spinner("Loading deals from API..."):
        raw_deals = fetch_deals(n=filters["n_deals"])

    if not raw_deals:
        st.warning(
            "No data available yet. Make sure the FastAPI server is running "
            "(`uvicorn app.api.main:app --reload`) and the pipeline has executed at least once."
        )
        return

    df = pd.DataFrame(raw_deals)
    df = apply_filters(df, filters)

    if df.empty:
        st.warning("No deals match your current filters. Try relaxing them.")
        return

    render_kpis(df)
    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["🗺️ Map", "📋 Deals Table", "📊 Neighbourhood Stats"])

    with tab1:
        render_map(df, selected_district=filters["district"])

    with tab2:
        render_deals_table(df)

    with tab3:
        render_bar_chart(df)


if __name__ == "__main__":
    main()
