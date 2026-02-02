"""Scraper for Kamino Finance on Solana."""

from typing import List, Dict, Any

from .base import BaseScraper
from models.opportunity import YieldOpportunity
from utils.risk import RiskAssessor


class KaminoLendScraper(BaseScraper):
    """Scraper for Kamino lending markets on Solana."""

    requires_vpn = False
    category = "Kamino Lend"
    cache_file = "kamino_lend"

    # DefiLlama yields API
    API_URL = "https://yields.llama.fi/pools"

    # Minimum TVL
    MIN_TVL_USD = 100_000

    # Stablecoin symbols
    STABLECOIN_SYMBOLS = [
        "USDC", "USDT", "DAI", "FRAX", "PYUSD", "USDS", "USDG", "USD1",
        "FDUSD", "USDH", "AUSD", "USDY", "EURC",
    ]

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Fetch lending data from DefiLlama yields API."""
        opportunities = []

        try:
            response = self._make_request(self.API_URL)
            data = response.json()
            pools = data.get("data", [])
            opportunities = self._parse_pools(pools)
        except Exception:
            opportunities = self._get_fallback_data()

        return opportunities

    def _parse_pools(self, pools: List[Dict]) -> List[YieldOpportunity]:
        """Parse pool data from DefiLlama API."""
        opportunities = []

        for pool in pools:
            try:
                project = pool.get("project", "").lower()

                # Only Kamino Lend pools
                if project != "kamino-lend":
                    continue

                symbol = pool.get("symbol", "").upper()

                # Check if stablecoin
                if not self._is_stablecoin(symbol):
                    continue

                # Get TVL
                tvl = pool.get("tvlUsd", 0)
                if tvl < self.MIN_TVL_USD:
                    continue

                # Get APY
                apy = pool.get("apy", 0)
                if apy <= 0:
                    continue

                chain = pool.get("chain", "Solana")
                pool_id = pool.get("pool", "")

                opp = YieldOpportunity(
                    category=self.category,
                    protocol="Kamino",
                    chain=chain,
                    stablecoin=symbol,
                    apy=apy,
                    tvl=tvl,
                    risk_score=RiskAssessor.calculate_risk_score(
                        strategy_type="lend",
                        protocol="Kamino",
                        chain=chain,
                        apy=apy,
                    ),
                    source_url="https://app.kamino.finance/lending",
                    additional_info={
                        "pool_id": pool_id,
                        "pool_meta": pool.get("poolMeta"),
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

    def _get_fallback_data(self) -> List[YieldOpportunity]:
        """Return fallback data when API fails."""
        fallback = [
            {"symbol": "USDC", "apy": 3.25, "tvl": 47_000_000},
            {"symbol": "PYUSD", "apy": 0.5, "tvl": 150_000_000},
            {"symbol": "USDS", "apy": 0.7, "tvl": 11_000_000},
            {"symbol": "USDT", "apy": 0.8, "tvl": 8_000_000},
        ]

        opportunities = []
        for item in fallback:
            opp = YieldOpportunity(
                category=self.category,
                protocol="Kamino",
                chain="Solana",
                stablecoin=item["symbol"],
                apy=item["apy"],
                tvl=item["tvl"],
                risk_score="Low",
                source_url="https://app.kamino.finance/lending",
            )
            opportunities.append(opp)

        return opportunities


class KaminoLoopScraper(BaseScraper):
    """Scraper for Kamino borrow/lend loop strategies on Solana."""

    requires_vpn = False
    category = "Kamino Borrow/Lend Loop"
    cache_file = "kamino_loop"

    # DefiLlama yields API
    API_URL = "https://yields.llama.fi/pools"

    # Minimum TVL
    MIN_TVL_USD = 50_000

    # Stablecoin symbols
    STABLECOIN_SYMBOLS = [
        "USDC", "USDT", "DAI", "FRAX", "PYUSD", "USDS", "USDG", "USD1",
        "FDUSD", "USDH", "AUSD", "USDY",
    ]

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Fetch liquidity data from DefiLlama yields API."""
        opportunities = []

        try:
            response = self._make_request(self.API_URL)
            data = response.json()
            pools = data.get("data", [])
            opportunities = self._parse_pools(pools)
        except Exception:
            opportunities = self._get_fallback_data()

        return opportunities

    def _parse_pools(self, pools: List[Dict]) -> List[YieldOpportunity]:
        """Parse pool data from DefiLlama API."""
        opportunities = []

        for pool in pools:
            try:
                project = pool.get("project", "").lower()

                # Only Kamino Liquidity pools (LP strategies)
                if project != "kamino-liquidity":
                    continue

                symbol = pool.get("symbol", "").upper()

                # Check if stablecoin LP
                if not self._is_stablecoin_pool(symbol):
                    continue

                # Get TVL
                tvl = pool.get("tvlUsd", 0)
                if tvl < self.MIN_TVL_USD:
                    continue

                # Get APY
                apy = pool.get("apy", 0)
                if apy <= 0:
                    continue

                # Filter out very high APYs (likely temporary/unsustainable)
                if apy > 100:
                    continue

                chain = pool.get("chain", "Solana")
                pool_id = pool.get("pool", "")

                opp = YieldOpportunity(
                    category=self.category,
                    protocol="Kamino",
                    chain=chain,
                    stablecoin=symbol,
                    apy=apy,
                    tvl=tvl,
                    risk_score=RiskAssessor.calculate_risk_score(
                        strategy_type="lp",
                        protocol="Kamino",
                        chain=chain,
                        apy=apy,
                    ),
                    source_url="https://app.kamino.finance/liquidity",
                    additional_info={
                        "pool_id": pool_id,
                        "pool_meta": pool.get("poolMeta"),
                        "is_lp": True,
                    },
                )
                opportunities.append(opp)

            except (KeyError, TypeError, ValueError):
                continue

        return opportunities

    def _is_stablecoin_pool(self, symbol: str) -> bool:
        """Check if pool is a stablecoin-stablecoin pair.

        Excludes mixed pairs like SOL-USDC or SOL-USDT.
        """
        symbol_upper = symbol.upper()

        # Split into token pairs
        parts = symbol_upper.replace("-", "/").split("/")

        if len(parts) != 2:
            # Single token or unknown format - check if it's a stablecoin
            for stable in self.STABLECOIN_SYMBOLS:
                if stable in symbol_upper:
                    return True
            return False

        # For LP pools, require BOTH tokens to be stablecoins
        # This excludes pairs like SOL-USDC, SOL-USDT, etc.
        stable_count = sum(1 for p in parts if any(s in p for s in self.STABLECOIN_SYMBOLS))
        return stable_count == 2

    def _get_fallback_data(self) -> List[YieldOpportunity]:
        """Return fallback data when API fails."""
        fallback = [
            {"symbol": "USDS-USDC", "apy": 0.5, "tvl": 25_000_000},
            {"symbol": "PYUSD-USDC", "apy": 0.1, "tvl": 30_000_000},
        ]

        opportunities = []
        for item in fallback:
            opp = YieldOpportunity(
                category=self.category,
                protocol="Kamino",
                chain="Solana",
                stablecoin=item["symbol"],
                apy=item["apy"],
                tvl=item["tvl"],
                risk_score="Medium",
                source_url="https://app.kamino.finance/liquidity",
            )
            opportunities.append(opp)

        return opportunities
