"""Streamlit web application for Stablecoin Yield Summarizer.

Self-contained version with dark theme and all scrapers.
"""

import streamlit as st
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

import requests
import pandas as pd


# =============================================================================
# Page Config (MUST be first Streamlit command)
# =============================================================================

st.set_page_config(
    page_title="Yield Terminal - Stablecoin Yields",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =============================================================================
# Dark Theme CSS
# =============================================================================

st.markdown("""
<style>
/* Dark theme for Streamlit */
.stApp {
    background-color: #0a0b0e;
    color: #f0f2f5;
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background-color: #12141a;
    border-right: 1px solid rgba(255, 255, 255, 0.1);
}

[data-testid="stSidebar"] .stMarkdown {
    color: #f0f2f5;
}

/* Headers */
h1, h2, h3 {
    color: #f0f2f5 !important;
}

/* Metrics */
[data-testid="stMetric"] {
    background-color: #1a1d25;
    padding: 16px;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

[data-testid="stMetricLabel"] {
    color: #8b919e !important;
}

[data-testid="stMetricValue"] {
    color: #00d4ff !important;
    font-weight: 600;
}

/* DataFrame styling */
[data-testid="stDataFrame"] {
    background-color: #12141a;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.stDataFrame {
    background-color: #12141a;
}

/* Table header */
thead tr th {
    background-color: #1a1d25 !important;
    color: #8b919e !important;
    font-weight: 600;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
}

/* Table rows */
tbody tr {
    background-color: #12141a !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06) !important;
}

tbody tr:hover {
    background-color: #1f232d !important;
}

tbody tr td {
    color: #f0f2f5 !important;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #00d4ff 0%, #4d7cff 100%);
    color: #0a0b0e;
    border: none;
    font-weight: 600;
    border-radius: 8px;
    transition: all 0.2s ease;
}

.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(0, 212, 255, 0.3);
}

/* Select boxes */
.stSelectbox > div > div {
    background-color: #1a1d25;
    border-color: rgba(255, 255, 255, 0.1);
    color: #f0f2f5;
}

/* Text inputs */
.stTextInput > div > div > input {
    background-color: #1a1d25;
    border-color: rgba(255, 255, 255, 0.1);
    color: #f0f2f5;
}

/* Number inputs */
.stNumberInput > div > div > input {
    background-color: #1a1d25;
    border-color: rgba(255, 255, 255, 0.1);
    color: #f0f2f5;
}

/* Multiselect */
.stMultiSelect > div > div {
    background-color: #1a1d25;
    border-color: rgba(255, 255, 255, 0.1);
}

/* Expander */
.streamlit-expanderHeader {
    background-color: #1a1d25;
    border-radius: 8px;
    color: #f0f2f5 !important;
}

.streamlit-expanderContent {
    background-color: #12141a;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 0 0 8px 8px;
}

/* Dividers */
hr {
    border-color: rgba(255, 255, 255, 0.1);
}

/* Info/Warning boxes */
.stAlert {
    background-color: #1a1d25;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

/* Link buttons */
.stLinkButton > a {
    background: linear-gradient(135deg, #00d4ff 0%, #4d7cff 100%);
    color: #0a0b0e !important;
    font-weight: 600;
}

/* Checkboxes */
.stCheckbox > label > span {
    color: #f0f2f5;
}

/* Caption text */
.stCaption {
    color: #5c6370 !important;
}

/* Risk badges */
.risk-low { color: #00ff88; }
.risk-medium { color: #ffb800; }
.risk-high { color: #ff6b35; }
.risk-very-high { color: #ff3860; }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# Configuration
# =============================================================================

SUPPORTED_CHAINS = [
    "Ethereum", "Base", "Optimism", "Arbitrum", "Avalanche", "BSC",
    "Polygon", "Sonic", "Berachain", "Solana", "TAC", "Unichain",
]

CACHE_DURATION = 300
REQUEST_TIMEOUT = 30


# =============================================================================
# Data Model
# =============================================================================

@dataclass
class YieldOpportunity:
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
            "category": self.category, "protocol": self.protocol,
            "chain": self.chain, "stablecoin": self.stablecoin,
            "apy": self.apy, "tvl": self.tvl, "risk_score": self.risk_score,
            "leverage": self.leverage, "source_url": self.source_url,
            "maturity_date": self.maturity_date.isoformat() if self.maturity_date else None,
            "borrow_apy": self.borrow_apy, "supply_apy": self.supply_apy,
            "reward_token": self.reward_token, "opportunity_type": self.opportunity_type,
            "additional_info": self.additional_info,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "YieldOpportunity":
        maturity = data.get("maturity_date")
        if maturity and isinstance(maturity, str):
            maturity = datetime.fromisoformat(maturity)
        return cls(
            category=data["category"], protocol=data["protocol"],
            chain=data["chain"], stablecoin=data["stablecoin"],
            apy=data["apy"], tvl=data.get("tvl"),
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
# Risk Assessment
# =============================================================================

class RiskAssessor:
    CHAIN_RISK = {"ethereum": 1, "arbitrum": 1, "base": 1, "optimism": 1, "polygon": 1,
                  "avalanche": 2, "bsc": 2, "solana": 2, "berachain": 3, "sonic": 3}
    STRATEGY_RISK = {"lend": 1, "loop": 3, "pendle_loop": 4, "reward": 2, "vault": 2}

    @classmethod
    def calculate_risk_score(cls, strategy_type: str, leverage: float = 1.0,
                            protocol: str = "", chain: str = "", apy: float = 0.0) -> str:
        score = cls.STRATEGY_RISK.get(strategy_type.lower(), 2) * 10
        if leverage > 1:
            score += (leverage - 1) * 15
            if leverage >= 5: score += 20
        score += cls.CHAIN_RISK.get(chain.lower(), 3) * 5
        if apy > 100: score += 20
        elif apy > 50: score += 10
        if score < 25: return "Low"
        elif score < 50: return "Medium"
        elif score < 75: return "High"
        return "Very High"


# =============================================================================
# Scrapers
# =============================================================================

class BaseScraper:
    category: str = ""
    cache_file: str = ""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
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
            age = (datetime.now() - datetime.fromisoformat(cache["timestamp"])).total_seconds()
            if age < CACHE_DURATION or stale_ok:
                return cache["data"]
        except:
            pass
        return None

    def _save_to_cache(self, data: List[Dict]) -> None:
        if self.cache_file:
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
        except:
            cached = self._get_cached_data(stale_ok=True)
            return [YieldOpportunity.from_dict(d) for d in cached] if cached else []

    def _fetch_data(self) -> List[YieldOpportunity]:
        return []


class MorphoLendScraper(BaseScraper):
    category = "Morpho Lend"
    cache_file = "morpho_lend_st"
    MIN_TVL_USD = 10_000
    MAX_APY_PERCENT = 50
    CHAIN_IDS = {"Ethereum": 1, "Base": 8453, "Arbitrum": 42161}
    STABLECOINS = ["USDC", "USDT", "DAI", "FRAX", "LUSD", "sDAI", "sUSDe", "USDe", "USDS", "GHO", "crvUSD"]

    def _fetch_data(self) -> List[YieldOpportunity]:
        opportunities = []
        for chain_name, chain_id in self.CHAIN_IDS.items():
            try:
                query = """query($chainId: Int!) { markets(where: { chainId_in: [$chainId] }) {
                    items { uniqueKey loanAsset { symbol } state { supplyApy supplyAssetsUsd } } } }"""
                resp = self.session.post("https://blue-api.morpho.org/graphql",
                    json={"query": query, "variables": {"chainId": chain_id}}, timeout=REQUEST_TIMEOUT)
                for market in resp.json().get("data", {}).get("markets", {}).get("items", []):
                    symbol = market.get("loanAsset", {}).get("symbol", "")
                    if not any(s in symbol.upper() for s in self.STABLECOINS):
                        continue
                    state = market.get("state", {})
                    apy = (state.get("supplyApy") or 0) * 100
                    tvl = state.get("supplyAssetsUsd") or 0
                    if tvl < self.MIN_TVL_USD or apy <= 0 or apy > self.MAX_APY_PERCENT:
                        continue
                    opportunities.append(YieldOpportunity(
                        category=self.category, protocol="Morpho", chain=chain_name,
                        stablecoin=symbol, apy=apy, tvl=tvl,
                        risk_score=RiskAssessor.calculate_risk_score("lend", chain=chain_name, apy=apy),
                        source_url=f"https://app.morpho.org/market?id={market.get('uniqueKey', '')}",
                    ))
            except:
                continue
        return opportunities


class MerklScraper(BaseScraper):
    category = "Merkl Rewards"
    cache_file = "merkl_st"
    MIN_TVL_USD = 10_000
    MAX_APR = 500
    STABLECOINS = ["USDC", "USDT", "DAI", "FRAX", "LUSD", "SDAI", "SUSDE", "USDE", "USDS", "GHO", "CRVUSD", "USD"]

    def _is_stablecoin(self, tokens: List[str], name: str) -> bool:
        if not tokens:
            return any(s in name.upper() for s in self.STABLECOINS)
        for token in tokens:
            if not any(s in token.upper() for s in self.STABLECOINS):
                return False
        return True

    def _fetch_data(self) -> List[YieldOpportunity]:
        opportunities = []
        try:
            for page in range(20):  # Max 20 pages
                resp = self.session.get(f"https://api.merkl.xyz/v4/opportunities?page={page}&items=100", timeout=REQUEST_TIMEOUT)
                data = resp.json()
                if not data:
                    break
                for item in data:
                    tokens = [t.get("symbol", "").upper() for t in item.get("tokens", []) if isinstance(t, dict)]
                    name = item.get("name", "") or ""
                    if not self._is_stablecoin(tokens, name):
                        continue
                    apr = item.get("apr", 0) or 0
                    tvl = item.get("tvl", 0) or 0
                    if tvl < self.MIN_TVL_USD or apr <= 0 or apr > self.MAX_APR:
                        continue
                    chain_data = item.get("chain", {})
                    chain = chain_data.get("name", "Unknown") if isinstance(chain_data, dict) else str(chain_data)
                    stablecoin = tokens[0] if tokens else "USD"
                    protocol = "Merkl"
                    for p in ["Morpho", "Euler", "Aave", "Compound", "Pendle", "Silo"]:
                        if p.upper() in name.upper():
                            protocol = p
                            break
                    opp_type = item.get("type", "")
                    identifier = item.get("identifier", "")
                    opportunities.append(YieldOpportunity(
                        category=self.category, protocol=protocol, chain=chain,
                        stablecoin=stablecoin, apy=apr, tvl=tvl,
                        opportunity_type=item.get("action", ""),
                        risk_score=RiskAssessor.calculate_risk_score("reward", chain=chain, apy=apr),
                        source_url=f"https://app.merkl.xyz/opportunities/{chain.lower()}/{opp_type}/{identifier}",
                        additional_info={"name": name, "tokens": tokens},
                    ))
                if len(data) < 100:
                    break
        except:
            pass
        return opportunities


class PendleFixedScraper(BaseScraper):
    category = "Pendle Fixed Yields"
    cache_file = "pendle_fixed_st"
    MIN_TVL_USD = 50_000
    MAX_APY = 100
    CHAIN_IDS = {"Ethereum": 1, "Arbitrum": 42161, "Base": 8453}
    STABLECOINS = ["USDC", "USDT", "DAI", "USDE", "SUSDE", "SDAI", "USDS", "GHO", "FRAX"]

    def _fetch_data(self) -> List[YieldOpportunity]:
        opportunities = []
        for chain_name, chain_id in self.CHAIN_IDS.items():
            try:
                resp = self.session.get(f"https://api-v2.pendle.finance/core/v1/{chain_id}/markets?order_by=name%3A1&skip=0&limit=100", timeout=REQUEST_TIMEOUT)
                for market in resp.json().get("results", []):
                    underlying = market.get("underlyingAsset", {}).get("symbol", "")
                    if not any(s in underlying.upper() for s in self.STABLECOINS):
                        continue
                    apy = (market.get("impliedApy") or 0) * 100
                    tvl = market.get("liquidity", {}).get("usd") or 0
                    if tvl < self.MIN_TVL_USD or apy <= 0 or apy > self.MAX_APY:
                        continue
                    maturity = None
                    if market.get("expiry"):
                        try:
                            maturity = datetime.fromisoformat(market["expiry"].replace("Z", "+00:00"))
                        except:
                            pass
                    opportunities.append(YieldOpportunity(
                        category=self.category, protocol="Pendle", chain=chain_name,
                        stablecoin=underlying, apy=apy, tvl=tvl, maturity_date=maturity,
                        risk_score=RiskAssessor.calculate_risk_score("lend", chain=chain_name, apy=apy),
                        source_url=f"https://app.pendle.finance/trade/markets/{market.get('address', '')}",
                    ))
            except:
                continue
        return opportunities


class PendleLoopScraper(BaseScraper):
    category = "Pendle Looping"
    cache_file = "pendle_loop_st"
    LEVERAGE_LEVELS = [2.0, 3.0, 5.0]
    MIN_LIQUIDITY = 500_000

    def __init__(self):
        super().__init__()
        self.pendle_scraper = PendleFixedScraper()

    def _fetch_data(self) -> List[YieldOpportunity]:
        opportunities = []
        try:
            pendle_opps = self.pendle_scraper.fetch(use_cache=True)
        except:
            return opportunities

        # Fetch Morpho borrow markets
        morpho_markets = self._fetch_morpho_markets()

        for pt_opp in pendle_opps:
            if pt_opp.chain not in ["Ethereum", "Arbitrum", "Base"]:
                continue
            # Find matching borrow markets
            for market in morpho_markets.get(pt_opp.chain, []):
                collateral_sym = market.get("collateral", "").upper()
                if not collateral_sym.startswith("PT-"):
                    continue
                # Check if underlying matches
                if pt_opp.stablecoin.upper() not in collateral_sym:
                    continue
                borrow_apy = market.get("borrow_apy", 0)
                liquidity = market.get("liquidity", 0)
                if liquidity < self.MIN_LIQUIDITY:
                    continue
                lltv = market.get("lltv", 0.85)
                for leverage in self.LEVERAGE_LEVELS:
                    max_lev = 1 / (1 - lltv) if lltv < 1 else 1
                    if leverage > max_lev * 0.9:
                        continue
                    net_apy = pt_opp.apy * leverage - borrow_apy * (leverage - 1)
                    if net_apy <= 0:
                        continue
                    opportunities.append(YieldOpportunity(
                        category=self.category, protocol="Pendle + Morpho",
                        chain=pt_opp.chain, stablecoin=pt_opp.stablecoin,
                        apy=net_apy, tvl=liquidity, leverage=leverage,
                        supply_apy=pt_opp.apy, borrow_apy=borrow_apy,
                        maturity_date=pt_opp.maturity_date,
                        risk_score=RiskAssessor.calculate_risk_score("pendle_loop", leverage=leverage, chain=pt_opp.chain, apy=net_apy),
                        source_url=f"https://app.morpho.org/market?id={market.get('market_id', '')}",
                        additional_info={"pt_yield": pt_opp.apy, "borrow_rate": borrow_apy, "lltv": lltv * 100},
                    ))
        return opportunities

    def _fetch_morpho_markets(self) -> Dict[str, List[Dict]]:
        markets_by_chain = {}
        chain_ids = {"Ethereum": 1, "Base": 8453, "Arbitrum": 42161}
        for chain_name, chain_id in chain_ids.items():
            try:
                query = """query($chainId: Int!) { markets(where: { chainId_in: [$chainId] }, first: 500) {
                    items { uniqueKey collateralAsset { symbol } loanAsset { symbol }
                            state { borrowApy liquidityAssetsUsd } lltv } } }"""
                resp = self.session.post("https://blue-api.morpho.org/graphql",
                    json={"query": query, "variables": {"chainId": chain_id}}, timeout=REQUEST_TIMEOUT)
                markets = []
                for m in resp.json().get("data", {}).get("markets", {}).get("items", []):
                    collateral = m.get("collateralAsset", {}).get("symbol", "")
                    if not collateral.upper().startswith("PT-"):
                        continue
                    state = m.get("state", {})
                    borrow_apy = (state.get("borrowApy") or 0) * 100
                    liquidity = state.get("liquidityAssetsUsd") or 0
                    lltv = float(m.get("lltv", 0))
                    if lltv > 1:
                        lltv = lltv / 1e18
                    markets.append({
                        "collateral": collateral, "borrow_apy": borrow_apy,
                        "liquidity": liquidity, "lltv": lltv,
                        "market_id": m.get("uniqueKey", ""),
                    })
                markets_by_chain[chain_name] = markets
            except:
                markets_by_chain[chain_name] = []
        return markets_by_chain


# Available scrapers
SCRAPERS = {
    "Morpho Lend": MorphoLendScraper,
    "Merkl Rewards": MerklScraper,
    "Pendle Fixed Yields": PendleFixedScraper,
    "Pendle Looping": PendleLoopScraper,
}


# =============================================================================
# Core Functions
# =============================================================================

def fetch_opportunities(categories: Optional[List[str]] = None,
                       use_cache: bool = True, stale_ok: bool = False) -> List[YieldOpportunity]:
    opportunities = []
    scraper_classes = SCRAPERS if not categories else {k: v for k, v in SCRAPERS.items() if k in categories}
    for scraper_class in scraper_classes.values():
        try:
            opportunities.extend(scraper_class().fetch(use_cache=use_cache, stale_ok=stale_ok))
        except:
            pass
    return opportunities


def is_yt_opportunity(opp: YieldOpportunity) -> bool:
    if "YT" in (opp.opportunity_type or "").upper():
        return True
    if (opp.stablecoin or "").upper().startswith("YT"):
        return True
    name = (opp.additional_info.get("name", "") or "").upper()
    return "HOLD YT" in name or "HOLD PENDLE YT" in name


def filter_opportunities(opportunities: List[YieldOpportunity], min_apy: Optional[float] = None,
                        max_risk: Optional[str] = None, chain: Optional[str] = None,
                        stablecoin: Optional[str] = None, protocol: Optional[str] = None,
                        max_leverage: Optional[float] = None, min_tvl: Optional[float] = None,
                        exclude_yt: bool = False) -> List[YieldOpportunity]:
    filtered = opportunities
    if min_apy: filtered = [o for o in filtered if o.apy >= min_apy]
    if max_risk:
        levels = ["Low", "Medium", "High", "Very High"]
        if max_risk in levels:
            idx = levels.index(max_risk)
            filtered = [o for o in filtered if levels.index(o.risk_score) <= idx]
    if chain: filtered = [o for o in filtered if o.chain.lower() == chain.lower()]
    if stablecoin: filtered = [o for o in filtered if stablecoin.upper() in o.stablecoin.upper()]
    if protocol: filtered = [o for o in filtered if protocol.lower() in o.protocol.lower()]
    if max_leverage: filtered = [o for o in filtered if o.leverage <= max_leverage]
    if min_tvl: filtered = [o for o in filtered if o.tvl and o.tvl >= min_tvl]
    if exclude_yt: filtered = [o for o in filtered if not is_yt_opportunity(o)]
    return filtered


def sort_opportunities(opportunities: List[YieldOpportunity], sort_by: str = "apy", ascending: bool = False) -> List[YieldOpportunity]:
    risk_order = {"Low": 0, "Medium": 1, "High": 2, "Very High": 3}
    keys = {"apy": lambda o: o.apy, "tvl": lambda o: o.tvl or 0,
            "risk": lambda o: risk_order.get(o.risk_score, 2),
            "chain": lambda o: o.chain.lower(), "protocol": lambda o: o.protocol.lower()}
    return sorted(opportunities, key=keys.get(sort_by.lower(), keys["apy"]), reverse=not ascending)


def format_apy(apy: float) -> str:
    if apy >= 100: return f"{apy:,.0f}%"
    elif apy >= 10: return f"{apy:.1f}%"
    return f"{apy:.2f}%"


def format_tvl(tvl: float) -> str:
    if not tvl: return "-"
    if tvl >= 1e9: return f"${tvl/1e9:.2f}B"
    if tvl >= 1e6: return f"${tvl/1e6:.2f}M"
    if tvl >= 1e3: return f"${tvl/1e3:.1f}K"
    return f"${tvl:.0f}"


# =============================================================================
# Main App
# =============================================================================

@st.cache_data(ttl=300, show_spinner=False)
def load_opportunities(categories: tuple = None) -> List[dict]:
    opps = fetch_opportunities(categories=list(categories) if categories else None, use_cache=True, stale_ok=True)
    return [o.to_dict() for o in opps]


def main():
    st.title("📈 Yield Terminal")
    st.markdown("*Find the best stablecoin yields across DeFi*")

    # Sidebar
    with st.sidebar:
        st.header("Filters")
        categories = list(SCRAPERS.keys())
        selected_categories = st.multiselect("Categories", options=categories, default=[])
        selected_chain = st.selectbox("Chain", options=["All Chains"] + SUPPORTED_CHAINS)
        stablecoin_filter = st.text_input("Stablecoin", placeholder="e.g., USDC")
        protocol_filter = st.text_input("Protocol", placeholder="e.g., Morpho")
        min_apy = st.number_input("Min APY (%)", min_value=0.0, max_value=1000.0, value=0.0, step=0.5)
        exclude_yt = st.checkbox("Exclude Yield Tokens (YT)", value=False)
        max_risk = st.selectbox("Max Risk", options=["Any", "Low", "Medium", "High", "Very High"])
        max_leverage_opts = {"Any": None, "1x (No Leverage)": 1.0, "Up to 2x": 2.0, "Up to 3x": 3.0, "Up to 5x": 5.0}
        max_leverage = max_leverage_opts[st.selectbox("Max Leverage", options=list(max_leverage_opts.keys()))]
        min_tvl_opts = {"Any": None, "$100K+": 1e5, "$1M+": 1e6, "$10M+": 1e7, "$100M+": 1e8}
        min_tvl = min_tvl_opts[st.selectbox("Min TVL", options=list(min_tvl_opts.keys()))]
        st.divider()
        sort_by = st.selectbox("Sort By", options=["APY", "TVL", "Risk", "Chain", "Protocol"]).lower()
        ascending = st.checkbox("Ascending Order", value=False)
        st.divider()
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # Load data
    with st.spinner("Loading yield opportunities..."):
        try:
            opp_dicts = load_opportunities(categories=tuple(selected_categories) if selected_categories else None)
            opportunities = [YieldOpportunity.from_dict(d) for d in opp_dicts]
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
            stablecoin=stablecoin_filter or None,
            protocol=protocol_filter or None,
            max_leverage=max_leverage,
            min_tvl=min_tvl,
            exclude_yt=exclude_yt,
        )
        opportunities = sort_opportunities(opportunities, sort_by=sort_by, ascending=ascending)

    # Stats
    if opportunities:
        apys = [o.apy for o in opportunities]
        tvls = [o.tvl for o in opportunities if o.tvl]
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        col1.metric("Opportunities", len(opportunities))
        col2.metric("Avg APY", f"{sum(apys)/len(apys):.1f}%")
        col3.metric("Max APY", f"{max(apys):.1f}%")
        col4.metric("Total TVL", format_tvl(sum(tvls)) if tvls else "-")
        col5.metric("Protocols", len(set(o.protocol for o in opportunities)))
        col6.metric("Chains", len(set(o.chain for o in opportunities)))

    st.divider()

    # Table
    if not opportunities:
        st.info("No opportunities found. Click 'Refresh Data' to fetch latest yields.")
    else:
        st.subheader(f"Yield Opportunities ({len(opportunities)} results)")

        table_data = [{
            "Category": o.category, "Protocol": o.protocol, "Chain": o.chain,
            "Stablecoin": ("🔶 " if is_yt_opportunity(o) else "") + o.stablecoin,
            "APY": o.apy, "TVL": o.tvl or 0, "Risk": o.risk_score,
            "Leverage": f"{o.leverage}x" if o.leverage > 1 else "-",
            "URL": o.source_url,
        } for o in opportunities]

        df = pd.DataFrame(table_data)
        df_display = df.copy()
        df_display["APY"] = df_display["APY"].apply(format_apy)
        df_display["TVL"] = df_display["TVL"].apply(format_tvl)

        st.dataframe(df_display.drop(columns=["URL"]), use_container_width=True, height=600, hide_index=True)

        # Detailed view with links
        with st.expander("View detailed data with links", expanded=False):
            for i, opp in enumerate(opportunities[:100]):
                cols = st.columns([4, 1])
                with cols[0]:
                    st.markdown(f"**{opp.protocol}** - {opp.stablecoin} on {opp.chain}")
                    st.caption(f"APY: {format_apy(opp.apy)} | TVL: {format_tvl(opp.tvl)} | Risk: {opp.risk_score}")
                with cols[1]:
                    if opp.source_url:
                        st.link_button("Open", opp.source_url, use_container_width=True)
                if i < min(99, len(opportunities) - 1):
                    st.divider()

    st.divider()
    st.caption(f"Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")


if __name__ == "__main__":
    main()
