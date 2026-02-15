"""Scraper for Stake DAO vault yields."""

from typing import List, Dict, Any

from .base import BaseScraper
from models.opportunity import YieldOpportunity
from utils.risk import RiskAssessor


class StakeDaoScraper(BaseScraper):
    """Scraper for Stake DAO stablecoin strategies."""

    requires_vpn = False
    category = "Stake DAO Vaults"
    cache_file = "stakedao"

    # Stake DAO API endpoints per chain
    API_URLS = {
        "Ethereum": "https://api.stakedao.org/api/strategies/curve/1.json",
        "Arbitrum": "https://api.stakedao.org/api/strategies/curve/42161.json",
        "BSC": "https://api.stakedao.org/api/strategies/curve/56.json",
    }

    MIN_TVL_USD = 10_000
    MAX_APR_PERCENT = 100

    STABLECOIN_KEYWORDS = [
        "usd", "dai", "frax", "lusd", "susd", "gusd", "busd",
        "tusd", "dola", "mim", "crvusd", "gho", "pyusd",
    ]

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Fetch strategies from Stake DAO API."""
        opportunities = []

        for chain_name, url in self.API_URLS.items():
            try:
                response = self._make_request(url)
                data = response.json()
                # API returns strategies under "deployed" key
                if isinstance(data, list):
                    strategies = data
                elif isinstance(data, dict):
                    strategies = data.get("deployed", data.get("strategies", []))
                else:
                    strategies = []

                for strategy in strategies:
                    opp = self._parse_strategy(strategy, chain_name)
                    if opp:
                        opportunities.append(opp)
            except Exception:
                continue

        return opportunities

    def _parse_strategy(self, strategy: Dict[str, Any], chain: str) -> YieldOpportunity | None:
        """Parse a single strategy."""
        try:
            name = (strategy.get("name", "") or "").lower()

            # Filter for stablecoin strategies
            if not any(kw in name for kw in self.STABLECOIN_KEYWORDS):
                # Also check coins
                coins = strategy.get("coins", [])
                coin_symbols = [c.get("symbol", "").lower() for c in coins if isinstance(c, dict)]
                if not any(any(kw in sym for kw in self.STABLECOIN_KEYWORDS) for sym in coin_symbols):
                    return None

            # Get APR
            apr_data = strategy.get("apr", {})
            if isinstance(apr_data, dict):
                projected = apr_data.get("projected", {})
                if isinstance(projected, dict):
                    total_apr = float(projected.get("total", 0) or 0)
                else:
                    total_apr = float(projected or 0)
            else:
                total_apr = float(apr_data or 0)

            if total_apr <= 0 or total_apr > self.MAX_APR_PERCENT:
                return None

            # Get TVL
            tvl = float(strategy.get("tvl", 0) or 0)
            if tvl < self.MIN_TVL_USD:
                return None

            # Get stablecoin symbol
            coins = strategy.get("coins", [])
            stablecoin = self._extract_stablecoin(coins, name)

            strategy_name = strategy.get("name", "Stake DAO Strategy")
            slug = strategy.get("slug", "")

            return YieldOpportunity(
                category=self.category,
                protocol="Stake DAO",
                chain=chain,
                stablecoin=stablecoin,
                apy=total_apr,
                tvl=tvl,
                risk_score=RiskAssessor.calculate_risk_score(
                    strategy_type="vault",
                    protocol="Stake DAO",
                    chain=chain,
                    apy=total_apr,
                ),
                source_url=f"https://app.stakedao.org/strategies/{slug}" if slug else "https://app.stakedao.org",
                additional_info={
                    "strategy_name": strategy_name,
                },
            )

        except (KeyError, TypeError, ValueError):
            return None

    def _extract_stablecoin(self, coins: List, name: str) -> str:
        """Extract the main stablecoin symbol from coins list or name."""
        stable_priority = ["USDC", "USDT", "DAI", "FRAX", "CRVUSD", "GHO", "PYUSD"]

        for coin in coins:
            if isinstance(coin, dict):
                sym = coin.get("symbol", "").upper()
                if sym in stable_priority:
                    return sym

        # Fallback: check name
        name_upper = name.upper()
        for stable in stable_priority:
            if stable in name_upper:
                return stable

        return "USD"

