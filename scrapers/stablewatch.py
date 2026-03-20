"""Scraper for yield-bearing stablecoins from various protocol sources."""

from typing import List, Optional, Dict, Any

from .base import BaseScraper
from models.opportunity import YieldOpportunity
from utils.risk import RiskAssessor


class StableWatchScraper(BaseScraper):
    """Scraper for yield-bearing stablecoins from protocol APIs."""

    requires_vpn = False
    category = "Yield-Bearing Stablecoins"
    cache_file = "stablewatch"

    # Known yield-bearing stablecoins with their data sources
    YIELD_STABLECOINS = [
        # Ethena
        {"symbol": "sUSDe", "protocol": "Ethena", "chain": "Ethereum", "api": "ethena"},
        {"symbol": "USDe", "protocol": "Ethena", "chain": "Ethereum", "api": "ethena"},
        # Sky (formerly Maker)
        {"symbol": "sUSDS", "protocol": "Sky", "chain": "Ethereum", "api": "sky"},
        {"symbol": "USDS", "protocol": "Sky", "chain": "Ethereum", "api": "sky"},
        {"symbol": "sDAI", "protocol": "MakerDAO", "chain": "Ethereum", "api": "maker"},
        # Re Protocol
        {"symbol": "reUSD", "protocol": "Re Protocol", "chain": "Ethereum", "api": "re"},
        {"symbol": "reUSDe", "protocol": "Re Protocol", "chain": "Ethereum", "api": "re"},
        # Nest Credit
        {"symbol": "nALPHA", "protocol": "Nest Credit", "chain": "Ethereum", "api": "nest"},
    ]

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Fetch yield-bearing stablecoin data from various sources."""
        opportunities = []

        # Try to fetch from protocol APIs
        api_data = self._fetch_protocol_data()

        # Combine with known stablecoins
        for coin in self.YIELD_STABLECOINS:
            symbol = coin["symbol"]
            api_key = coin["api"]

            # Try to get live data
            live_data = api_data.get(api_key, {}).get(symbol, {})

            apy = live_data.get("apy")
            tvl = live_data.get("tvl")

            # Skip if no yield data
            if apy is None or apy <= 0:
                continue

            opp = YieldOpportunity(
                category=self.category,
                protocol=coin["protocol"],
                chain=coin["chain"],
                stablecoin=symbol,
                apy=apy,
                tvl=tvl,
                risk_score=RiskAssessor.calculate_risk_score(
                    strategy_type="yield_bearing",
                    protocol=coin["protocol"],
                    chain=coin["chain"],
                    apy=apy,
                ),
                source_url=self._get_source_url(coin["protocol"]),
            )
            opportunities.append(opp)

        return opportunities

    def _fetch_protocol_data(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Fetch live data from protocol APIs.

        Returns:
            Dict mapping api_key -> symbol -> {apy, tvl}
        """
        data = {}

        # Fetch Ethena data
        try:
            data["ethena"] = self._fetch_ethena()
        except Exception:
            pass

        # Fetch Sky/Maker data
        try:
            sky_data = self._fetch_sky()
            data["sky"] = sky_data
            data["maker"] = sky_data
        except Exception:
            pass

        # Fetch Re Protocol data
        try:
            data["re"] = self._fetch_re_protocol()
        except Exception:
            pass

        # Fetch Nest Credit data
        try:
            data["nest"] = self._fetch_nest_credit()
        except Exception:
            pass

        return data

    def _fetch_ethena(self) -> Dict[str, Dict[str, Any]]:
        """Fetch Ethena sUSDe APY."""
        response = self._make_request(
            "https://ethena.fi/api/yields/protocol-and-staking-yield",
        )
        data = response.json()

        # Extract sUSDe APY
        staking_yield = data.get("stakingYield", {})
        apy = staking_yield.get("value", 0)

        # Try to get TVL
        tvl = None
        try:
            tvl_response = self._make_request(
                "https://ethena.fi/api/statistics",
            )
            tvl_data = tvl_response.json()
            tvl = tvl_data.get("sUSDeTVL", 0) or tvl_data.get("totalTVL", 0)
        except Exception:
            pass

        return {
            "sUSDe": {"apy": apy, "tvl": tvl},
            "USDe": {"apy": 0, "tvl": None},
        }

    def _fetch_sky(self) -> Dict[str, Dict[str, Any]]:
        """Fetch Sky/MakerDAO savings rate."""
        response = self._make_request(
            "https://sky.money/api/savings-rate",
        )
        data = response.json()
        ssr = data.get("rate", 0) * 100  # Convert to percentage

        return {
            "sUSDS": {"apy": ssr, "tvl": data.get("tvl")},
            "USDS": {"apy": 0, "tvl": data.get("tvl")},
            "sDAI": {"apy": ssr, "tvl": data.get("sdaiTvl")},
        }

    def _fetch_re_protocol(self) -> Dict[str, Dict[str, Any]]:
        """Fetch Re Protocol reUSD/reUSDe APY from live API."""
        response = self._make_request("https://api.re.xyz/apy/get-apy")
        data = response.json()
        result = {}
        api_data = data.get("data", data)
        for symbol in ["reUSD", "reUSDe"]:
            token_data = api_data.get(symbol, {})
            apy = token_data.get("apy", 0)
            if apy:
                result[symbol] = {"apy": float(apy), "tvl": None}
        return result

    def _fetch_nest_credit(self) -> Dict[str, Dict[str, Any]]:
        """Fetch Nest Credit vault APY from live API."""
        response = self._make_request("https://app.nest.credit/api/vaults")
        data = response.json()
        result = {}
        vaults = data if isinstance(data, list) else data.get("vaults", [])
        for vault in vaults:
            slug = vault.get("slug", "")
            if slug == "nest-alpha-vault":
                apy = vault.get("apy") or vault.get("estimatedApy")
                if apy is not None:
                    apy_val = float(apy)
                    # API returns decimal (0.0935 = 9.35%), convert to percentage
                    if apy_val < 1:
                        apy_val = apy_val * 100
                    result["nALPHA"] = {"apy": apy_val, "tvl": vault.get("tvl")}
        return result

    def _get_source_url(self, protocol: str) -> str:
        """Get source URL for protocol."""
        urls = {
            "Ethena": "https://ethena.fi",
            "Sky": "https://sky.money",
            "MakerDAO": "https://spark.fi",
            "Re Protocol": "https://app.re.xyz/transparency",
            "Nest Credit": "https://app.nest.credit/vaults/nest-alpha-vault",
        }
        return urls.get(protocol, "https://www.stablewatch.io")
