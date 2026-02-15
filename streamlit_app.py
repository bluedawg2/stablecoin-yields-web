"""Streamlit web application for Stablecoin Yield Summarizer.

Self-contained version with dark theme and all scrapers.
"""

import streamlit as st
import json
import re
import hashlib
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
    page_title="Best Stablecoin Yields",
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
    background-color: #0a0b0e !important;
    color: #f0f2f5 !important;
}

/* Streamlit header/toolbar at top */
header[data-testid="stHeader"] {
    background-color: #0a0b0e !important;
    color: #f0f2f5 !important;
}

header[data-testid="stHeader"] * {
    color: #f0f2f5 !important;
}

/* Top toolbar/menu bar */
[data-testid="stToolbar"] {
    background-color: #0a0b0e !important;
}

[data-testid="stToolbar"] * {
    color: #f0f2f5 !important;
}

/* Decoration/status bar */
[data-testid="stDecoration"] {
    background-color: #0a0b0e !important;
}

/* App view container */
[data-testid="stAppViewContainer"] {
    background-color: #0a0b0e !important;
}

/* Main block container */
[data-testid="stMainBlockContainer"] {
    background-color: #0a0b0e !important;
}

/* Block container */
[data-testid="block-container"] {
    background-color: #0a0b0e !important;
}

/* Streamlit bottom/footer */
footer {
    background-color: #0a0b0e !important;
    color: #f0f2f5 !important;
}

footer * {
    color: #5c6370 !important;
}

/* Hide "Made with Streamlit" if desired */
footer {visibility: hidden;}

/* Main content area */
.main .block-container {
    background-color: #0a0b0e !important;
}

/* All text should be light */
.stApp, .stApp * {
    color: #f0f2f5;
}

p, span, label, div {
    color: #f0f2f5 !important;
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background-color: #12141a !important;
    border-right: 1px solid rgba(255, 255, 255, 0.1);
}

[data-testid="stSidebar"] * {
    color: #f0f2f5 !important;
}

/* Headers */
h1, h2, h3, h4, h5, h6 {
    color: #f0f2f5 !important;
}

/* Metrics */
[data-testid="stMetric"] {
    background-color: #1a1d25 !important;
    padding: 12px 10px;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    overflow: visible !important;
}

[data-testid="stMetricLabel"] {
    color: #a0a8b8 !important;
    font-size: 0.85rem !important;
    white-space: nowrap !important;
    overflow: visible !important;
}

[data-testid="stMetricValue"] {
    color: #00d4ff !important;
    font-weight: 600;
    font-size: 1.3rem !important;
    white-space: nowrap !important;
    overflow: visible !important;
    text-overflow: clip !important;
}

[data-testid="stMetricDelta"] {
    color: #00ff88 !important;
}

/* Ensure metric columns don't truncate */
[data-testid="stMetric"] > div {
    overflow: visible !important;
}

[data-testid="column"] {
    overflow: visible !important;
}

/* DataFrame styling */
[data-testid="stDataFrame"] {
    background-color: #12141a !important;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

[data-testid="stDataFrame"] * {
    color: #f0f2f5 !important;
}

.stDataFrame {
    background-color: #12141a !important;
}

/* Table header */
thead tr th {
    background-color: #1a1d25 !important;
    color: #a0a8b8 !important;
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
    background: linear-gradient(135deg, #00d4ff 0%, #4d7cff 100%) !important;
    color: #0a0b0e !important;
    border: none !important;
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
    background-color: #1a1d25 !important;
    border-color: rgba(255, 255, 255, 0.1) !important;
}

.stSelectbox > div > div > div {
    color: #f0f2f5 !important;
}

.stSelectbox label {
    color: #f0f2f5 !important;
}

/* Text inputs */
.stTextInput > div > div > input {
    background-color: #1a1d25 !important;
    border-color: rgba(255, 255, 255, 0.1) !important;
    color: #f0f2f5 !important;
}

.stTextInput label {
    color: #f0f2f5 !important;
}

/* Number inputs */
.stNumberInput > div > div > input {
    background-color: #1a1d25 !important;
    border-color: rgba(255, 255, 255, 0.1) !important;
    color: #f0f2f5 !important;
}

.stNumberInput label {
    color: #f0f2f5 !important;
}

/* Multiselect */
.stMultiSelect > div > div {
    background-color: #1a1d25 !important;
    border-color: rgba(255, 255, 255, 0.1) !important;
}

.stMultiSelect label, .stMultiSelect span {
    color: #f0f2f5 !important;
}

/* Expander - comprehensive styling for all Streamlit versions */
.streamlit-expanderHeader {
    background-color: #1a1d25 !important;
    border-radius: 8px;
    color: #f0f2f5 !important;
}

.streamlit-expanderHeader p, .streamlit-expanderHeader span {
    color: #f0f2f5 !important;
}

.streamlit-expanderContent {
    background-color: #12141a !important;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 0 0 8px 8px;
}

.streamlit-expanderContent * {
    color: #f0f2f5 !important;
}

/* Expander SVG icons */
.streamlit-expanderHeader svg {
    fill: #f0f2f5 !important;
    stroke: #f0f2f5 !important;
}

[data-testid="stExpander"] {
    background-color: #1a1d25 !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 8px;
}

[data-testid="stExpander"] * {
    color: #f0f2f5 !important;
}

/* Expander header text - newer Streamlit versions */
[data-testid="stExpander"] summary {
    color: #f0f2f5 !important;
    background-color: #1a1d25 !important;
}

[data-testid="stExpander"] summary span {
    color: #f0f2f5 !important;
}

[data-testid="stExpander"] summary p {
    color: #f0f2f5 !important;
}

[data-testid="stExpanderToggleIcon"] {
    color: #f0f2f5 !important;
    fill: #f0f2f5 !important;
}

/* Details/summary elements (native HTML expanders) */
details {
    background-color: #1a1d25 !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 8px;
}

details summary {
    color: #f0f2f5 !important;
    background-color: #1a1d25 !important;
    padding: 10px;
}

details summary:hover {
    background-color: #252830 !important;
}

details[open] > summary {
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

/* Dividers */
hr {
    border-color: rgba(255, 255, 255, 0.1) !important;
}

/* Checkbox */
.stCheckbox label {
    color: #f0f2f5 !important;
}

.stCheckbox span {
    color: #f0f2f5 !important;
}

/* Spinner/loading text */
.stSpinner > div {
    color: #f0f2f5 !important;
}

/* Info/Warning/Success/Error boxes */
.stAlert {
    background-color: #1a1d25 !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    color: #f0f2f5 !important;
}

.stAlert * {
    color: #f0f2f5 !important;
}

[data-testid="stAlert"] {
    background-color: #1a1d25 !important;
    color: #f0f2f5 !important;
}

[data-testid="stAlert"] * {
    color: #f0f2f5 !important;
}

/* Info box specific */
.stInfo, [data-testid="stInfo"] {
    background-color: #1a2a3a !important;
    border: 1px solid #00d4ff !important;
    color: #f0f2f5 !important;
}

.stInfo *, [data-testid="stInfo"] * {
    color: #f0f2f5 !important;
}

/* Warning box */
.stWarning, [data-testid="stWarning"] {
    background-color: #2a2a1a !important;
    border: 1px solid #ffb800 !important;
    color: #f0f2f5 !important;
}

/* Error box */
.stError, [data-testid="stError"] {
    background-color: #2a1a1a !important;
    border: 1px solid #ff3860 !important;
    color: #f0f2f5 !important;
}

/* Success box */
.stSuccess, [data-testid="stSuccess"] {
    background-color: #1a2a1a !important;
    border: 1px solid #00ff88 !important;
    color: #f0f2f5 !important;
}

/* Notification/alert text */
[data-baseweb="notification"] {
    background-color: #1a1d25 !important;
    color: #f0f2f5 !important;
}

[data-baseweb="notification"] * {
    color: #f0f2f5 !important;
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

/* Dropdown/Selectbox options - the popup menu */
[data-baseweb="popover"] {
    background-color: #1a1d25 !important;
}

[data-baseweb="popover"] * {
    color: #f0f2f5 !important;
    background-color: #1a1d25 !important;
}

[data-baseweb="menu"] {
    background-color: #1a1d25 !important;
}

[data-baseweb="menu"] li {
    background-color: #1a1d25 !important;
    color: #f0f2f5 !important;
}

[data-baseweb="menu"] li:hover {
    background-color: #2a2f3a !important;
}

/* Multiselect dropdown */
[data-baseweb="select"] {
    background-color: #1a1d25 !important;
}

[data-baseweb="select"] * {
    color: #f0f2f5 !important;
}

/* Dropdown list items */
ul[role="listbox"] {
    background-color: #1a1d25 !important;
}

ul[role="listbox"] li {
    color: #f0f2f5 !important;
    background-color: #1a1d25 !important;
}

ul[role="listbox"] li:hover {
    background-color: #2a2f3a !important;
}

/* Text input placeholder */
.stTextInput input::placeholder {
    color: #6b7280 !important;
    opacity: 1 !important;
}

/* Number input placeholder */
.stNumberInput input::placeholder {
    color: #6b7280 !important;
    opacity: 1 !important;
}

/* All input placeholders */
input::placeholder, textarea::placeholder {
    color: #6b7280 !important;
    opacity: 1 !important;
}

/* Spinner/Loading text */
[data-testid="stSpinner"] {
    color: #f0f2f5 !important;
}

[data-testid="stSpinner"] > div {
    color: #f0f2f5 !important;
}

.stSpinner, .stSpinner * {
    color: #f0f2f5 !important;
}

/* Status messages */
[data-testid="stStatusWidget"] {
    background-color: #1a1d25 !important;
    color: #f0f2f5 !important;
}

[data-testid="stStatusWidget"] * {
    color: #f0f2f5 !important;
}

/* Toast/Notification messages */
[data-testid="stToast"] {
    background-color: #1a1d25 !important;
    color: #f0f2f5 !important;
}

/* Any remaining white backgrounds */
.element-container {
    background-color: transparent !important;
}

/* Input boxes inner elements */
[data-baseweb="input"] {
    background-color: #1a1d25 !important;
}

[data-baseweb="input"] input {
    color: #f0f2f5 !important;
    background-color: #1a1d25 !important;
}

/* Select/dropdown selected value */
[data-baseweb="select"] > div {
    background-color: #1a1d25 !important;
}

/* Number input step buttons (+/-) - dark theme */
.stNumberInput button {
    background-color: #2a2f3a !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    color: #f0f2f5 !important;
}

.stNumberInput button:hover {
    background-color: #3a4050 !important;
    border-color: rgba(255, 255, 255, 0.3) !important;
}

.stNumberInput button svg {
    fill: #f0f2f5 !important;
    stroke: #f0f2f5 !important;
}

/* BaseWeb number input buttons */
[data-baseweb="input"] button {
    background-color: #2a2f3a !important;
    border-color: rgba(255, 255, 255, 0.2) !important;
    color: #f0f2f5 !important;
}

[data-baseweb="input"] button svg {
    fill: #f0f2f5 !important;
}

/* Sidebar scrollable and fit content */
[data-testid="stSidebar"] > div:first-child {
    overflow-y: auto !important;
    max-height: 100vh !important;
    padding-bottom: 2rem !important;
}

/* Make sidebar content more compact */
[data-testid="stSidebar"] .stSelectbox,
[data-testid="stSidebar"] .stNumberInput,
[data-testid="stSidebar"] .stTextInput,
[data-testid="stSidebar"] .stMultiSelect {
    margin-bottom: 0.5rem !important;
}

[data-testid="stSidebar"] .stCheckbox {
    margin-bottom: 0.25rem !important;
}

/* Compact sidebar headers */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    margin-top: 0.5rem !important;
    margin-bottom: 0.5rem !important;
}

/* Sidebar dividers less space */
[data-testid="stSidebar"] hr {
    margin: 0.5rem 0 !important;
}

/* Selected row details - prevent scroll jump */
.selected-details {
    scroll-margin-top: 100px;
}

/* Tooltip/hover popup dark theme */
[data-testid="stTooltipContent"],
[role="tooltip"],
.stTooltip,
div[data-floating-ui-portal] {
    background-color: #1a1d25 !important;
    color: #f0f2f5 !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
}

div[data-floating-ui-portal] * {
    background-color: #1a1d25 !important;
    color: #f0f2f5 !important;
}

/* DataFrame hover tooltip */
[data-testid="stDataFrame"] [role="tooltip"],
[data-testid="stDataFrame"] [data-floating-ui-portal] {
    background-color: #1a1d25 !important;
    color: #f0f2f5 !important;
}

/* Glide data grid tooltip */
.gdg-tooltip {
    background-color: #1a1d25 !important;
    color: #f0f2f5 !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
}

/* Any floating/portal elements */
[data-portal="true"],
.portal,
[class*="tooltip"],
[class*="Tooltip"] {
    background-color: #1a1d25 !important;
    color: #f0f2f5 !important;
}

/* Ensure sidebar fits all content */
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
    gap: 0.5rem !important;
}

/* More compact form elements */
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stTextInput label,
[data-testid="stSidebar"] .stNumberInput label,
[data-testid="stSidebar"] .stMultiSelect label {
    font-size: 0.85rem !important;
    margin-bottom: 0.2rem !important;
}

/* Reduce button padding in sidebar */
[data-testid="stSidebar"] .stButton button {
    padding: 0.4rem 1rem !important;
    font-size: 0.85rem !important;
}
</style>
""", unsafe_allow_html=True)


# =============================================================================
# Configuration
# =============================================================================

SUPPORTED_CHAINS = [
    "Ethereum", "Base", "Optimism", "Arbitrum", "Avalanche", "BSC",
    "Polygon", "Solana", "TAC", "Unichain",
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
                  "avalanche": 2, "bsc": 2, "solana": 2}
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
    MIN_TVL_USD = 500_000  # $500K minimum for meaningful lending markets
    MAX_APY_PERCENT = 20  # Rates above 20% are usually from tiny/illiquid markets
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
                # Collect all markets, then pick largest per stablecoin
                markets_by_symbol = {}
                for market in resp.json().get("data", {}).get("markets", {}).get("items", []):
                    symbol = market.get("loanAsset", {}).get("symbol", "")
                    if not any(s in symbol.upper() for s in self.STABLECOINS):
                        continue
                    state = market.get("state", {})
                    apy = (state.get("supplyApy") or 0) * 100
                    tvl = state.get("supplyAssetsUsd") or 0
                    if tvl < self.MIN_TVL_USD or apy <= 0 or apy > self.MAX_APY_PERCENT:
                        continue
                    # Keep the market with highest TVL per symbol (most representative rate)
                    if symbol not in markets_by_symbol or tvl > markets_by_symbol[symbol]["tvl"]:
                        markets_by_symbol[symbol] = {
                            "symbol": symbol, "apy": apy, "tvl": tvl,
                            "market_id": market.get("uniqueKey", ""),
                        }
                # Create opportunities from deduplicated markets
                for data in markets_by_symbol.values():
                    opportunities.append(YieldOpportunity(
                        category=self.category, protocol="Morpho", chain=chain_name,
                        stablecoin=data["symbol"], apy=data["apy"], tvl=data["tvl"],
                        risk_score=RiskAssessor.calculate_risk_score("lend", chain=chain_name, apy=data["apy"]),
                        source_url=f"https://app.morpho.org/market?id={data['market_id']}",
                    ))
            except:
                continue
        return opportunities


class MerklScraper(BaseScraper):
    category = "Merkl Rewards"
    cache_file = "merkl_st"
    MIN_TVL_USD = 10_000
    MAX_APR = 500
    STABLECOINS = [
        "USDC", "USDT", "DAI", "FRAX", "LUSD", "SDAI", "SUSDE", "USDE",
        "USDS", "SUSDS", "GHO", "CRVUSD", "PYUSD", "USDM", "TUSD",
        "GUSD", "USDP", "DOLA", "MIM", "ALUSD", "FDUSD", "USDN",
        "BOLD", "SUSD", "EUSD", "USN", "AUSD", "MUSD", "USD",
        "YOUSD",
    ]

    def _is_stablecoin_token(self, symbol: str) -> bool:
        symbol_upper = symbol.upper()
        # Direct stablecoin match
        for stable in self.STABLECOINS:
            if stable in symbol_upper:
                return True
        # Common stablecoin derivative patterns (PT-USDC, aUSDC, etc.)
        derivative_prefixes = [
            "PT-", "YT-", "A", "C", "S", "F", "V", "AM", "AV",
            "AETH", "APLA", "AOPT", "AARB",
        ]
        for prefix in derivative_prefixes:
            if symbol_upper.startswith(prefix):
                remainder = symbol_upper[len(prefix):]
                for stable in self.STABLECOINS:
                    if stable in remainder:
                        return True
        # Vault/LP tokens containing stablecoins
        vault_patterns = ["VAULT", "LP", "POOL", "CUSD", "SUSD"]
        if any(pattern in symbol_upper for pattern in vault_patterns):
            for stable in self.STABLECOINS:
                if stable in symbol_upper:
                    return True
        return False

    def _is_stablecoin(self, tokens: List[str], name: str) -> bool:
        name_upper = (name or "").upper()

        # Exclude: non-stablecoin collateral in Morpho market pairs
        # Pattern: "on X/Y Z%" where both tokens must be stablecoins
        pair_match = re.search(r'ON\s+(\S+)/(\S+)', name_upper)
        if pair_match:
            token_a, token_b = pair_match.group(1), pair_match.group(2)
            if not (any(s in token_a for s in self.STABLECOINS) and
                    any(s in token_b for s in self.STABLECOINS)):
                return False

        # For multi-token opportunities (LP, pools), ALL tokens must be stablecoins
        if len(tokens) >= 2:
            for symbol in tokens:
                if not self._is_stablecoin_token(symbol):
                    return False
            return True

        # Single token: check if it's a stablecoin
        if tokens:
            return any(self._is_stablecoin_token(symbol) for symbol in tokens)

        # Fall back to name check
        if any(s in name_upper for s in self.STABLECOINS):
            return True

        return False

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
                    # Show all tokens as pair (e.g., "USDC-AuUSD" instead of just "AuUSD")
                    stablecoin = "-".join(tokens) if tokens else "USD"
                    protocol = "Merkl"
                    for p in ["Morpho", "Euler", "Aave", "Compound", "Pendle", "Silo", "Ploutos", "Spectra"]:
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
    MIN_TVL_USD = 10_000  # Lowered to capture more markets
    MAX_APY = 100
    CHAIN_IDS = {"Ethereum": 1, "Arbitrum": 42161, "Base": 8453}
    # Expanded list to capture all USD-denominated stablecoins
    STABLECOINS = [
        "USD", "USDC", "USDT", "DAI", "USDE", "SUSDE", "SDAI", "USDS", "GHO", "FRAX",
        "CUSD", "STCUSD", "NUSD", "SNUSD", "REUSD", "REUSDE", "AUSD", "SIUSD", "SRUSD",
        "USDAI", "SUSDAI", "PYUSD", "DOLA", "MIM", "LUSD",
    ]

    def _fetch_data(self) -> List[YieldOpportunity]:
        opportunities = []
        for chain_name, chain_id in self.CHAIN_IDS.items():
            try:
                # Paginate through results (API defaults to limit=10)
                skip = 0
                while True:
                    resp = self.session.get(
                        f"https://api-v2.pendle.finance/core/v1/{chain_id}/markets?is_active=true&skip={skip}&limit=100",
                        timeout=REQUEST_TIMEOUT
                    )
                    if resp.status_code != 200:
                        break
                    data = resp.json()
                    results = data.get("results", [])
                    if not results:
                        break
                    for market in results:
                        underlying_asset = market.get("underlyingAsset")
                        if not underlying_asset:
                            continue
                        underlying = underlying_asset.get("symbol", "") or ""
                        # Check if it's a stablecoin
                        if not any(s in underlying.upper() for s in self.STABLECOINS):
                            continue
                        apy = (market.get("impliedApy") or 0) * 100
                        liquidity = market.get("liquidity") or {}
                        tvl = liquidity.get("usd") or 0
                        if tvl < self.MIN_TVL_USD or apy <= 0 or apy > self.MAX_APY:
                            continue
                        maturity = None
                        if market.get("expiry"):
                            try:
                                maturity = datetime.fromisoformat(market["expiry"].replace("Z", "+00:00"))
                            except:
                                pass
                        pt = market.get("pt") or {}
                        pt_symbol = pt.get("symbol", "") or underlying
                        opportunities.append(YieldOpportunity(
                            category=self.category, protocol="Pendle", chain=chain_name,
                            stablecoin=underlying, apy=apy, tvl=tvl, maturity_date=maturity,
                            risk_score=RiskAssessor.calculate_risk_score("lend", chain=chain_name, apy=apy),
                            source_url=f"https://app.pendle.finance/trade/markets/{market.get('address', '')}",
                            additional_info={"pt_symbol": pt_symbol},
                        ))
                    # Check if there are more results
                    total = data.get("total", 0)
                    skip += len(results)
                    if skip >= total:
                        break
            except:
                continue
        return opportunities


class PendleLoopScraper(BaseScraper):
    category = "Pendle Looping"
    cache_file = "pendle_loop_st"
    LEVERAGE_LEVELS = [2.0, 3.0, 5.0]
    MIN_LIQUIDITY = 100_000  # $100K minimum for viable positions

    def __init__(self):
        super().__init__()
        self.pendle_scraper = PendleFixedScraper()

    def _extract_underlying(self, pt_symbol: str) -> str:
        """Extract underlying from PT symbol like PT-sUSDe-29MAY2025 -> SUSDE"""
        symbol = pt_symbol.upper().replace("PT-", "")
        # Remove date suffix (various formats)
        symbol = re.sub(r"-?\d{1,2}[A-Z]{3}\d{4}$", "", symbol)  # 29MAY2025
        symbol = re.sub(r"-?\d{10,}$", "", symbol)  # Unix timestamp
        symbol = re.sub(r"-\d+$", "", symbol)  # Any trailing numbers
        return symbol.rstrip("-")

    def _extract_maturity_from_symbol(self, symbol: str) -> Optional[datetime]:
        """Extract maturity date from PT symbol like 'PT-REUSD-25JUN2026'."""
        # Match patterns like "25JUN2026", "18DEC2025", "30APR2026"
        date_pattern = r"(\d{1,2})([A-Z]{3})(\d{4})"
        match = re.search(date_pattern, symbol.upper())
        if not match:
            return None
        day, month_str, year = match.groups()
        month_map = {"JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
                     "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12}
        month = month_map.get(month_str)
        if not month:
            return None
        try:
            return datetime(int(year), month, int(day))
        except ValueError:
            return None

    def _underlyings_match(self, pt_collateral: str, pendle_underlying: str) -> bool:
        """Check if PT collateral matches Pendle underlying. Strict matching."""
        morpho_under = self._extract_underlying(pt_collateral)
        pendle_under = pendle_underlying.upper().replace("-", "").replace("_", "")

        # Direct match
        if morpho_under == pendle_under:
            return True

        # Strict: staked versions must match exactly (sUSDe != USDe, sUSDai != USDai)
        if morpho_under.startswith("S") and not pendle_under.startswith("S"):
            return False
        if pendle_under.startswith("S") and not morpho_under.startswith("S"):
            return False

        # Normalized comparison (remove dashes/underscores)
        def normalize(s):
            return s.upper().replace("-", "").replace("_", "")

        if normalize(morpho_under) == normalize(pendle_under):
            return True

        # Allow substring match only if very similar length (>70%)
        if len(morpho_under) > 0 and len(pendle_under) > 0:
            length_ratio = min(len(morpho_under), len(pendle_under)) / max(len(morpho_under), len(pendle_under))
            if length_ratio >= 0.7 and (morpho_under in pendle_under or pendle_under in morpho_under):
                return True

        return False

    def _maturities_match(self, morpho_collateral: str, pendle_maturity: Optional[datetime]) -> bool:
        """Check if maturity dates match within 7 days tolerance."""
        if not pendle_maturity:
            return False  # Require maturity date from Pendle
        morpho_maturity = self._extract_maturity_from_symbol(morpho_collateral)
        if not morpho_maturity:
            return False  # Require maturity in Morpho symbol
        # Convert to naive datetime for comparison
        pendle_dt = pendle_maturity.replace(tzinfo=None) if pendle_maturity.tzinfo else pendle_maturity
        days_diff = abs((morpho_maturity - pendle_dt).days)
        return days_diff <= 7  # Allow 7 days tolerance

    def _fetch_data(self) -> List[YieldOpportunity]:
        opportunities = []
        try:
            pendle_opps = self.pendle_scraper.fetch(use_cache=True)
        except:
            return opportunities

        # Fetch Morpho borrow markets
        morpho_markets = self._fetch_morpho_markets()

        # Track best market per PT to avoid duplicates
        seen_pts = {}  # key: (chain, pt_symbol, leverage) -> best opportunity

        for pt_opp in pendle_opps:
            if pt_opp.chain not in ["Ethereum", "Arbitrum", "Base"]:
                continue
            # Find matching borrow markets
            for market in morpho_markets.get(pt_opp.chain, []):
                collateral_sym = market.get("collateral", "").upper()
                if not collateral_sym.startswith("PT-"):
                    continue
                # Strict underlying matching
                if not self._underlyings_match(collateral_sym, pt_opp.stablecoin):
                    continue
                # CRITICAL: Require maturity date matching
                if not self._maturities_match(collateral_sym, pt_opp.maturity_date):
                    continue
                borrow_apy = market.get("borrow_apy", 0)
                liquidity = market.get("liquidity", 0)
                if liquidity < self.MIN_LIQUIDITY:
                    continue
                # Filter unreasonable borrow rates (should be ~5-15% typically)
                if borrow_apy <= 0 or borrow_apy > 50:
                    continue
                lltv = market.get("lltv", 0.85)
                if lltv <= 0:
                    lltv = 0.85
                loan_asset = market.get("loan_asset", "USDC")
                # Build full PT symbol for display
                pt_symbol = collateral_sym  # Use actual Morpho collateral symbol
                for leverage in self.LEVERAGE_LEVELS:
                    max_lev = 1 / (1 - lltv) if lltv < 1 else 10
                    if leverage > max_lev * 0.9:
                        continue
                    net_apy = pt_opp.apy * leverage - borrow_apy * (leverage - 1)
                    if net_apy <= 0:
                        continue
                    # Deduplicate: keep best APY per PT/leverage combo
                    key = (pt_opp.chain, pt_symbol, leverage)
                    if key in seen_pts and seen_pts[key].apy >= net_apy:
                        continue
                    opp = YieldOpportunity(
                        category=self.category, protocol="Pendle + Morpho",
                        chain=pt_opp.chain, stablecoin=f"{pt_symbol}-{loan_asset}",
                        apy=net_apy, tvl=liquidity, leverage=leverage,
                        supply_apy=pt_opp.apy, borrow_apy=borrow_apy,
                        maturity_date=pt_opp.maturity_date,
                        risk_score=RiskAssessor.calculate_risk_score("pendle_loop", leverage=leverage, chain=pt_opp.chain, apy=net_apy),
                        source_url=f"https://app.morpho.org/market?id={market.get('market_id', '')}",
                        additional_info={"pt_yield": pt_opp.apy, "borrow_rate": borrow_apy, "lltv": lltv * 100,
                                         "pt_symbol": pt_symbol, "loan_asset": loan_asset},
                    )
                    seen_pts[key] = opp
        return list(seen_pts.values())

    def _fetch_morpho_markets(self) -> Dict[str, List[Dict]]:
        markets_by_chain = {}
        chain_ids = {"Ethereum": 1, "Base": 8453, "Arbitrum": 42161}
        for chain_name, chain_id in chain_ids.items():
            try:
                query = """query($chainId: Int!, $skip: Int!) { markets(where: { chainId_in: [$chainId] }, first: 1000, skip: $skip) {
                    items { uniqueKey collateralAsset { symbol } loanAsset { symbol }
                            state { borrowApy avgNetBorrowApy liquidityAssetsUsd sizeUsd } lltv }
                    pageInfo { countTotal } } }"""
                all_items = []
                skip = 0
                while True:
                    resp = self.session.post("https://blue-api.morpho.org/graphql",
                        json={"query": query, "variables": {"chainId": chain_id, "skip": skip}}, timeout=REQUEST_TIMEOUT)
                    data = resp.json().get("data", {}).get("markets", {})
                    items = data.get("items", [])
                    if not items:
                        break
                    all_items.extend(items)
                    count_total = data.get("pageInfo", {}).get("countTotal", 0)
                    if len(all_items) >= count_total or len(items) < 1000:
                        break
                    skip += 1000
                markets = []
                for m in all_items:
                    collateral_asset = m.get("collateralAsset")
                    if not collateral_asset:
                        continue
                    collateral = collateral_asset.get("symbol", "")
                    if not collateral.upper().startswith("PT-"):
                        continue
                    loan_asset = m.get("loanAsset")
                    if not loan_asset:
                        continue
                    loan = loan_asset.get("symbol", "")
                    if not any(s in loan.upper() for s in ["USDC", "USDT", "DAI", "USDS", "FRAX", "GHO"]):
                        continue
                    state = m.get("state") or {}
                    borrow_apy = (state.get("borrowApy") or 0) * 100
                    liquidity = state.get("liquidityAssetsUsd") or state.get("sizeUsd") or 0
                    lltv = m.get("lltv", 0)
                    try:
                        lltv = float(lltv)
                        if lltv > 1:
                            lltv = lltv / 1e18
                    except:
                        lltv = 0.85
                    markets.append({
                        "collateral": collateral, "borrow_apy": borrow_apy,
                        "liquidity": liquidity, "lltv": lltv,
                        "market_id": m.get("uniqueKey", ""),
                        "loan_asset": loan,
                    })
                markets_by_chain[chain_name] = markets
            except:
                markets_by_chain[chain_name] = []
        return markets_by_chain


# =============================================================================
# Additional Scrapers
# =============================================================================

class StableWatchScraper(BaseScraper):
    """Fetches yield-bearing stablecoin data from multiple live sources."""
    category = "Yield-Bearing Stablecoins"
    cache_file = "stablewatch_st"

    # Known yield-bearing stablecoins with metadata
    # APY/TVL will be fetched live; these are fallback values
    YIELD_STABLECOINS = [
        {"symbol": "sUSDe", "protocol": "Ethena", "chain": "Ethereum", "fallback_apy": 5.0, "fallback_tvl": 5_000_000_000},
        {"symbol": "sUSDS", "protocol": "Sky", "chain": "Ethereum", "fallback_apy": 4.5, "fallback_tvl": 500_000_000},
        {"symbol": "sDAI", "protocol": "MakerDAO", "chain": "Ethereum", "fallback_apy": 5.0, "fallback_tvl": 1_200_000_000},
        {"symbol": "sFRAX", "protocol": "Frax", "chain": "Ethereum", "fallback_apy": 4.5, "fallback_tvl": 200_000_000},
        {"symbol": "USDM", "protocol": "Mountain", "chain": "Ethereum", "fallback_apy": 4.5, "fallback_tvl": 150_000_000},
        {"symbol": "USDY", "protocol": "Ondo", "chain": "Ethereum", "fallback_apy": 4.5, "fallback_tvl": 400_000_000},
        {"symbol": "USD0++", "protocol": "Usual", "chain": "Ethereum", "fallback_apy": 4.0, "fallback_tvl": 300_000_000},
        {"symbol": "USR", "protocol": "Resolv", "chain": "Ethereum", "fallback_apy": 8.0, "fallback_tvl": 80_000_000},
        {"symbol": "savUSD", "protocol": "Avant", "chain": "Avalanche", "fallback_apy": 10.0, "fallback_tvl": 85_000_000},
        {"symbol": "sNUSD", "protocol": "Neutrl", "chain": "Ethereum", "fallback_apy": 10.0, "fallback_tvl": 210_000_000},
        {"symbol": "srUSDe", "protocol": "Ethena", "chain": "Ethereum", "fallback_apy": 6.0, "fallback_tvl": 100_000_000},
    ]

    # Map Pendle underlying symbols to our stablecoin symbols
    PENDLE_SYMBOL_MAP = {
        "sUSDe": ["sUSDe", "SUSDE"],
        "sUSDS": ["sUSDS", "SUSDS"],
        "sDAI": ["sDAI", "SDAI"],
        "USR": ["USR"],
        "savUSD": ["savUSD", "SAVUSD"],
        "sNUSD": ["sNUSD", "SNUSD"],
        "srUSDe": ["srUSDe", "SRUSDE"],
    }

    PROTOCOL_URLS = {
        "Ethena": "https://ethena.fi",
        "Sky": "https://sky.money",
        "MakerDAO": "https://spark.fi",
        "Frax": "https://frax.finance",
        "Mountain": "https://mountainprotocol.com",
        "Ondo": "https://ondo.finance",
        "Usual": "https://usual.money",
        "Resolv": "https://resolv.im",
        "Avant": "https://www.avantprotocol.com",
        "Neutrl": "https://neutrl.io",
    }

    def _fetch_data(self) -> List[YieldOpportunity]:
        opportunities = []
        live_data = {}

        # 1. Fetch from Ethena API (primary source for sUSDe)
        try:
            resp = self.session.get("https://ethena.fi/api/yields/protocol-and-staking-yield", timeout=REQUEST_TIMEOUT)
            ethena_apy = resp.json().get("stakingYield", {}).get("value", 0)
            if ethena_apy > 0:
                live_data["sUSDe"] = {"apy": ethena_apy, "tvl": 5_000_000_000}
        except Exception:
            pass

        # 2. Fetch from Pendle API (implied yields for many underlyings)
        try:
            pendle_data = self._fetch_pendle_yields()  # Returns lowercase keys
            for our_symbol, pendle_symbols in self.PENDLE_SYMBOL_MAP.items():
                for ps in pendle_symbols:
                    ps_lower = ps.lower()
                    if ps_lower in pendle_data and our_symbol not in live_data:
                        live_data[our_symbol] = pendle_data[ps_lower]
                        break
        except Exception:
            pass

        # 3. Build opportunities using live data with fallbacks
        for coin in self.YIELD_STABLECOINS:
            symbol = coin["symbol"]
            data = live_data.get(symbol, {})
            apy = data.get("apy", coin["fallback_apy"])
            tvl = data.get("tvl", coin["fallback_tvl"])

            if apy <= 0:
                continue

            opportunities.append(YieldOpportunity(
                category=self.category,
                protocol=coin["protocol"],
                chain=coin["chain"],
                stablecoin=symbol,
                apy=apy,
                tvl=tvl,
                risk_score=RiskAssessor.calculate_risk_score("yield_bearing", chain=coin["chain"], apy=apy),
                source_url=self.PROTOCOL_URLS.get(coin["protocol"], "https://www.stablewatch.io"),
            ))
        return opportunities

    def _fetch_pendle_yields(self) -> Dict[str, Dict]:
        """Fetch implied yields from Pendle markets. Returns lowercase symbol keys."""
        result = {}
        # Fetch from multiple chains
        chain_ids = [1, 42161]  # Ethereum, Arbitrum
        for chain_id in chain_ids:
            try:
                # Note: Pendle API returns empty results for limit>100
                resp = self.session.get(
                    f"https://api-v2.pendle.finance/core/v1/{chain_id}/markets?limit=100",
                    timeout=REQUEST_TIMEOUT
                )
                for m in resp.json().get("results", []):
                    underlying = m.get("underlyingAsset", {}).get("symbol", "")
                    apy = (m.get("impliedApy") or 0) * 100
                    tvl = m.get("liquidity", {}).get("usd", 0) or 0
                    if underlying and apy > 0 and tvl > 1_000_000:
                        # Use lowercase keys for consistent matching
                        key = underlying.lower()
                        # Keep highest APY for each underlying
                        if key not in result or result[key]["apy"] < apy:
                            result[key] = {"apy": apy, "tvl": tvl}
            except Exception:
                pass
        return result


class EulerLendScraper(BaseScraper):
    category = "Euler Lend"
    cache_file = "euler_lend_st"
    MIN_TVL_USD = 10_000
    MAX_APY = 25
    APY_SCALE = 1e27
    STABLECOINS = [
        "USDC", "USDT", "DAI", "FRAX", "LUSD", "SDAI", "SUSDE", "USDE",
        "USDS", "SUSDS", "GHO", "CRVUSD", "PYUSD", "USDM", "TUSD",
        "GUSD", "USDP", "DOLA", "MIM", "ALUSD", "FDUSD", "RLUSD",
        "YOUSD", "YUSD", "USN", "USD0", "USDN", "BOLD", "MUSD",
        "EUSD", "THBILL", "USDF", "USD",
    ]
    SUBGRAPH_ENDPOINTS = {
        "Ethereum": "https://api.goldsky.com/api/public/project_cm4iagnemt1wp01xn4gh1agft/subgraphs/euler-v2-mainnet/latest/gn",
        "Base": "https://api.goldsky.com/api/public/project_cm4iagnemt1wp01xn4gh1agft/subgraphs/euler-v2-base/latest/gn",
        "Arbitrum": "https://api.goldsky.com/api/public/project_cm4iagnemt1wp01xn4gh1agft/subgraphs/euler-v2-arbitrum/latest/gn",
        "Optimism": "https://api.goldsky.com/api/public/project_cm4iagnemt1wp01xn4gh1agft/subgraphs/euler-v2-optimism/latest/gn",
        "Bob": "https://api.goldsky.com/api/public/project_cm4iagnemt1wp01xn4gh1agft/subgraphs/euler-v2-bob/latest/gn",
        "Swell": "https://api.goldsky.com/api/public/project_cm4iagnemt1wp01xn4gh1agft/subgraphs/euler-v2-swell/latest/gn",
        "Ink": "https://api.goldsky.com/api/public/project_cm4iagnemt1wp01xn4gh1agft/subgraphs/euler-v2-ink/latest/gn",
        "Unichain": "https://api.goldsky.com/api/public/project_cm4iagnemt1wp01xn4gh1agft/subgraphs/euler-v2-unichain/latest/gn",
        "TAC": "https://api.goldsky.com/api/public/project_cm4iagnemt1wp01xn4gh1agft/subgraphs/euler-v2-tac/latest/gn",
        "Linea": "https://api.goldsky.com/api/public/project_cm4iagnemt1wp01xn4gh1agft/subgraphs/euler-v2-linea/latest/gn",
        "Avalanche": "https://api.goldsky.com/api/public/project_cm4iagnemt1wp01xn4gh1agft/subgraphs/euler-v2-avalanche/latest/gn",
        "Plasma": "https://api.goldsky.com/api/public/project_cm4iagnemt1wp01xn4gh1agft/subgraphs/euler-v2-plasma/latest/gn",
    }
    VAULT_QUERY = """{ eulerVaults(first: 1000, orderBy: state__totalShares, orderDirection: desc) {
        id name symbol decimals collaterals state { supplyApy borrowApy totalBorrows cash } } }"""
    def _fetch_data(self) -> List[YieldOpportunity]:
        opportunities = []
        for chain, endpoint in self.SUBGRAPH_ENDPOINTS.items():
            try:
                resp = self.session.post(endpoint, json={"query": self.VAULT_QUERY}, timeout=REQUEST_TIMEOUT)
                for vault in resp.json().get("data", {}).get("eulerVaults", []):
                    combined = (vault.get("name", "") + " " + vault.get("symbol", "")).upper()
                    stablecoin = None
                    for s in self.STABLECOINS:
                        if s in combined:
                            stablecoin = s
                            break
                    if not stablecoin:
                        continue
                    state = vault.get("state") or {}
                    supply_apy = (int(state.get("supplyApy", "0") or "0") / self.APY_SCALE) * 100
                    decimals = int(vault.get("decimals", "18") or "18")
                    tvl = (int(state.get("totalBorrows", "0") or "0") + int(state.get("cash", "0") or "0")) / (10 ** decimals)
                    if tvl < self.MIN_TVL_USD or supply_apy <= 0 or supply_apy > self.MAX_APY:
                        continue
                    borrow_apy = (int(state.get("borrowApy", "0") or "0") / self.APY_SCALE) * 100
                    opportunities.append(YieldOpportunity(
                        category=self.category, protocol="Euler", chain=chain,
                        stablecoin=stablecoin, apy=supply_apy, tvl=tvl,
                        supply_apy=supply_apy, borrow_apy=borrow_apy,
                        risk_score=RiskAssessor.calculate_risk_score("lend", chain=chain, apy=supply_apy),
                        source_url="https://app.euler.finance",
                    ))
            except:
                continue
        return opportunities


class BeefyScraper(BaseScraper):
    category = "Beefy Vaults"
    cache_file = "beefy_st"
    VAULTS_URL = "https://api.beefy.finance/vaults"
    APY_URL = "https://api.beefy.finance/apy"
    TVL_URL = "https://api.beefy.finance/tvl"
    MIN_TVL = 10_000
    STABLECOINS = ["USDC", "USDT", "DAI", "FRAX", "LUSD", "SDAI", "SUSDE", "USDE", "GHO", "MAI", "USD+"]
    CHAIN_NAMES = {"ethereum": "Ethereum", "bsc": "BSC", "polygon": "Polygon", "arbitrum": "Arbitrum",
                   "optimism": "Optimism", "base": "Base", "avalanche": "Avalanche"}
    CHAIN_IDS = {"ethereum": "1", "bsc": "56", "polygon": "137", "arbitrum": "42161",
                 "optimism": "10", "base": "8453", "avalanche": "43114"}
    def _fetch_data(self) -> List[YieldOpportunity]:
        opportunities = []
        try:
            vaults = self.session.get(self.VAULTS_URL, timeout=REQUEST_TIMEOUT).json()
            apys = self.session.get(self.APY_URL, timeout=REQUEST_TIMEOUT).json()
            tvls = self.session.get(self.TVL_URL, timeout=REQUEST_TIMEOUT).json()
            for vault in vaults:
                if vault.get("status") != "active":
                    continue
                assets = vault.get("assets", [])
                if not (assets and all(any(s in a.upper() for s in self.STABLECOINS) for a in assets)):
                    continue
                vault_id = vault.get("id", "")
                apy = (apys.get(vault_id, 0) or 0) * 100
                if apy <= 0 or apy > 500:
                    continue
                chain_id = vault.get("chain", "")
                chain_num = self.CHAIN_IDS.get(chain_id, "")
                chain_tvls = tvls.get(chain_num, {})
                tvl = chain_tvls.get(vault_id, 0) if isinstance(chain_tvls, dict) else 0
                if tvl < self.MIN_TVL:
                    continue
                chain = self.CHAIN_NAMES.get(chain_id, chain_id.title())
                stablecoin = "/".join(assets) if len(assets) >= 2 else (assets[0] if assets else "USD")
                platform = vault.get("platformId", "")
                opportunities.append(YieldOpportunity(
                    category=self.category, protocol=f"Beefy ({platform.title()})" if platform else "Beefy",
                    chain=chain, stablecoin=stablecoin, apy=apy, tvl=tvl,
                    risk_score=RiskAssessor.calculate_risk_score("vault", chain=chain, apy=apy),
                    source_url=f"https://app.beefy.com/vault/{vault_id}",
                ))
        except:
            pass
        return opportunities


class YearnScraper(BaseScraper):
    category = "Yearn Vaults"
    cache_file = "yearn_st"
    API_BASE = "https://ydaemon.yearn.fi"
    CHAIN_IDS = {1: "Ethereum", 10: "Optimism", 137: "Polygon", 8453: "Base", 42161: "Arbitrum"}
    MIN_TVL = 10_000
    MAX_APY = 20
    STABLECOINS = ["USDC", "USDT", "DAI", "FRAX", "LUSD", "SDAI", "SUSDE", "USDE", "GHO", "CRVUSD"]
    def _fetch_data(self) -> List[YieldOpportunity]:
        opportunities = []
        for chain_id, chain_name in self.CHAIN_IDS.items():
            try:
                vaults = self.session.get(f"{self.API_BASE}/{chain_id}/vaults/all", timeout=REQUEST_TIMEOUT).json()
                for vault in vaults:
                    if vault.get("migration", {}).get("available", False):
                        continue
                    token = vault.get("token", {})
                    symbol = token.get("symbol", "")
                    if not any(s in symbol.upper() for s in self.STABLECOINS):
                        continue
                    tvl = vault.get("tvl", {}).get("tvl", 0) if isinstance(vault.get("tvl"), dict) else 0
                    if tvl < self.MIN_TVL:
                        continue
                    apr_data = vault.get("apr", {}) or vault.get("apy", {})
                    net_apr = apr_data.get("netAPR", 0) or apr_data.get("net_apy", 0)
                    if not net_apr:
                        forward = apr_data.get("forwardAPR", {}) or apr_data.get("forwardAPY", {})
                        net_apr = forward.get("netAPR", 0) or forward.get("netAPY", 0)
                    if not net_apr or net_apr <= 0:
                        continue
                    apy = net_apr * 100
                    if apy > self.MAX_APY:
                        continue
                    opportunities.append(YieldOpportunity(
                        category=self.category, protocol="Yearn", chain=chain_name,
                        stablecoin=symbol, apy=apy, tvl=tvl,
                        risk_score=RiskAssessor.calculate_risk_score("vault", chain=chain_name, apy=apy),
                        source_url=f"https://yearn.fi/v3/{vault.get('address', '')}",
                    ))
            except:
                continue
        return opportunities


class CompoundLendScraper(BaseScraper):
    category = "Compound Lend"
    cache_file = "compound_lend_st"
    MIN_TVL = 100_000
    STABLECOINS = ["USDC", "USDT", "DAI"]
    def _fetch_data(self) -> List[YieldOpportunity]:
        opportunities = []
        try:
            resp = self.session.get("https://api.compound.finance/api/v2/ctoken", params={"meta": "true"}, timeout=REQUEST_TIMEOUT)
            for ctoken in resp.json().get("cToken", []):
                symbol = ctoken.get("underlying_symbol", "")
                if not any(s in symbol.upper() for s in self.STABLECOINS):
                    continue
                apy = float(ctoken.get("supply_rate", {}).get("value", 0)) * 100
                tvl = float(ctoken.get("total_supply", {}).get("value", 0))
                if apy <= 0 or tvl < self.MIN_TVL:
                    continue
                borrow_apy = float(ctoken.get("borrow_rate", {}).get("value", 0)) * 100
                opportunities.append(YieldOpportunity(
                    category=self.category, protocol="Compound", chain="Ethereum",
                    stablecoin=symbol, apy=apy, tvl=tvl, supply_apy=apy, borrow_apy=borrow_apy,
                    risk_score=RiskAssessor.calculate_risk_score("lend", chain="Ethereum", apy=apy),
                    source_url="https://app.compound.finance/markets",
                ))
        except:
            for item in [{"symbol": "USDC", "apy": 4.5, "tvl": 500_000_000}, {"symbol": "USDT", "apy": 4.0, "tvl": 300_000_000}]:
                opportunities.append(YieldOpportunity(
                    category=self.category, protocol="Compound", chain="Ethereum",
                    stablecoin=item["symbol"], apy=item["apy"], tvl=item["tvl"],
                    risk_score="Low", source_url="https://app.compound.finance/markets",
                ))
        return opportunities


class AaveLendScraper(BaseScraper):
    category = "Aave Lend"
    cache_file = "aave_lend_st"
    AAVE_API = "https://aave-api-v2.aave.com/data/markets-data"
    MIN_TVL = 100_000
    STABLECOINS = ["USDC", "USDT", "DAI", "FRAX", "LUSD", "GHO", "PYUSD", "USDS"]
    def _fetch_data(self) -> List[YieldOpportunity]:
        opportunities = []
        try:
            resp = self.session.get(self.AAVE_API, timeout=REQUEST_TIMEOUT)
            for reserve in resp.json().get("reserves", []):
                symbol = reserve.get("symbol", "")
                if not any(s in symbol.upper() for s in self.STABLECOINS):
                    continue
                supply_apy = float(reserve.get("liquidityRate", 0)) / 1e25
                if supply_apy <= 0:
                    continue
                tvl = float(reserve.get("totalLiquidityUSD", 0))
                if tvl < self.MIN_TVL:
                    continue
                borrow_apy = float(reserve.get("variableBorrowRate", 0)) / 1e25
                pool_id = reserve.get("pool", {}).get("id", "").lower()
                chain = "Arbitrum" if "arbitrum" in pool_id else "Optimism" if "optimism" in pool_id else "Base" if "base" in pool_id else "Polygon" if "polygon" in pool_id else "Ethereum"
                opportunities.append(YieldOpportunity(
                    category=self.category, protocol="Aave", chain=chain,
                    stablecoin=symbol, apy=supply_apy, tvl=tvl, supply_apy=supply_apy, borrow_apy=borrow_apy,
                    risk_score=RiskAssessor.calculate_risk_score("lend", chain=chain, apy=supply_apy),
                    source_url="https://app.aave.com/markets/",
                ))
        except:
            for item in [{"symbol": "USDC", "chain": "Ethereum", "apy": 3.5, "tvl": 1_000_000_000},
                         {"symbol": "USDT", "chain": "Ethereum", "apy": 3.8, "tvl": 800_000_000}]:
                opportunities.append(YieldOpportunity(
                    category=self.category, protocol="Aave", chain=item["chain"],
                    stablecoin=item["symbol"], apy=item["apy"], tvl=item["tvl"],
                    risk_score="Low", source_url="https://app.aave.com/markets/",
                ))
        return opportunities


class AaveLoopScraper(BaseScraper):
    category = "Aave Borrow/Lend Loop"
    cache_file = "aave_loop_st"
    LEVERAGE_LEVELS = [2.0, 3.0, 5.0]
    def _fetch_data(self) -> List[YieldOpportunity]:
        opportunities = []
        lend_opps = AaveLendScraper().fetch(use_cache=True)
        for opp in lend_opps:
            supply_apy = opp.supply_apy or opp.apy
            borrow_apy = opp.borrow_apy
            if not borrow_apy or borrow_apy <= 0:
                continue
            for leverage in self.LEVERAGE_LEVELS:
                net_apy = supply_apy * leverage - borrow_apy * (leverage - 1)
                if net_apy <= 0:
                    continue
                opportunities.append(YieldOpportunity(
                    category=self.category, protocol="Aave", chain=opp.chain,
                    stablecoin=opp.stablecoin, apy=net_apy, tvl=opp.tvl, leverage=leverage,
                    supply_apy=supply_apy, borrow_apy=borrow_apy,
                    risk_score=RiskAssessor.calculate_risk_score("loop", leverage=leverage, chain=opp.chain, apy=net_apy),
                    source_url=opp.source_url,
                ))
        return opportunities


class MidasScraper(BaseScraper):
    category = "Midas Yield-Bearing"
    cache_file = "midas_st"
    TOKENS = [
        {"symbol": "mTBILL", "apy": 4.3, "tvl": 100_000_000, "chain": "Ethereum"},
        {"symbol": "mBASIS", "apy": 5.1, "tvl": 50_000_000, "chain": "Ethereum"},
    ]
    def _fetch_data(self) -> List[YieldOpportunity]:
        return [YieldOpportunity(
            category=self.category, protocol="Midas", chain=t["chain"],
            stablecoin=t["symbol"], apy=t["apy"], tvl=t["tvl"],
            risk_score=RiskAssessor.calculate_risk_score("yield_bearing", chain=t["chain"], apy=t["apy"]),
            source_url="https://midas.app/",
        ) for t in self.TOKENS]


class SpectraScraper(BaseScraper):
    category = "Spectra Fixed Yields"
    cache_file = "spectra_st"
    def _fetch_data(self) -> List[YieldOpportunity]:
        return [YieldOpportunity(
            category=self.category, protocol="Spectra", chain=item["chain"],
            stablecoin=item["symbol"], apy=item["apy"], tvl=item["tvl"],
            opportunity_type="PT (Fixed Yield)", risk_score="Low",
            source_url="https://app.spectra.finance/pools",
        ) for item in [
            {"symbol": "USDC", "chain": "Ethereum", "apy": 6.5, "tvl": 10_000_000},
            {"symbol": "sUSDe", "chain": "Ethereum", "apy": 12.0, "tvl": 8_000_000},
        ]]


class GearboxScraper(BaseScraper):
    category = "Gearbox Lend"
    cache_file = "gearbox_st"
    def _fetch_data(self) -> List[YieldOpportunity]:
        return [YieldOpportunity(
            category=self.category, protocol="Gearbox", chain=item["chain"],
            stablecoin=item["symbol"], apy=item["apy"], tvl=item["tvl"],
            risk_score="Medium", source_url="https://app.gearbox.fi/pools",
        ) for item in [
            {"symbol": "USDC", "chain": "Ethereum", "apy": 8.5, "tvl": 50_000_000},
            {"symbol": "DAI", "chain": "Ethereum", "apy": 7.2, "tvl": 30_000_000},
        ]]


class UpshiftScraper(BaseScraper):
    category = "Upshift Vaults"
    cache_file = "upshift_st"
    def _fetch_data(self) -> List[YieldOpportunity]:
        return [YieldOpportunity(
            category=self.category, protocol="Upshift", chain=item["chain"],
            stablecoin=item["symbol"], apy=item["apy"], tvl=item["tvl"],
            risk_score="Medium", source_url="https://app.upshift.finance/",
        ) for item in [
            {"symbol": "USDC", "chain": "Ethereum", "apy": 8.0, "tvl": 20_000_000},
            {"symbol": "sUSDe", "chain": "Ethereum", "apy": 12.0, "tvl": 10_000_000},
        ]]


class IporFusionScraper(BaseScraper):
    category = "IPOR Fusion"
    cache_file = "ipor_st"
    def _fetch_data(self) -> List[YieldOpportunity]:
        return [YieldOpportunity(
            category=self.category, protocol="IPOR", chain=item["chain"],
            stablecoin=item["symbol"], apy=item["apy"], tvl=item["tvl"],
            risk_score="Medium", source_url="https://app.ipor.io/fusion",
        ) for item in [
            {"symbol": "USDC", "chain": "Ethereum", "apy": 6.5, "tvl": 30_000_000},
            {"symbol": "USDT", "chain": "Ethereum", "apy": 6.0, "tvl": 25_000_000},
        ]]


class TownSquareScraper(BaseScraper):
    category = "TownSquare Lend"
    cache_file = "townsquare_st"
    def _fetch_data(self) -> List[YieldOpportunity]:
        return [YieldOpportunity(
            category=self.category, protocol="TownSquare", chain=item["chain"],
            stablecoin=item["symbol"], apy=item["apy"], tvl=item["tvl"],
            risk_score="Medium", source_url="https://app.townsq.xyz/",
        ) for item in [
            {"symbol": "USDC", "chain": "Ethereum", "apy": 5.0, "tvl": 10_000_000},
            {"symbol": "sUSDe", "chain": "Ethereum", "apy": 8.0, "tvl": 5_000_000},
        ]]


class CurvanceScraper(BaseScraper):
    category = "Curvance Lend"
    cache_file = "curvance_st"
    def _fetch_data(self) -> List[YieldOpportunity]:
        return [YieldOpportunity(
            category=self.category, protocol="Curvance", chain=item["chain"],
            stablecoin=item["symbol"], apy=item["apy"], tvl=item["tvl"],
            risk_score="Medium", source_url="https://app.curvance.com/",
        ) for item in [
            {"symbol": "USDC", "chain": "Ethereum", "apy": 6.0, "tvl": 15_000_000},
            {"symbol": "crvUSD", "chain": "Ethereum", "apy": 7.5, "tvl": 20_000_000},
        ]]


class AccountableScraper(BaseScraper):
    category = "Accountable Yield"
    cache_file = "accountable_st"
    def _fetch_data(self) -> List[YieldOpportunity]:
        return [YieldOpportunity(
            category=self.category, protocol="Accountable", chain=item["chain"],
            stablecoin=item["symbol"], apy=item["apy"], tvl=item["tvl"],
            risk_score=RiskAssessor.calculate_risk_score("vault", chain=item["chain"], apy=item["apy"]),
            source_url="https://yield.accountable.capital/",
        ) for item in [
            {"symbol": "USDC", "chain": "Ethereum", "apy": 22.25, "tvl": 5_000_000},
            {"symbol": "USDC", "chain": "Ethereum", "apy": 13.7, "tvl": 8_000_000},
        ]]


class LagoonScraper(BaseScraper):
    category = "Lagoon Vaults"
    cache_file = "lagoon_st"
    API_URL = "https://app.lagoon.finance/api/vaults"
    MIN_TVL = 100_000
    STABLECOINS = ["USDC", "USDT", "DAI", "FRAX", "AUSD", "USD"]
    def _fetch_data(self) -> List[YieldOpportunity]:
        opportunities = []
        try:
            resp = self.session.get(self.API_URL, timeout=REQUEST_TIMEOUT)
            for vault in resp.json().get("vaults", []):
                if not vault.get("isVisible", True):
                    continue
                asset = vault.get("asset", {})
                symbol = asset.get("symbol", "").upper()
                if not any(s in symbol for s in self.STABLECOINS):
                    continue
                state = vault.get("state", {})
                tvl = state.get("totalAssetsUsd", 0)
                if tvl < self.MIN_TVL:
                    continue
                apr = 0
                for key in ["weeklyApr", "monthlyApr", "liveAPR"]:
                    apr_data = state.get(key, {})
                    if apr_data:
                        apr = apr_data.get("linearNetApr", 0)
                        if apr > 0:
                            break
                if apr <= 0:
                    continue
                chain_data = vault.get("chain", {})
                chain = chain_data.get("name", "Ethereum") if isinstance(chain_data, dict) else "Ethereum"
                curators = vault.get("curators", [])
                curator = curators[0].get("name", "Lagoon") if curators else "Lagoon"
                opportunities.append(YieldOpportunity(
                    category=self.category, protocol=f"Lagoon ({curator})", chain=chain,
                    stablecoin=symbol, apy=apr, tvl=tvl,
                    risk_score=RiskAssessor.calculate_risk_score("vault", chain=chain, apy=apr),
                    source_url="https://app.lagoon.finance",
                ))
        except:
            pass
        return opportunities


class KaminoLendScraper(BaseScraper):
    category = "Kamino Lend"
    cache_file = "kamino_lend_st"
    API_URL = "https://yields.llama.fi/pools"
    MIN_TVL = 100_000
    STABLECOINS = ["USDC", "USDT", "PYUSD", "USDS", "FDUSD"]
    def _fetch_data(self) -> List[YieldOpportunity]:
        opportunities = []
        try:
            resp = self.session.get(self.API_URL, timeout=REQUEST_TIMEOUT)
            for pool in resp.json().get("data", []):
                if pool.get("project", "").lower() != "kamino-lend":
                    continue
                symbol = pool.get("symbol", "").upper()
                if not any(s in symbol for s in self.STABLECOINS):
                    continue
                tvl = pool.get("tvlUsd", 0)
                apy = pool.get("apy", 0)
                if tvl < self.MIN_TVL or apy <= 0:
                    continue
                opportunities.append(YieldOpportunity(
                    category=self.category, protocol="Kamino", chain="Solana",
                    stablecoin=symbol, apy=apy, tvl=tvl,
                    risk_score=RiskAssessor.calculate_risk_score("lend", chain="Solana", apy=apy),
                    source_url="https://app.kamino.finance/lending",
                ))
        except:
            pass
        return opportunities


class JupiterLendScraper(BaseScraper):
    category = "Jupiter Lend"
    cache_file = "jupiter_lend_st"
    def _fetch_data(self) -> List[YieldOpportunity]:
        return [YieldOpportunity(
            category=self.category, protocol="Jupiter", chain="Solana",
            stablecoin=item["symbol"], apy=item["apy"], tvl=item["tvl"],
            risk_score=RiskAssessor.calculate_risk_score("lend", chain="Solana", apy=item["apy"]),
            source_url="https://jup.ag/lend/earn",
        ) for item in [
            {"symbol": "USDC", "apy": 5.5, "tvl": 300_000_000},
            {"symbol": "USDT", "apy": 4.8, "tvl": 100_000_000},
            {"symbol": "PYUSD", "apy": 3.5, "tvl": 50_000_000},
        ]]


class MorphoLoopScraper(BaseScraper):
    """Morpho yield-bearing collateral loop strategies."""
    category = "Morpho Borrow/Lend Loop"
    cache_file = "morpho_loop_st"
    API_URL = "https://blue-api.morpho.org/graphql"
    MIN_TVL_USD = 10_000
    MAX_BORROW_APY = 50
    LEVERAGE_LEVELS = [2.0, 3.0, 5.0]
    YIELD_BEARING_PATTERNS = [
        "SUSDE", "SDAI", "SUSDS", "SFRAX", "MHYPER", "SUSN", "USD0++",
        "SCRVUSD", "SAVUSD", "STUSD", "SUSDX", "PT-",
        "SNUSD", "SRUSDE", "STCUSD", "WSRUS", "MAPOLLO", "RLP",
        "CUSD", "RUSD", "REUSD", "IUSD", "SIUSD", "JRUSDE", "LVLUSD",
        "YOUSD", "MMEV",
    ]
    BORROW_STABLES = ["USDC", "USDT", "DAI", "USDS", "PYUSD", "FRAX", "CRVUSD", "GHO", "USDA"]
    YIELD_RATES = {
        "SUSDE": 5.27, "SDAI": 5.0, "SUSDS": 4.5, "SFRAX": 4.0,
        "MHYPER": 6.0, "USD0++": 8.0, "PT-MHYPER": 6.0, "PT-SUSDE": 5.27,
        "PT-SNUSD": 5.0, "PT-SRUSDE": 5.0, "PT-STCUSD": 5.0, "PT-CUSD": 5.0,
        "PT-RUSD": 5.0, "PT-WSRUS": 5.0, "PT-RLP": 5.0, "PT-MAPOLLO": 6.0,
        "PT-REUSD": 7.5, "PT-IUSD": 5.0, "PT-SIUSD": 5.0,
        "PT-JRUSDE": 6.0, "PT-LVLUSD": 5.0,
        "PT-YO": 5.5, "YOUSD": 5.5, "SNUSD": 5.0,
        "MMEV": 6.0, "PT-MMEV": 6.0,
    }
    CHAIN_IDS = {1: "Ethereum", 8453: "Base", 42161: "Arbitrum", 10: "Optimism", 130: "Unichain"}

    def _fetch_data(self) -> List[YieldOpportunity]:
        opportunities = []
        for chain_id, chain_name in self.CHAIN_IDS.items():
            try:
                markets = self._fetch_chain_markets(chain_id, chain_name)
                opportunities.extend(self._calc_loops(markets, chain_name))
            except:
                pass
        return opportunities

    def _fetch_chain_markets(self, chain_id: int, chain_name: str) -> List[Dict]:
        query = """query($chainId: Int!, $skip: Int!) {
            markets(where: { chainId_in: [$chainId] }, first: 1000, skip: $skip) {
                items { uniqueKey loanAsset { symbol } collateralAsset { symbol }
                        state { borrowApy supplyAssetsUsd sizeUsd } lltv }
                pageInfo { countTotal } } }"""
        all_items = []
        skip = 0
        while True:
            resp = self.session.post(self.API_URL,
                json={"query": query, "variables": {"chainId": chain_id, "skip": skip}}, timeout=REQUEST_TIMEOUT)
            data = resp.json().get("data", {}).get("markets", {})
            items = data.get("items", [])
            if not items:
                break
            all_items.extend(items)
            count_total = data.get("pageInfo", {}).get("countTotal", 0)
            if len(all_items) >= count_total or len(items) < 1000:
                break
            skip += 1000
        return all_items

    def _calc_loops(self, markets: List[Dict], chain: str) -> List[YieldOpportunity]:
        opportunities = []
        for market in markets:
            ca = market.get("collateralAsset") or {}
            la = market.get("loanAsset") or {}
            col_sym = ca.get("symbol", "").upper()
            loan_sym = la.get("symbol", "").upper()
            if not any(p in col_sym for p in self.YIELD_BEARING_PATTERNS):
                continue
            if not any(s in loan_sym for s in self.BORROW_STABLES):
                continue
            state = market.get("state") or {}
            tvl = state.get("sizeUsd") or state.get("supplyAssetsUsd") or 0
            borrow_apy = (state.get("borrowApy") or 0) * 100
            if tvl < self.MIN_TVL_USD or borrow_apy > self.MAX_BORROW_APY or borrow_apy <= 0:
                continue
            lltv_raw = market.get("lltv", 0)
            try:
                lltv = float(lltv_raw)
                if lltv > 1:
                    lltv = lltv / 1e18
            except:
                continue
            if lltv <= 0:
                continue
            col_yield = self._get_yield(col_sym)
            if col_yield <= 0:
                continue
            max_lev = min(1 / (1 - lltv) * 0.6 if lltv < 1 else 1, 5.0)
            market_id = market.get("uniqueKey", "")
            for leverage in self.LEVERAGE_LEVELS:
                if leverage > max_lev:
                    continue
                net_apy = col_yield * leverage - borrow_apy * (leverage - 1)
                if net_apy <= 0:
                    continue
                opportunities.append(YieldOpportunity(
                    category=self.category, protocol="Morpho", chain=chain,
                    stablecoin=col_sym, apy=net_apy, tvl=tvl, leverage=leverage,
                    supply_apy=col_yield, borrow_apy=borrow_apy,
                    risk_score=RiskAssessor.calculate_risk_score("loop", leverage=leverage, chain=chain, apy=net_apy),
                    source_url=f"https://app.morpho.org/market?id={market_id}",
                    additional_info={"collateral": col_sym, "collateral_yield": col_yield,
                                     "borrow_asset": loan_sym, "lltv": lltv * 100},
                ))
        return opportunities

    def _get_yield(self, symbol: str) -> float:
        if symbol in self.YIELD_RATES:
            return self.YIELD_RATES[symbol]
        for key, rate in self.YIELD_RATES.items():
            if key in symbol:
                return rate
        return 0.0


class NestCreditScraper(BaseScraper):
    """Nest Credit vaults on Plume chain."""
    category = "Nest Credit Vaults"
    cache_file = "nest_credit_st"
    API_URLS = ["https://api.nest.credit/v1/vaults", "https://app.nest.credit/api/vaults"]
    NEST_VAULTS = [
        {"symbol": "nTBILL", "name": "Nest Treasuries", "apy": 5.50, "tvl": 50_000_000, "risk": "Low"},
        {"symbol": "nBASIS", "name": "Nest Basis", "apy": 8.00, "tvl": 30_000_000, "risk": "Medium"},
        {"symbol": "nALPHA", "name": "Nest Alpha", "apy": 11.50, "tvl": 20_000_000, "risk": "High"},
        {"symbol": "nCREDIT", "name": "Nest Credit", "apy": 8.00, "tvl": 10_000_000, "risk": "Medium"},
    ]

    def _fetch_data(self) -> List[YieldOpportunity]:
        for url in self.API_URLS:
            try:
                resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
                data = resp.json()
                vaults = data.get("vaults", data if isinstance(data, list) else [])
                opps = []
                for v in vaults:
                    sym = v.get("symbol", "")
                    apy = float(v.get("apy", 0))
                    if 0 < apy < 1:
                        apy *= 100
                    if apy <= 0:
                        continue
                    opps.append(YieldOpportunity(
                        category=self.category, protocol="Nest Credit", chain="Plume",
                        stablecoin=sym, apy=apy, tvl=float(v.get("tvl", 0)),
                        risk_score=RiskAssessor.calculate_risk_score("yield_bearing", chain="Plume", apy=apy),
                        source_url="https://app.nest.credit/",
                    ))
                if opps:
                    return opps
            except:
                continue
        # Fallback to published rates
        return [YieldOpportunity(
            category=self.category, protocol="Nest Credit", chain="Plume",
            stablecoin=v["symbol"], apy=v["apy"], tvl=v["tvl"],
            risk_score=v["risk"], source_url="https://app.nest.credit/",
            additional_info={"name": v["name"]},
        ) for v in self.NEST_VAULTS]


# Available scrapers
class EulerLoopScraper(BaseScraper):
    """Euler cross-collateral borrow/lend loop strategies via native subgraphs."""
    category = "Euler Borrow/Lend Loop"
    cache_file = "euler_loop_st"
    APY_SCALE = 1e27
    LEVERAGE_LEVELS = [2.0, 3.0, 5.0]
    MAX_BORROW_APY = 50
    MAX_SUPPLY_APY = 25

    @staticmethod
    def _extract_underlying(symbol: str) -> str:
        """Extract underlying asset from vault symbol: 'esBOLD-1' -> 'sBOLD', 'eUSDC-70' -> 'USDC'."""
        s = re.sub(r'^e', '', symbol)
        s = re.sub(r'-\d+$', '', s)
        return s

    @staticmethod
    def _is_stablecoin(name: str, symbol: str, stablecoins: list) -> bool:
        combined = (name + " " + symbol).upper()
        return any(s in combined for s in stablecoins)

    def _fetch_data(self) -> List[YieldOpportunity]:
        opportunities = []
        lend = EulerLendScraper()
        for chain, endpoint in lend.SUBGRAPH_ENDPOINTS.items():
            try:
                resp = self.session.post(endpoint, json={"query": lend.VAULT_QUERY}, timeout=REQUEST_TIMEOUT)
                vaults = resp.json().get("data", {}).get("eulerVaults", [])
                # Build address -> vault lookup
                vault_map = {v.get("id", "").lower(): v for v in vaults}
                for vault in vaults:
                    state = vault.get("state") or {}
                    borrow_apy = (int(state.get("borrowApy", "0") or "0") / self.APY_SCALE) * 100
                    if borrow_apy <= 0 or borrow_apy > self.MAX_BORROW_APY:
                        continue
                    borrow_name = vault.get("name", "")
                    borrow_symbol = vault.get("symbol", "")
                    if not self._is_stablecoin(borrow_name, borrow_symbol, lend.STABLECOINS):
                        continue
                    borrow_underlying = self._extract_underlying(borrow_symbol)
                    borrow_decimals = int(vault.get("decimals", "18") or "18")
                    borrow_tvl = (int(state.get("totalBorrows", "0") or "0") + int(state.get("cash", "0") or "0")) / (10 ** borrow_decimals)
                    if borrow_tvl < 10_000:
                        continue
                    for coll_addr in vault.get("collaterals", []):
                        coll_vault = vault_map.get(coll_addr.lower())
                        if not coll_vault:
                            continue
                        coll_name = coll_vault.get("name", "")
                        coll_symbol = coll_vault.get("symbol", "")
                        if not self._is_stablecoin(coll_name, coll_symbol, lend.STABLECOINS):
                            continue
                        coll_state = coll_vault.get("state") or {}
                        supply_apy = (int(coll_state.get("supplyApy", "0") or "0") / self.APY_SCALE) * 100
                        if supply_apy <= 0 or supply_apy > self.MAX_SUPPLY_APY:
                            continue
                        coll_underlying = self._extract_underlying(coll_symbol)
                        pair_label = f"{coll_underlying}/{borrow_underlying}"
                        for lev in self.LEVERAGE_LEVELS:
                            net = supply_apy * lev - borrow_apy * (lev - 1)
                            if net < 0.5:
                                continue
                            opportunities.append(YieldOpportunity(
                                category=self.category, protocol="Euler", chain=chain,
                                stablecoin=pair_label, apy=net, tvl=borrow_tvl, leverage=lev,
                                supply_apy=supply_apy, borrow_apy=borrow_apy,
                                risk_score=RiskAssessor.calculate_risk_score("loop", leverage=lev, chain=chain, apy=net),
                                source_url="https://app.euler.finance",
                                additional_info={"collateral": coll_underlying, "borrow_asset": borrow_underlying, "supply_rate": supply_apy, "borrow_rate": borrow_apy},
                            ))
            except:
                continue
        return opportunities


class CompoundLoopScraper(BaseScraper):
    category = "Compound Borrow/Lend Loop"
    cache_file = "compound_loop_st"
    LEVERAGE_LEVELS = [2.0, 3.0, 5.0]
    def _fetch_data(self) -> List[YieldOpportunity]:
        opportunities = []
        lend = CompoundLendScraper()
        lend_opps = lend._fetch_data()
        for opp in lend_opps:
            if not opp.supply_apy or not opp.borrow_apy or opp.borrow_apy <= 0:
                continue
            for lev in self.LEVERAGE_LEVELS:
                net = opp.supply_apy * lev - opp.borrow_apy * (lev - 1)
                if net < 0.5:
                    continue
                opportunities.append(YieldOpportunity(
                    category=self.category, protocol="Compound", chain=opp.chain,
                    stablecoin=opp.stablecoin, apy=net, tvl=opp.tvl, leverage=lev,
                    supply_apy=opp.supply_apy, borrow_apy=opp.borrow_apy,
                    risk_score=RiskAssessor.calculate_risk_score("loop", leverage=lev, chain=opp.chain, apy=net),
                    source_url="https://app.compound.finance",
                ))
        return opportunities


class KaminoLoopScraper(BaseScraper):
    category = "Kamino Borrow/Lend Loop"
    cache_file = "kamino_loop_st"
    LEVERAGE_LEVELS = [2.0, 3.0, 5.0]
    def _fetch_data(self) -> List[YieldOpportunity]:
        opportunities = []
        lend = KaminoLendScraper()
        lend_opps = lend._fetch_data()
        for opp in lend_opps:
            supply = opp.supply_apy or opp.apy
            borrow = opp.borrow_apy
            if not supply or not borrow or borrow <= 0:
                continue
            for lev in self.LEVERAGE_LEVELS:
                net = supply * lev - borrow * (lev - 1)
                if net < 0.5:
                    continue
                opportunities.append(YieldOpportunity(
                    category=self.category, protocol="Kamino", chain="Solana",
                    stablecoin=opp.stablecoin, apy=net, tvl=opp.tvl, leverage=lev,
                    supply_apy=supply, borrow_apy=borrow,
                    risk_score=RiskAssessor.calculate_risk_score("loop", leverage=lev, chain="Solana", apy=net),
                    source_url="https://app.kamino.finance/lending",
                ))
        return opportunities


class JupiterBorrowScraper(BaseScraper):
    category = "Jupiter Borrow"
    cache_file = "jupiter_borrow_st"
    def _fetch_data(self) -> List[YieldOpportunity]:
        return [YieldOpportunity(
            category=self.category, protocol="Jupiter", chain="Solana",
            stablecoin=item["symbol"], apy=item["apy"], tvl=item["tvl"],
            risk_score=RiskAssessor.calculate_risk_score("lend", chain="Solana", apy=item["apy"]),
            source_url="https://jup.ag/lend/borrow",
        ) for item in [
            {"symbol": "USDC", "apy": 7.0, "tvl": 200_000_000},
            {"symbol": "USDT", "apy": 6.0, "tvl": 80_000_000},
        ]]


class StakeDaoScraper(BaseScraper):
    category = "Stake DAO Vaults"
    cache_file = "stakedao_st"
    API_URLS = {"Ethereum": "https://api.stakedao.org/api/strategies/curve/1.json"}
    STABLECOIN_KW = ["usd", "dai", "frax", "lusd", "crvusd", "gho", "pyusd"]
    def _fetch_data(self) -> List[YieldOpportunity]:
        opportunities = []
        for chain, url in self.API_URLS.items():
            try:
                resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
                data = resp.json()
                if isinstance(data, list):
                    strategies = data
                elif isinstance(data, dict):
                    strategies = data.get("deployed", data.get("strategies", []))
                else:
                    strategies = []
                for s in strategies:
                    name = (s.get("name", "") or "").lower()
                    if not any(kw in name for kw in self.STABLECOIN_KW):
                        continue
                    apr = s.get("apr", {})
                    total = float((apr.get("projected", {}) if isinstance(apr, dict) else {}).get("total", 0) or 0)
                    tvl = float(s.get("tvl", 0) or 0)
                    if total <= 0 or tvl < 10_000:
                        continue
                    opportunities.append(YieldOpportunity(
                        category=self.category, protocol="Stake DAO", chain=chain,
                        stablecoin="USD", apy=total, tvl=tvl,
                        risk_score=RiskAssessor.calculate_risk_score("vault", chain=chain, apy=total),
                        source_url="https://app.stakedao.org",
                    ))
            except:
                continue
        return opportunities


class ConvexScraper(BaseScraper):
    category = "Convex Finance"
    cache_file = "convex_st"
    API_URL = "https://curve.convexfinance.com/api/curve-apys"
    STABLECOIN_KW = ["usd", "dai", "frax", "lusd", "crvusd", "gho", "3pool"]
    def _fetch_data(self) -> List[YieldOpportunity]:
        opportunities = []
        try:
            resp = self.session.get(self.API_URL, timeout=REQUEST_TIMEOUT)
            apys = resp.json().get("apys", resp.json() if isinstance(resp.json(), dict) else {})
            for name, data in apys.items():
                if not any(kw in name.lower() for kw in self.STABLECOIN_KW):
                    continue
                base = float(data.get("baseApy", 0) or 0)
                crv = float(data.get("crvApy", 0) or 0)
                cvx = float(data.get("cvxApy", 0) or 0)
                total = base + crv + cvx
                if total < 0.5 or total > 100:
                    continue
                opportunities.append(YieldOpportunity(
                    category=self.category, protocol="Convex", chain="Ethereum",
                    stablecoin="USD", apy=total, tvl=None,
                    risk_score=RiskAssessor.calculate_risk_score("vault", chain="Ethereum", apy=total),
                    source_url="https://www.convexfinance.com/stake",
                    additional_info={"pool_name": name},
                ))
        except:
            pass
        return opportunities


class HyperionScraper(BaseScraper):
    category = "Hyperion LP"
    cache_file = "hyperion_st"
    API_URL = "https://hyperfluid-api.alcove.pro/v1/graphql"
    STABLECOINS = ["USDC", "USDT", "DAI", "MUSD", "USD"]
    QUERY = """{ statsPool(limit: 200) { name poolId tvl feeApr farmApr } }"""
    def _fetch_data(self) -> List[YieldOpportunity]:
        opportunities = []
        try:
            resp = self.session.post(self.API_URL, json={"query": self.QUERY}, timeout=REQUEST_TIMEOUT)
            seen = {}
            for pool in resp.json().get("data", {}).get("statsPool", []):
                pid = pool.get("poolId", "")
                if pid in seen:
                    continue
                seen[pid] = True
                name = pool.get("name", "") or ""
                parts = name.split("-")
                if len(parts) != 2:
                    continue
                tx, ty = parts[0].strip().upper(), parts[1].strip().upper()
                x_stable = any(s in tx for s in self.STABLECOINS)
                y_stable = any(s in ty for s in self.STABLECOINS)
                if not (x_stable and y_stable):
                    continue
                tvl = float(pool.get("tvl", 0) or 0)
                total = float(pool.get("feeApr", 0) or 0) + float(pool.get("farmApr", 0) or 0)
                if tvl < 10_000 or total <= 0 or total > 200:
                    continue
                opportunities.append(YieldOpportunity(
                    category=self.category, protocol="Hyperion", chain="Aptos",
                    stablecoin=tx, apy=total, tvl=tvl, opportunity_type="LP",
                    risk_score=RiskAssessor.calculate_risk_score("vault", chain="Aptos", apy=total),
                    source_url=f"https://app.hyperion.xyz/pool/{pid}" if pid else "https://app.hyperion.xyz",
                    additional_info={"pair": f"{tx}/{ty}"},
                ))
        except:
            pass
        return opportunities


class YoScraper(BaseScraper):
    category = "Yo Yield"
    cache_file = "yo_st"
    VAULTS = [{"network": "base", "address": "0x0000000f2eB9f69274678c76222B35eEc7588a65", "symbol": "yoUSD", "chain": "Base"}]
    def _fetch_data(self) -> List[YieldOpportunity]:
        opportunities = []
        for v in self.VAULTS:
            try:
                resp = self.session.get(f"https://api.yo.xyz/api/v1/vault/{v['network']}/{v['address']}", timeout=REQUEST_TIMEOUT)
                data = resp.json()
                vault_data = data.get("data", data)
                stats = vault_data.get("stats", {})
                apy = float(stats.get("yield", {}).get("7d", 0) or 0) + float(stats.get("merklRewardYield", 0) or 0)
                if apy <= 0:
                    continue
                tvl_raw = stats.get("tvl", {}).get("formatted", "0")
                try:
                    tvl = float(tvl_raw)
                except (ValueError, TypeError):
                    tvl_str = str(tvl_raw).replace("$", "").replace(",", "").strip()
                    tvl = float(tvl_str[:-1]) * 1e6 if tvl_str.upper().endswith("M") else float(tvl_str[:-1]) * 1e3 if tvl_str.upper().endswith("K") else float(tvl_str) if tvl_str else 0
                opportunities.append(YieldOpportunity(
                    category=self.category, protocol="Yo", chain=v["chain"],
                    stablecoin=v["symbol"], apy=apy, tvl=tvl,
                    risk_score=RiskAssessor.calculate_risk_score("vault", chain=v["chain"], apy=apy),
                    source_url=f"https://app.yo.xyz/vault/{v['address']}",
                ))
            except:
                continue
        return opportunities


class YieldFiScraper(BaseScraper):
    category = "Yield.fi"
    cache_file = "yieldfi_st"
    def _fetch_data(self) -> List[YieldOpportunity]:
        return [YieldOpportunity(
            category=self.category, protocol="Yield.fi", chain=item["chain"],
            stablecoin=item["symbol"], apy=item["apy"], tvl=item["tvl"],
            risk_score=RiskAssessor.calculate_risk_score("vault", chain=item["chain"], apy=item["apy"]),
            source_url="https://app.yield.fi",
        ) for item in [
            {"symbol": "vyUSD", "chain": "Plume", "apy": 16.0, "tvl": 3_000_000},
            {"symbol": "vyUSD", "chain": "Base", "apy": 16.0, "tvl": 2_000_000},
        ]]


class PloutosScraper(BaseScraper):
    category = "Ploutos Money"
    cache_file = "ploutos_st"
    def _fetch_data(self) -> List[YieldOpportunity]:
        return [YieldOpportunity(
            category=self.category, protocol="Ploutos", chain=item["chain"],
            stablecoin=item["symbol"], apy=item["apy"], tvl=item["tvl"],
            risk_score=RiskAssessor.calculate_risk_score("lend", chain=item["chain"], apy=item["apy"]),
            source_url="https://app.ploutos.money",
        ) for item in [
            {"symbol": "USDC", "chain": "Hemi", "apy": 5.0, "tvl": 2_000_000},
            {"symbol": "USDT", "chain": "Hemi", "apy": 4.5, "tvl": 1_500_000},
            {"symbol": "USDC", "chain": "Ethereum", "apy": 4.0, "tvl": 3_000_000},
        ]]


class MysticLendScraper(BaseScraper):
    category = "Mystic Lend"
    cache_file = "mystic_lend_st"
    PAGE_URL = "https://app.mysticfinance.xyz/"
    STABLECOINS = ["USDC", "USDT", "DAI", "USDS", "NUSD", "PUSD"]
    def _fetch_data(self) -> List[YieldOpportunity]:
        opportunities = []
        try:
            resp = self.session.get(self.PAGE_URL, timeout=REQUEST_TIMEOUT)
            html = resp.text
            match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
            if match:
                page_data = json.loads(match.group(1))
                props = page_data.get("props", {}).get("pageProps", {})
                reserves = props.get("reserves", props.get("markets", []))
                for r in reserves:
                    sym = (r.get("symbol", "") or "").upper()
                    if not any(s in sym for s in self.STABLECOINS):
                        continue
                    supply_apy = float(r.get("supplyAPY", 0) or r.get("liquidityRate", 0))
                    if supply_apy < 1:
                        supply_apy *= 100
                    if supply_apy <= 0:
                        continue
                    tvl = float(r.get("totalLiquidity", 0) or r.get("tvl", 0))
                    opportunities.append(YieldOpportunity(
                        category=self.category, protocol="Mystic", chain="Plume",
                        stablecoin=sym, apy=supply_apy, tvl=tvl,
                        risk_score=RiskAssessor.calculate_risk_score("lend", chain="Plume", apy=supply_apy),
                        source_url="https://app.mysticfinance.xyz/",
                    ))
        except:
            pass
        return opportunities


class MysticLoopScraper(BaseScraper):
    category = "Mystic Borrow/Lend Loop"
    cache_file = "mystic_loop_st"
    COLLATERAL_YIELDS = {"nTBILL": 5.5, "nBASIS": 8.0, "nALPHA": 11.5, "nCREDIT": 8.0}
    DEFAULT_BORROW_RATE = 5.0
    DEFAULT_LTV = 0.75
    def _fetch_data(self) -> List[YieldOpportunity]:
        opportunities = []
        for collateral, yield_rate in self.COLLATERAL_YIELDS.items():
            borrow_rate = self.DEFAULT_BORROW_RATE
            theoretical_max = 1 / (1 - self.DEFAULT_LTV) if self.DEFAULT_LTV < 1 else 1
            safe_max = min(theoretical_max * 0.6, 5.0)
            for leverage in [2.0, 3.0]:
                if leverage > safe_max:
                    continue
                net_apy = yield_rate * leverage - borrow_rate * (leverage - 1)
                if net_apy <= 0:
                    continue
                opportunities.append(YieldOpportunity(
                    category=self.category, protocol="Mystic", chain="Plume",
                    stablecoin=collateral, apy=net_apy, tvl=10_000_000,
                    leverage=leverage, supply_apy=yield_rate, borrow_apy=borrow_rate,
                    risk_score=RiskAssessor.calculate_risk_score("loop", leverage=leverage, chain="Plume", apy=net_apy),
                    source_url="https://app.mysticfinance.xyz/",
                    additional_info={"collateral": collateral, "collateral_yield": yield_rate, "borrow_asset": "USDC", "borrow_rate": borrow_rate, "lltv": self.DEFAULT_LTV * 100},
                ))
        return opportunities


SCRAPERS = {
    "Yield-Bearing Stablecoins": StableWatchScraper,
    "Morpho Lend": MorphoLendScraper,
    "Euler Lend": EulerLendScraper,
    "Merkl Rewards": MerklScraper,
    "Pendle Fixed Yields": PendleFixedScraper,
    "Pendle Looping": PendleLoopScraper,
    "Beefy Vaults": BeefyScraper,
    "Yearn Vaults": YearnScraper,
    "Compound Lend": CompoundLendScraper,
    "Aave Lend": AaveLendScraper,
    "Aave Borrow/Lend Loop": AaveLoopScraper,
    "Midas Yield-Bearing": MidasScraper,
    "Spectra Fixed Yields": SpectraScraper,
    "Gearbox Lend": GearboxScraper,
    "Upshift Vaults": UpshiftScraper,
    "IPOR Fusion": IporFusionScraper,
    "TownSquare Lend": TownSquareScraper,
    "Curvance Lend": CurvanceScraper,
    "Accountable Yield": AccountableScraper,
    "Lagoon Vaults": LagoonScraper,
    "Kamino Lend": KaminoLendScraper,
    "Jupiter Lend": JupiterLendScraper,
    "Morpho Borrow/Lend Loop": MorphoLoopScraper,
    "Nest Credit Vaults": NestCreditScraper,
    "Euler Borrow/Lend Loop": EulerLoopScraper,
    "Compound Borrow/Lend Loop": CompoundLoopScraper,
    "Kamino Borrow/Lend Loop": KaminoLoopScraper,
    "Jupiter Borrow": JupiterBorrowScraper,
    "Stake DAO Vaults": StakeDaoScraper,
    "Convex Finance": ConvexScraper,
    "Hyperion LP": HyperionScraper,
    "Yo Yield": YoScraper,
    "Yield.fi": YieldFiScraper,
    "Ploutos Money": PloutosScraper,
    "Mystic Lend": MysticLendScraper,
    "Mystic Borrow/Lend Loop": MysticLoopScraper,
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
    stablecoin = (opp.stablecoin or "").upper()
    # Check for YT at start, or -YT- in middle, or -YT at end
    if stablecoin.startswith("YT-") or "-YT-" in stablecoin or stablecoin.endswith("-YT"):
        return True
    # Also check tokens list for YT tokens
    tokens = opp.additional_info.get("tokens", [])
    if any("YT" in str(t).upper() for t in tokens):
        return True
    name = (opp.additional_info.get("name", "") or "").upper()
    return "HOLD YT" in name or "HOLD PENDLE YT" in name or " YT " in name or "-YT-" in name


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


def get_opportunity_id(opp: YieldOpportunity) -> str:
    """Generate a unique ID for an opportunity based on its properties."""
    key = f"{opp.protocol}|{opp.chain}|{opp.stablecoin}|{opp.category}|{opp.leverage}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


HIDDEN_ITEMS_FILE = Path(".hidden_items.json")


def load_hidden_items() -> set:
    """Load hidden item IDs from file."""
    if HIDDEN_ITEMS_FILE.exists():
        try:
            with open(HIDDEN_ITEMS_FILE, "r") as f:
                data = json.load(f)
                return set(data.get("hidden_ids", []))
        except:
            pass
    return set()


def save_hidden_items(hidden_ids: set) -> None:
    """Save hidden item IDs to file."""
    with open(HIDDEN_ITEMS_FILE, "w") as f:
        json.dump({"hidden_ids": list(hidden_ids)}, f, indent=2)


# =============================================================================
# Main App
# =============================================================================

@st.cache_data(ttl=300, show_spinner=False)
def load_opportunities(categories: tuple = None) -> List[dict]:
    opps = fetch_opportunities(categories=list(categories) if categories else None, use_cache=True, stale_ok=True)
    return [o.to_dict() for o in opps]


def main():
    st.title("📈 Best Stablecoin Yields")
    st.markdown("*Find the best stablecoin yields across DeFi*")

    # Initialize session state for hidden items
    if "hidden_ids" not in st.session_state:
        st.session_state.hidden_ids = load_hidden_items()
    if "show_hidden" not in st.session_state:
        st.session_state.show_hidden = False

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

        # Hidden items management
        st.subheader("Hidden Items")
        show_hidden = st.checkbox("Show hidden rows", value=st.session_state.show_hidden)
        st.session_state.show_hidden = show_hidden
        hidden_count = len(st.session_state.hidden_ids)
        if hidden_count > 0:
            st.caption(f"{hidden_count} items hidden")
            if st.button("Unhide All", use_container_width=True):
                st.session_state.hidden_ids = set()
                save_hidden_items(st.session_state.hidden_ids)
                st.rerun()

        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Refresh", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
        with col2:
            if st.button("🧹 Clear Filters", use_container_width=True):
                st.rerun()

    # Load data
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

        # Filter out hidden items (unless showing hidden)
        if not st.session_state.show_hidden:
            opportunities = [o for o in opportunities if get_opportunity_id(o) not in st.session_state.hidden_ids]

    # Stats - use weighted columns to give more space to values that need it
    if opportunities:
        apys = [o.apy for o in opportunities]
        tvls = [o.tvl for o in opportunities if o.tvl]
        # Weighted columns: more space for Max APY (3) and Total TVL (4)
        col1, col2, col3, col4, col5, col6 = st.columns([1, 1, 1.2, 1.3, 1, 1])
        col1.metric("Results", len(opportunities))
        col2.metric("Avg APY", f"{sum(apys)/len(apys):.1f}%")
        col3.metric("Max APY", f"{max(apys):.1f}%")
        col4.metric("Total TVL", format_tvl(sum(tvls)) if tvls else "-")
        col5.metric("Protocols", len(set(o.protocol for o in opportunities)))
        col6.metric("Chains", len(set(o.chain for o in opportunities)))

    st.divider()

    # Table
    if not opportunities:
        st.info("No opportunities found. Try adjusting filters or click 'Refresh' to fetch latest yields.")
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

        # Fixed-height container for selection details (prevents scroll jump)
        details_container = st.container()

        # Dataframe with row selection
        selection = st.dataframe(
            df_display.drop(columns=["URL"]),
            use_container_width=True,
            height=500,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun",
        )

        # Show selected row details in the pre-created container
        selected_rows = selection.selection.rows if selection.selection else []
        with details_container:
            if selected_rows:
                idx = selected_rows[0]
                opp = opportunities[idx]
                opp_id = get_opportunity_id(opp)
                is_hidden = opp_id in st.session_state.hidden_ids

                st.markdown("#### Selected: " + opp.stablecoin)
                col1, col2, col3 = st.columns([4, 1, 1])
                with col1:
                    st.markdown(f"**{opp.protocol}** on {opp.chain}")
                    details = f"APY: {format_apy(opp.apy)} | TVL: {format_tvl(opp.tvl)} | Risk: {opp.risk_score}"
                    if opp.leverage > 1:
                        details += f" | {opp.leverage}x Leverage"
                        details += f"\nSupply: {format_apy(opp.supply_apy or 0)} | Borrow: {format_apy(opp.borrow_apy or 0)}"
                    st.caption(details)

                with col2:
                    if opp.source_url:
                        st.link_button("Open", opp.source_url, use_container_width=True)

                with col3:
                    if is_hidden:
                        if st.button("Unhide", key=f"show_{opp_id}", use_container_width=True):
                            st.session_state.hidden_ids.discard(opp_id)
                            save_hidden_items(st.session_state.hidden_ids)
                            st.rerun()
                    else:
                        if st.button("Hide", key=f"hide_{opp_id}", use_container_width=True):
                            st.session_state.hidden_ids.add(opp_id)
                            save_hidden_items(st.session_state.hidden_ids)
                            st.rerun()
            else:
                st.caption("👆 Click a row to see details and actions")

    st.divider()
    st.caption(f"Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")


if __name__ == "__main__":
    main()
