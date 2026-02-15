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
    {
        statsPool(limit: 200) {
            name
            poolId
            tvl
            feeApr
            farmApr
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
            pools = data.get("data", {}).get("statsPool", [])

            # Deduplicate by poolId - take the latest entry (first due to ordering)
            seen_pools = {}
            for pool in pools:
                pool_id = pool.get("poolId", "")
                if pool_id not in seen_pools:
                    seen_pools[pool_id] = pool

            for pool in seen_pools.values():
                opp = self._parse_pool(pool)
                if opp:
                    opportunities.append(opp)
        except Exception:
            pass

        return opportunities

    def _parse_pool(self, pool: Dict[str, Any]) -> YieldOpportunity | None:
        """Parse a single pool from statsPool query."""
        try:
            # Pool name format is "TOKEN_X-TOKEN_Y" (e.g., "USDt-USDC", "APT-USDC")
            name = pool.get("name", "") or ""
            parts = name.split("-")

            if len(parts) != 2:
                return None

            token_x = parts[0].strip().upper()
            token_y = parts[1].strip().upper()

            # Both tokens must be stablecoins for stablecoin-only pairs
            x_is_stable = self._is_stablecoin(token_x)
            y_is_stable = self._is_stablecoin(token_y)

            if not (x_is_stable and y_is_stable):
                return None

            stablecoin = token_x if x_is_stable else token_y
            pair_name = f"{token_x}/{token_y}"

            tvl = float(pool.get("tvl", 0) or 0)
            if tvl < self.MIN_TVL_USD:
                return None

            fee_apr = float(pool.get("feeApr", 0) or 0)
            farm_apr = float(pool.get("farmApr", 0) or 0)
            total_apr = fee_apr + farm_apr

            if total_apr <= 0 or total_apr > self.MAX_APR:
                return None

            pool_id = pool.get("poolId", "")

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
                source_url=f"https://app.hyperion.xyz/pool/{pool_id}" if pool_id else "https://app.hyperion.xyz",
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

