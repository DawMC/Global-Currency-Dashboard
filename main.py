import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import folium
from streamlit_folium import st_folium

# ---------------- Page config ----------------
st.set_page_config(page_title="Currency Comparison", layout="wide")

# ---------------- Data loader ----------------
@st.cache_data
def load_currency_data(file_path):
    """Load currency data and return the most recent closing value"""
    df = pd.read_csv(file_path, skiprows=3)  # Skip 3 rows to get to actual data
    df.columns = ['Date', 'Close', 'High', 'Low', 'Open', 'Volume']
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date', ascending=False)
    most_recent = df.iloc[0]
    return {'close': float(most_recent['Close']), 'date': most_recent['Date']}

# ---------------- Ingest CSVs ----------------
currencies = {
    'BRL': load_currency_data('Price-Data/BRL_Brazilian-Real.csv'),
    'EUR': load_currency_data('Price-Data/EUR_European-Euro.csv'),
    'JPY': load_currency_data('Price-Data/JPY_Japanese-Yen.csv'),
    'ZAR': load_currency_data('Price-Data/ZAR_South-African-Rand.csv'),
}

# ---------------- Derived metrics ----------------
for code in currencies:
    rate = currencies[code]['close']
    currencies[code]['rate'] = rate
    # USD per 1 unit of foreign currency (as % of $1)
    currencies[code]['percentage'] = (1 / rate) * 100

# ---------------- Donut helper (Matplotlib) ----------------
def donut_matplotlib(percentage, colors, center_text):
    """
    Draw a donut chart using Matplotlib.
    `colors` should be a list of slice colors in order.
    """
    # Normalize pieces for a ring visualization
    values = np.array(percentage, dtype=float)
    total = values.sum()
    if total == 0:
        values = np.array([1.0])  # avoid zero-division
        colors = ['#E8E8E8']

    fig, ax = plt.subplots(figsize=(3.5, 3.5))
    wedges, _ = ax.pie(values, colors=colors, startangle=90, counterclock=False)
    # "Hole"
    circle = plt.Circle((0, 0), 0.70, color='white')
    ax.add_artist(circle)
    ax.set(aspect="equal")
    ax.axis('off')

    # Center annotation
    ax.text(0, 0, center_text, ha='center', va='center', fontsize=22, fontweight='bold')
    fig.tight_layout()
    return fig

# ---------------- UI ----------------
st.title("US Dollar compared to international currency")
st.subheader("How your dollar will transfer for your next vacation abroad")

col_text, col_map = st.columns([1, 2])

with col_text:
    st.write("### This info will tell you best conversion rate to the US dollar")
    st.write("")
    st.write("**Green is good; red is bad** (from a US traveler’s perspective)")

with col_map:
    st.write("### World view")
    st.caption("Green ≈ better USD buying power · Red ≈ stronger local currency vs USD")

    coords = {
        "BRL": {"name": "Brazil", "lat": -14.2350, "lon": -51.9253, "code": "BRL"},
        "EUR": {"name": "Europe", "lat": 54.5260,  "lon": 15.2551,  "code": "EUR"},
        "JPY": {"name": "Japan",  "lat": 36.2048,  "lon": 138.2529, "code": "JPY"},
        "ZAR": {"name": "South Africa", "lat": 30.5595, "lon": 22.9375, "code": "ZAR"},
        "USD": {"name": "United States", "lat": 39.8283, "lon": -98.5795, "code": "USD"},
    }

    def color_for(code, pct):
        if code == "BRL":
            return "green" if pct < 25 else "red"
        if code == "EUR":
            return "red" if pct >= 100 else "green"
        if code == "JPY":
            return "green" if pct < 1 else "red"
        if code == "ZAR":
            return "green" if pct < 10 else "red"
        return "gray"

    # Build Folium map
    m = folium.Map(location=[20, 0], zoom_start=2, tiles="CartoDB positron")

    fg = folium.FeatureGroup(name="Currencies").add_to(m)

    for k, meta in coords.items():
        if k == "USD":
            folium.CircleMarker(
                location=[meta["lat"], meta["lon"]],
                radius=6,
                color="gray",
                fill=True,
                fill_opacity=0.9,
                popup="United States (base currency: USD)"
            ).add_to(fg)
            continue

        rate = currencies[k]['rate']
        pct  = currencies[k]['percentage']
        dt   = currencies[k]['date'].strftime("%Y-%m-%d")
        # radius scaled by favorability (smaller pct => bigger radius, clamped)
        radius = max(6, min(14, 14 - (pct if k != "EUR" else min(pct, 160)/4)))
        folium.CircleMarker(
            location=[meta["lat"], meta["lon"]],
            radius=radius,
            color=color_for(k, pct),
            fill=True,
            fill_color=color_for(k, pct),
            fill_opacity=0.8,
            popup=(
                f"<b>{meta['name']}</b><br>"
                f"1 USD = {rate:.2f} {meta['code']}<br>"
                f"USD per 1 {meta['code']}: {1/rate:.4f}<br>"
                f"Date: {dt}"
            )
        ).add_to(fg)

    folium.LayerControl(collapsed=False).add_to(m)
    st_folium(m, height=520, use_container_width=True)

st.write("")
st.markdown("---")

# ---------------- Donut row (Matplotlib) ----------------
st.write("### Currency Exchange Rates")
cols = st.columns(4)

# BRL
with cols[0]:
    brl_pct = currencies['BRL']['percentage']
    main = min(100, brl_pct)
    rest = max(0, 100 - brl_pct)
    fig = donut_matplotlib(
        [main, rest],
        colors=["#90EE90" if brl_pct < 25 else "#FFB6C6", "#E8E8E8"],
        center_text=f"{brl_pct:.1f}%"
    )
    st.pyplot(fig, use_container_width=True)
    st.markdown("**BRL - Brazilian Real**")
    st.caption(f"1 USD = {currencies['BRL']['rate']:.2f} BRL")

# EUR (overflow >100 handled as a third wedge)
with cols[1]:
    eur_pct = currencies['EUR']['percentage']
    if eur_pct > 100:
        overflow = eur_pct - 100
        values = [100, min(overflow, 100), 0]  # visualize up to +100 overflow
        colors = ['#FFB6C6', '#CC0000', '#E8E8E8']
    else:
        values = [eur_pct, 100 - eur_pct]
        colors = ['#FFB6C6', '#E8E8E8']

    fig = donut_matplotlib(values, colors=colors, center_text=f"{eur_pct:.1f}%")
    st.pyplot(fig, use_container_width=True)
    st.markdown("**EUR - European Euro**")
    st.caption(f"1 USD = {currencies['EUR']['rate']:.2f} EUR")

# JPY
with cols[2]:
    jpy_pct = currencies['JPY']['percentage']
    main = min(100, jpy_pct)
    rest = max(0, 100 - jpy_pct)
    fig = donut_matplotlib(
        [main, rest],
        colors=["#90EE90" if jpy_pct < 1 else "#FFB6C6", "#E8E8E8"],
        center_text=f"{jpy_pct:.2f}%"
    )
    st.pyplot(fig, use_container_width=True)
    st.markdown("**JPY - Japanese Yen**")
    st.caption(f"1 USD = {currencies['JPY']['rate']:.2f} JPY")

# ZAR
with cols[3]:
    zar_pct = currencies['ZAR']['percentage']
    main = min(100, zar_pct)
    rest = max(0, 100 - zar_pct)
    fig = donut_matplotlib(
        [main, rest],
        colors=["#90EE90" if zar_pct < 10 else "#FFB6C6", "#E8E8E8"],
        center_text=f"{zar_pct:.1f}%"
    )
    st.pyplot(fig, use_container_width=True)
    st.markdown("**ZAR - South African Rand**")
    st.caption(f"1 USD = {currencies['ZAR']['rate']:.2f} ZAR")

st.markdown("---")
st.caption("Tip: Update the CSV files to refresh rates; the dashboard reads the latest row.")
