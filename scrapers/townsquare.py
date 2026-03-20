"""Scraper for TownSquare lending (supply APY only, no points)."""

from typing import List, Dict, Any

from .base import BaseScraper
from models.opportunity import YieldOpportunity
from utils.risk import RiskAssessor


class TownSquareScraper(BaseScraper):
    """Scraper for TownSquare lending rates (supply APY without TownSq points)."""

    requires_vpn = False
    category = "TownSquare Lend"
    cache_file = "townsquare"

    # TownSquare API endpoint
    API_URL = "https://api.townsq.xyz/v1/markets"

    # Minimum TVL
    MIN_TVL_USD = 10_000

    # Stablecoin symbols
    STABLECOIN_SYMBOLS = [
        "USDC", "USDT", "DAI", "FRAX", "LUSD", "SDAI", "SUSDE", "USDE",
        "USDS", "GHO", "CRVUSD", "PYUSD",
    ]

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Fetch market data from TownSquare."""
        opportunities = []

        # Try multiple API patterns
        api_urls = [
            "https://api.townsq.xyz/v1/markets",
            "https://app.townsq.xyz/api/markets",
            "https://townsq.xyz/api/v1/markets",
        ]

        for api_url in api_urls:
            try:
                response = self._make_request(api_url)
                data = response.json()
                opportunities = self._parse_markets(data)
                if opportunities:
                    break
            except Exception:
                continue

        return opportunities

    def _parse_markets(self, data: Any) -> List[YieldOpportunity]:
        """Parse market data from API."""
        opportunities = []

        markets = data if isinstance(data, list) else data.get("markets", data.get("data", []))

        for market in markets:
            try:
                # Get asset symbol
                asset = market.get("asset", {})
                symbol = asset.get("symbol", "") or market.get("symbol", "") or market.get("token", "")

                if not self._is_stablecoin(symbol):
                    continue

                # Get supply APY (base rate only, excluding points)
                # Look for base APY, not total APY which includes points
                supply_apy = float(
                    market.get("supplyApy", 0) or
                    market.get("baseSupplyApy", 0) or
                    market.get("nativeApy", 0) or
                    market.get("apy", 0)
                )

                # If there's a separate points APY, subtract it
                points_apy = float(market.get("pointsApy", 0) or market.get("townsqPointsApy", 0))
                if points_apy > 0 and supply_apy > points_apy:
                    supply_apy = supply_apy - points_apy

                if supply_apy < 1:
                    supply_apy = supply_apy * 100

                if supply_apy <= 0:
                    continue

                # Get TVL
                tvl = float(market.get("tvl", 0) or market.get("totalSupply", 0) or market.get("totalValueLocked", 0))
                if tvl < self.MIN_TVL_USD:
                    continue

                # Get chain
                chain = market.get("chain", "Ethereum")
                if isinstance(chain, dict):
                    chain = chain.get("name", "Ethereum")

                # Get borrow rate
                borrow_apy = float(market.get("borrowApy", 0) or market.get("baseBorrowApy", 0))
                if borrow_apy < 1:
                    borrow_apy = borrow_apy * 100

                opp = YieldOpportunity(
                    category=self.category,
                    protocol="TownSquare",
                    chain=chain,
                    stablecoin=symbol,
                    apy=supply_apy,
                    tvl=tvl,
                    supply_apy=supply_apy,
                    borrow_apy=borrow_apy,
                    risk_score=RiskAssessor.calculate_risk_score(
                        strategy_type="lend",
                        protocol="TownSquare",
                        chain=chain,
                        apy=supply_apy,
                    ),
                    source_url="https://app.townsq.xyz/",
                    additional_info={
                        "market_address": market.get("address", ""),
                        "borrow_rate": borrow_apy,
                        "points_excluded": True,
                    },
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

