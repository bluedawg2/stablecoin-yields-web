"""Scraper for Mystic Finance lending on Plume."""

import re
import json
from typing import List, Dict, Any

from .base import BaseScraper
from models.opportunity import YieldOpportunity
from utils.risk import RiskAssessor


class MysticLendScraper(BaseScraper):
    """Scraper for Mystic Finance lending markets on Plume.

    Mystic is an Aave V3 fork on Plume that enables lending, borrowing,
    and looping strategies with RWA-backed stablecoins.
    """

    requires_vpn = False
    category = "Mystic Lend"
    cache_file = "mystic_lend"

    PAGE_URL = "https://app.mysticfinance.xyz/"

    # Plume RPC for contract reads
    PLUME_RPC = "https://rpc.plumenetwork.xyz"

    # Stablecoin symbols
    STABLECOIN_SYMBOLS = [
        "USDC", "USDT", "DAI", "USDS", "NUSD", "PUSD",
    ]

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Fetch lending data from Mystic Finance."""
        opportunities = []

        # Try to fetch from the Mystic app page (SPA with embedded data)
        try:
            response = self._make_request(self.PAGE_URL)
            html = response.text

            # Try Next.js data
            match = re.search(
                r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
                html,
                re.DOTALL,
            )
            if match:
                page_data = json.loads(match.group(1))
                opportunities = self._parse_page_data(page_data)

            if not opportunities:
                # Try to find inline JSON data
                json_match = re.search(r'"reserves"\s*:\s*(\[.*?\])', html, re.DOTALL)
                if json_match:
                    reserves = json.loads(json_match.group(1))
                    opportunities = self._parse_reserves(reserves)
        except Exception:
            pass

        return opportunities

    def _parse_page_data(self, page_data: Dict) -> List[YieldOpportunity]:
        """Parse Next.js page data for market info."""
        opportunities = []

        try:
            props = page_data.get("props", {}).get("pageProps", {})
            reserves = props.get("reserves", props.get("markets", []))
            if reserves:
                opportunities = self._parse_reserves(reserves)
        except Exception:
            pass

        return opportunities

    def _parse_reserves(self, reserves: List[Dict]) -> List[YieldOpportunity]:
        """Parse reserve/market data."""
        opportunities = []

        for reserve in reserves:
            try:
                symbol = (reserve.get("symbol", "") or "").upper()
                if not self._is_stablecoin(symbol):
                    continue

                supply_apy = float(reserve.get("supplyAPY", 0) or reserve.get("liquidityRate", 0))
                if supply_apy < 1:
                    supply_apy = supply_apy * 100

                borrow_apy = float(reserve.get("borrowAPY", 0) or reserve.get("variableBorrowRate", 0))
                if borrow_apy < 1:
                    borrow_apy = borrow_apy * 100

                tvl = float(reserve.get("totalLiquidity", 0) or reserve.get("tvl", 0))

                if supply_apy <= 0:
                    continue

                opp = YieldOpportunity(
                    category=self.category,
                    protocol="Mystic",
                    chain="Plume",
                    stablecoin=symbol,
                    apy=supply_apy,
                    tvl=tvl,
                    supply_apy=supply_apy,
                    borrow_apy=borrow_apy,
                    risk_score=RiskAssessor.calculate_risk_score(
                        strategy_type="simple_lend",
                        protocol="Mystic",
                        chain="Plume",
                        apy=supply_apy,
                    ),
                    source_url="https://app.mysticfinance.xyz/",
                    additional_info={
                        "borrow_rate": borrow_apy,
                    },
                )
                opportunities.append(opp)

            except (KeyError, TypeError, ValueError):
                continue

        return opportunities

    def _is_stablecoin(self, symbol: str) -> bool:
        """Check if symbol is a stablecoin."""
        symbol_upper = symbol.upper()
        return any(stable in symbol_upper for stable in self.STABLECOIN_SYMBOLS)



class MysticLoopScraper(BaseScraper):
    """Scraper for Mystic Finance borrow/lend loop strategies on Plume.

    Uses Nest Credit vault yields as collateral, borrows stablecoins on Mystic.
    """

    requires_vpn = False
    category = "Mystic Borrow/Lend Loop"
    cache_file = "mystic_loop"

    # Nest Credit yield-bearing tokens available as collateral on Mystic
    COLLATERAL_YIELDS = {
        "nTBILL": 5.5,
        "nBASIS": 8.0,
        "nALPHA": 11.5,
        "nCREDIT": 8.0,
    }

    # Default borrow rate for stablecoins on Mystic (conservative estimate)
    DEFAULT_BORROW_RATE = 5.0

    # LTV for Nest tokens on Mystic
    DEFAULT_LTV = 0.75

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Calculate loop opportunities using Nest tokens as collateral."""
        opportunities = []

        # Calculate loop strategies for each Nest token
        for collateral, yield_rate in self.COLLATERAL_YIELDS.items():
            borrow_rate = self.DEFAULT_BORROW_RATE
            lltv = self.DEFAULT_LTV

            # Calculate max safe leverage
            theoretical_max = 1 / (1 - lltv) if lltv < 1 else 1
            safe_max = min(theoretical_max * 0.6, 5.0)

            for leverage in [2.0, 3.0]:
                if leverage > safe_max:
                    continue

                net_apy = yield_rate * leverage - borrow_rate * (leverage - 1)
                if net_apy <= 0:
                    continue

                opp = YieldOpportunity(
                    category=self.category,
                    protocol="Mystic",
                    chain="Plume",
                    stablecoin=collateral,
                    apy=net_apy,
                    tvl=10_000_000,  # Estimated
                    leverage=leverage,
                    supply_apy=yield_rate,
                    borrow_apy=borrow_rate,
                    risk_score=RiskAssessor.calculate_risk_score(
                        strategy_type="loop",
                        leverage=leverage,
                        protocol="Mystic",
                        chain="Plume",
                        apy=net_apy,
                    ),
                    source_url="https://app.mysticfinance.xyz/",
                    additional_info={
                        "collateral": collateral,
                        "collateral_yield": yield_rate,
                        "borrow_asset": "USDC",
                        "borrow_rate": borrow_rate,
                        "lltv": lltv * 100,
                    },
                )
                opportunities.append(opp)

        return opportunities
