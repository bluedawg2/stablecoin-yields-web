"""Scraper for Pendle looping strategies."""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from .base import BaseScraper
from .pendle_fixed import PendleFixedScraper
from models.opportunity import YieldOpportunity
from utils.risk import RiskAssessor
from config import PENDLE_LOOP_CHAINS, PENDLE_LOOP_PROTOCOLS, LEVERAGE_LEVELS


class PendleLoopScraper(BaseScraper):
    """Calculates Pendle looping strategies (PT as collateral, borrow stablecoin)."""

    requires_vpn = False
    category = "Pendle Looping"
    cache_file = "pendle_loop"

    # Morpho API for live borrow rates
    MORPHO_API_URL = "https://blue-api.morpho.org/graphql"

    # Minimum liquidity to consider a borrow market viable (in USD)
    # Set higher to filter out illiquid markets that can't handle real positions
    # Markets under $500k liquidity are generally too thin for meaningful positions
    # and may display misleading rates that users cannot actually access
    MIN_LIQUIDITY_USD = 500_000

    # Fallback borrow rates if API fails (conservative estimates)
    FALLBACK_BORROW_RATES = {
        "Euler": {"USDC": 7.5, "USDT": 7.0, "DAI": 8.0},
        "Morpho": {"USDC": 6.5, "USDT": 6.0, "DAI": 7.0},
        "Silo": {"USDC": 8.0, "USDT": 7.5, "DAI": 8.5},
        "Aave": {"USDC": 5.5, "USDT": 5.0, "DAI": 6.0},
    }

    # Max LTV for PT collateral by protocol (fallback)
    DEFAULT_PT_LTV = {
        "Euler": 0.80,
        "Morpho": 0.85,
        "Silo": 0.75,
        "Aave": 0.70,
    }

    # Chain ID mappings
    CHAIN_IDS = {
        "Ethereum": 1,
        "Base": 8453,
        "Arbitrum": 42161,
        "Optimism": 10,
    }

    # Stablecoins that can be borrowed
    BORROW_STABLES = ["USDC", "USDT", "DAI", "USDS", "FRAX", "GHO", "PYUSD", "USDTB", "AUSD"]

    def __init__(self):
        """Initialize with Pendle fixed scraper for PT yields."""
        super().__init__()
        self.pendle_scraper = PendleFixedScraper()
        self._morpho_markets_cache: Dict[str, List[Dict]] = {}  # chain -> markets

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Calculate Pendle looping yields using live borrow rates."""
        opportunities = []

        # Fetch live Morpho borrow markets first
        self._fetch_morpho_markets()

        # Get Pendle PT yields
        try:
            pendle_opportunities = self.pendle_scraper.fetch(use_cache=True)
        except Exception:
            pendle_opportunities = self.pendle_scraper._get_known_markets()

        # Filter for chains that support PT looping
        pendle_opportunities = [
            opp for opp in pendle_opportunities
            if opp.chain in PENDLE_LOOP_CHAINS
        ]

        # Calculate looped yields for each PT market using Morpho live data
        for pt_opp in pendle_opportunities:
            # Only use Morpho (has live PT collateral markets)
            loop_opps = self._calculate_morpho_loop_yields(pt_opp)
            opportunities.extend(loop_opps)

        return opportunities

    def _fetch_morpho_markets(self) -> None:
        """Fetch all Morpho borrow markets for supported chains."""
        for chain_name, chain_id in self.CHAIN_IDS.items():
            try:
                markets = self._fetch_morpho_chain_markets(chain_id)
                self._morpho_markets_cache[chain_name] = markets
            except Exception:
                self._morpho_markets_cache[chain_name] = []

    def _fetch_morpho_chain_markets(self, chain_id: int) -> List[Dict]:
        """Fetch Morpho markets for a specific chain.

        Args:
            chain_id: Chain ID to fetch.

        Returns:
            List of market data dicts.
        """
        query = """
        query GetMarkets($chainId: Int!) {
            markets(where: { chainId_in: [$chainId] }, first: 1000) {
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
                        netBorrowApy
                        avgNetBorrowApy
                        supplyAssetsUsd
                        borrowAssetsUsd
                        liquidityAssetsUsd
                    }
                    lltv
                }
            }
        }
        """

        response = self._make_request(
            self.MORPHO_API_URL,
            method="POST",
            json_data={
                "query": query,
                "variables": {"chainId": chain_id},
            },
        )

        data = response.json()
        return data.get("data", {}).get("markets", {}).get("items", [])

    def _find_best_borrow_markets(
        self, chain: str, collateral_symbol: str, maturity_date: Optional[datetime] = None
    ) -> List[Dict]:
        """Find the best borrow markets for a given collateral on Morpho.

        Args:
            chain: Chain name.
            collateral_symbol: Collateral token symbol (e.g., "USDe", "sUSDe").
            maturity_date: PT maturity date to match against Morpho market.

        Returns:
            List of viable borrow markets sorted by rate (lowest first).
        """
        markets = self._morpho_markets_cache.get(chain, [])
        viable_markets = []

        for market in markets:
            collateral = market.get("collateralAsset", {})
            loan = market.get("loanAsset", {})
            state = market.get("state", {})

            if not collateral or not loan:
                continue

            collateral_sym = collateral.get("symbol", "").upper()
            loan_sym = loan.get("symbol", "").upper()

            # STRICT MATCHING: For PT tokens, the Morpho market MUST have a PT collateral
            # that matches both the underlying AND the maturity date
            is_pt_collateral = collateral_sym.startswith("PT-") or "PT-" in collateral_sym

            # If we're looking for a PT loop opportunity, require PT collateral on Morpho
            if not is_pt_collateral:
                continue

            # Extract underlying from PT symbol (e.g., "PT-SUSDE-27MAR2025" -> "SUSDE")
            morpho_underlying = self._extract_underlying_from_pt(collateral_sym)
            pendle_underlying = collateral_symbol.upper()

            # Check if underlying matches - require exact or very close match
            # Be strict to avoid matching sUSDai with USDai (they're different tokens)
            underlying_match = self._underlyings_match(morpho_underlying, pendle_underlying)

            if not underlying_match:
                continue

            # REQUIRE maturity date matching for PT markets
            if maturity_date:
                morpho_maturity = self._extract_maturity_from_symbol(collateral_sym)
                if not morpho_maturity:
                    # No maturity in Morpho symbol - skip this market
                    continue
                # Strict matching: allow only 3 days tolerance
                days_diff = abs((morpho_maturity - maturity_date).days)
                if days_diff > 3:
                    continue  # Skip markets with wrong maturity
            else:
                # No maturity date provided from Pendle - cannot validate, skip
                continue

            # Check if loan is a stablecoin we can borrow
            if not any(stable in loan_sym for stable in self.BORROW_STABLES):
                continue

            # Get market stats
            # Use borrowApy (current rate), NOT avgNetBorrowApy (historical average
            # that includes MORPHO rewards and understates actual borrow cost)
            borrow_raw = state.get("borrowApy") or 0
            borrow_apy = borrow_raw * 100
            liquidity = state.get("liquidityAssetsUsd") or state.get("supplyAssetsUsd") or 0

            # Filter out markets with insufficient liquidity
            if liquidity < self.MIN_LIQUIDITY_USD:
                continue

            # Filter out unreasonable borrow rates
            if borrow_apy <= 0 or borrow_apy > 50:
                continue

            # Parse LLTV
            lltv = self._parse_lltv(market.get("lltv", "0"))

            viable_markets.append({
                "loan_symbol": loan_sym,
                "borrow_apy": borrow_apy,
                "liquidity": liquidity,
                "lltv": lltv,
                "market_id": market.get("uniqueKey", ""),
            })

        # Sort by borrow rate (lowest first)
        viable_markets.sort(key=lambda m: m["borrow_apy"])
        return viable_markets

    def _parse_lltv(self, lltv_raw: Any) -> float:
        """Parse LLTV value from various formats."""
        try:
            lltv_val = float(lltv_raw)
            if lltv_val > 1:
                return lltv_val / 1e18
            return lltv_val
        except (ValueError, TypeError):
            return 0.85  # Default

    def _extract_underlying_from_pt(self, pt_symbol: str) -> str:
        """Extract underlying asset from PT symbol like 'PT-SUSDE-27MAR2025'.

        Args:
            pt_symbol: PT token symbol.

        Returns:
            Underlying asset symbol (e.g., "SUSDE").
        """
        import re

        # Remove PT- prefix
        symbol = pt_symbol.upper().replace("PT-", "")

        # Remove date suffix (e.g., "-27MAR2025" or "27MAR2025")
        date_pattern = r"-?\d{1,2}[A-Z]{3}\d{4}$"
        symbol = re.sub(date_pattern, "", symbol)

        # Remove any trailing dashes
        return symbol.rstrip("-")

    def _underlyings_match(self, morpho_underlying: str, pendle_underlying: str) -> bool:
        """Check if Morpho and Pendle underlyings match.

        Strict matching to avoid confusing similar tokens like:
        - sUSDai vs USDai (staked vs unstaked)
        - sUSDe vs USDe
        - srUSDe vs rUSDe

        Args:
            morpho_underlying: Underlying extracted from Morpho PT symbol.
            pendle_underlying: Underlying from Pendle opportunity.

        Returns:
            True if underlyings match.
        """
        m = morpho_underlying.upper()
        p = pendle_underlying.upper()

        # Exact match
        if m == p:
            return True

        # Handle common variations in naming (normalize both)
        # Remove common prefixes/suffixes that don't change the underlying
        def normalize(s: str) -> str:
            # Strip common wrapper prefixes that don't change the underlying asset
            s = s.replace("-", "").replace("_", "")
            return s

        m_norm = normalize(m)
        p_norm = normalize(p)

        if m_norm == p_norm:
            return True

        # Special case: staked versions must match exactly
        # sUSDai should NOT match USDai, sUSDe should NOT match USDe
        if m.startswith("S") and not p.startswith("S"):
            return False
        if p.startswith("S") and not m.startswith("S"):
            return False

        # Require exact match after normalization - substring matching causes cross-contamination
        # (e.g., REUSD matching REUSDE which are different tokens)
        return False

    def _extract_maturity_from_symbol(self, symbol: str) -> Optional[datetime]:
        """Extract maturity date from PT symbol like 'PT-REUSD-25JUN2026'.

        Args:
            symbol: Token symbol with embedded date.

        Returns:
            Datetime if found, None otherwise.
        """
        import re

        # Match patterns like "25JUN2026", "18DEC2025", "30APR2026"
        date_pattern = r"(\d{1,2})([A-Z]{3})(\d{4})"
        match = re.search(date_pattern, symbol.upper())

        if not match:
            return None

        day, month_str, year = match.groups()

        month_map = {
            "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4,
            "MAY": 5, "JUN": 6, "JUL": 7, "AUG": 8,
            "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
        }

        month = month_map.get(month_str)
        if not month:
            return None

        try:
            return datetime(int(year), month, int(day))
        except ValueError:
            return None

    def _calculate_morpho_loop_yields(self, pt_opp: YieldOpportunity) -> List[YieldOpportunity]:
        """Calculate loop yields using live Morpho borrow markets.

        Args:
            pt_opp: Base PT opportunity.

        Returns:
            List of loop opportunities at various leverage levels.
        """
        opportunities = []

        # Find borrow markets for this PT's underlying
        # PT-USDe can use USDe as collateral on Morpho
        # Pass maturity date to match correct Morpho market (avoid expired markets)
        underlying = pt_opp.stablecoin
        maturity = pt_opp.maturity_date
        # Convert to naive datetime for comparison if needed
        if maturity and maturity.tzinfo is not None:
            maturity = maturity.replace(tzinfo=None)
        borrow_markets = self._find_best_borrow_markets(pt_opp.chain, underlying, maturity)

        if not borrow_markets:
            # No viable Morpho markets found - don't generate fake opportunities
            return opportunities

        # Create opportunities for each viable borrow market
        for market in borrow_markets[:3]:  # Top 3 lowest rate markets
            for leverage in LEVERAGE_LEVELS:
                if leverage == 1.0:
                    continue

                lltv = market["lltv"]
                if lltv <= 0:
                    lltv = 0.85

                # Check if leverage is achievable
                max_leverage = 1 / (1 - lltv) if lltv < 1 else 1
                if leverage > max_leverage * 0.9:  # 90% of max for safety
                    continue

                pt_yield = pt_opp.apy
                borrow_rate = market["borrow_apy"]

                # Net APY calculation
                net_apy = pt_yield * leverage - borrow_rate * (leverage - 1)

                if net_apy <= 0:
                    continue

                pt_symbol = f"PT-{pt_opp.stablecoin}"
                loan_symbol = market["loan_symbol"]

                risk_score = RiskAssessor.calculate_risk_score(
                    strategy_type="pendle_loop",
                    leverage=leverage,
                    protocol="Morpho",
                    chain=pt_opp.chain,
                    maturity_date=pt_opp.maturity_date,
                    apy=net_apy,
                )

                # Build source URL
                market_id = market.get("market_id", "")
                source_url = f"https://app.morpho.org/market?id={market_id}" if market_id else "https://app.pendle.finance"

                # Use Morpho liquidity as TVL (actual borrowable amount)
                morpho_liquidity = market["liquidity"]

                opp = YieldOpportunity(
                    category=self.category,
                    protocol="Pendle + Morpho",
                    chain=pt_opp.chain,
                    stablecoin=pt_opp.stablecoin,
                    apy=net_apy,
                    tvl=morpho_liquidity,  # Show Morpho liquidity, not Pendle TVL
                    leverage=leverage,
                    supply_apy=pt_yield,
                    borrow_apy=borrow_rate,
                    maturity_date=pt_opp.maturity_date,
                    risk_score=risk_score,
                    source_url=source_url,
                    additional_info={
                        "collateral": pt_symbol,
                        "collateral_yield": pt_yield,
                        "borrow_asset": loan_symbol,
                        "borrow_rate": borrow_rate,
                        "pt_symbol": pt_symbol,
                        "pt_fixed_yield": pt_yield,
                        "lending_protocol": "Morpho",
                        "lltv": lltv * 100,
                        "liquidity": morpho_liquidity,
                        "pendle_tvl": pt_opp.tvl,  # Keep original Pendle TVL for reference
                        "market_id": market_id,
                        "risk_warning": RiskAssessor.get_leverage_risk_warning(leverage),
                        "maturity_risk": self._get_maturity_warning(pt_opp.maturity_date),
                    },
                )
                opportunities.append(opp)

        return opportunities

    def _calculate_loop_yield_fallback(
        self,
        pt_opp: YieldOpportunity,
        lending_protocol: str,
        leverage: float,
    ) -> Optional[YieldOpportunity]:
        """Calculate loop yield using fallback rates (when live data unavailable).

        Strategy: Deposit PT as collateral, borrow stablecoin, buy more PT, repeat.

        Args:
            pt_opp: Base PT opportunity with fixed yield.
            lending_protocol: Protocol to borrow from.
            leverage: Target leverage level.

        Returns:
            Loop opportunity or None if not viable.
        """
        # Get borrow rate for the stablecoin
        borrow_rates = self.FALLBACK_BORROW_RATES.get(lending_protocol, {})

        # Map the PT underlying to a borrowable stablecoin
        borrow_stable = self._get_borrow_stablecoin(pt_opp.stablecoin)
        borrow_rate = borrow_rates.get(borrow_stable, 7.0)  # Default 7%

        # Get max LTV for this protocol
        max_ltv = self.DEFAULT_PT_LTV.get(lending_protocol, 0.75)

        # Check if leverage is achievable with given LTV
        # Max leverage = 1 / (1 - LTV)
        max_leverage = 1 / (1 - max_ltv)
        if leverage > max_leverage:
            return None

        # Calculate effective yield
        # At leverage L:
        # - You earn PT yield on L times your capital
        # - You pay borrow rate on (L-1) times your capital
        pt_yield = pt_opp.apy
        net_apy = pt_yield * leverage - borrow_rate * (leverage - 1)

        # Skip if negative yield
        if net_apy <= 0:
            return None

        # Calculate risk score
        risk_score = RiskAssessor.calculate_risk_score(
            strategy_type="pendle_loop",
            leverage=leverage,
            protocol=lending_protocol,
            chain=pt_opp.chain,
            maturity_date=pt_opp.maturity_date,
            apy=net_apy,
        )

        pt_symbol = f"PT-{pt_opp.stablecoin}"

        return YieldOpportunity(
            category=self.category,
            protocol=f"Pendle + {lending_protocol}",
            chain=pt_opp.chain,
            stablecoin=pt_opp.stablecoin,
            apy=net_apy,
            tvl=pt_opp.tvl,
            leverage=leverage,
            supply_apy=pt_yield,
            borrow_apy=borrow_rate,
            maturity_date=pt_opp.maturity_date,
            risk_score=risk_score,
            source_url="https://app.pendle.finance",
            additional_info={
                # Consistent keys for display (collateral -> borrow_asset format)
                "collateral": pt_symbol,
                "collateral_yield": pt_yield,
                "borrow_asset": borrow_stable,
                "borrow_rate": borrow_rate,
                # Additional Pendle-specific info
                "pt_symbol": pt_symbol,
                "pt_fixed_yield": pt_yield,
                "borrow_stablecoin": borrow_stable,
                "lending_protocol": lending_protocol,
                "max_ltv": max_ltv,
                "lltv": max_ltv * 100,  # Percentage for display
                "estimated_rate": True,  # Flag that this uses estimated rates
                "risk_warning": RiskAssessor.get_leverage_risk_warning(leverage),
                "maturity_risk": self._get_maturity_warning(pt_opp.maturity_date),
            },
        )

    def _get_borrow_stablecoin(self, pt_underlying: str) -> str:
        """Map PT underlying to borrowable stablecoin.

        Args:
            pt_underlying: PT underlying asset symbol.

        Returns:
            Borrowable stablecoin symbol.
        """
        # Most PT strategies borrow USDC or the underlying stable
        underlying_upper = pt_underlying.upper()

        if "USDC" in underlying_upper:
            return "USDC"
        if "USDT" in underlying_upper:
            return "USDT"
        if "DAI" in underlying_upper or "SDAI" in underlying_upper:
            return "DAI"

        # Default to USDC
        return "USDC"

    def _get_maturity_warning(self, maturity: Optional[datetime]) -> Optional[str]:
        """Get warning about maturity date.

        Args:
            maturity: Maturity date.

        Returns:
            Warning message or None.
        """
        if not maturity:
            return None

        # Handle timezone-aware vs naive datetimes
        now = datetime.now()
        if maturity.tzinfo is not None:
            from datetime import timezone
            now = datetime.now(timezone.utc)
        days_to_maturity = (maturity - now).days

        if days_to_maturity < 7:
            return "CRITICAL: Less than 7 days to maturity - extreme liquidation risk"
        if days_to_maturity < 14:
            return "WARNING: Less than 14 days to maturity - high liquidation risk"
        if days_to_maturity < 30:
            return "CAUTION: Less than 30 days to maturity - monitor closely"

        return None
