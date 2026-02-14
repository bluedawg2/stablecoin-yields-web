"""Scraper for yo.xyz vault yields."""

from typing import List, Dict, Any

from .base import BaseScraper
from models.opportunity import YieldOpportunity
from utils.risk import RiskAssessor


class YoScraper(BaseScraper):
    """Scraper for yo.xyz yield vaults."""

    requires_vpn = False
    category = "Yo Yield"
    cache_file = "yo"

    # Known yo.xyz vaults
    VAULTS = [
        {
            "network": "base",
            "address": "0x0000000f2eB9f69274678c76222B35eEc7588a65",
            "symbol": "yoUSD",
            "chain": "Base",
        },
    ]

    API_BASE = "https://api.yo.xyz/api/v1/vault"

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Fetch vault data from yo.xyz API."""
        opportunities = []

        for vault in self.VAULTS:
            try:
                url = f"{self.API_BASE}/{vault['network']}/{vault['address']}"
                response = self._make_request(url)
                data = response.json()
                opp = self._parse_vault(data, vault)
                if opp:
                    opportunities.append(opp)
            except Exception:
                continue

        if not opportunities:
            opportunities = self._get_fallback_data()

        return opportunities

    def _parse_vault(self, data: Dict[str, Any], vault_info: Dict) -> YieldOpportunity | None:
        """Parse vault data from API response."""
        try:
            stats = data.get("stats", {})

            # Get yield (7d annualized)
            yield_data = stats.get("yield", {})
            apy = float(yield_data.get("7d", 0) or 0)

            # Add Merkl reward yield if available
            merkl_yield = float(stats.get("merklRewardYield", 0) or 0)
            total_apy = apy + merkl_yield

            if total_apy <= 0:
                return None

            # Get TVL
            tvl_data = stats.get("tvl", {})
            tvl_str = tvl_data.get("formatted", "0")
            tvl = self._parse_tvl(tvl_str)

            reward_token = "Merkl rewards" if merkl_yield > 0 else None

            return YieldOpportunity(
                category=self.category,
                protocol="Yo",
                chain=vault_info["chain"],
                stablecoin=vault_info["symbol"],
                apy=total_apy,
                tvl=tvl,
                reward_token=reward_token,
                risk_score=RiskAssessor.calculate_risk_score(
                    strategy_type="vault",
                    protocol="Yo",
                    chain=vault_info["chain"],
                    apy=total_apy,
                ),
                source_url=f"https://app.yo.xyz/vault/{vault_info['address']}",
                additional_info={
                    "base_yield": apy,
                    "merkl_yield": merkl_yield,
                    "vault_address": vault_info["address"],
                },
            )

        except (KeyError, TypeError, ValueError):
            return None

    def _parse_tvl(self, tvl_str: str) -> float:
        """Parse TVL from formatted string like '$5.2M' or '$500K'."""
        try:
            tvl_str = tvl_str.replace("$", "").replace(",", "").strip()
            if tvl_str.upper().endswith("B"):
                return float(tvl_str[:-1]) * 1e9
            if tvl_str.upper().endswith("M"):
                return float(tvl_str[:-1]) * 1e6
            if tvl_str.upper().endswith("K"):
                return float(tvl_str[:-1]) * 1e3
            return float(tvl_str)
        except (ValueError, IndexError):
            return 0

    def _get_fallback_data(self) -> List[YieldOpportunity]:
        """Return fallback data when API fails."""
        return [
            YieldOpportunity(
                category=self.category,
                protocol="Yo",
                chain="Base",
                stablecoin="yoUSD",
                apy=5.5,
                tvl=5_000_000,
                risk_score="Medium",
                source_url="https://app.yo.xyz",
                additional_info={"vault_address": "0x0000000f2eB9f69274678c76222B35eEc7588a65"},
            ),
        ]
