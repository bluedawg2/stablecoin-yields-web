"""Scraper for Euler lending rates via native Euler v2 subgraphs."""

from typing import List, Dict, Any

from .base import BaseScraper
from models.opportunity import YieldOpportunity
from utils.risk import RiskAssessor


class EulerLendScraper(BaseScraper):
    """Scraper for Euler lending rates via native Goldsky-hosted subgraphs."""

    requires_vpn = False
    category = "Euler Lend"
    cache_file = "euler_lend"

    # Minimum TVL to filter out empty/unreliable markets
    MIN_TVL_USD = 10_000

    # Maximum reasonable APY (filter out anomalies/data errors)
    MAX_APY_PERCENT = 25

    # Euler v2 subgraph endpoints (Goldsky-hosted)
    SUBGRAPH_ENDPOINTS = {
        "Ethereum": "https://api.goldsky.com/api/public/project_cm4iagnemt1wp01xn4gh1agft/subgraphs/euler-v2-mainnet/latest/gn",
        "Base": "https://api.goldsky.com/api/public/project_cm4iagnemt1wp01xn4gh1agft/subgraphs/euler-v2-base/latest/gn",
        "Arbitrum": "https://api.goldsky.com/api/public/project_cm4iagnemt1wp01xn4gh1agft/subgraphs/euler-v2-arbitrum/latest/gn",
        "Optimism": "https://api.goldsky.com/api/public/project_cm4iagnemt1wp01xn4gh1agft/subgraphs/euler-v2-optimism/latest/gn",
        "Bob": "https://api.goldsky.com/api/public/project_cm4iagnemt1wp01xn4gh1agft/subgraphs/euler-v2-bob/latest/gn",
        "Swell": "https://api.goldsky.com/api/public/project_cm4iagnemt1wp01xn4gh1agft/subgraphs/euler-v2-swell/latest/gn",
        "Ink": "https://api.goldsky.com/api/public/project_cm4iagnemt1wp01xn4gh1agft/subgraphs/euler-v2-ink/latest/gn",
        "Unichain": "https://api.goldsky.com/api/public/project_cm4iagnemt1wp01xn4gh1agft/subgraphs/euler-v2-unichain/latest/gn",
        "TAC": "https://api.goldsky.com/api/public/project_cm4iagnemt1wp01xn4gh1agft/subgraphs/euler-v2-tac/latest/gn",
        "Linea": "https://api.goldsky.com/api/public/project_cm4iagnemt1wp01xn4gh1agft/subgraphs/euler-v2-linea/latest/gn",
        "Avalanche": "https://api.goldsky.com/api/public/project_cm4iagnemt1wp01xn4gh1agft/subgraphs/euler-v2-avalanche/latest/gn",
        "Plasma": "https://api.goldsky.com/api/public/project_cm4iagnemt1wp01xn4gh1agft/subgraphs/euler-v2-plasma/latest/gn",
    }

    # Stablecoin patterns in vault names/symbols
    STABLECOIN_PATTERNS = [
        "USDC", "USDT", "USDAI", "SDAI", "DAI", "FRAX", "LUSD", "SUSDE", "USDE",
        "USDS", "SUSDS", "GHO", "CRVUSD", "PYUSD", "USDM", "TUSD",
        "GUSD", "USDP", "DOLA", "MIM", "ALUSD", "FDUSD", "RLUSD",
        "YOUSD", "YUSD", "USN", "USD0", "USDN", "BOLD", "MUSD",
        "EUSD", "THBILL", "USDF", "USD",
    ]

    # APY scale factor (subgraph stores APY as BigInt with 1e27 precision)
    APY_SCALE = 1e27

    VAULT_QUERY = """
    {
        eulerVaults(first: 1000, orderBy: state__totalShares, orderDirection: desc) {
            id
            name
            symbol
            decimals
            collaterals
            state {
                supplyApy
                borrowApy
                totalBorrows
                cash
            }
        }
    }
    """

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Fetch lending rates from Euler native subgraphs."""
        opportunities = []

        for chain_name, endpoint in self.SUBGRAPH_ENDPOINTS.items():
            try:
                chain_opps = self._fetch_chain_data(chain_name, endpoint)
                opportunities.extend(chain_opps)
            except Exception:
                continue

        return opportunities

    def _fetch_chain_data(self, chain: str, endpoint: str) -> List[YieldOpportunity]:
        """Fetch vault data for a specific chain."""
        response = self._make_request(
            endpoint,
            method="POST",
            json_data={"query": self.VAULT_QUERY},
        )

        data = response.json()
        vaults = data.get("data", {}).get("eulerVaults", [])
        return self._parse_vaults(vaults, chain)

    def _parse_vaults(self, vaults: List[Dict[str, Any]], chain: str) -> List[YieldOpportunity]:
        """Parse vault data from subgraph response."""
        opportunities = []

        for vault in vaults:
            try:
                name = vault.get("name", "")
                symbol = vault.get("symbol", "")

                # Extract the underlying stablecoin from vault name/symbol
                # Format: "EVK Vault eUSDC-1" or "eUSDC-1"
                stablecoin = self._extract_stablecoin(name, symbol)
                if not stablecoin:
                    continue

                state = vault.get("state")
                if not state:
                    continue

                # APY is stored as BigInt with 1e27 precision
                supply_apy_raw = int(state.get("supplyApy", "0") or "0")
                supply_apy = (supply_apy_raw / self.APY_SCALE) * 100  # to percentage

                # Calculate TVL: total_borrows + cash = total supply (in token units)
                decimals = int(vault.get("decimals", "18") or "18")
                total_borrows = int(state.get("totalBorrows", "0") or "0")
                cash = int(state.get("cash", "0") or "0")
                total_supply = (total_borrows + cash) / (10 ** decimals)

                # For stablecoins, 1 token ~= $1
                tvl = total_supply

                if tvl < self.MIN_TVL_USD:
                    continue

                if supply_apy <= 0 or supply_apy > self.MAX_APY_PERCENT:
                    continue

                borrow_apy_raw = int(state.get("borrowApy", "0") or "0")
                borrow_apy = (borrow_apy_raw / self.APY_SCALE) * 100

                vault_id = vault.get("id", "")

                opp = YieldOpportunity(
                    category=self.category,
                    protocol="Euler",
                    chain=chain,
                    stablecoin=stablecoin,
                    apy=supply_apy,
                    tvl=tvl,
                    supply_apy=supply_apy,
                    borrow_apy=borrow_apy,
                    risk_score=RiskAssessor.calculate_risk_score(
                        strategy_type="simple_lend",
                        protocol="Euler",
                        chain=chain,
                        apy=supply_apy,
                    ),
                    source_url=f"https://app.euler.finance/vault/{vault_id}" if vault_id else "https://app.euler.finance",
                    additional_info={
                        "vault_name": name,
                        "vault_symbol": symbol,
                        "vault_id": vault_id,
                        "data_source": "Euler Subgraph",
                    },
                )
                opportunities.append(opp)

            except (KeyError, TypeError, ValueError):
                continue

        return opportunities

    def _extract_stablecoin(self, name: str, symbol: str) -> str | None:
        """Extract stablecoin symbol from vault name/symbol.

        Vault names like "EVK Vault eUSDC-1", symbols like "eUSDC-1".
        """
        # Check name and symbol for stablecoin patterns.
        # Search the uppercased combined string but return the original-case
        # substring so that e.g. "eUSDai-1" yields "USDai" not "USDAI".
        combined_orig = name + " " + symbol
        combined_upper = combined_orig.upper()
        for stable in self.STABLECOIN_PATTERNS:
            idx = combined_upper.find(stable)
            if idx != -1:
                return combined_orig[idx: idx + len(stable)]
        return None
