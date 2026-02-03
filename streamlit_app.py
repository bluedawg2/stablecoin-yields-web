"""Streamlit web application for Stablecoin Yield Summarizer.

Provides a web UI for browsing stablecoin yield opportunities.
"""

import streamlit as st
from datetime import datetime
from typing import List

from models.opportunity import YieldOpportunity
from main import (
    fetch_opportunities,
    filter_opportunities,
    sort_opportunities,
    is_yt_opportunity,
    SCRAPERS,
)
from config import SUPPORTED_CHAINS


# Page configuration
st.set_page_config(
    page_title="Yield Terminal - Stablecoin Yields",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


def get_all_categories() -> List[str]:
    """Get list of all available categories."""
    return list(SCRAPERS.keys())


def get_all_chains() -> List[str]:
    """Get list of all supported chains."""
    return SUPPORTED_CHAINS


def format_apy(apy: float) -> str:
    """Format APY for display."""
    if apy >= 100:
        return f"{apy:,.0f}%"
    elif apy >= 10:
        return f"{apy:.1f}%"
    else:
        return f"{apy:.2f}%"


def format_tvl(tvl: float) -> str:
    """Format TVL for display."""
    if tvl is None or tvl == 0:
        return "-"
    elif tvl >= 1_000_000_000:
        return f"${tvl / 1_000_000_000:.2f}B"
    elif tvl >= 1_000_000:
        return f"${tvl / 1_000_000:.2f}M"
    elif tvl >= 1_000:
        return f"${tvl / 1_000:.1f}K"
    else:
        return f"${tvl:.0f}"


def get_risk_color(risk: str) -> str:
    """Get color for risk level."""
    colors = {
        "Low": "green",
        "Medium": "orange",
        "High": "red",
        "Very High": "red",
    }
    return colors.get(risk, "gray")


@st.cache_data(ttl=300, show_spinner=False)
def load_opportunities(categories: List[str] = None, refresh: bool = False) -> List[YieldOpportunity]:
    """Load opportunities with caching."""
    return fetch_opportunities(
        categories=categories if categories else None,
        use_cache=not refresh,
        stale_ok=True,
    )


def main():
    # Custom CSS for styling
    st.markdown("""
    <style>
    .stMetric {
        background-color: #1e1e2e;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #313244;
    }
    .stMetric label {
        color: #cdd6f4 !important;
    }
    .stMetric [data-testid="stMetricValue"] {
        color: #89b4fa !important;
    }
    div[data-testid="stDataFrame"] {
        width: 100%;
    }
    .risk-low { color: #a6e3a1; }
    .risk-medium { color: #f9e2af; }
    .risk-high { color: #f38ba8; }
    </style>
    """, unsafe_allow_html=True)

    # Header
    st.title("📈 Yield Terminal")
    st.markdown("*Find the best stablecoin yields across DeFi*")

    # Sidebar filters
    with st.sidebar:
        st.header("Filters")

        # Category filter
        categories = get_all_categories()
        selected_categories = st.multiselect(
            "Categories",
            options=categories,
            default=[],
            help="Select categories to filter (empty = all)",
        )

        # Chain filter
        chains = get_all_chains()
        selected_chain = st.selectbox(
            "Chain",
            options=["All Chains"] + chains,
            index=0,
        )

        # Stablecoin filter
        stablecoin_filter = st.text_input(
            "Stablecoin",
            placeholder="e.g., USDC",
        )

        # Protocol filter
        protocol_filter = st.text_input(
            "Protocol",
            placeholder="e.g., Morpho",
        )

        # Min APY
        min_apy = st.number_input(
            "Min APY (%)",
            min_value=0.0,
            max_value=1000.0,
            value=0.0,
            step=0.5,
        )

        # Exclude YT tokens
        exclude_yt = st.checkbox(
            "Exclude Yield Tokens (YT)",
            value=False,
        )

        # Max Risk
        max_risk = st.selectbox(
            "Max Risk",
            options=["Any", "Low", "Medium", "High", "Very High"],
            index=0,
        )

        # Max Leverage
        max_leverage_options = {
            "Any": None,
            "1x (No Leverage)": 1.0,
            "Up to 2x": 2.0,
            "Up to 3x": 3.0,
            "Up to 5x": 5.0,
        }
        max_leverage_label = st.selectbox(
            "Max Leverage",
            options=list(max_leverage_options.keys()),
            index=0,
        )
        max_leverage = max_leverage_options[max_leverage_label]

        # Min TVL
        min_tvl_options = {
            "Any": None,
            "$100K+": 100_000,
            "$1M+": 1_000_000,
            "$10M+": 10_000_000,
            "$100M+": 100_000_000,
        }
        min_tvl_label = st.selectbox(
            "Min TVL",
            options=list(min_tvl_options.keys()),
            index=0,
        )
        min_tvl = min_tvl_options[min_tvl_label]

        st.divider()

        # Sort options
        sort_by = st.selectbox(
            "Sort By",
            options=["APY", "TVL", "Risk", "Chain", "Protocol"],
            index=0,
        ).lower()

        ascending = st.checkbox("Ascending Order", value=False)

        st.divider()

        # Refresh button
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # Load data
    with st.spinner("Loading yield opportunities..."):
        try:
            opportunities = load_opportunities(
                categories=selected_categories if selected_categories else None,
            )
        except Exception as e:
            st.error(f"Error loading data: {e}")
            opportunities = []

    # Apply filters
    if opportunities:
        opportunities = filter_opportunities(
            opportunities,
            min_apy=min_apy if min_apy > 0 else None,
            max_risk=max_risk if max_risk != "Any" else None,
            chain=selected_chain if selected_chain != "All Chains" else None,
            stablecoin=stablecoin_filter if stablecoin_filter else None,
            protocol=protocol_filter if protocol_filter else None,
            max_leverage=max_leverage,
            min_tvl=min_tvl,
            exclude_yt=exclude_yt,
        )

        # Sort
        opportunities = sort_opportunities(
            opportunities,
            sort_by=sort_by,
            ascending=ascending,
        )

    # Statistics
    if opportunities:
        apys = [o.apy for o in opportunities]
        tvls = [o.tvl for o in opportunities if o.tvl]
        protocols = set(o.protocol for o in opportunities)
        chains_in_data = set(o.chain for o in opportunities)

        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            st.metric("Opportunities", len(opportunities))
        with col2:
            st.metric("Avg APY", f"{sum(apys) / len(apys):.1f}%")
        with col3:
            st.metric("Max APY", f"{max(apys):.1f}%")
        with col4:
            st.metric("Total TVL", format_tvl(sum(tvls)) if tvls else "-")
        with col5:
            st.metric("Protocols", len(protocols))
        with col6:
            st.metric("Chains", len(chains_in_data))

    st.divider()

    # Display table
    if not opportunities:
        st.info("No opportunities found matching your filters.")
    else:
        st.subheader(f"Yield Opportunities ({len(opportunities)} results)")

        # Create data for display
        table_data = []
        for opp in opportunities:
            is_yt = is_yt_opportunity(opp)
            table_data.append({
                "Category": opp.category,
                "Protocol": opp.protocol,
                "Chain": opp.chain,
                "Stablecoin": ("🔶 " if is_yt else "") + opp.stablecoin,
                "APY": opp.apy,
                "TVL": opp.tvl if opp.tvl else 0,
                "Risk": opp.risk_score,
                "Leverage": f"{opp.leverage}x" if opp.leverage > 1 else "-",
                "URL": opp.source_url,
            })

        # Display as dataframe with custom formatting
        import pandas as pd
        df = pd.DataFrame(table_data)

        # Format columns for display
        df_display = df.copy()
        df_display["APY"] = df_display["APY"].apply(lambda x: format_apy(x))
        df_display["TVL"] = df_display["TVL"].apply(lambda x: format_tvl(x))

        # Use st.dataframe for interactive table
        st.dataframe(
            df_display.drop(columns=["URL"]),
            use_container_width=True,
            height=600,
            column_config={
                "Category": st.column_config.TextColumn("Category", width="medium"),
                "Protocol": st.column_config.TextColumn("Protocol", width="small"),
                "Chain": st.column_config.TextColumn("Chain", width="small"),
                "Stablecoin": st.column_config.TextColumn("Stablecoin", width="small"),
                "APY": st.column_config.TextColumn("APY", width="small"),
                "TVL": st.column_config.TextColumn("TVL", width="small"),
                "Risk": st.column_config.TextColumn("Risk", width="small"),
                "Leverage": st.column_config.TextColumn("Leverage", width="small"),
            },
            hide_index=True,
        )

        # Show detailed view on expansion
        with st.expander("View detailed data with links"):
            for i, opp in enumerate(opportunities[:50]):  # Limit to 50 for performance
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"**{opp.protocol}** - {opp.stablecoin} on {opp.chain}")
                    st.caption(f"APY: {format_apy(opp.apy)} | TVL: {format_tvl(opp.tvl)} | Risk: {opp.risk_score}")
                with col2:
                    if opp.source_url:
                        st.link_button("Open", opp.source_url, use_container_width=True)
                if i < len(opportunities[:50]) - 1:
                    st.divider()

    # Footer
    st.divider()
    st.caption(f"Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")


if __name__ == "__main__":
    main()
