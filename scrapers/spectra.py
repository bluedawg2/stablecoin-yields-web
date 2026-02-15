"""Scraper for Spectra Finance fixed yields."""

import re
import json
from typing import List, Dict, Any
from datetime import datetime

from .base import BaseScraper
from models.opportunity import YieldOpportunity
from utils.risk import RiskAssessor


class SpectraScraper(BaseScraper):
    """Scraper for Spectra Finance PT fixed yields.

    Fetches pool data from Spectra's Next.js embedded page data,
    which contains live PT yields, TVL, and maturity info.
    """

    requires_vpn = False
    category = "Spectra Fixed Yields"
    cache_file = "spectra"

    PAGE_URL = "https://app.spectra.finance/fixed-rate"

    # Minimum TVL
    MIN_TVL_USD = 10_000

    # Chain ID mappings
    CHAIN_IDS = {
        1: "Ethereum",
        42161: "Arbitrum",
        8453: "Base",
        10: "Optimism",
        146: "Sonic",
        43111: "Katana",
        56: "BSC",
        43114: "Avalanche",
        14: "Flare",
        999: "Hyperliquid",
        747474: "Flow",
    }

    # Stablecoin symbols
    STABLECOIN_SYMBOLS = [
        "USDC", "USDT", "DAI", "FRAX", "LUSD", "SDAI", "SUSDE", "USDE",
        "USDS", "SUSDS", "GHO", "CRVUSD", "PYUSD", "USDM", "BOLD",
        "USDAI", "DOLA", "USDN",
    ]

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Fetch pool data from Spectra's embedded page data."""
        opportunities = []

        try:
            response = self._make_request(self.PAGE_URL)
            html = response.text

            # Extract __NEXT_DATA__ JSON from the page
            match = re.search(
                r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
                html,
                re.DOTALL,
            )
            if not match:
                return []

            page_data = json.loads(match.group(1))
            queries = (
                page_data.get("props", {})
                .get("pageProps", {})
                .get("dehydratedState", {})
                .get("queries", [])
            )

            # Find the query that contains PT pool data
            for query in queries:
                state_data = query.get("state", {}).get("data", [])
                if (
                    isinstance(state_data, list)
                    and len(state_data) > 0
                    and isinstance(state_data[0], dict)
                    and "address" in state_data[0]
                    and "tvl" in state_data[0]
                ):
                    opportunities = self._parse_pt_data(state_data)
                    break

        except Exception:
            pass

        return opportunities

    def _parse_pt_data(self, pt_list: List[Dict]) -> List[YieldOpportunity]:
        """Parse PT token data from Spectra's embedded page data.

        Args:
            pt_list: List of PT token objects from page data.

        Returns:
            List of opportunities.
        """
        opportunities = []

        for pt in pt_list:
            try:
                # Get underlying symbol
                underlying = pt.get("underlying", {})
                if not isinstance(underlying, dict):
                    continue
                symbol = underlying.get("symbol", "")

                if not self._is_stablecoin(symbol):
                    continue

                # Get TVL
                tvl_data = pt.get("tvl", {})
                tvl_usd = tvl_data.get("usd", 0) if isinstance(tvl_data, dict) else 0
                if tvl_usd < self.MIN_TVL_USD:
                    continue

                # Get chain
                chain_id = pt.get("chainId", 1)
                chain = self.CHAIN_IDS.get(chain_id, f"Chain-{chain_id}")

                # Get maturity date
                maturity_ts = pt.get("maturity")
                maturity_date = None
                if maturity_ts:
                    try:
                        maturity_date = datetime.fromtimestamp(int(maturity_ts))
                    except (ValueError, TypeError, OSError):
                        pass

                # Get PT APY from the AMM pools sub-array
                pools = pt.get("pools", [])
                if not pools:
                    continue

                # Use the best pool's ptApy
                best_apy = 0
                best_pool_address = ""
                for pool in pools:
                    pt_apy = pool.get("ptApy", 0) or 0
                    if pt_apy > best_apy:
                        best_apy = pt_apy
                        best_pool_address = pool.get("address", "")

                if best_apy <= 0 or best_apy > 100:
                    continue

                # PT symbol for display
                pt_symbol = pt.get("symbol", symbol)

                # Build source URL
                chain_slug = {
                    1: "eth", 42161: "arb", 8453: "base", 10: "op",
                    146: "sonic", 43111: "katana", 56: "bsc",
                    43114: "avax", 14: "flare",
                }.get(chain_id, str(chain_id))
                pt_address = pt.get("address", "")
                source_url = f"https://app.spectra.finance/fixed-rate/{chain_slug}:{pt_address}"

                opp = YieldOpportunity(
                    category=self.category,
                    protocol="Spectra",
                    chain=chain,
                    stablecoin=symbol,
                    apy=best_apy,
                    tvl=tvl_usd,
                    maturity_date=maturity_date,
                    opportunity_type="PT (Fixed Yield)",
                    risk_score=RiskAssessor.calculate_risk_score(
                        strategy_type="fixed",
                        protocol="Spectra",
                        chain=chain,
                        apy=best_apy,
                    ),
                    source_url=source_url,
                    additional_info={
                        "pt_symbol": pt_symbol,
                        "pool_address": best_pool_address,
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

