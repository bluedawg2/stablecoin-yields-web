"""Scraper for Ploutos Money lending markets (fallback-data based)."""

from typing import List

from .base import BaseScraper
from models.opportunity import YieldOpportunity
from utils.risk import RiskAssessor


class PloutosScraper(BaseScraper):
    """Scraper for Ploutos Money (Aave v3 fork).

    Ploutos has no public API (on-chain only), so this uses
    periodically-updated fallback data. Ploutos rewards also
    appear in Merkl (already captured by MerklScraper).
    """

    requires_vpn = False
    category = "Ploutos Money"
    cache_file = "ploutos"

    # Known Ploutos markets with approximate rates
    KNOWN_MARKETS = [
        {
            "symbol": "USDC",
            "chain": "Hemi",
            "apy": 5.0,
            "tvl": 2_000_000,
            "description": "USDC lending on Hemi",
        },
        {
            "symbol": "USDT",
            "chain": "Hemi",
            "apy": 4.5,
            "tvl": 1_500_000,
            "description": "USDT lending on Hemi",
        },
        {
            "symbol": "USDC",
            "chain": "Ethereum",
            "apy": 4.0,
            "tvl": 3_000_000,
            "description": "USDC lending on Ethereum",
        },
    ]

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Return known market data (no live API available)."""
        opportunities = []

        for market in self.KNOWN_MARKETS:
            opp = YieldOpportunity(
                category=self.category,
                protocol="Ploutos",
                chain=market["chain"],
                stablecoin=market["symbol"],
                apy=market["apy"],
                tvl=market["tvl"],
                risk_score=RiskAssessor.calculate_risk_score(
                    strategy_type="lend",
                    protocol="Ploutos",
                    chain=market["chain"],
                    apy=market["apy"],
                ),
                source_url="https://app.ploutos.money",
                additional_info={
                    "description": market["description"],
                    "data_source": "Fallback (on-chain only)",
                },
            )
            opportunities.append(opp)

        return opportunities
