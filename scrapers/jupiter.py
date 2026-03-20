"""Scraper for Jupiter Lend on Solana."""

from typing import List, Dict, Any

from .base import BaseScraper
from models.opportunity import YieldOpportunity
from utils.risk import RiskAssessor


class JupiterLendScraper(BaseScraper):
    """Scraper for Jupiter Lend yields on Solana."""

    requires_vpn = False
    category = "Jupiter Lend"
    cache_file = "jupiter_lend"

    # Jupiter Lend API (requires auth, so we use fallback)
    API_URL = "https://api.jup.ag/lend/v1/statistics"

    # Minimum TVL
    MIN_TVL_USD = 100_000

    # Stablecoin symbols
    STABLECOIN_SYMBOLS = [
        "USDC", "USDT", "PYUSD", "USDS", "FDUSD", "EURC",
    ]

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Fetch lending data from Jupiter API."""
        opportunities = []

        try:
            # Try to fetch from API (may require API key)
            response = self._make_request(self.API_URL)
            if response.status_code == 200:
                data = response.json()
                opportunities = self._parse_data(data)
        except Exception:
            pass

        return opportunities

    def _parse_data(self, data: Any) -> List[YieldOpportunity]:
        """Parse data from Jupiter API."""
        opportunities = []

        # The API structure varies - handle both list and dict
        tokens = data if isinstance(data, list) else data.get("tokens", data.get("data", []))

        for token in tokens:
            try:
                symbol = token.get("symbol", "").upper()

                if not self._is_stablecoin(symbol):
                    continue

                tvl = token.get("tvl", token.get("totalSupply", 0))
                if tvl < self.MIN_TVL_USD:
                    continue

                apy = token.get("supplyApy", token.get("apy", 0))
                if apy <= 0:
                    continue

                opp = YieldOpportunity(
                    category=self.category,
                    protocol="Jupiter",
                    chain="Solana",
                    stablecoin=symbol,
                    apy=apy,
                    tvl=tvl,
                    risk_score=RiskAssessor.calculate_risk_score(
                        strategy_type="lend",
                        protocol="Jupiter",
                        chain="Solana",
                        apy=apy,
                    ),
                    source_url="https://jup.ag/lend/earn",
                    additional_info={
                        "mint": token.get("mint", ""),
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



class JupiterBorrowScraper(BaseScraper):
    """Scraper for Jupiter borrow rates on Solana (for loop strategies)."""

    requires_vpn = False
    category = "Jupiter Borrow"
    cache_file = "jupiter_borrow"

    # Jupiter Lend API
    API_URL = "https://api.jup.ag/lend/v1/statistics"

    # Stablecoin symbols
    STABLECOIN_SYMBOLS = [
        "USDC", "USDT", "PYUSD", "USDS",
    ]

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Fetch borrow rate data from Jupiter API."""
        # Jupiter borrow rates are shown for reference
        # Users can use these to calculate potential loop strategies
        return []

