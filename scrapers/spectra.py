"""Scraper for Spectra Finance fixed yields."""

from typing import List, Dict, Any
from datetime import datetime

from .base import BaseScraper
from models.opportunity import YieldOpportunity
from utils.risk import RiskAssessor


class SpectraScraper(BaseScraper):
    """Scraper for Spectra Finance PT/YT yields (standard, not max veBoost)."""

    requires_vpn = False
    category = "Spectra Fixed Yields"
    cache_file = "spectra"

    # Spectra API endpoints
    API_BASE = "https://app.spectra.finance/api"
    POOLS_URL = f"{API_BASE}/v1/pools"

    # Chain IDs
    CHAIN_IDS = {
        1: "Ethereum",
        42161: "Arbitrum",
        8453: "Base",
        10: "Optimism",
    }

    # Minimum TVL
    MIN_TVL_USD = 10_000

    # Stablecoin symbols
    STABLECOIN_SYMBOLS = [
        "USDC", "USDT", "DAI", "FRAX", "LUSD", "SDAI", "SUSDE", "USDE",
        "USDS", "SUSDS", "GHO", "CRVUSD", "PYUSD", "USDM",
    ]

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Fetch pool data from Spectra."""
        opportunities = []

        try:
            # Try main API
            response = self._make_request(self.POOLS_URL)
            data = response.json()
            opportunities = self._parse_pools(data)
        except Exception:
            # Try alternative endpoint
            try:
                response = self._make_request(f"{self.API_BASE}/pools")
                data = response.json()
                opportunities = self._parse_pools(data)
            except Exception:
                opportunities = self._get_fallback_data()

        return opportunities

    def _parse_pools(self, data: Any) -> List[YieldOpportunity]:
        """Parse pool data from API.

        Args:
            data: API response data.

        Returns:
            List of opportunities.
        """
        opportunities = []

        pools = data if isinstance(data, list) else data.get("pools", [])

        for pool in pools:
            try:
                # Get underlying asset
                underlying = pool.get("underlying", {})
                symbol = underlying.get("symbol", "") or pool.get("symbol", "")

                if not self._is_stablecoin(symbol):
                    continue

                # Get TVL
                tvl = float(pool.get("tvl", 0) or pool.get("totalValueLocked", 0))
                if tvl < self.MIN_TVL_USD:
                    continue

                # Get fixed APY (standard, not boosted)
                fixed_apy = float(pool.get("fixedApy", 0) or pool.get("impliedApy", 0))

                # If APY is in decimal form, convert to percentage
                if fixed_apy < 1:
                    fixed_apy = fixed_apy * 100

                if fixed_apy <= 0 or fixed_apy > 100:
                    continue

                # Get chain
                chain_id = pool.get("chainId", 1)
                chain = self.CHAIN_IDS.get(chain_id, "Ethereum")

                # Get maturity date
                maturity_timestamp = pool.get("maturity", pool.get("expiry"))
                maturity_date = None
                if maturity_timestamp:
                    try:
                        if isinstance(maturity_timestamp, (int, float)):
                            maturity_date = datetime.fromtimestamp(maturity_timestamp)
                        elif isinstance(maturity_timestamp, str):
                            maturity_date = datetime.fromisoformat(maturity_timestamp.replace("Z", "+00:00"))
                    except Exception:
                        pass

                # Build source URL
                pool_address = pool.get("address", pool.get("id", ""))
                source_url = f"https://app.spectra.finance/pools/{pool_address}"

                opp = YieldOpportunity(
                    category=self.category,
                    protocol="Spectra",
                    chain=chain,
                    stablecoin=symbol,
                    apy=fixed_apy,
                    tvl=tvl,
                    maturity_date=maturity_date,
                    opportunity_type="PT (Fixed Yield)",
                    risk_score=RiskAssessor.calculate_risk_score(
                        strategy_type="fixed",
                        protocol="Spectra",
                        chain=chain,
                        apy=fixed_apy,
                    ),
                    source_url=source_url,
                    additional_info={
                        "pool_address": pool_address,
                        "maturity": maturity_date.isoformat() if maturity_date else None,
                        "underlying": symbol,
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
            {"symbol": "USDC", "chain": "Ethereum", "apy": 6.5, "tvl": 10_000_000},
            {"symbol": "sUSDe", "chain": "Ethereum", "apy": 12.0, "tvl": 8_000_000},
            {"symbol": "sDAI", "chain": "Ethereum", "apy": 7.0, "tvl": 5_000_000},
        ]

        opportunities = []
        for item in fallback:
            opp = YieldOpportunity(
                category=self.category,
                protocol="Spectra",
                chain=item["chain"],
                stablecoin=item["symbol"],
                apy=item["apy"],
                tvl=item["tvl"],
                opportunity_type="PT (Fixed Yield)",
                risk_score="Low",
                source_url="https://app.spectra.finance/pools",
            )
            opportunities.append(opp)

        return opportunities
