"""Scraper for Morpho borrow/lend loop strategies using yield-bearing collateral."""

import re
import json
import sys
from datetime import datetime, date
from typing import List, Dict, Any, Optional

from .base import BaseScraper
from models.opportunity import YieldOpportunity
from utils.risk import RiskAssessor
from config import LEVERAGE_LEVELS


class MorphoLoopScraper(BaseScraper):
    """Calculates leveraged yield from Morpho using yield-bearing collateral.

    Strategy: Deposit yield-bearing stablecoin as collateral, borrow regular stablecoin,
    buy more yield-bearing stablecoin, repeat (loop).

    Example: mHYPER (7.68% yield) as collateral -> borrow USDC (3.82%) -> buy more mHYPER
    Net APY at 5x leverage = 7.68% * 5 - 3.82% * 4 = 23.12%
    """

    requires_vpn = False
    category = "Morpho Borrow/Lend Loop"
    cache_file = "morpho_loop"

    API_URL = "https://blue-api.morpho.org/graphql"

    # Minimum TVL for valid markets
    MIN_TVL_USD = 10_000

    # Maximum borrow APY to consider (filter out extreme rates)
    MAX_BORROW_APY = 50

    # Yield-bearing stablecoin patterns (as collateral)
    YIELD_BEARING_PATTERNS = [
        "SUSDE", "SDAI", "SUSDS", "SFRAX", "MHYPER", "SUSN", "USD0++",
        "SCRVUSD", "SAVUSD", "STUSD", "SUSDX", "PT-",  # PT tokens are yield-bearing
        "SNUSD", "SRUSDE", "STCUSD", "WSRUS", "MAPOLLO", "RLP",
        "CUSD", "RUSD", "REUSD", "IUSD", "SIUSD", "JRUSDE", "LVLUSD",
        "YOUSD", "MMEV",
    ]

    # Regular stablecoins (to borrow)
    BORROW_STABLES = [
        "USDC", "USDT", "DAI", "USDS", "PYUSD", "FRAX", "CRVUSD", "GHO", "USDA",
    ]

    # Fallback yield rates — only used when live data is unavailable.
    # Updated to conservative estimates; live rates are preferred.
    FALLBACK_YIELD_RATES = {
        "SUSDE": 5.0,
        "SDAI": 6.0,
        "SUSDS": 6.5,
        "SFRAX": 3.5,
        "MHYPER": 6.0,
        "USD0++": 4.0,
        "SCRVUSD": 5.0,
        "YOUSD": 8.0,
        "SNUSD": 10.0,
        "MMEV": 6.0,
        "SRUSDE": 5.0,
        "STCUSD": 5.0,
    }

    # Chain ID mappings
    CHAIN_IDS = {
        1: "Ethereum",
        8453: "Base",
        42161: "Arbitrum",
        10: "Optimism",
        10143: "Monad",
        130: "Unichain",
    }

    # Protocol yield API endpoints for live yield lookup
    YIELD_APIS = {
        "SUSDE": "https://ethena.fi/api/yields/protocol-and-staking-yield",
        "SUSDS": "https://info.sky.money/api/savings/info",
    }

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Fetch yield-bearing collateral markets and calculate loop APYs."""
        opportunities = []

        try:
            # First, fetch live yield rates for collateral assets
            self._live_yields = self._fetch_live_yield_rates()

            markets = self._fetch_markets()
            opportunities = self._calculate_loop_opportunities(markets)
        except Exception:
            pass

        return opportunities

    def _fetch_live_yield_rates(self) -> Dict[str, float]:
        """Fetch live yield rates from protocol APIs.

        Returns:
            Dict mapping collateral symbol -> yield rate as percentage.
        """
        live_rates = {}

        # 1. Fetch sUSDe yield from Ethena
        try:
            resp = self._make_request(self.YIELD_APIS["SUSDE"])
            data = resp.json()
            # Ethena returns {"stakingYield": {"value": "0.0527"}} or similar
            staking = data.get("stakingYield", {})
            if isinstance(staking, dict):
                val = float(staking.get("value", 0))
                if val > 0 and val < 1:
                    live_rates["SUSDE"] = val * 100
                elif val > 1:
                    live_rates["SUSDE"] = val
        except Exception:
            pass

        # 2. Fetch sUSDS yield from Sky/Maker
        try:
            resp = self._make_request(self.YIELD_APIS["SUSDS"])
            data = resp.json()
            # Sky returns {"ssr": "0.065"} or {"rate": "6.5"} etc.
            rate = data.get("ssr") or data.get("rate") or data.get("apy")
            if rate:
                rate_f = float(rate)
                if 0 < rate_f < 1:
                    live_rates["SUSDS"] = rate_f * 100
                elif rate_f > 1:
                    live_rates["SUSDS"] = rate_f
        except Exception:
            pass

        # 3. Fetch PT token implied yields from Pendle API
        pt_yields = self._fetch_pendle_pt_yields()
        live_rates.update(pt_yields)

        # 4. Fetch yields from Spectra embedded data for additional PT tokens
        spectra_yields = self._fetch_spectra_pt_yields()
        # Only add Spectra yields for tokens not already covered by Pendle
        for k, v in spectra_yields.items():
            if k not in live_rates:
                live_rates[k] = v

        return live_rates

    def _fetch_pendle_pt_yields(self) -> Dict[str, float]:
        """Fetch PT implied yields from Pendle API.

        Returns:
            Dict mapping PT symbol -> implied APY percentage.
        """
        pt_yields = {}
        pendle_chains = {1: "Ethereum", 42161: "Arbitrum", 8453: "Base", 130: "Unichain"}

        for chain_id in pendle_chains:
            try:
                url = f"https://api-v2.pendle.finance/core/v1/{chain_id}/markets"
                resp = self._make_request(url, params={"limit": 200})
                data = resp.json()
                markets = data if isinstance(data, list) else data.get("results", [])

                for market in markets:
                    # Get implied APY
                    implied = market.get("impliedApy", 0) or 0
                    if implied <= 0:
                        # Also try ptDiscount for implied yield calculation
                        pt_discount = market.get("ptDiscount", 0) or 0
                        if pt_discount > 0:
                            # Approximate: implied APY ≈ discount / time_to_maturity * 365
                            expiry = market.get("expiry", "")
                            if expiry:
                                try:
                                    maturity = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
                                    days = (maturity - datetime.now(maturity.tzinfo)).days
                                    if days > 0:
                                        implied = (pt_discount / days) * 365
                                except Exception:
                                    pass
                        if implied <= 0:
                            continue

                    # Convert to percentage if needed
                    if 0 < implied < 1:
                        implied = implied * 100

                    if implied <= 0 or implied > 100:
                        continue

                    # Get PT symbol
                    pt = market.get("pt", {})
                    pt_symbol = (pt.get("symbol", "") or "").upper()
                    if pt_symbol:
                        # Normalize: strip maturity date suffix for matching
                        # e.g., "PT-CUSD-23JUL2026-(ETH)" -> store both full and base
                        pt_yields[pt_symbol] = implied

                        # Also store without date for base matching
                        base_match = re.match(r'(PT-[A-Z]+)', pt_symbol)
                        if base_match:
                            base_key = base_match.group(1)
                            # Keep the highest yield for base symbol
                            if base_key not in pt_yields or implied > pt_yields[base_key]:
                                pt_yields[base_key] = implied

            except Exception:
                continue

        return pt_yields

    def _fetch_spectra_pt_yields(self) -> Dict[str, float]:
        """Fetch PT implied yields from Spectra's embedded page data.

        Returns:
            Dict mapping PT symbol -> implied APY percentage.
        """
        pt_yields = {}

        try:
            resp = self._make_request("https://app.spectra.finance/fixed-rate")
            html = resp.text

            import re as _re
            match = _re.search(
                r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
                html,
                _re.DOTALL,
            )
            if not match:
                return pt_yields

            page_data = json.loads(match.group(1))
            queries = (
                page_data.get("props", {})
                .get("pageProps", {})
                .get("dehydratedState", {})
                .get("queries", [])
            )

            for query in queries:
                state_data = query.get("state", {}).get("data", [])
                if not isinstance(state_data, list):
                    continue

                for pt in state_data:
                    if not isinstance(pt, dict) or "pools" not in pt:
                        continue

                    pt_symbol = (pt.get("symbol", "") or "").upper()
                    if not pt_symbol.startswith("PT-"):
                        continue

                    # Get the best ptApy from pools
                    best_apy = 0
                    for pool in pt.get("pools", []):
                        apy = pool.get("ptApy", 0) or 0
                        if apy > best_apy:
                            best_apy = apy

                    if 0 < best_apy <= 100:
                        pt_yields[pt_symbol] = best_apy
                        # Also store base symbol
                        base_match = re.match(r'(PT-[A-Z]+)', pt_symbol)
                        if base_match:
                            base_key = base_match.group(1)
                            if base_key not in pt_yields or best_apy > pt_yields[base_key]:
                                pt_yields[base_key] = best_apy

        except Exception:
            pass

        return pt_yields

    def _fetch_markets(self) -> List[Dict[str, Any]]:
        """Fetch all Morpho markets with yield-bearing collateral, per chain."""
        all_markets = []

        for chain_id, chain_name in self.CHAIN_IDS.items():
            try:
                markets = self._fetch_chain_markets(chain_id, chain_name)
                all_markets.extend(markets)
            except Exception:
                pass

        return all_markets

    def _fetch_chain_markets(self, chain_id: int, chain_name: str) -> List[Dict[str, Any]]:
        """Fetch all Morpho markets for a specific chain with pagination.

        Args:
            chain_id: Numeric chain ID.
            chain_name: Human-readable chain name.

        Returns:
            List of market dicts with chain info attached.
        """
        query = """
        query GetMarkets($chainId: Int!, $skip: Int!) {
            markets(where: { chainId_in: [$chainId] }, first: 1000, skip: $skip) {
                items {
                    uniqueKey
                    loanAsset {
                        symbol
                        address
                    }
                    collateralAsset {
                        symbol
                        address
                    }
                    state {
                        supplyApy
                        borrowApy
                        supplyAssetsUsd
                        borrowAssetsUsd
                        sizeUsd
                        totalLiquidityUsd
                    }
                    lltv
                }
                pageInfo {
                    countTotal
                    count
                }
            }
        }
        """

        all_markets = []
        skip = 0

        while True:
            response = self._make_request(
                self.API_URL,
                method="POST",
                json_data={
                    "query": query,
                    "variables": {"chainId": chain_id, "skip": skip},
                },
            )

            data = response.json()
            items = data.get("data", {}).get("markets", {}).get("items", [])

            if not items:
                break

            all_markets.extend(items)

            # Check if there are more pages
            page_info = data.get("data", {}).get("markets", {}).get("pageInfo", {})
            count_total = page_info.get("countTotal", 0)

            if len(all_markets) >= count_total or len(items) < 1000:
                break

            skip += 1000

        # Tag each market with the chain name
        for market in all_markets:
            market["_chain"] = chain_name

        return all_markets

    def _calculate_loop_opportunities(self, markets: List[Dict]) -> List[YieldOpportunity]:
        """Calculate loop opportunities for each valid market.

        Args:
            markets: List of Morpho markets.

        Returns:
            List of loop opportunities at various leverage levels.
        """
        opportunities = []

        for market in markets:
            collateral_asset = market.get("collateralAsset")
            loan_asset = market.get("loanAsset")

            if not collateral_asset or not loan_asset:
                continue

            collateral_symbol = collateral_asset.get("symbol", "").upper()
            loan_symbol = loan_asset.get("symbol", "").upper()

            # Check if collateral is yield-bearing
            if not self._is_yield_bearing(collateral_symbol):
                continue

            # Check if loan is a regular stablecoin
            if not self._is_borrow_stable(loan_symbol):
                continue

            # Get market data — use sizeUsd (matches Morpho UI "Total Market Size"),
            # fall back to supplyAssetsUsd for older API responses
            state = market.get("state", {})
            tvl = state.get("sizeUsd", 0) or state.get("supplyAssetsUsd", 0) or 0
            borrow_apy = (state.get("borrowApy", 0) or 0) * 100

            # Filter
            if tvl < self.MIN_TVL_USD:
                continue
            if borrow_apy > self.MAX_BORROW_APY or borrow_apy <= 0:
                continue

            # Get LLTV
            lltv = self._parse_lltv(market.get("lltv", "0"))
            if lltv <= 0:
                continue

            # Get collateral yield rate (live first, fallback to hardcoded)
            collateral_yield = self._get_collateral_yield(collateral_symbol)
            if collateral_yield <= 0:
                continue

            # Calculate max leverage from LLTV
            theoretical_max_leverage = 1 / (1 - lltv) if lltv < 1 else 1

            # Use SAFE max leverage (60% of theoretical) to avoid liquidation risk
            # At 60% utilization, you have ~40% buffer before liquidation
            safe_max_leverage = theoretical_max_leverage * 0.6
            # Cap at 5x regardless - higher leverage is too risky for stablecoin loops
            safe_max_leverage = min(safe_max_leverage, 5.0)

            # Use chain from per-chain query, fallback to Ethereum
            chain = market.get("_chain", "Ethereum")

            # Calculate loop APY at different leverage levels
            for leverage in LEVERAGE_LEVELS:
                if leverage > safe_max_leverage:
                    continue
                if leverage == 1.0:
                    continue  # Skip 1x, that's just holding

                # Net APY = collateral_yield * leverage - borrow_rate * (leverage - 1)
                net_apy = collateral_yield * leverage - borrow_apy * (leverage - 1)

                if net_apy <= 0:
                    continue

                # Build source URL
                market_id = market.get("uniqueKey", "")
                source_url = f"https://app.morpho.org/market?id={market_id}"

                opp = YieldOpportunity(
                    category=self.category,
                    protocol="Morpho",
                    chain=chain,
                    stablecoin=collateral_symbol,
                    apy=net_apy,
                    tvl=tvl,
                    leverage=leverage,
                    supply_apy=collateral_yield,
                    borrow_apy=borrow_apy,
                    risk_score=RiskAssessor.calculate_risk_score(
                        strategy_type="loop",
                        leverage=leverage,
                        protocol="Morpho",
                        chain=chain,
                        apy=net_apy,
                    ),
                    source_url=source_url,
                    additional_info={
                        "collateral": collateral_symbol,
                        "collateral_yield": collateral_yield,
                        "borrow_asset": loan_symbol,
                        "borrow_rate": borrow_apy,
                        "lltv": lltv * 100,
                        "theoretical_max_leverage": theoretical_max_leverage,
                        "safe_max_leverage": safe_max_leverage,
                        "risk_warning": RiskAssessor.get_leverage_risk_warning(leverage),
                    },
                )
                opportunities.append(opp)

        return opportunities

    def _is_yield_bearing(self, symbol: str) -> bool:
        """Check if symbol is a yield-bearing stablecoin."""
        if not any(pattern in symbol for pattern in self.YIELD_BEARING_PATTERNS):
            return False
        # Skip expired PT tokens
        if symbol.startswith("PT-") and self._is_pt_expired(symbol):
            return False
        return True

    @staticmethod
    def _is_pt_expired(symbol: str) -> bool:
        """Check if a PT token's maturity date has passed."""
        match = re.search(r'(\d{1,2})(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)(\d{4})', symbol)
        if not match:
            return False
        try:
            maturity = datetime.strptime(match.group(0), "%d%b%Y").date()
            return maturity < date.today()
        except ValueError:
            return False

    def _is_borrow_stable(self, symbol: str) -> bool:
        """Check if symbol is a regular stablecoin for borrowing."""
        return any(stable in symbol for stable in self.BORROW_STABLES)

    def _get_collateral_yield(self, symbol: str) -> float:
        """Get the yield rate for a yield-bearing stablecoin.

        Checks live data first (Pendle/Spectra PT yields, protocol APIs),
        then falls back to conservative hardcoded estimates.

        Args:
            symbol: Collateral symbol.

        Returns:
            Yield rate as percentage.
        """
        live = getattr(self, "_live_yields", {})

        # 1. Exact match in live data
        if symbol in live:
            return live[symbol]

        # 2. Partial match in live data (e.g., PT-CUSD-23JUL2026 matches PT-CUSD)
        for key, rate in live.items():
            if key in symbol:
                return rate
            # Only match symbol-in-key when key is not a PT token
            if symbol in key and not key.startswith("PT-"):
                return rate

        # 3. Exact match in fallback
        if symbol in self.FALLBACK_YIELD_RATES:
            return self.FALLBACK_YIELD_RATES[symbol]

        # 4. Partial match in fallback
        for key, rate in self.FALLBACK_YIELD_RATES.items():
            if key in symbol:
                return rate

        # No data - skip this asset
        return 0.0

    def _parse_lltv(self, lltv_raw: Any) -> float:
        """Parse LLTV value from various formats.

        Args:
            lltv_raw: Raw LLTV value.

        Returns:
            LLTV as decimal (0-1).
        """
        try:
            lltv_val = float(lltv_raw)
            # If it's a large number, it's in wei (18 decimals)
            if lltv_val > 1:
                return lltv_val / 1e18
            return lltv_val
        except (ValueError, TypeError):
            return 0
