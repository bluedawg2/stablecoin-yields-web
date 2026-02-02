"""Scraper for Morpho borrow/lend loop strategies using yield-bearing collateral."""

from typing import List, Dict, Any, Optional

from .base import BaseScraper
from models.opportunity import YieldOpportunity
from utils.risk import RiskAssessor
from config import LEVERAGE_LEVELS


class MorphoLoopScraper(BaseScraper):
    """Calculates leveraged yield from Morpho using yield-bearing collateral.

    Strategy: Deposit yield-bearing stablecoin as collateral, borrow regular stablecoin,
    buy more yield-bearing stablecoin, repeat (loop).

    Example: mHYPER (7.68% yield) as collateral -> borrow USDC (3.82%) -> buy more mHYPER
    Net APY at 5x leverage = 7.68% * 5 - 3.82% * 4 = 23.12%
    """

    requires_vpn = False
    category = "Morpho Borrow/Lend Loop"
    cache_file = "morpho_loop"

    API_URL = "https://blue-api.morpho.org/graphql"

    # Minimum TVL for valid markets
    MIN_TVL_USD = 10_000

    # Maximum borrow APY to consider (filter out extreme rates)
    MAX_BORROW_APY = 50

    # Yield-bearing stablecoin patterns (as collateral)
    YIELD_BEARING_PATTERNS = [
        "SUSDE", "SDAI", "SUSDS", "SFRAX", "MHYPER", "SUSN", "USD0++",
        "SCRVUSD", "SAVUSD", "STUSD", "SUSDX", "PT-",  # PT tokens are yield-bearing
    ]

    # Regular stablecoins (to borrow)
    BORROW_STABLES = [
        "USDC", "USDT", "DAI", "USDS", "PYUSD", "FRAX", "CRVUSD", "GHO", "USDA",
    ]

    # Known yield rates for yield-bearing stablecoins
    # Based on Pendle PT implied yields (more conservative/realistic)
    # These should be updated periodically to reflect current market rates
    YIELD_RATES = {
        "SUSDE": 5.27,      # Based on Pendle PT-sUSDe (~68 day maturity)
        "SDAI": 5.0,        # sDAI savings rate
        "SUSDS": 4.5,       # sUSDS rate
        "SFRAX": 4.0,       # sFRAX rate
        "MHYPER": 6.0,      # mHYPER (conservative estimate)
        "USD0++": 8.0,      # USD0++ (conservative estimate)
        "PT-MHYPER": 6.0,
        "PT-SUSDE": 5.27,
    }

    # Chain ID mappings
    CHAIN_IDS = {
        1: "Ethereum",
        8453: "Base",
        42161: "Arbitrum",
        10: "Optimism",
        10143: "Monad",
    }

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Fetch yield-bearing collateral markets and calculate loop APYs."""
        opportunities = []

        try:
            markets = self._fetch_markets()
            opportunities = self._calculate_loop_opportunities(markets)
        except Exception:
            pass

        return opportunities

    def _fetch_markets(self) -> List[Dict[str, Any]]:
        """Fetch all Morpho markets with yield-bearing collateral."""
        query = """
        {
            markets(first: 500) {
                items {
                    uniqueKey
                    loanAsset {
                        symbol
                        address
                    }
                    collateralAsset {
                        symbol
                        address
                    }
                    state {
                        supplyApy
                        borrowApy
                        supplyAssetsUsd
                        borrowAssetsUsd
                    }
                    lltv
                }
            }
        }
        """

        response = self._make_request(
            self.API_URL,
            method="POST",
            json_data={"query": query},
        )

        data = response.json()
        return data.get("data", {}).get("markets", {}).get("items", [])

    def _calculate_loop_opportunities(self, markets: List[Dict]) -> List[YieldOpportunity]:
        """Calculate loop opportunities for each valid market.

        Args:
            markets: List of Morpho markets.

        Returns:
            List of loop opportunities at various leverage levels.
        """
        opportunities = []

        for market in markets:
            collateral_asset = market.get("collateralAsset")
            loan_asset = market.get("loanAsset")

            if not collateral_asset or not loan_asset:
                continue

            collateral_symbol = collateral_asset.get("symbol", "").upper()
            loan_symbol = loan_asset.get("symbol", "").upper()

            # Check if collateral is yield-bearing
            if not self._is_yield_bearing(collateral_symbol):
                continue

            # Check if loan is a regular stablecoin
            if not self._is_borrow_stable(loan_symbol):
                continue

            # Get market data
            state = market.get("state", {})
            tvl = state.get("supplyAssetsUsd", 0) or 0
            borrow_apy = (state.get("borrowApy", 0) or 0) * 100

            # Filter
            if tvl < self.MIN_TVL_USD:
                continue
            if borrow_apy > self.MAX_BORROW_APY or borrow_apy <= 0:
                continue

            # Get LLTV
            lltv = self._parse_lltv(market.get("lltv", "0"))
            if lltv <= 0:
                continue

            # Get collateral yield rate
            collateral_yield = self._get_collateral_yield(collateral_symbol)
            if collateral_yield <= 0:
                continue

            # Calculate max leverage from LLTV
            theoretical_max_leverage = 1 / (1 - lltv) if lltv < 1 else 1

            # Use SAFE max leverage (60% of theoretical) to avoid liquidation risk
            # At 60% utilization, you have ~40% buffer before liquidation
            safe_max_leverage = theoretical_max_leverage * 0.6
            # Cap at 5x regardless - higher leverage is too risky for stablecoin loops
            safe_max_leverage = min(safe_max_leverage, 5.0)

            # Chain is Ethereum by default (can be extended with chain detection)
            chain = "Ethereum"

            # Calculate loop APY at different leverage levels
            for leverage in LEVERAGE_LEVELS:
                if leverage > safe_max_leverage:
                    continue
                if leverage == 1.0:
                    continue  # Skip 1x, that's just holding

                # Net APY = collateral_yield * leverage - borrow_rate * (leverage - 1)
                net_apy = collateral_yield * leverage - borrow_apy * (leverage - 1)

                if net_apy <= 0:
                    continue

                # Build source URL
                market_id = market.get("uniqueKey", "")
                source_url = f"https://app.morpho.org/market?id={market_id}"

                opp = YieldOpportunity(
                    category=self.category,
                    protocol="Morpho",
                    chain=chain,
                    stablecoin=collateral_symbol,
                    apy=net_apy,
                    tvl=tvl,
                    leverage=leverage,
                    supply_apy=collateral_yield,
                    borrow_apy=borrow_apy,
                    risk_score=RiskAssessor.calculate_risk_score(
                        strategy_type="loop",
                        leverage=leverage,
                        protocol="Morpho",
                        chain=chain,
                        apy=net_apy,
                    ),
                    source_url=source_url,
                    additional_info={
                        "collateral": collateral_symbol,
                        "collateral_yield": collateral_yield,
                        "borrow_asset": loan_symbol,
                        "borrow_rate": borrow_apy,
                        "lltv": lltv * 100,
                        "theoretical_max_leverage": theoretical_max_leverage,
                        "safe_max_leverage": safe_max_leverage,
                        "risk_warning": RiskAssessor.get_leverage_risk_warning(leverage),
                    },
                )
                opportunities.append(opp)

        return opportunities

    def _is_yield_bearing(self, symbol: str) -> bool:
        """Check if symbol is a yield-bearing stablecoin."""
        return any(pattern in symbol for pattern in self.YIELD_BEARING_PATTERNS)

    def _is_borrow_stable(self, symbol: str) -> bool:
        """Check if symbol is a regular stablecoin for borrowing."""
        return any(stable in symbol for stable in self.BORROW_STABLES)

    def _get_collateral_yield(self, symbol: str) -> float:
        """Get the yield rate for a yield-bearing stablecoin.

        Args:
            symbol: Collateral symbol.

        Returns:
            Yield rate as percentage.
        """
        # Check exact match first
        if symbol in self.YIELD_RATES:
            return self.YIELD_RATES[symbol]

        # Check partial match
        for key, rate in self.YIELD_RATES.items():
            if key in symbol:
                return rate

        # Default estimate for unknown yield-bearing assets
        return 5.0

    def _parse_lltv(self, lltv_raw: Any) -> float:
        """Parse LLTV value from various formats.

        Args:
            lltv_raw: Raw LLTV value.

        Returns:
            LLTV as decimal (0-1).
        """
        try:
            lltv_val = float(lltv_raw)
            # If it's a large number, it's in wei (18 decimals)
            if lltv_val > 1:
                return lltv_val / 1e18
            return lltv_val
        except (ValueError, TypeError):
            return 0
