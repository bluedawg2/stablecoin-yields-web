"""Scraper for Euler borrow/lend loop strategies via native subgraphs."""

from typing import List, Dict, Any

from .base import BaseScraper
from .euler_lend import EulerLendScraper
from models.opportunity import YieldOpportunity
from utils.risk import RiskAssessor
from config import LEVERAGE_LEVELS


class EulerLoopScraper(BaseScraper):
    """Calculates leveraged yield from Euler using supply/borrow rate spread.

    Strategy: Supply stablecoin -> borrow same stablecoin -> re-supply (loop).
    Net APY = supply_rate * leverage - borrow_rate * (leverage - 1)
    """

    requires_vpn = False
    category = "Euler Borrow/Lend Loop"
    cache_file = "euler_loop"

    # Minimum net APY to show (filter out unprofitable loops)
    MIN_NET_APY = 0.5

    # Maximum borrow APY to consider
    MAX_BORROW_APY = 50

    # APY scale factor (same as lend scraper)
    APY_SCALE = 1e27

    # Stablecoin patterns
    STABLECOIN_PATTERNS = [
        "USDC", "USDT", "DAI", "FRAX", "LUSD", "SDAI", "SUSDE", "USDE",
        "USDS", "SUSDS", "GHO", "CRVUSD", "PYUSD", "USDM", "TUSD",
        "GUSD", "USDP", "DOLA", "MIM", "ALUSD", "FDUSD", "RLUSD",
        "YOUSD", "YUSD", "USN", "USD0",
    ]

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Fetch Euler vault data and calculate loop APYs."""
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

                for vault in vaults:
                    loop_opps = self._calculate_loop_for_vault(vault, chain_name)
                    opportunities.extend(loop_opps)
            except Exception:
                continue

        return opportunities

    def _calculate_loop_for_vault(self, vault: Dict[str, Any], chain: str) -> List[YieldOpportunity]:
        """Calculate loop opportunities for a single vault."""
        opportunities = []

        try:
            name = vault.get("name", "")
            symbol = vault.get("symbol", "")

            stablecoin = self._extract_stablecoin(name, symbol)
            if not stablecoin:
                return []

            state = vault.get("state")
            if not state:
                return []

            # Parse APYs from BigInt (1e27 precision)
            supply_apy_raw = int(state.get("supplyApy", "0") or "0")
            borrow_apy_raw = int(state.get("borrowApy", "0") or "0")

            supply_apy = (supply_apy_raw / self.APY_SCALE) * 100
            borrow_apy = (borrow_apy_raw / self.APY_SCALE) * 100

            if supply_apy <= 0 or borrow_apy <= 0:
                return []
            if borrow_apy > self.MAX_BORROW_APY:
                return []

            # Calculate TVL
            decimals = int(vault.get("decimals", "18") or "18")
            total_borrows = int(state.get("totalBorrows", "0") or "0")
            cash = int(state.get("cash", "0") or "0")
            tvl = (total_borrows + cash) / (10 ** decimals)

            if tvl < 10_000:
                return []

            vault_id = vault.get("id", "")

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
                    stablecoin=stablecoin,
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
                    source_url=f"https://app.euler.finance/vault/{vault_id}" if vault_id else "https://app.euler.finance",
                    additional_info={
                        "vault_name": name,
                        "vault_id": vault_id,
                        "borrow_rate": borrow_apy,
                        "supply_rate": supply_apy,
                        "data_source": "Euler Subgraph",
                        "risk_warning": RiskAssessor.get_leverage_risk_warning(leverage),
                    },
                )
                opportunities.append(opp)

        except (KeyError, TypeError, ValueError):
            pass

        return opportunities

    def _extract_stablecoin(self, name: str, symbol: str) -> str | None:
        """Extract stablecoin symbol from vault name/symbol."""
        combined = (name + " " + symbol).upper()
        for stable in self.STABLECOIN_PATTERNS:
            if stable in combined:
                return stable
        return None
