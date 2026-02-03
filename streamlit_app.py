"""Streamlit web application for Stablecoin Yield Summarizer.

Self-contained version that doesn't depend on main.py imports.
"""

import streamlit as st
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

import requests
import pandas as pd


# =============================================================================
# Configuration (copied from config.py)
# =============================================================================

SUPPORTED_CHAINS = [
    "Ethereum", "Base", "Optimism", "Plasma", "Monad", "BSC", "World Chain",
    "HyperEVM", "Arbitrum", "Avalanche", "Etherlink", "Plume", "Katana",
    "Solana", "TAC", "Unichain", "Hemi", "Ink", "Polygon", "Sonic",
    "Berachain", "Sei",
]

CACHE_DURATION = 300  # 5 minutes
REQUEST_TIMEOUT = 30
RATE_LIMIT_DELAY = 1.0


# =============================================================================
# Data Model (copied from models/opportunity.py)
# =============================================================================

@dataclass
class YieldOpportunity:
    """Represents a yield opportunity from any source."""
    category: str
    protocol: str
    chain: str
    stablecoin: str
    apy: float
    tvl: Optional[float] = None
    risk_score: str = "Medium"
    leverage: float = 1.0
    source_url: str = ""
    maturity_date: Optional[datetime] = None
    borrow_apy: Optional[float] = None
    supply_apy: Optional[float] = None
    reward_token: Optional[str] = None
    opportunity_type: str = ""
    additional_info: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "protocol": self.protocol,
            "chain": self.chain,
            "stablecoin": self.stablecoin,
            "apy": self.apy,
            "tvl": self.tvl,
            "risk_score": self.risk_score,
            "leverage": self.leverage,
            "source_url": self.source_url,
            "maturity_date": self.maturity_date.isoformat() if self.maturity_date else None,
            "borrow_apy": self.borrow_apy,
            "supply_apy": self.supply_apy,
            "reward_token": self.reward_token,
            "opportunity_type": self.opportunity_type,
            "additional_info": self.additional_info,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "YieldOpportunity":
        maturity = data.get("maturity_date")
        if maturity and isinstance(maturity, str):
            maturity = datetime.fromisoformat(maturity)
        return cls(
            category=data["category"],
            protocol=data["protocol"],
            chain=data["chain"],
            stablecoin=data["stablecoin"],
            apy=data["apy"],
            tvl=data.get("tvl"),
            risk_score=data.get("risk_score", "Medium"),
            leverage=data.get("leverage", 1.0),
            source_url=data.get("source_url", ""),
            maturity_date=maturity,
            borrow_apy=data.get("borrow_apy"),
            supply_apy=data.get("supply_apy"),
            reward_token=data.get("reward_token"),
            opportunity_type=data.get("opportunity_type", ""),
            additional_info=data.get("additional_info", {}),
        )


# =============================================================================
# Risk Assessment (copied from utils/risk.py)
# =============================================================================

class RiskAssessor:
    PROTOCOL_MATURITY = {
        "aave": 1, "morpho": 2, "euler": 2, "pendle": 2, "compound": 1,
        "silo": 3, "merkl": 2, "beefy": 2, "yearn": 1, "midas": 3,
        "spectra": 3, "gearbox": 2, "upshift": 3, "ipor": 3,
        "townsquare": 3, "curvance": 3, "accountable": 3,
    }
    CHAIN_RISK = {
        "ethereum": 1, "arbitrum": 1, "base": 1, "optimism": 1, "polygon": 1,
        "avalanche": 2, "bsc": 2, "solana": 2, "berachain": 3, "sonic": 3,
        "sei": 3, "monad": 4, "plasma": 4, "hyperevm": 4, "etherlink": 4,
        "plume": 4, "katana": 4, "tac": 4, "unichain": 3, "hemi": 4,
        "ink": 4, "world chain": 3,
    }
    STRATEGY_RISK = {
        "simple_lend": 1, "lend": 1, "loop": 3, "pendle_fixed": 2,
        "pendle_loop": 4, "reward": 2, "yield_bearing": 2, "vault": 2, "fixed": 2,
    }

    @classmethod
    def calculate_risk_score(cls, strategy_type: str, leverage: float = 1.0,
                            protocol: str = "", chain: str = "",
                            maturity_date: Optional[datetime] = None,
                            apy: float = 0.0) -> str:
        score = cls.STRATEGY_RISK.get(strategy_type.lower(), 2) * 10
        if leverage > 1:
            score += (leverage - 1) * 15
            if leverage >= 5: score += 20
            if leverage >= 7: score += 20
            if leverage >= 10: score += 30

        protocol_lower = protocol.lower()
        for proto, maturity in cls.PROTOCOL_MATURITY.items():
            if proto in protocol_lower:
                score += maturity * 5
                break
        else:
            score += 15

        chain_risk = cls.CHAIN_RISK.get(chain.lower(), 4)
        score += chain_risk * 5

        if apy > 100: score += 20
        elif apy > 50: score += 10
        elif apy > 30: score += 5

        if score < 25: return "Low"
        elif score < 50: return "Medium"
        elif score < 75: return "High"
        else: return "Very High"


# =============================================================================
# Simplified Scrapers for Streamlit
# =============================================================================

class BaseScraper:
    """Base scraper with caching."""
    requires_vpn: bool = False
    category: str = ""
    cache_file: str = ""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/html, */*",
        })
        self._cache_dir = Path(".cache")
        self._cache_dir.mkdir(exist_ok=True)

    def _get_cached_data(self, stale_ok: bool = False) -> Optional[List[Dict]]:
        if not self.cache_file:
            return None
        cache_path = self._cache_dir / f"{self.cache_file}.json"
        if not cache_path.exists():
            return None
        try:
            with open(cache_path, "r") as f:
                cache = json.load(f)
            cached_time = datetime.fromisoformat(cache["timestamp"])
            age_seconds = (datetime.now() - cached_time).total_seconds()
            if age_seconds < CACHE_DURATION or stale_ok:
                return cache["data"]
        except (json.JSONDecodeError, KeyError, ValueError):
            pass
        return None

    def _save_to_cache(self, data: List[Dict]) -> None:
        if not self.cache_file:
            return
        cache_path = self._cache_dir / f"{self.cache_file}.json"
        with open(cache_path, "w") as f:
            json.dump({"timestamp": datetime.now().isoformat(), "data": data}, f)

    def fetch(self, use_cache: bool = True, stale_ok: bool = False) -> List[YieldOpportunity]:
        if use_cache or stale_ok:
            cached = self._get_cached_data(stale_ok=stale_ok)
            if cached:
                return [YieldOpportunity.from_dict(d) for d in cached]
        try:
            opportunities = self._fetch_data()
            self._save_to_cache([o.to_dict() for o in opportunities])
            return opportunities
        except Exception:
            cached = self._get_cached_data(stale_ok=True)
            if cached:
                return [YieldOpportunity.from_dict(d) for d in cached]
            return []

    def _fetch_data(self) -> List[YieldOpportunity]:
        return []


class MorphoLendScraper(BaseScraper):
    """Scraper for Morpho lending markets."""
    category = "Morpho Lend"
    cache_file = "morpho_lend"

    # Minimum TVL to filter out empty/unreliable markets
    MIN_TVL_USD = 10_000
    # Maximum reasonable APY (filter out data anomalies)
    MAX_APY_PERCENT = 50

    CHAIN_IDS = {
        "Ethereum": 1,
        "Base": 8453,
        "Arbitrum": 42161,
    }

    STABLECOIN_SYMBOLS = [
        "USDC", "USDT", "DAI", "FRAX", "LUSD", "sDAI", "sUSDe", "USDe",
        "USDS", "sUSDS", "GHO", "crvUSD", "pyUSD", "USDM", "DOLA", "MIM",
    ]

    def _is_stablecoin(self, symbol: str) -> bool:
        symbol_upper = symbol.upper()
        return any(stable.upper() in symbol_upper for stable in self.STABLECOIN_SYMBOLS)

    def _fetch_data(self) -> List[YieldOpportunity]:
        opportunities = []
        for chain_name, chain_id in self.CHAIN_IDS.items():
            try:
                chain_opps = self._fetch_chain_data(chain_name, chain_id)
                opportunities.extend(chain_opps)
            except Exception:
                continue
        return opportunities

    def _fetch_chain_data(self, chain_name: str, chain_id: int) -> List[YieldOpportunity]:
        opportunities = []
        query = """
        query GetMarkets($chainId: Int!) {
            markets(where: { chainId_in: [$chainId] }) {
                items {
                    uniqueKey
                    loanAsset { symbol }
                    collateralAsset { symbol }
                    state {
                        supplyApy
                        supplyAssetsUsd
                    }
                }
            }
        }
        """
        try:
            resp = self.session.post(
                "https://blue-api.morpho.org/graphql",
                json={"query": query, "variables": {"chainId": chain_id}},
                timeout=REQUEST_TIMEOUT
            )
            data = resp.json()
            markets = data.get("data", {}).get("markets", {}).get("items", [])

            for market in markets:
                loan_asset = market.get("loanAsset", {}).get("symbol", "")
                if not self._is_stablecoin(loan_asset):
                    continue

                state = market.get("state", {})
                apy = (state.get("supplyApy") or 0) * 100
                tvl = state.get("supplyAssetsUsd") or 0

                # Filter out empty/low-TVL markets (unreliable APY)
                if tvl < self.MIN_TVL_USD:
                    continue

                # Filter out unrealistic APY values (data anomalies)
                if apy <= 0 or apy > self.MAX_APY_PERCENT:
                    continue

                market_id = market.get("uniqueKey", "")
                opportunities.append(YieldOpportunity(
                    category=self.category,
                    protocol="Morpho",
                    chain=chain_name,
                    stablecoin=loan_asset,
                    apy=apy,
                    tvl=tvl,
                    risk_score=RiskAssessor.calculate_risk_score("lend", protocol="morpho", chain=chain_name, apy=apy),
                    source_url=f"https://app.morpho.org/market?id={market_id}" if market_id else "https://app.morpho.org",
                ))
        except Exception:
            pass
        return opportunities


class DefiLlamaScraper(BaseScraper):
    """Generic DeFi Llama yields scraper."""
    category = "DeFi Yields"
    cache_file = "defillama"

    # Minimum TVL to filter out empty/unreliable pools
    MIN_TVL_USD = 100_000
    # Maximum reasonable APY (filter out data anomalies)
    MAX_APY_PERCENT = 100

    STABLECOIN_SYMBOLS = {"USDC", "USDT", "DAI", "FRAX", "LUSD", "GHO", "PYUSD",
                          "USDE", "SUSDE", "USDS", "SUSDS", "SDAI", "CUSD", "CRVUSD",
                          "FRXUSD", "SFRXUSD", "EUSD", "USDM", "USDY", "DOLA", "MIM"}

    def _fetch_data(self) -> List[YieldOpportunity]:
        opportunities = []
        try:
            resp = self.session.get(
                "https://yields.llama.fi/pools",
                timeout=REQUEST_TIMEOUT
            )
            data = resp.json().get("data", [])
            for pool in data:
                symbol = pool.get("symbol", "").upper()
                if not any(s in symbol for s in self.STABLECOIN_SYMBOLS):
                    continue

                apy = pool.get("apy") or 0
                tvl = pool.get("tvlUsd") or 0

                # Filter out low-TVL pools (unreliable APY)
                if tvl < self.MIN_TVL_USD:
                    continue

                # Filter out unrealistic APY values
                if apy <= 0 or apy > self.MAX_APY_PERCENT:
                    continue

                chain = pool.get("chain", "Unknown")
                project = pool.get("project", "Unknown")
                opportunities.append(YieldOpportunity(
                    category="DeFi Yields",
                    protocol=project.replace("-", " ").title(),
                    chain=chain.title(),
                    stablecoin=symbol.split("-")[0] if "-" in symbol else symbol,
                    apy=apy,
                    tvl=tvl,
                    risk_score=RiskAssessor.calculate_risk_score("lend", protocol=project, chain=chain, apy=apy),
                    source_url=f"https://defillama.com/yields/pool/{pool.get('pool', '')}",
                ))
        except Exception:
            pass
        return opportunities


# Available scrapers
SCRAPERS = {
    "Morpho Lend": MorphoLendScraper,
    "DeFi Yields": DefiLlamaScraper,
}


# =============================================================================
# Core Functions
# =============================================================================

def fetch_opportunities(categories: Optional[List[str]] = None,
                       use_cache: bool = True,
                       stale_ok: bool = False) -> List[YieldOpportunity]:
    """Fetch yield opportunities from scrapers."""
    opportunities = []
    scraper_classes = SCRAPERS if not categories else {
        k: v for k, v in SCRAPERS.items() if k in categories
    }
    for category_name, scraper_class in scraper_classes.items():
        try:
            scraper = scraper_class()
            opportunities.extend(scraper.fetch(use_cache=use_cache, stale_ok=stale_ok))
        except Exception:
            pass
    return opportunities


def is_yt_opportunity(opp: YieldOpportunity) -> bool:
    """Check if opportunity is a Yield Token."""
    opp_type = (opp.opportunity_type or "").upper()
    if "YT" in opp_type:
        return True
    stablecoin = (opp.stablecoin or "").upper()
    if stablecoin.startswith("YT-") or stablecoin.startswith("YT "):
        return True
    name = (opp.additional_info.get("name", "") or "").upper()
    if "HOLD PENDLE YT" in name or "HOLD YT" in name:
        return True
    return False


def filter_opportunities(opportunities: List[YieldOpportunity],
                        min_apy: Optional[float] = None,
                        max_risk: Optional[str] = None,
                        chain: Optional[str] = None,
                        stablecoin: Optional[str] = None,
                        protocol: Optional[str] = None,
                        max_leverage: Optional[float] = None,
                        min_tvl: Optional[float] = None,
                        exclude_yt: bool = False) -> List[YieldOpportunity]:
    """Filter opportunities by criteria."""
    filtered = opportunities
    if min_apy is not None:
        filtered = [o for o in filtered if o.apy >= min_apy]
    if max_risk:
        risk_levels = ["Low", "Medium", "High", "Very High"]
        if max_risk.title() in risk_levels:
            max_idx = risk_levels.index(max_risk.title())
            filtered = [o for o in filtered if risk_levels.index(o.risk_score) <= max_idx]
    if chain:
        filtered = [o for o in filtered if o.chain.lower() == chain.lower()]
    if stablecoin:
        filtered = [o for o in filtered if stablecoin.upper() in o.stablecoin.upper()]
    if protocol:
        filtered = [o for o in filtered if protocol.lower() in o.protocol.lower()]
    if max_leverage is not None:
        filtered = [o for o in filtered if o.leverage <= max_leverage]
    if min_tvl is not None:
        filtered = [o for o in filtered if o.tvl and o.tvl >= min_tvl]
    if exclude_yt:
        filtered = [o for o in filtered if not is_yt_opportunity(o)]
    return filtered


def sort_opportunities(opportunities: List[YieldOpportunity],
                      sort_by: str = "apy",
                      ascending: bool = False) -> List[YieldOpportunity]:
    """Sort opportunities by field."""
    risk_order = {"Low": 0, "Medium": 1, "High": 2, "Very High": 3}
    sort_keys = {
        "apy": lambda o: o.apy,
        "tvl": lambda o: o.tvl if o.tvl else 0,
        "risk": lambda o: risk_order.get(o.risk_score, 2),
        "chain": lambda o: o.chain.lower(),
        "protocol": lambda o: o.protocol.lower(),
    }
    key_func = sort_keys.get(sort_by.lower(), sort_keys["apy"])
    return sorted(opportunities, key=key_func, reverse=not ascending)


# =============================================================================
# Streamlit UI
# =============================================================================

st.set_page_config(
    page_title="Yield Terminal - Stablecoin Yields",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


def format_apy(apy: float) -> str:
    if apy >= 100:
        return f"{apy:,.0f}%"
    elif apy >= 10:
        return f"{apy:.1f}%"
    return f"{apy:.2f}%"


def format_tvl(tvl: float) -> str:
    if tvl is None or tvl == 0:
        return "-"
    elif tvl >= 1_000_000_000:
        return f"${tvl / 1_000_000_000:.2f}B"
    elif tvl >= 1_000_000:
        return f"${tvl / 1_000_000:.2f}M"
    elif tvl >= 1_000:
        return f"${tvl / 1_000:.1f}K"
    return f"${tvl:.0f}"


@st.cache_data(ttl=300, show_spinner=False)
def load_opportunities(categories: tuple = None) -> List[dict]:
    """Load opportunities with caching."""
    opps = fetch_opportunities(
        categories=list(categories) if categories else None,
        use_cache=True,
        stale_ok=True,
    )
    return [o.to_dict() for o in opps]


def main():
    st.markdown("""
    <style>
    .stMetric { background-color: #1e1e2e; padding: 15px; border-radius: 10px; border: 1px solid #313244; }
    div[data-testid="stDataFrame"] { width: 100%; }
    </style>
    """, unsafe_allow_html=True)

    st.title("📈 Yield Terminal")
    st.markdown("*Find the best stablecoin yields across DeFi*")

    with st.sidebar:
        st.header("Filters")
        categories = list(SCRAPERS.keys())
        selected_categories = st.multiselect("Categories", options=categories, default=[])
        selected_chain = st.selectbox("Chain", options=["All Chains"] + SUPPORTED_CHAINS, index=0)
        stablecoin_filter = st.text_input("Stablecoin", placeholder="e.g., USDC")
        protocol_filter = st.text_input("Protocol", placeholder="e.g., Morpho")
        min_apy = st.number_input("Min APY (%)", min_value=0.0, max_value=1000.0, value=0.0, step=0.5)
        exclude_yt = st.checkbox("Exclude Yield Tokens (YT)", value=False)
        max_risk = st.selectbox("Max Risk", options=["Any", "Low", "Medium", "High", "Very High"], index=0)

        max_leverage_options = {"Any": None, "1x (No Leverage)": 1.0, "Up to 2x": 2.0, "Up to 3x": 3.0, "Up to 5x": 5.0}
        max_leverage = max_leverage_options[st.selectbox("Max Leverage", options=list(max_leverage_options.keys()), index=0)]

        min_tvl_options = {"Any": None, "$100K+": 100_000, "$1M+": 1_000_000, "$10M+": 10_000_000, "$100M+": 100_000_000}
        min_tvl = min_tvl_options[st.selectbox("Min TVL", options=list(min_tvl_options.keys()), index=0)]

        st.divider()
        sort_by = st.selectbox("Sort By", options=["APY", "TVL", "Risk", "Chain", "Protocol"], index=0).lower()
        ascending = st.checkbox("Ascending Order", value=False)
        st.divider()

        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    with st.spinner("Loading yield opportunities..."):
        try:
            opp_dicts = load_opportunities(
                categories=tuple(selected_categories) if selected_categories else None
            )
            opportunities = [YieldOpportunity.from_dict(d) for d in opp_dicts]
        except Exception as e:
            st.error(f"Error loading data: {e}")
            opportunities = []

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
        opportunities = sort_opportunities(opportunities, sort_by=sort_by, ascending=ascending)

    if opportunities:
        apys = [o.apy for o in opportunities]
        tvls = [o.tvl for o in opportunities if o.tvl]
        protocols = set(o.protocol for o in opportunities)
        chains_in_data = set(o.chain for o in opportunities)

        col1, col2, col3, col4, col5, col6 = st.columns(6)
        col1.metric("Opportunities", len(opportunities))
        col2.metric("Avg APY", f"{sum(apys) / len(apys):.1f}%")
        col3.metric("Max APY", f"{max(apys):.1f}%")
        col4.metric("Total TVL", format_tvl(sum(tvls)) if tvls else "-")
        col5.metric("Protocols", len(protocols))
        col6.metric("Chains", len(chains_in_data))

    st.divider()

    if not opportunities:
        st.info("No opportunities found. Click 'Refresh Data' to fetch latest yields.")
    else:
        st.subheader(f"Yield Opportunities ({len(opportunities)} results)")

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

        df = pd.DataFrame(table_data)
        df_display = df.copy()
        df_display["APY"] = df_display["APY"].apply(format_apy)
        df_display["TVL"] = df_display["TVL"].apply(format_tvl)

        st.dataframe(
            df_display.drop(columns=["URL"]),
            use_container_width=True,
            height=600,
            hide_index=True,
        )

        with st.expander("View detailed data with links"):
            for i, opp in enumerate(opportunities[:50]):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"**{opp.protocol}** - {opp.stablecoin} on {opp.chain}")
                    st.caption(f"APY: {format_apy(opp.apy)} | TVL: {format_tvl(opp.tvl)} | Risk: {opp.risk_score}")
                with col2:
                    if opp.source_url:
                        st.link_button("Open", opp.source_url, use_container_width=True)
                if i < 49:
                    st.divider()

    st.divider()
    st.caption(f"Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")


if __name__ == "__main__":
    main()
