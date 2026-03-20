"""Scraper for Midas yield-bearing stablecoins."""

from typing import List, Dict, Any

from .base import BaseScraper
from models.opportunity import YieldOpportunity
from utils.risk import RiskAssessor


class MidasScraper(BaseScraper):
    """Scraper for Midas yield-bearing stablecoins (mTBILL, mBASIS, etc.)."""

    requires_vpn = False
    category = "Midas Yield-Bearing"
    cache_file = "midas"

    # Midas API endpoints to try (primary + fallbacks)
    API_URLS = [
        "https://api.midas.app/v1/tokens",
        "https://api.midas.app/api/tokens",
        "https://app.midas.app/api/tokens",
    ]

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Fetch Midas token data, trying multiple API endpoints."""
        for url in self.API_URLS:
            try:
                response = self._make_request(url)
                data = response.json()
                opportunities = self._parse_api_data(data)
                if opportunities:
                    return opportunities
            except Exception:
                continue

        return []

    def _parse_api_data(self, data: Dict) -> List[YieldOpportunity]:
        """Parse API response data."""
        opportunities = []

        tokens = data.get("tokens", data if isinstance(data, list) else [])

        for token in tokens:
            try:
                symbol = token.get("symbol", "")

                # Only USD-denominated tokens
                if not any(s in symbol.upper() for s in ["USD", "TBILL", "BASIS"]):
                    continue

                apy = float(token.get("apy", 0)) * 100 if token.get("apy", 0) < 1 else float(token.get("apy", 0))
                tvl = float(token.get("tvl", 0))

                if apy <= 0:
                    continue

                chain = token.get("chain", "Ethereum")

                opp = YieldOpportunity(
                    category=self.category,
                    protocol="Midas",
                    chain=chain,
                    stablecoin=symbol,
                    apy=apy,
                    tvl=tvl,
                    risk_score=RiskAssessor.calculate_risk_score(
                        strategy_type="yield_bearing",
                        protocol="Midas",
                        chain=chain,
                        apy=apy,
                    ),
                    source_url="https://midas.app/",
                    additional_info={
                        "description": token.get("description", ""),
                    },
                )
                opportunities.append(opp)

            except (KeyError, TypeError, ValueError):
                continue

        return opportunities
