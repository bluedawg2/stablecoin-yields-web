"""Scraper for yield.fi vault yields (fallback-data based)."""

from typing import List

from .base import BaseScraper
from models.opportunity import YieldOpportunity
from utils.risk import RiskAssessor


class YieldFiScraper(BaseScraper):
    """Scraper for yield.fi vaults.

    yield.fi has no public API (SDK only), so this uses periodically-updated
    fallback data for known vaults.
    """

    requires_vpn = False
    category = "Yield.fi"
    cache_file = "yieldfi"

    # Known yield.fi vaults with approximate rates
    KNOWN_VAULTS = [
        {
            "symbol": "vyUSD",
            "chain": "Plume",
            "apy": 16.0,
            "tvl": 3_000_000,
            "description": "vyUSD vault on Plume",
        },
        {
            "symbol": "vyUSD",
            "chain": "Base",
            "apy": 16.0,
            "tvl": 2_000_000,
            "description": "vyUSD vault on Base",
        },
    ]

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Return known vault data (no live API available)."""
        opportunities = []

        for vault in self.KNOWN_VAULTS:
            opp = YieldOpportunity(
                category=self.category,
                protocol="Yield.fi",
                chain=vault["chain"],
                stablecoin=vault["symbol"],
                apy=vault["apy"],
                tvl=vault["tvl"],
                risk_score=RiskAssessor.calculate_risk_score(
                    strategy_type="vault",
                    protocol="Yield.fi",
                    chain=vault["chain"],
                    apy=vault["apy"],
                ),
                source_url="https://app.yield.fi",
                additional_info={
                    "description": vault["description"],
                    "data_source": "Fallback (no public API)",
                },
            )
            opportunities.append(opp)

        return opportunities
