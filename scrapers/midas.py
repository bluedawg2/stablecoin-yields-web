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

    # Fallback data for Midas tokens (updated to current rates per RWA.xyz)
    MIDAS_TOKENS = [
        {
            "symbol": "mTBILL",
            "name": "Midas T-Bill",
            "apy": 4.3,
            "tvl": 100_000_000,
            "chain": "Ethereum",
            "description": "Tokenized US Treasury Bills",
            "risk": "Low",
        },
        {
            "symbol": "mBASIS",
            "name": "Midas Basis",
            "apy": 5.1,
            "tvl": 50_000_000,
            "chain": "Ethereum",
            "description": "Basis trading strategy",
            "risk": "Medium",
        },
        {
            "symbol": "mBTC",
            "name": "Midas BTC Yield",
            "apy": 6.5,
            "tvl": 30_000_000,
            "chain": "Ethereum",
            "description": "BTC yield strategy",
            "risk": "Medium",
        },
    ]

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Fetch Midas token data, trying multiple API endpoints."""
        # Try each API endpoint
        for url in self.API_URLS:
            try:
                response = self._make_request(url)
                data = response.json()
                opportunities = self._parse_api_data(data)
                if opportunities:
                    return opportunities
            except Exception:
                continue

        # All API endpoints failed - use fallback data
        return self._get_fallback_data()

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

    def _get_fallback_data(self) -> List[YieldOpportunity]:
        """Return fallback data for Midas tokens."""
        opportunities = []

        for token in self.MIDAS_TOKENS:
            opp = YieldOpportunity(
                category=self.category,
                protocol="Midas",
                chain=token["chain"],
                stablecoin=token["symbol"],
                apy=token["apy"],
                tvl=token["tvl"],
                risk_score=token["risk"],
                source_url="https://midas.app/",
                additional_info={
                    "description": token["description"],
                    "name": token["name"],
                },
            )
            opportunities.append(opp)

        return opportunities
