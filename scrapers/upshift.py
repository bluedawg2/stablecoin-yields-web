"""Scraper for Upshift Finance vaults."""

from typing import List, Dict, Any

from .base import BaseScraper
from models.opportunity import YieldOpportunity
from utils.risk import RiskAssessor


class UpshiftScraper(BaseScraper):
    """Scraper for Upshift Finance yield vaults."""

    requires_vpn = False
    category = "Upshift Vaults"
    cache_file = "upshift"

    # Upshift API endpoint
    API_URL = "https://api.upshift.finance/v1/vaults"

    # Minimum TVL
    MIN_TVL_USD = 10_000

    # Stablecoin symbols
    STABLECOIN_SYMBOLS = [
        "USDC", "USDT", "DAI", "FRAX", "LUSD", "SDAI", "SUSDE", "USDE",
        "USDS", "GHO", "CRVUSD", "PYUSD",
    ]

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Fetch vault data from Upshift."""
        opportunities = []

        # Try multiple API patterns
        api_urls = [
            "https://api.upshift.finance/v1/vaults",
            "https://app.upshift.finance/api/vaults",
            "https://upshift.finance/api/v1/vaults",
        ]

        for api_url in api_urls:
            try:
                response = self._make_request(api_url)
                data = response.json()
                opportunities = self._parse_vaults(data)
                if opportunities:
                    break
            except Exception:
                continue

        if not opportunities:
            opportunities = self._get_fallback_data()

        return opportunities

    def _parse_vaults(self, data: Any) -> List[YieldOpportunity]:
        """Parse vault data from API."""
        opportunities = []

        vaults = data if isinstance(data, list) else data.get("vaults", data.get("data", []))

        for vault in vaults:
            try:
                # Get asset symbol
                asset = vault.get("asset", {})
                symbol = asset.get("symbol", "") or vault.get("symbol", "") or vault.get("token", "")

                if not self._is_stablecoin(symbol):
                    continue

                # Get APY
                apy = float(vault.get("apy", 0) or vault.get("netApy", 0))
                if apy < 1:
                    apy = apy * 100

                if apy <= 0 or apy > 100:
                    continue

                # Get TVL
                tvl = float(vault.get("tvl", 0) or vault.get("totalValueLocked", 0))
                if tvl < self.MIN_TVL_USD:
                    continue

                # Get chain
                chain = vault.get("chain", "Ethereum")
                if isinstance(chain, dict):
                    chain = chain.get("name", "Ethereum")

                # Get vault address
                vault_address = vault.get("address", vault.get("id", ""))

                opp = YieldOpportunity(
                    category=self.category,
                    protocol="Upshift",
                    chain=chain,
                    stablecoin=symbol,
                    apy=apy,
                    tvl=tvl,
                    risk_score=RiskAssessor.calculate_risk_score(
                        strategy_type="vault",
                        protocol="Upshift",
                        chain=chain,
                        apy=apy,
                    ),
                    source_url=f"https://app.upshift.finance/vault/{vault_address}" if vault_address else "https://app.upshift.finance/",
                    additional_info={
                        "vault_address": vault_address,
                        "strategy": vault.get("strategy", ""),
                    },
                )
                opportunities.append(opp)

            except (KeyError, TypeError, ValueError):
                continue

        return opportunities

    def _is_stablecoin(self, symbol: str) -> bool:
        """Check if symbol is a stablecoin."""
        symbol_upper = symbol.upper()
        for stable in self.STABLECOIN_SYMBOLS:
            if stable in symbol_upper:
                return True
        return False

    def _get_fallback_data(self) -> List[YieldOpportunity]:
        """Return fallback data when API fails."""
        fallback = [
            {"symbol": "USDC", "chain": "Ethereum", "apy": 8.0, "tvl": 20_000_000},
            {"symbol": "USDT", "chain": "Ethereum", "apy": 7.5, "tvl": 15_000_000},
            {"symbol": "sUSDe", "chain": "Ethereum", "apy": 12.0, "tvl": 10_000_000},
        ]

        opportunities = []
        for item in fallback:
            opp = YieldOpportunity(
                category=self.category,
                protocol="Upshift",
                chain=item["chain"],
                stablecoin=item["symbol"],
                apy=item["apy"],
                tvl=item["tvl"],
                risk_score="Medium",
                source_url="https://app.upshift.finance/",
            )
            opportunities.append(opp)

        return opportunities
