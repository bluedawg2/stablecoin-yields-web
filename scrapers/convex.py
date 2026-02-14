"""Scraper for Convex Finance yields."""

from typing import List, Dict, Any

from .base import BaseScraper
from models.opportunity import YieldOpportunity
from utils.risk import RiskAssessor


class ConvexScraper(BaseScraper):
    """Scraper for Convex Finance stablecoin pool yields."""

    requires_vpn = False
    category = "Convex Finance"
    cache_file = "convex"

    API_URL = "https://curve.convexfinance.com/api/curve-apys"

    MIN_APY = 0.5
    MAX_APY = 100

    STABLECOIN_KEYWORDS = [
        "usd", "dai", "frax", "lusd", "susd", "gusd", "busd",
        "tusd", "dola", "mim", "crvusd", "gho", "pyusd", "3pool",
        "usdn", "musd", "rai",
    ]

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Fetch Convex pool APYs from their API."""
        opportunities = []

        try:
            response = self._make_request(self.API_URL)
            data = response.json()
            apys = data.get("apys", data if isinstance(data, dict) else {})

            for pool_name, pool_data in apys.items():
                opp = self._parse_pool(pool_name, pool_data)
                if opp:
                    opportunities.append(opp)
        except Exception:
            opportunities = self._get_fallback_data()

        return opportunities

    def _parse_pool(self, pool_name: str, pool_data: Dict[str, Any]) -> YieldOpportunity | None:
        """Parse a single pool's data."""
        try:
            name_lower = pool_name.lower()

            # Filter for stablecoin pools
            if not any(kw in name_lower for kw in self.STABLECOIN_KEYWORDS):
                return None

            # Calculate total APY (base + CRV + CVX rewards)
            base_apy = float(pool_data.get("baseApy", 0) or 0)
            crv_apy = float(pool_data.get("crvApy", 0) or 0)
            cvx_apy = float(pool_data.get("cvxApy", 0) or 0)
            total_apy = base_apy + crv_apy + cvx_apy

            if total_apy < self.MIN_APY or total_apy > self.MAX_APY:
                return None

            # Extract stablecoin from name
            stablecoin = self._extract_stablecoin(pool_name)

            # Reward tokens
            reward_parts = []
            if crv_apy > 0:
                reward_parts.append("CRV")
            if cvx_apy > 0:
                reward_parts.append("CVX")
            reward_token = ", ".join(reward_parts) if reward_parts else None

            return YieldOpportunity(
                category=self.category,
                protocol="Convex",
                chain="Ethereum",
                stablecoin=stablecoin,
                apy=total_apy,
                tvl=None,  # Not available in this endpoint
                reward_token=reward_token,
                risk_score=RiskAssessor.calculate_risk_score(
                    strategy_type="vault",
                    protocol="Convex",
                    chain="Ethereum",
                    apy=total_apy,
                ),
                source_url="https://www.convexfinance.com/stake",
                additional_info={
                    "pool_name": pool_name,
                    "base_apy": base_apy,
                    "crv_apy": crv_apy,
                    "cvx_apy": cvx_apy,
                },
            )

        except (KeyError, TypeError, ValueError):
            return None

    def _extract_stablecoin(self, pool_name: str) -> str:
        """Extract the main stablecoin from pool name."""
        name_upper = pool_name.upper()
        stable_priority = ["USDC", "USDT", "DAI", "FRAX", "CRVUSD", "GHO", "PYUSD", "LUSD"]
        for stable in stable_priority:
            if stable in name_upper:
                return stable
        if "3POOL" in name_upper:
            return "USDC"
        return "USD"

    def _get_fallback_data(self) -> List[YieldOpportunity]:
        """Return fallback data when API fails."""
        fallback = [
            {"symbol": "USDC", "apy": 4.0, "name": "USDC/USDT"},
            {"symbol": "crvUSD", "apy": 6.0, "name": "crvUSD/USDT"},
            {"symbol": "FRAX", "apy": 5.0, "name": "FRAX/USDC"},
        ]

        return [
            YieldOpportunity(
                category=self.category,
                protocol="Convex",
                chain="Ethereum",
                stablecoin=item["symbol"],
                apy=item["apy"],
                tvl=None,
                risk_score="Low",
                source_url="https://www.convexfinance.com/stake",
                additional_info={"pool_name": item["name"]},
            )
            for item in fallback
        ]
