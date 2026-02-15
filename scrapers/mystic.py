"""Scraper for Mystic Finance lending on Plume.

Mystic is a Morpho Blue fork on Plume that enables lending, borrowing,
and looping strategies with RWA-backed Nest Credit tokens as collateral.

APIs:
  - Mystic Morpho Blue: https://api.mysticfinance.xyz/morphoCache/lite?chainId=98866
  - Nest Credit vaults: https://api.nest.credit/v1/vaults/details-lite
"""

from typing import List, Dict

from .base import BaseScraper
from models.opportunity import YieldOpportunity
from utils.risk import RiskAssessor
from config import LEVERAGE_LEVELS


class MysticLendScraper(BaseScraper):
    """Scraper for Mystic Finance pUSD vault lending on Plume."""

    requires_vpn = False
    category = "Mystic Lend"
    cache_file = "mystic_lend"

    MYSTIC_API = "https://api.mysticfinance.xyz/morphoCache/lite?chainId=98866"

    # Stablecoin vault assets we care about
    LEND_STABLES = {"PUSD", "USDC", "USDT"}

    MIN_TVL = 10_000

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Fetch lending vault data from Mystic Morpho Blue API."""
        opportunities = []

        try:
            resp = self._make_request(self.MYSTIC_API)
            data = resp.json()
        except Exception:
            return opportunities

        for vault in data.get("vaults", []):
            try:
                symbol = (vault.get("vaultAssetSymbol", "") or "").upper()
                if symbol not in self.LEND_STABLES:
                    continue

                apy = float(vault.get("vaultApr", 0) or 0)
                tvl = float(vault.get("tvl", 0) or 0)

                if apy <= 0 or tvl < self.MIN_TVL:
                    continue

                vault_name = vault.get("vaultName", "")

                opp = YieldOpportunity(
                    category=self.category,
                    protocol="Mystic",
                    chain="Plume",
                    stablecoin=symbol,
                    apy=apy,
                    tvl=tvl,
                    supply_apy=apy,
                    risk_score=RiskAssessor.calculate_risk_score(
                        strategy_type="simple_lend",
                        protocol="Mystic",
                        chain="Plume",
                        apy=apy,
                    ),
                    source_url="https://app.mysticfinance.xyz/",
                    additional_info={
                        "vault_name": vault_name,
                    },
                )
                opportunities.append(opp)
            except (KeyError, TypeError, ValueError):
                continue

        return opportunities


class MysticLoopScraper(BaseScraper):
    """Scraper for Mystic Finance borrow/lend loop strategies on Plume.

    Uses Nest Credit vault tokens (nALPHA, nTBILL, nBASIS) as collateral,
    borrows pUSD on Mystic's Morpho Blue markets. Fetches live collateral
    yields from Nest Credit API and live borrow rates/LLTV from Mystic API.
    """

    requires_vpn = False
    category = "Mystic Borrow/Lend Loop"
    cache_file = "mystic_loop"

    MYSTIC_API = "https://api.mysticfinance.xyz/morphoCache/lite?chainId=98866"
    NEST_API = "https://api.nest.credit/v1/vaults/details-lite"

    # Nest tokens to include as collateral (exclude nCREDIT due to volatile APY)
    NEST_COLLATERALS = {"NALPHA", "NTBILL", "NBASIS"}

    MIN_TVL = 10_000
    MAX_BORROW_APR = 50

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Fetch live market data and calculate loop opportunities."""
        opportunities = []

        # Fetch live collateral yields from Nest Credit
        nest_yields = self._fetch_nest_yields()

        # Fetch Mystic Morpho Blue markets
        try:
            resp = self._make_request(self.MYSTIC_API)
            data = resp.json()
            markets = data.get("markets", [])
        except Exception:
            return opportunities

        for market in markets:
            try:
                collateral = market.get("collateralAsset", "")
                loan = market.get("loanAsset", "")
                collateral_upper = collateral.upper()

                # Only Nest token collateral borrowing pUSD
                if collateral_upper not in self.NEST_COLLATERALS:
                    continue
                if loan.upper() != "PUSD":
                    continue

                borrow_apr = float(market.get("borrowApr", 0) or 0)
                lltv = float(market.get("lltv", 0) or 0)
                total_supply = float(market.get("totalSupplyAssets", 0) or 0)
                loan_price = float(market.get("loanAssetPrice", 1) or 1)

                tvl = total_supply * loan_price
                if tvl < self.MIN_TVL:
                    continue
                if borrow_apr <= 0 or borrow_apr > self.MAX_BORROW_APR:
                    continue

                # Get collateral yield: prefer Nest Credit API (live), fall back to Mystic's embedded yield
                collateral_yield = nest_yields.get(collateral_upper, 0)
                if collateral_yield <= 0:
                    try:
                        collateral_yield = float(market.get("collateralAssetYield", 0) or 0)
                    except (ValueError, TypeError):
                        continue
                if collateral_yield <= 0:
                    continue

                # Calculate max safe leverage
                theoretical_max = 1 / (1 - lltv) if lltv < 1 else 1
                safe_max = min(theoretical_max * 0.6, 5.0)

                for leverage in LEVERAGE_LEVELS:
                    if leverage <= 1.0 or leverage > safe_max:
                        continue

                    net_apy = collateral_yield * leverage - borrow_apr * (leverage - 1)
                    if net_apy <= 0:
                        continue

                    opp = YieldOpportunity(
                        category=self.category,
                        protocol="Mystic",
                        chain="Plume",
                        stablecoin=collateral,
                        apy=net_apy,
                        tvl=tvl,
                        leverage=leverage,
                        supply_apy=collateral_yield,
                        borrow_apy=borrow_apr,
                        risk_score=RiskAssessor.calculate_risk_score(
                            strategy_type="loop",
                            leverage=leverage,
                            protocol="Mystic",
                            chain="Plume",
                            apy=net_apy,
                        ),
                        source_url="https://app.mysticfinance.xyz/markets",
                        additional_info={
                            "collateral": collateral,
                            "collateral_yield": collateral_yield,
                            "borrow_asset": "pUSD",
                            "borrow_rate": borrow_apr,
                            "lltv": lltv * 100,
                        },
                    )
                    opportunities.append(opp)

            except (KeyError, TypeError, ValueError):
                continue

        return opportunities

    def _fetch_nest_yields(self) -> Dict[str, float]:
        """Fetch live vault yields from Nest Credit API.

        Returns dict of uppercase symbol -> rolling 7d APY as percentage.
        """
        yields = {}
        try:
            resp = self._make_request(self.NEST_API)
            data = resp.json()
            vaults = data.get("data", data) if isinstance(data, dict) else data
            for vault in vaults:
                symbol = (vault.get("symbol", "") or "").upper()
                if symbol not in self.NEST_COLLATERALS:
                    continue
                apy_data = vault.get("apy", {})
                rolling7d = apy_data.get("rolling7d", 0) or 0
                if rolling7d > 0:
                    yields[symbol] = rolling7d * 100
        except Exception:
            pass
        return yields
