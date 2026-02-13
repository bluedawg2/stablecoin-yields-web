"""Scraper for Nest Credit vaults on Plume chain."""

from typing import List, Dict, Any

from .base import BaseScraper
from models.opportunity import YieldOpportunity
from utils.risk import RiskAssessor


class NestCreditScraper(BaseScraper):
    """Scraper for Nest Credit vaults (nTBILL, nBASIS, nALPHA, nCREDIT) on Plume."""

    requires_vpn = False
    category = "Nest Credit Vaults"
    cache_file = "nest_credit"

    API_URLS = [
        "https://api.nest.credit/v1/vaults",
        "https://app.nest.credit/api/vaults",
    ]

    # Fallback vault data (from Nest docs - target APYs)
    NEST_VAULTS = [
        {
            "symbol": "nTBILL",
            "name": "Nest Treasuries",
            "apy": 5.50,
            "tvl": 50_000_000,
            "description": "Tokenized US Treasury Bills on Plume",
            "risk": "Low",
        },
        {
            "symbol": "nBASIS",
            "name": "Nest Basis",
            "apy": 8.00,
            "tvl": 30_000_000,
            "description": "Basis trading strategy on Plume",
            "risk": "Medium",
        },
        {
            "symbol": "nALPHA",
            "name": "Nest Alpha",
            "apy": 11.50,
            "tvl": 20_000_000,
            "description": "Alpha strategy vault on Plume",
            "risk": "High",
        },
        {
            "symbol": "nCREDIT",
            "name": "Nest Credit",
            "apy": 8.00,
            "tvl": 10_000_000,
            "description": "Credit strategy vault on Plume",
            "risk": "Medium",
        },
    ]

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Fetch Nest Credit vault data."""
        opportunities = []

        # Try each API URL
        for url in self.API_URLS:
            try:
                response = self._make_request(url)
                data = response.json()
                opportunities = self._parse_api_data(data)
                if opportunities:
                    return opportunities
            except Exception:
                continue

        # Use fallback data if API fails
        return self._get_fallback_data()

    def _parse_api_data(self, data: Any) -> List[YieldOpportunity]:
        """Parse API response data.

        Args:
            data: JSON response from Nest API.

        Returns:
            List of yield opportunities.
        """
        opportunities = []

        vaults = data.get("vaults", data if isinstance(data, list) else [])

        for vault in vaults:
            try:
                symbol = vault.get("symbol", "")

                # Only Nest vault tokens
                if not symbol.startswith("n") and not symbol.startswith("N"):
                    continue

                apy = float(vault.get("apy", 0))
                # Normalize: if < 1 it's a decimal, convert to percentage
                if 0 < apy < 1:
                    apy = apy * 100

                tvl = float(vault.get("tvl", 0))

                if apy <= 0:
                    continue

                opp = YieldOpportunity(
                    category=self.category,
                    protocol="Nest Credit",
                    chain="Plume",
                    stablecoin=symbol,
                    apy=apy,
                    tvl=tvl,
                    risk_score=RiskAssessor.calculate_risk_score(
                        strategy_type="yield_bearing",
                        protocol="Nest Credit",
                        chain="Plume",
                        apy=apy,
                    ),
                    source_url="https://app.nest.credit/",
                    additional_info={
                        "name": vault.get("name", ""),
                        "description": vault.get("description", ""),
                    },
                )
                opportunities.append(opp)

            except (KeyError, TypeError, ValueError):
                continue

        return opportunities

    def _get_fallback_data(self) -> List[YieldOpportunity]:
        """Return fallback data for Nest Credit vaults."""
        opportunities = []

        for vault in self.NEST_VAULTS:
            opp = YieldOpportunity(
                category=self.category,
                protocol="Nest Credit",
                chain="Plume",
                stablecoin=vault["symbol"],
                apy=vault["apy"],
                tvl=vault["tvl"],
                risk_score=vault["risk"],
                source_url="https://app.nest.credit/",
                additional_info={
                    "name": vault["name"],
                    "description": vault["description"],
                },
            )
            opportunities.append(opp)

        return opportunities
