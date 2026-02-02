"""Scraper for Euler lending rates via DefiLlama API."""

from typing import List, Dict, Any

from .base import BaseScraper
from models.opportunity import YieldOpportunity
from utils.risk import RiskAssessor


class EulerLendScraper(BaseScraper):
    """Scraper for Euler lending rates via DefiLlama pools API.

    Note: TAC chain may not be available in DefiLlama yet.
    For TAC chain data, check app.euler.finance directly.
    """

    requires_vpn = False
    category = "Euler Lend"
    cache_file = "euler_lend"

    # DefiLlama pools API (has pre-calculated APYs)
    DEFILLAMA_API = "https://yields.llama.fi/pools"

    # Minimum TVL to filter out empty/unreliable markets
    MIN_TVL_USD = 10_000

    # Maximum reasonable APY (filter out anomalies/data errors)
    # Real lending rates rarely exceed 25% sustainably
    MAX_APY_PERCENT = 25

    # Chains where Euler actually has active vaults
    # Avalanche is NOT supported by Euler - filter it out
    SUPPORTED_EULER_CHAINS = [
        "Ethereum", "Base", "Arbitrum", "Optimism",
        "Sonic", "Berachain", "Bob", "Swell", "Ink",
    ]

    # Stablecoin symbols to filter
    STABLECOIN_SYMBOLS = [
        "USDC", "USDT", "DAI", "FRAX", "LUSD", "SDAI", "SUSDE", "USDE",
        "USDS", "SUSDS", "GHO", "CRVUSD", "PYUSD", "USDM", "TUSD",
        "GUSD", "USDP", "DOLA", "MIM", "ALUSD", "FDUSD", "RLUSD",
        "YOUSD", "YUSD", "USN", "USD",
    ]

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Fetch lending rates from DefiLlama API."""
        opportunities = []

        try:
            response = self._make_request(self.DEFILLAMA_API)
            data = response.json()
            pools = data.get("data", [])

            # Filter for Euler pools
            euler_pools = [p for p in pools if "euler" in p.get("project", "").lower()]

            for pool in euler_pools:
                opp = self._parse_pool(pool)
                if opp:
                    opportunities.append(opp)

        except Exception:
            pass

        return opportunities

    def _parse_pool(self, pool: Dict[str, Any]) -> YieldOpportunity | None:
        """Parse a DefiLlama pool into an opportunity.

        Args:
            pool: Pool data from DefiLlama.

        Returns:
            YieldOpportunity or None if not valid.
        """
        try:
            symbol = pool.get("symbol", "")
            chain = pool.get("chain", "")
            apy = pool.get("apy", 0) or 0
            tvl = pool.get("tvlUsd", 0) or 0
            pool_id = pool.get("pool", "")

            # Filter for stablecoins
            if not self._is_stablecoin(symbol):
                return None

            # Filter out chains where Euler doesn't have vaults
            if chain not in self.SUPPORTED_EULER_CHAINS:
                return None

            # Filter out low TVL
            if tvl < self.MIN_TVL_USD:
                return None

            # Filter out unrealistic APY (likely data errors from DefiLlama)
            if apy <= 0 or apy > self.MAX_APY_PERCENT:
                return None

            return YieldOpportunity(
                category=self.category,
                protocol="Euler",
                chain=chain,
                stablecoin=symbol,
                apy=apy,
                tvl=tvl,
                supply_apy=apy,
                risk_score=RiskAssessor.calculate_risk_score(
                    strategy_type="simple_lend",
                    protocol="Euler",
                    chain=chain,
                    apy=apy,
                ),
                source_url="https://app.euler.finance",
                additional_info={
                    "pool_id": pool_id,
                    "data_source": "DefiLlama",
                },
            )

        except (KeyError, TypeError, ValueError):
            return None

    def _is_stablecoin(self, symbol: str) -> bool:
        """Check if a symbol is a stablecoin.

        Args:
            symbol: Token symbol.

        Returns:
            True if stablecoin.
        """
        symbol_upper = symbol.upper()
        return any(stable in symbol_upper for stable in self.STABLECOIN_SYMBOLS)
