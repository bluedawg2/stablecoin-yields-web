"""Scraper for Pendle fixed yields."""

from datetime import datetime
from typing import List, Dict, Any, Optional

from .base import BaseScraper
from models.opportunity import YieldOpportunity
from utils.risk import RiskAssessor
from config import PENDLE_TARGET_STABLECOINS


class PendleFixedScraper(BaseScraper):
    """Scraper for Pendle fixed yield opportunities."""

    requires_vpn = False
    category = "Pendle Fixed Yields"
    cache_file = "pendle_fixed"

    API_URL = "https://api-v2.pendle.finance/core/v1"

    # Chain ID mappings for Pendle
    CHAIN_IDS = {
        "Ethereum": 1,
        "Arbitrum": 42161,
        "Base": 8453,
        "Optimism": 10,
        "BSC": 56,
    }

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Fetch fixed yield data from Pendle."""
        opportunities = []

        for chain_name, chain_id in self.CHAIN_IDS.items():
            try:
                chain_opps = self._fetch_chain_data(chain_name, chain_id)
                opportunities.extend(chain_opps)
            except Exception:
                continue

        # Fallback to known markets if API fails
        if not opportunities:
            opportunities = self._get_known_markets()

        return opportunities

    def _fetch_chain_data(self, chain_name: str, chain_id: int) -> List[YieldOpportunity]:
        """Fetch data for a specific chain.

        Args:
            chain_name: Name of the chain.
            chain_id: Chain ID.

        Returns:
            List of opportunities for this chain.
        """
        # Fetch markets
        response = self._make_request(
            f"{self.API_URL}/{chain_id}/markets",
        )

        data = response.json()
        return self._parse_markets(data, chain_name)

    def _parse_markets(self, data: Any, chain: str) -> List[YieldOpportunity]:
        """Parse market data from API response.

        Args:
            data: API response data.
            chain: Chain name.

        Returns:
            List of opportunities.
        """
        opportunities = []

        # Handle response format
        markets = data if isinstance(data, list) else data.get("results", data.get("markets", []))

        for market in markets:
            try:
                # Get underlying asset info
                underlying = market.get("underlyingAsset", market.get("underlying", {}))
                symbol = underlying.get("symbol", market.get("symbol", ""))

                # Filter for target stablecoins
                if not self._is_target_stablecoin(symbol):
                    continue

                # Extract fixed yield (PT implied APY)
                fixed_apy = self._extract_fixed_apy(market)
                if fixed_apy <= 0:
                    continue

                # Extract maturity date
                maturity = self._extract_maturity(market)

                # Extract TVL
                tvl = market.get("liquidity", {}).get("usd", market.get("tvl", 0))

                # Get protocol name
                protocol = market.get("protocol", market.get("name", "Pendle"))

                opp = YieldOpportunity(
                    category=self.category,
                    protocol=f"Pendle ({protocol})" if protocol != "Pendle" else "Pendle",
                    chain=chain,
                    stablecoin=symbol,
                    apy=fixed_apy,
                    tvl=tvl,
                    maturity_date=maturity,
                    risk_score=RiskAssessor.calculate_risk_score(
                        strategy_type="pendle_fixed",
                        protocol="Pendle",
                        chain=chain,
                        maturity_date=maturity,
                        apy=fixed_apy,
                    ),
                    source_url="https://app.pendle.finance/trade/markets",
                    additional_info={
                        "maturity": maturity.isoformat() if maturity else None,
                        "pt_symbol": f"PT-{symbol}",
                    },
                )
                opportunities.append(opp)

            except (KeyError, TypeError, ValueError):
                continue

        return opportunities

    def _is_target_stablecoin(self, symbol: str) -> bool:
        """Check if symbol matches target stablecoins.

        Args:
            symbol: Token symbol.

        Returns:
            True if target stablecoin.
        """
        symbol_upper = symbol.upper()

        # Check against target list (exact or partial match)
        for target in PENDLE_TARGET_STABLECOINS:
            target_upper = target.upper()
            if target_upper in symbol_upper or symbol_upper in target_upper:
                return True

        # Match any symbol containing "USD" (catches stcUSD, cUSD, etc.)
        if "USD" in symbol_upper:
            return True

        # Match other common stable patterns
        stable_patterns = ["DAI", "FRAX", "LUSD", "GHO", "PYUSD", "DOLA", "MIM"]
        return any(p in symbol_upper for p in stable_patterns)

    def _extract_fixed_apy(self, market: dict) -> float:
        """Extract fixed APY from market data.

        Args:
            market: Market data.

        Returns:
            Fixed APY as percentage.
        """
        # Try various field names for PT implied APY
        for key in ["impliedApy", "ptApy", "fixedApy", "apy", "ptImpliedApy"]:
            if key in market:
                val = market[key]
                if isinstance(val, (int, float)):
                    return float(val) * 100 if val < 1 else float(val)

        # Try nested structure
        pt = market.get("pt", {})
        for key in ["impliedApy", "apy"]:
            if key in pt:
                val = pt[key]
                if isinstance(val, (int, float)):
                    return float(val) * 100 if val < 1 else float(val)

        return 0.0

    def _extract_maturity(self, market: dict) -> Optional[datetime]:
        """Extract maturity date from market data.

        Args:
            market: Market data.

        Returns:
            Maturity datetime or None.
        """
        for key in ["expiry", "maturity", "expiryDate", "maturityDate"]:
            if key in market:
                val = market[key]
                if isinstance(val, (int, float)):
                    # Unix timestamp
                    return datetime.fromtimestamp(val)
                if isinstance(val, str):
                    try:
                        return datetime.fromisoformat(val.replace("Z", "+00:00"))
                    except ValueError:
                        try:
                            return datetime.strptime(val, "%Y-%m-%d")
                        except ValueError:
                            pass
        return None

    def _get_known_markets(self) -> List[YieldOpportunity]:
        """Return empty list - do not generate fake fallback data.

        Previously this generated hardcoded fake markets with computed maturity dates,
        which resulted in phantom opportunities (e.g., PT-USDe-16Mar2026) that don't
        actually exist on Pendle. Better to show nothing than fake data.
        """
        return []
