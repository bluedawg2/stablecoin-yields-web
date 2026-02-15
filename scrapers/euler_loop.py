"""Scraper for Euler cross-collateral borrow/lend loop strategies via native subgraphs."""

import re
from typing import List, Dict, Any

from .base import BaseScraper
from .euler_lend import EulerLendScraper
from models.opportunity import YieldOpportunity
from utils.risk import RiskAssessor
from config import LEVERAGE_LEVELS


class EulerLoopScraper(BaseScraper):
    """Calculates leveraged yield from Euler cross-collateral loops.

    Strategy: Supply collateral stablecoin -> borrow different stablecoin -> re-supply (loop).
    Net APY = supply_rate * leverage - borrow_rate * (leverage - 1)
    Uses the vault collaterals field from the subgraph to discover valid pairs.
    """

    requires_vpn = False
    category = "Euler Borrow/Lend Loop"
    cache_file = "euler_loop"

    # Minimum net APY to show (filter out unprofitable loops)
    MIN_NET_APY = 0.5

    # Maximum borrow APY to consider
    MAX_BORROW_APY = 50
    MAX_SUPPLY_APY = 25

    # APY scale factor (same as lend scraper)
    APY_SCALE = 1e27

    MIN_TVL = 10_000

    @staticmethod
    def _extract_underlying(symbol: str) -> str:
        """Extract underlying asset from vault symbol.

        Examples: 'esBOLD-1' -> 'sBOLD', 'eUSDC-70' -> 'USDC',
        'ePT-sUSDai-19MAR2026-4' -> 'PT-sUSDai-19MAR2026'
        """
        s = re.sub(r'^e', '', symbol)
        s = re.sub(r'-\d+$', '', s)
        return s

    @staticmethod
    def _is_stablecoin(name: str, symbol: str, patterns: list) -> bool:
        """Check if a vault's name/symbol matches any stablecoin pattern."""
        combined = (name + " " + symbol).upper()
        return any(p in combined for p in patterns)

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Fetch Euler vault data and calculate cross-collateral loop APYs."""
        opportunities = []
        lend_scraper = EulerLendScraper()

        for chain_name, endpoint in lend_scraper.SUBGRAPH_ENDPOINTS.items():
            try:
                response = lend_scraper._make_request(
                    endpoint,
                    method="POST",
                    json_data={"query": lend_scraper.VAULT_QUERY},
                )
                data = response.json()
                vaults = data.get("data", {}).get("eulerVaults", [])

                # Build address -> vault lookup
                vault_map = {v.get("id", "").lower(): v for v in vaults}

                chain_opps = self._find_cross_collateral_loops(
                    vaults, vault_map, chain_name, lend_scraper.STABLECOIN_PATTERNS
                )
                opportunities.extend(chain_opps)
            except Exception:
                continue

        return opportunities

    def _find_cross_collateral_loops(
        self,
        vaults: List[Dict[str, Any]],
        vault_map: Dict[str, Dict[str, Any]],
        chain: str,
        stablecoin_patterns: list,
    ) -> List[YieldOpportunity]:
        """Find cross-collateral loop opportunities for a chain."""
        opportunities = []

        for vault in vaults:
            try:
                state = vault.get("state")
                if not state:
                    continue

                # This vault is the borrow vault
                borrow_apy = (int(state.get("borrowApy", "0") or "0") / self.APY_SCALE) * 100
                if borrow_apy <= 0 or borrow_apy > self.MAX_BORROW_APY:
                    continue

                borrow_name = vault.get("name", "")
                borrow_symbol = vault.get("symbol", "")
                if not self._is_stablecoin(borrow_name, borrow_symbol, stablecoin_patterns):
                    continue

                borrow_underlying = self._extract_underlying(borrow_symbol)

                # Calculate TVL of the borrow vault
                decimals = int(vault.get("decimals", "18") or "18")
                total_borrows = int(state.get("totalBorrows", "0") or "0")
                cash = int(state.get("cash", "0") or "0")
                tvl = (total_borrows + cash) / (10 ** decimals)
                if tvl < self.MIN_TVL:
                    continue

                # Check each accepted collateral vault
                for coll_addr in vault.get("collaterals", []):
                    coll_vault = vault_map.get(coll_addr.lower())
                    if not coll_vault:
                        continue

                    coll_name = coll_vault.get("name", "")
                    coll_symbol = coll_vault.get("symbol", "")
                    if not self._is_stablecoin(coll_name, coll_symbol, stablecoin_patterns):
                        continue

                    coll_state = coll_vault.get("state")
                    if not coll_state:
                        continue

                    supply_apy = (int(coll_state.get("supplyApy", "0") or "0") / self.APY_SCALE) * 100
                    if supply_apy <= 0 or supply_apy > self.MAX_SUPPLY_APY:
                        continue

                    coll_underlying = self._extract_underlying(coll_symbol)
                    pair_label = f"{coll_underlying}/{borrow_underlying}"

                    for leverage in LEVERAGE_LEVELS:
                        if leverage <= 1.0 or leverage > 5.0:
                            continue

                        net_apy = supply_apy * leverage - borrow_apy * (leverage - 1)
                        if net_apy < self.MIN_NET_APY:
                            continue

                        opp = YieldOpportunity(
                            category=self.category,
                            protocol="Euler",
                            chain=chain,
                            stablecoin=pair_label,
                            apy=net_apy,
                            tvl=tvl,
                            leverage=leverage,
                            supply_apy=supply_apy,
                            borrow_apy=borrow_apy,
                            risk_score=RiskAssessor.calculate_risk_score(
                                strategy_type="loop",
                                leverage=leverage,
                                protocol="Euler",
                                chain=chain,
                                apy=net_apy,
                            ),
                            source_url="https://app.euler.finance",
                            additional_info={
                                "collateral": coll_underlying,
                                "borrow_asset": borrow_underlying,
                                "supply_rate": supply_apy,
                                "borrow_rate": borrow_apy,
                                "data_source": "Euler Subgraph",
                                "risk_warning": RiskAssessor.get_leverage_risk_warning(leverage),
                            },
                        )
                        opportunities.append(opp)

            except (KeyError, TypeError, ValueError):
                continue

        return opportunities
