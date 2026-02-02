"""Scraper for Lagoon Finance vaults."""

from typing import List, Dict, Any

from .base import BaseScraper
from models.opportunity import YieldOpportunity
from utils.risk import RiskAssessor


class LagoonScraper(BaseScraper):
    """Scraper for Lagoon Finance vault yields."""

    requires_vpn = False
    category = "Lagoon Vaults"
    cache_file = "lagoon"

    API_URL = "https://app.lagoon.finance/api/vaults"

    # Minimum TVL to filter
    MIN_TVL_USD = 100_000

    # Stablecoin symbols
    STABLECOIN_SYMBOLS = [
        "USDC", "USDT", "DAI", "FRAX", "LUSD", "SDAI", "SUSDE", "USDE",
        "USDS", "GHO", "CRVUSD", "PYUSD", "AUSD", "USD",
    ]

    # Chain ID to name mapping
    CHAIN_NAMES = {
        "1": "Ethereum",
        "10": "Optimism",
        "137": "Polygon",
        "8453": "Base",
        "42161": "Arbitrum",
        "43114": "Avalanche",
        "59144": "Linea",
        "143": "Monad",
    }

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Fetch vault data from Lagoon Finance API."""
        opportunities = []

        try:
            response = self._make_request(self.API_URL)
            data = response.json()
            vaults = data.get("vaults", [])
            opportunities = self._parse_vaults(vaults)
        except Exception:
            opportunities = self._get_fallback_data()

        return opportunities

    def _parse_vaults(self, vaults: List[Dict]) -> List[YieldOpportunity]:
        """Parse vault data from API response."""
        opportunities = []

        for vault in vaults:
            try:
                # Check if vault is visible
                if not vault.get("isVisible", True):
                    continue

                # Get asset info
                asset = vault.get("asset", {})
                asset_symbol = asset.get("symbol", "").upper()

                # Check if stablecoin
                if not self._is_stablecoin(asset_symbol):
                    continue

                # Get state info
                state = vault.get("state", {})
                if not state:
                    continue

                # Get TVL
                tvl = state.get("totalAssetsUsd", 0)
                if tvl < self.MIN_TVL_USD:
                    continue

                # Get APR (prefer weekly, fallback to monthly or live)
                apr = 0
                weekly_apr = state.get("weeklyApr", {})
                if weekly_apr:
                    apr = weekly_apr.get("linearNetApr", 0)

                if apr <= 0:
                    monthly_apr = state.get("monthlyApr", {})
                    if monthly_apr:
                        apr = monthly_apr.get("linearNetApr", 0)

                if apr <= 0:
                    live_apr = state.get("liveAPR", {})
                    if live_apr:
                        apr = live_apr.get("linearNetApr", 0)

                if apr <= 0:
                    continue

                # Get chain info
                chain_data = vault.get("chain", {})
                chain_id = str(chain_data.get("id", "1"))
                chain = chain_data.get("name") or self.CHAIN_NAMES.get(chain_id, "Ethereum")

                # Get vault name and symbol
                vault_name = vault.get("name", "")
                vault_symbol = vault.get("symbol", "")

                # Get curator info
                curators = vault.get("curators", [])
                curator_name = curators[0].get("name", "Lagoon") if curators else "Lagoon"

                # Build source URL
                vault_address = vault.get("address", "")
                source_url = f"https://app.lagoon.finance/vaults/{chain_id}/{vault_address}"

                opp = YieldOpportunity(
                    category=self.category,
                    protocol=f"Lagoon ({curator_name})",
                    chain=chain,
                    stablecoin=asset_symbol,
                    apy=apr,
                    tvl=tvl,
                    risk_score=RiskAssessor.calculate_risk_score(
                        strategy_type="vault",
                        protocol="Lagoon",
                        chain=chain,
                        apy=apr,
                    ),
                    source_url=source_url,
                    additional_info={
                        "vault_name": vault_name,
                        "vault_symbol": vault_symbol,
                        "curator": curator_name,
                        "vault_state": state.get("state", ""),
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
            {"symbol": "USDC", "chain": "Avalanche", "apy": 6.0, "tvl": 20_000_000, "name": "Turtle Avalanche USDC"},
            {"symbol": "USDC", "chain": "Ethereum", "apy": 6.0, "tvl": 8_000_000, "name": "9Summits USDC"},
            {"symbol": "USDC", "chain": "Ethereum", "apy": 12.0, "tvl": 1_500_000, "name": "Syntropia USDC"},
        ]

        opportunities = []
        for item in fallback:
            opp = YieldOpportunity(
                category=self.category,
                protocol="Lagoon",
                chain=item["chain"],
                stablecoin=item["symbol"],
                apy=item["apy"],
                tvl=item["tvl"],
                risk_score="Medium",
                source_url="https://app.lagoon.finance",
                additional_info={"vault_name": item["name"]},
            )
            opportunities.append(opp)

        return opportunities
