import json

from datetime import datetime, timezone

from typing import Any

import pandas as pd

import requests

import streamlit as st

GAMMA_MARKETS_URL = "https://gamma-api.polymarket.com/markets"

st.set_page_config(page_title="WhaleWatch AI", page_icon="🐋", layout="wide")

st.title("🐋 WhaleWatch AI")

st.caption("Phase 1: live Polymarket market intelligence for quick checks on your phone.")

def safe_float(value: Any, default=0.0):

    try:

        if value is None or value == "":

            return default

        return float(value)

    except Exception:

        return default

def parse_jsonish(value: Any):

    if isinstance(value, (list, dict)):

        return value

    if isinstance(value, str):

        try:

            return json.loads(value)

        except Exception:

            return None

    return None

def fmt_money(value):

    n = safe_float(value)

    if n >= 1_000_000:

        return f"${n/1_000_000:.1f}M"

    if n >= 1_000:

        return f"${n/1_000:.0f}K"

    return f"${n:,.0f}"

def fmt_pct(value):

    n = safe_float(value, None)

    if n is None:

        return "n/a"

    if n <= 1:

        n *= 100

    return f"{n:.0f}%"

@st.cache_data(ttl=60)

def fetch_markets(limit=250):

    params = {

        "closed": "false",

        "active": "true",

        "archived": "false",

        "limit": limit,

        "offset": 0,

        "order": "volume24hr",

        "ascending": "false",

    }

    r = requests.get(GAMMA_MARKETS_URL, params=params, timeout=15)

    r.raise_for_status()

    data = r.json()

    return data if isinstance(data, list) else data.get("markets", [])

def market_to_row(m):

    prices = parse_jsonish(m.get("outcomePrices")) or []

    yes_price = safe_float(prices[0], None) if prices else None

    volume_24h = safe_float(m.get("volume24hr") or m.get("volume24hrClob"))

    volume = safe_float(m.get("volume") or m.get("volumeClob"))

    liquidity = safe_float(m.get("liquidity") or m.get("liquidityClob"))

    score = 0

    score += min(volume_24h / 20000, 35)

    score += min(liquidity / 50000, 25)

    score += min(volume / 250000, 20)

    if yes_price is not None:

        score += max(0, 20 - abs(yes_price - 0.5) * 35)

    score = int(max(0, min(100, round(score))))

    slug = m.get("slug")

    return {

        "Market": m.get("question") or m.get("title") or "Untitled market",

        "Category": m.get("category") or "General",

        "YES": fmt_pct(yes_price),

        "24h Volume": fmt_money(volume_24h),

        "Liquidity": fmt_money(liquidity),

        "Opportunity Score": score,

        "Link": f"https://polymarket.com/market/{slug}" if slug else "https://polymarket.com/markets",

    }

if st.button("🔄 Refresh data", use_container_width=True):

    st.cache_data.clear()

    st.rerun()

try:

    markets = fetch_markets()

    rows = [market_to_row(m) for m in markets]

    df = pd.DataFrame(rows)

except Exception as e:

    st.error("Could not load Polymarket data right now. Try refreshing in a minute.")

    st.caption(str(e))

    st.stop()

if df.empty:

    st.warning("No markets loaded.")

    st.stop()

st.metric("Markets loaded", len(df))

st.metric("Last refresh", datetime.now(timezone.utc).strftime("%H:%M UTC"))

tab1, tab2, tab3 = st.tabs(["🔥 Top Opportunities", "📈 All Markets", "🧭 Roadmap"])

with tab1:

    st.subheader("Top Opportunities Right Now")

    st.caption("Research list only — not financial advice.")

    top = df.sort_values("Opportunity Score", ascending=False).head(10)

    for _, row in top.iterrows():

        st.markdown(f"### {row['Market']}")

        st.write(

            f"**YES:** {row['YES']} | **24h Volume:** {row['24h Volume']} | "

            f"**Liquidity:** {row['Liquidity']} | **Score:** {row['Opportunity Score']}/100"

        )

        st.link_button("Open market", row["Link"], use_container_width=True)

        st.divider()

with tab2:

    st.subheader("Live Polymarket Markets")

    search = st.text_input("Search markets")

    shown = df

    if search:

        shown = df[df["Market"].str.lower().str.contains(search.lower(), na=False)]

    st.dataframe(shown, use_container_width=True, hide_index=True)

with tab3:

    st.subheader("WhaleWatch AI Roadmap")

    st.write("✅ Phase 1: Live markets, search, mobile dashboard")

    st.write("Next: wallet tracking, whale alerts, smart-money scoring, and consensus signals.")
    
    st.caption("Research only. Prediction markets are risky. This app does not place trades.")