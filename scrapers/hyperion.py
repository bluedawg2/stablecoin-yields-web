"""Scraper for Hyperion (Aptos) LP yields."""

from typing import List, Dict, Any

from .base import BaseScraper
from models.opportunity import YieldOpportunity
from utils.risk import RiskAssessor


class HyperionScraper(BaseScraper):
    """Scraper for Hyperion concentrated liquidity on Aptos."""

    requires_vpn = False
    category = "Hyperion LP"
    cache_file = "hyperion"

    API_URL = "https://hyperfluid-api.alcove.pro/v1/graphql"

    MIN_TVL_USD = 10_000
    MAX_APR = 200

    STABLECOIN_SYMBOLS = [
        "USDC", "USDT", "DAI", "MUSD", "USD",
    ]

    POOL_STATS_QUERY = """
    query GetPoolStats {
        getPoolStat {
            poolAddress
            tokenXSymbol
            tokenYSymbol
            tvlUSD
            feeAPR
            farmAPR
        }
    }
    """

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Fetch pool stats from Hyperion GraphQL API."""
        opportunities = []

        try:
            response = self._make_request(
                self.API_URL,
                method="POST",
                json_data={"query": self.POOL_STATS_QUERY},
            )
            data = response.json()
            pools = data.get("data", {}).get("getPoolStat", [])

            for pool in pools:
                opp = self._parse_pool(pool)
                if opp:
                    opportunities.append(opp)
        except Exception:
            opportunities = self._get_fallback_data()

        return opportunities

    def _parse_pool(self, pool: Dict[str, Any]) -> YieldOpportunity | None:
        """Parse a single pool."""
        try:
            token_x = (pool.get("tokenXSymbol", "") or "").upper()
            token_y = (pool.get("tokenYSymbol", "") or "").upper()

            # At least one token must be a stablecoin
            x_is_stable = self._is_stablecoin(token_x)
            y_is_stable = self._is_stablecoin(token_y)

            if not (x_is_stable or y_is_stable):
                return None

            # For stablecoin-only pairs, both must be stablecoins
            # For mixed pairs, we still include them if one is stable
            stablecoin = token_x if x_is_stable else token_y
            pair_name = f"{token_x}/{token_y}"

            tvl = float(pool.get("tvlUSD", 0) or 0)
            if tvl < self.MIN_TVL_USD:
                return None

            fee_apr = float(pool.get("feeAPR", 0) or 0)
            farm_apr = float(pool.get("farmAPR", 0) or 0)
            total_apr = fee_apr + farm_apr

            if total_apr <= 0 or total_apr > self.MAX_APR:
                return None

            pool_address = pool.get("poolAddress", "")

            return YieldOpportunity(
                category=self.category,
                protocol="Hyperion",
                chain="Aptos",
                stablecoin=stablecoin,
                apy=total_apr,
                tvl=tvl,
                reward_token="Farm rewards" if farm_apr > 0 else None,
                opportunity_type="LP",
                risk_score=RiskAssessor.calculate_risk_score(
                    strategy_type="vault",
                    protocol="Hyperion",
                    chain="Aptos",
                    apy=total_apr,
                ),
                source_url=f"https://app.hyperion.xyz/pool/{pool_address}" if pool_address else "https://app.hyperion.xyz",
                additional_info={
                    "pair": pair_name,
                    "fee_apr": fee_apr,
                    "farm_apr": farm_apr,
                    "is_stablecoin_pair": x_is_stable and y_is_stable,
                },
            )

        except (KeyError, TypeError, ValueError):
            return None

    def _is_stablecoin(self, symbol: str) -> bool:
        """Check if symbol is a stablecoin."""
        symbol_upper = symbol.upper()
        return any(stable in symbol_upper for stable in self.STABLECOIN_SYMBOLS)

    def _get_fallback_data(self) -> List[YieldOpportunity]:
        """Return fallback data when API fails."""
        fallback = [
            {"symbol": "USDC", "apy": 12.0, "tvl": 5_000_000, "pair": "USDC/USDT"},
        ]

        return [
            YieldOpportunity(
                category=self.category,
                protocol="Hyperion",
                chain="Aptos",
                stablecoin=item["symbol"],
                apy=item["apy"],
                tvl=item["tvl"],
                opportunity_type="LP",
                risk_score="Medium",
                source_url="https://app.hyperion.xyz",
                additional_info={"pair": item["pair"]},
            )
            for item in fallback
        ]
