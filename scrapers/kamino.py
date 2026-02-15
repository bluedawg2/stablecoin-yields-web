"""Scraper for Kamino Finance on Solana."""

import re
import json
from typing import List, Dict, Any

from .base import BaseScraper
from models.opportunity import YieldOpportunity
from utils.risk import RiskAssessor


class KaminoLendScraper(BaseScraper):
    """Scraper for Kamino lending markets on Solana.

    Fetches data from Kamino's app page (embedded Next.js data).
    """

    requires_vpn = False
    category = "Kamino Lend"
    cache_file = "kamino_lend"

    APP_URL = "https://app.kamino.finance/lending"

    # Minimum TVL
    MIN_TVL_USD = 100_000

    # Stablecoin symbols
    STABLECOIN_SYMBOLS = [
        "USDC", "USDT", "DAI", "FRAX", "PYUSD", "USDS", "USDG", "USD1",
        "FDUSD", "USDH", "AUSD", "USDY", "EURC",
    ]

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Fetch lending data from Kamino."""
        opportunities = []

        try:
            response = self._make_request(self.APP_URL)
            html = response.text

            match = re.search(
                r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
                html,
                re.DOTALL,
            )
            if match:
                page_data = json.loads(match.group(1))
                reserves = self._extract_reserves(page_data)
                if reserves:
                    opportunities = self._parse_reserves(reserves)
        except Exception:
            pass

        return opportunities

    def _extract_reserves(self, page_data: Dict) -> List[Dict]:
        """Extract reserve data from Next.js page data."""
        try:
            props = page_data.get("props", {}).get("pageProps", {})
            for key in ["reserves", "markets", "data", "lending"]:
                if key in props and isinstance(props[key], list):
                    return props[key]
            queries = props.get("dehydratedState", {}).get("queries", [])
            for q in queries:
                data = q.get("state", {}).get("data", [])
                if isinstance(data, list) and len(data) > 0:
                    return data
        except Exception:
            pass
        return []

    def _parse_reserves(self, reserves: List[Dict]) -> List[YieldOpportunity]:
        """Parse reserve data into opportunities."""
        opportunities = []

        for reserve in reserves:
            try:
                symbol = (reserve.get("symbol", "") or "").upper()
                if not self._is_stablecoin(symbol):
                    continue

                apy = float(reserve.get("supplyApy", 0) or reserve.get("apy", 0))
                if apy < 1:
                    apy = apy * 100

                tvl = float(reserve.get("totalSupply", 0) or reserve.get("tvl", 0))
                if tvl < self.MIN_TVL_USD:
                    continue

                if apy <= 0:
                    continue

                borrow_apy = float(reserve.get("borrowApy", 0) or 0)
                if borrow_apy < 1:
                    borrow_apy = borrow_apy * 100

                opp = YieldOpportunity(
                    category=self.category,
                    protocol="Kamino",
                    chain="Solana",
                    stablecoin=symbol,
                    apy=apy,
                    tvl=tvl,
                    supply_apy=apy,
                    borrow_apy=borrow_apy,
                    risk_score=RiskAssessor.calculate_risk_score(
                        strategy_type="lend",
                        protocol="Kamino",
                        chain="Solana",
                        apy=apy,
                    ),
                    source_url="https://app.kamino.finance/lending",
                    additional_info={"borrow_rate": borrow_apy},
                )
                opportunities.append(opp)

            except (KeyError, TypeError, ValueError):
                continue

        return opportunities

    def _is_stablecoin(self, symbol: str) -> bool:
        """Check if symbol is a stablecoin."""
        symbol_upper = symbol.upper()
        for stable in self.STABLECOIN_SYMBOLS:
            if stable in symbol_upper:
                return True
        return False


class KaminoLoopScraper(BaseScraper):
    """Scraper for Kamino borrow/lend loop strategies on Solana.

    Uses Kamino lending data to calculate yield-bearing stablecoin loops.
    """

    requires_vpn = False
    category = "Kamino Borrow/Lend Loop"
    cache_file = "kamino_loop"

    APP_URL = "https://app.kamino.finance/lending"

    # Stablecoins
    STABLECOIN_SYMBOLS = [
        "USDC", "USDT", "DAI", "FRAX", "PYUSD", "USDS", "USDG", "USD1",
        "FDUSD", "USDH", "AUSD", "USDY",
    ]

    # Yield-bearing stablecoins that can serve as collateral for loops
    YIELD_BEARING = {"USDS", "USD1", "USDY", "PYUSD"}

    # LTV for stablecoin collateral on Kamino
    DEFAULT_LTV = 0.80

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Fetch lending data and calculate loop opportunities."""
        opportunities = []

        try:
            response = self._make_request(self.APP_URL)
            html = response.text

            match = re.search(
                r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
                html,
                re.DOTALL,
            )
            if match:
                page_data = json.loads(match.group(1))
                opportunities = self._calculate_loops(page_data)
        except Exception:
            pass

        return opportunities

    def _calculate_loops(self, page_data: Dict) -> List[YieldOpportunity]:
        """Calculate loop opportunities from lending data."""
        opportunities = []

        try:
            props = page_data.get("props", {}).get("pageProps", {})
            reserves = []
            for key in ["reserves", "markets", "data", "lending"]:
                if key in props and isinstance(props[key], list):
                    reserves = props[key]
                    break
            if not reserves:
                queries = props.get("dehydratedState", {}).get("queries", [])
                for q in queries:
                    data = q.get("state", {}).get("data", [])
                    if isinstance(data, list) and len(data) > 0:
                        reserves = data
                        break

            # Build rate lookup
            supply_rates = {}
            borrow_rates = {}
            tvls = {}
            for reserve in reserves:
                symbol = (reserve.get("symbol", "") or "").upper()
                supply_apy = float(reserve.get("supplyApy", 0) or reserve.get("apy", 0))
                if supply_apy < 1:
                    supply_apy *= 100
                borrow_apy = float(reserve.get("borrowApy", 0) or 0)
                if borrow_apy < 1:
                    borrow_apy *= 100
                tvl = float(reserve.get("totalSupply", 0) or reserve.get("tvl", 0))

                supply_rates[symbol] = supply_apy
                borrow_rates[symbol] = borrow_apy
                tvls[symbol] = tvl

            # Calculate loops: deposit yield-bearing, borrow regular
            for collateral in self.YIELD_BEARING:
                if collateral not in supply_rates:
                    continue
                collateral_yield = supply_rates[collateral]
                if collateral_yield <= 0:
                    continue

                for borrow_asset in ["USDC", "USDT"]:
                    if borrow_asset not in borrow_rates:
                        continue
                    borrow_rate = borrow_rates[borrow_asset]
                    if borrow_rate <= 0:
                        continue

                    tvl = tvls.get(collateral, 0)
                    theoretical_max = 1 / (1 - self.DEFAULT_LTV)
                    safe_max = min(theoretical_max * 0.6, 5.0)

                    for leverage in [2.0, 3.0]:
                        if leverage > safe_max:
                            continue

                        net_apy = collateral_yield * leverage - borrow_rate * (leverage - 1)
                        if net_apy <= 0:
                            continue

                        opp = YieldOpportunity(
                            category=self.category,
                            protocol="Kamino",
                            chain="Solana",
                            stablecoin=collateral,
                            apy=net_apy,
                            tvl=tvl,
                            leverage=leverage,
                            supply_apy=collateral_yield,
                            borrow_apy=borrow_rate,
                            risk_score=RiskAssessor.calculate_risk_score(
                                strategy_type="loop",
                                leverage=leverage,
                                protocol="Kamino",
                                chain="Solana",
                                apy=net_apy,
                            ),
                            source_url="https://app.kamino.finance/lending",
                            additional_info={
                                "collateral": collateral,
                                "collateral_yield": collateral_yield,
                                "borrow_asset": borrow_asset,
                                "borrow_rate": borrow_rate,
                                "lltv": self.DEFAULT_LTV * 100,
                            },
                        )
                        opportunities.append(opp)

        except Exception:
            pass

        return opportunities
