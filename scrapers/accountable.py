"""Scraper for Accountable Capital yields."""

from typing import List, Dict, Any

from .base import BaseScraper
from models.opportunity import YieldOpportunity
from utils.risk import RiskAssessor


class AccountableScraper(BaseScraper):
    """Scraper for Accountable Capital yield opportunities."""

    requires_vpn = False
    category = "Accountable Yield"
    cache_file = "accountable"

    # Accountable API endpoint
    API_URL = "https://api.accountable.capital/v1/yields"

    # Minimum TVL
    MIN_TVL_USD = 10_000

    # Stablecoin symbols
    STABLECOIN_SYMBOLS = [
        "USDC", "USDT", "DAI", "FRAX", "LUSD", "SDAI", "SUSDE", "USDE",
        "USDS", "GHO", "CRVUSD", "PYUSD",
    ]

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Fetch yield data from Accountable Capital."""
        opportunities = []

        # Try multiple API patterns
        api_urls = [
            "https://api.accountable.capital/v1/yields",
            "https://yield.accountable.capital/api/yields",
            "https://accountable.capital/api/v1/yields",
        ]

        for api_url in api_urls:
            try:
                response = self._make_request(api_url)
                data = response.json()
                opportunities = self._parse_yields(data)
                if opportunities:
                    break
            except Exception:
                continue

        if not opportunities:
            opportunities = self._get_fallback_data()

        return opportunities

    def _parse_yields(self, data: Any) -> List[YieldOpportunity]:
        """Parse yield data from API."""
        opportunities = []

        yields = data if isinstance(data, list) else data.get("yields", data.get("opportunities", data.get("data", [])))

        for yield_item in yields:
            try:
                # Get asset symbol
                symbol = yield_item.get("asset", "") or yield_item.get("symbol", "") or yield_item.get("token", "")

                if not self._is_stablecoin(symbol):
                    continue

                # Get APY
                apy = float(yield_item.get("apy", 0) or yield_item.get("yield", 0) or yield_item.get("rate", 0))
                if apy < 1:
                    apy = apy * 100

                if apy <= 0:
                    continue

                # Get TVL
                tvl = float(yield_item.get("tvl", 0) or yield_item.get("totalValueLocked", 0))
                if tvl < self.MIN_TVL_USD:
                    continue

                # Get chain
                chain = yield_item.get("chain", "Ethereum")
                if isinstance(chain, dict):
                    chain = chain.get("name", "Ethereum")

                # Get protocol
                protocol = yield_item.get("protocol", "Accountable")

                opp = YieldOpportunity(
                    category=self.category,
                    protocol=f"Accountable ({protocol})" if protocol != "Accountable" else "Accountable",
                    chain=chain,
                    stablecoin=symbol,
                    apy=apy,
                    tvl=tvl,
                    risk_score=RiskAssessor.calculate_risk_score(
                        strategy_type="vault",
                        protocol="Accountable",
                        chain=chain,
                        apy=apy,
                    ),
                    source_url="https://yield.accountable.capital/",
                    additional_info={
                        "underlying_protocol": protocol,
                        "verified": yield_item.get("verified", True),
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
        """Return fallback data when API fails.

        Based on vaults listed at yield.accountable.capital.
        Note: Delta neutral and cBTC vaults are excluded (not stablecoins).
        """
        fallback = [
            {
                "name": "Aegis Yield Vault",
                "symbol": "USDC",
                "chain": "Ethereum",
                "apy": 22.25,
                "tvl": 5_000_000,
            },
            {
                "name": "Yuzu Money Vault",
                "symbol": "USDC",
                "chain": "Ethereum",
                "apy": 13.7,
                "tvl": 8_000_000,
            },
            {
                "name": "Asia Credit Yield Vault",
                "symbol": "USDC",
                "chain": "Ethereum",
                "apy": 9.25,
                "tvl": 10_000_000,
            },
        ]

        opportunities = []
        for item in fallback:
            opp = YieldOpportunity(
                category=self.category,
                protocol="Accountable",
                chain=item["chain"],
                stablecoin=item["symbol"],
                apy=item["apy"],
                tvl=item["tvl"],
                risk_score=RiskAssessor.calculate_risk_score(
                    strategy_type="vault",
                    protocol="Accountable",
                    chain=item["chain"],
                    apy=item["apy"],
                ),
                source_url="https://yield.accountable.capital/",
                additional_info={
                    "vault_name": item["name"],
                    "verified": True,
                },
            )
            opportunities.append(opp)

        return opportunities
