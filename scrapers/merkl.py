"""Scraper for Merkl rewards."""

import re
from typing import List, Dict, Any

from .base import BaseScraper
from models.opportunity import YieldOpportunity
from utils.risk import RiskAssessor


class MerklScraper(BaseScraper):
    """Scraper for Merkl protocol rewards."""

    requires_vpn = False
    category = "Merkl Rewards"
    cache_file = "merkl"

    API_URL = "https://api.merkl.xyz/v4/opportunities"

    # Minimum TVL to filter out empty/unreliable opportunities
    MIN_TVL_USD = 1_000

    # Minimum daily rewards to filter out inactive campaigns
    MIN_DAILY_REWARDS_USD = 1

    # Maximum reasonable APR (filter out anomalies)
    MAX_APR_PERCENT = 500

    # Stablecoin symbols to filter
    STABLECOIN_SYMBOLS = [
        "USDC", "USDT", "DAI", "FRAX", "LUSD", "SDAI", "SUSDE", "USDE",
        "USDS", "SUSDS", "GHO", "CRVUSD", "PYUSD", "USDM", "TUSD",
        "GUSD", "USDP", "DOLA", "MIM", "ALUSD", "FDUSD", "USDN",
        "BOLD", "SUSD", "EUSD", "USN", "AUSD", "MUSD", "USD",
    ]

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Fetch active reward campaigns from Merkl with pagination."""
        opportunities = []
        total_api_items = 0

        # Fetch all pages
        page = 0
        max_pages = 60  # Safety limit (~6000 opportunities)

        while page < max_pages:
            try:
                response = self._make_request(
                    self.API_URL,
                    params={"page": page, "items": 100},
                )
                data = response.json()

                if not data or not isinstance(data, list):
                    break

                total_api_items += len(data)
                page_opportunities = self._parse_opportunities(data)
                opportunities.extend(page_opportunities)

                # Stop if we got less than a full page
                if len(data) < 100:
                    break

                page += 1

            except Exception as e:
                # Log but continue - don't let one page failure stop everything
                import sys
                print(f"Warning: Merkl page {page} failed: {e}", file=sys.stderr)
                break

        # Safety check: if we got API data but 0 opportunities, something is wrong
        # Don't return empty to avoid caching bad data
        if total_api_items > 0 and len(opportunities) == 0:
            raise RuntimeError(
                f"Merkl API returned {total_api_items} items but 0 passed filters - "
                "possible API format change or filter issue"
            )

        return opportunities

    def _parse_opportunities(self, data: List[Dict[str, Any]]) -> List[YieldOpportunity]:
        """Parse opportunity data from API response.

        Args:
            data: API response data (list of opportunities).

        Returns:
            List of opportunities.
        """
        opportunities = []

        for item in data:
            if not isinstance(item, dict):
                continue

            try:
                # Check if this is a stablecoin opportunity
                tokens = item.get("tokens", [])
                token_symbols = [
                    t.get("symbol", "").upper()
                    for t in tokens
                    if isinstance(t, dict)
                ]
                name = (item.get("name", "") or "").upper()

                if not self._is_stablecoin_opportunity(token_symbols, name):
                    continue

                # Extract APR (already in percentage form, e.g., 5.0 = 5%)
                apr = item.get("apr", 0)
                if not apr or apr <= 0:
                    continue

                # APR is already a percentage, use directly
                apr_pct = float(apr)

                # Filter out unrealistic APRs
                if apr_pct > self.MAX_APR_PERCENT:
                    continue

                # Extract TVL
                tvl = item.get("tvl", 0) or 0

                # Filter out low TVL opportunities
                if tvl < self.MIN_TVL_USD:
                    continue

                # Filter out low daily rewards
                daily_rewards = item.get("dailyRewards", 0) or 0
                if daily_rewards < self.MIN_DAILY_REWARDS_USD:
                    continue

                # Extract chain info
                chain_data = item.get("chain", {})
                if isinstance(chain_data, dict):
                    chain = chain_data.get("name", "Unknown")
                else:
                    chain = str(chain_data)

                # Get the main stablecoin symbol
                stablecoin = self._extract_stablecoin(token_symbols, name)

                # Get protocol/action info
                action = item.get("action", "")
                opp_type = item.get("type", action)
                opp_name = item.get("name", "") or ""
                protocol = self._extract_protocol(opp_name, action)

                # Extract opportunity type from name (e.g., "Hold Pendle YT", "Lend", "Supply")
                opportunity_type = self._extract_opportunity_type(opp_name, action)

                # Get reward tokens
                reward_tokens = self._extract_reward_tokens(item)

                # Build direct link to opportunity
                identifier = item.get("identifier", "")
                chain_slug = chain.lower().replace(" ", "-")
                source_url = f"https://app.merkl.xyz/opportunities/{chain_slug}/{opp_type}/{identifier}"

                opp = YieldOpportunity(
                    category=self.category,
                    protocol=protocol,
                    chain=chain,
                    stablecoin=stablecoin,
                    apy=apr_pct,
                    tvl=tvl,
                    reward_token=reward_tokens,
                    opportunity_type=opportunity_type,
                    risk_score=RiskAssessor.calculate_risk_score(
                        strategy_type="reward",
                        protocol=protocol,
                        chain=chain,
                        apy=apr_pct,
                    ),
                    source_url=source_url,
                    additional_info={
                        "action": action,
                        "reward_tokens": reward_tokens,
                        "name": opp_name,
                        "identifier": identifier,
                        "tokens": token_symbols,  # Store all token symbols for display
                    },
                )
                opportunities.append(opp)

            except (KeyError, TypeError, ValueError):
                continue

        return opportunities

    def _is_stablecoin_opportunity(self, token_symbols: List[str], name: str) -> bool:
        """Check if this is a stablecoin opportunity.

        Uses name-based and token-based heuristics to handle protocol-internal
        tokens (debt tokens, LP tokens) that appear alongside real assets.

        Args:
            token_symbols: List of token symbols.
            name: Opportunity name.

        Returns:
            True if stablecoin opportunity.
        """
        name_upper = (name or "").upper()

        # Exclude: non-stablecoin collateral in Morpho market pairs
        # Pattern: "on X/Y Z%" where X is the collateral token
        pair_match = re.search(r'on\s+(\S+)/\S+', name_upper)
        if pair_match:
            collateral = pair_match.group(1)
            if not any(s in collateral for s in self.STABLECOIN_SYMBOLS):
                return False

        # Include: name mentions a stablecoin
        if any(s in name_upper for s in self.STABLECOIN_SYMBOLS):
            return True

        # Include: any token contains a stablecoin substring
        if token_symbols:
            return any(
                any(s in symbol for s in self.STABLECOIN_SYMBOLS)
                for symbol in token_symbols
            )

        return False

    def _is_stablecoin_token(self, symbol: str) -> bool:
        """Check if a token symbol is a stablecoin or stablecoin derivative.

        Args:
            symbol: Token symbol.

        Returns:
            True if stablecoin or derivative (PT, YT, aToken, etc.)
        """
        symbol_upper = symbol.upper()

        # Direct stablecoin match
        for stable in self.STABLECOIN_SYMBOLS:
            if stable in symbol_upper:
                return True

        # Common stablecoin derivative patterns
        # PT-USDC, YT-USDC, aUSDC, cUSDC, sUSDC, etc.
        derivative_prefixes = [
            "PT-", "YT-", "A", "C", "S", "F", "V", "AM", "AV",
            "AETH", "APLA", "AOPT", "AARB",  # Aave tokens
        ]

        for prefix in derivative_prefixes:
            if symbol_upper.startswith(prefix):
                remainder = symbol_upper[len(prefix):]
                for stable in self.STABLECOIN_SYMBOLS:
                    if stable in remainder:
                        return True

        # Vault tokens, LP tokens containing stablecoins
        vault_patterns = ["VAULT", "LP", "POOL", "CUSD", "SUSD"]
        if any(pattern in symbol_upper for pattern in vault_patterns):
            for stable in self.STABLECOIN_SYMBOLS:
                if stable in symbol_upper:
                    return True

        return False

    def _extract_stablecoin(self, token_symbols: List[str], name: str) -> str:
        """Extract the main stablecoin symbol.

        Args:
            token_symbols: List of token symbols.
            name: Opportunity name.

        Returns:
            Stablecoin symbol.
        """
        # Check tokens first
        for symbol in token_symbols:
            for stable in self.STABLECOIN_SYMBOLS:
                if stable in symbol:
                    return symbol

        # Check name
        for stable in self.STABLECOIN_SYMBOLS:
            if stable in name:
                return stable

        return token_symbols[0] if token_symbols else "USD"

    def _extract_protocol(self, name: str, action: str) -> str:
        """Extract protocol name from opportunity.

        Args:
            name: Opportunity name.
            action: Action type.

        Returns:
            Protocol name.
        """
        # Common protocol patterns
        protocols = [
            "Morpho", "Euler", "Aave", "Compound", "Pendle", "Silo",
            "Moonwell", "Velodrome", "Aerodrome", "Uniswap", "Curve",
            "Balancer", "Camelot", "Radiant", "Stargate", "Grove",
            "Spectra", "Napier", "Equilibria", "Yearn", "Convex",
            "Ploutos",
        ]

        name_upper = name.upper()
        for proto in protocols:
            if proto.upper() in name_upper:
                return proto

        # Fall back to action type
        if action:
            action_map = {
                "MORPHOVAULT": "Morpho",
                "AAVE_NET_LENDING": "Aave",
                "CLAMM": "DEX LP",
                "UNISWAP_V4": "Uniswap",
                "TOWNSQUARE_LENDING": "Townsquare",
                "ERC20LOGPROCESSOR": "Staking",
            }
            return action_map.get(action, action.replace("_", " ").title())

        return "Merkl"

    def _extract_opportunity_type(self, name: str, action: str) -> str:
        """Extract opportunity type from name for display and filtering.

        Args:
            name: Opportunity name.
            action: Action type from API.

        Returns:
            Human-readable opportunity type.
        """
        name_lower = name.lower()

        # Check for specific patterns in the name
        if "hold pendle yt" in name_lower or "hold yt" in name_lower:
            return "Hold Pendle YT"
        if "hold spectra yt" in name_lower:
            return "Hold Spectra YT"
        if "hold napier" in name_lower:
            return "Hold Napier YT"
        if "pendle lp" in name_lower or "stake pendle" in name_lower:
            return "Pendle LP"
        if name_lower.startswith("hold "):
            return "Hold"
        if name_lower.startswith("lend "):
            return "Lend"
        if name_lower.startswith("supply "):
            return "Supply"
        if name_lower.startswith("borrow "):
            return "Borrow"
        if name_lower.startswith("provide "):
            return "Provide LP"
        if name_lower.startswith("stake "):
            return "Stake"
        if "vault" in name_lower:
            return "Vault"
        if "pool" in name_lower or "lp" in name_lower:
            return "LP"

        # Fall back to action
        action_map = {
            "HOLD": "Hold",
            "LEND": "Lend",
            "POOL": "LP",
            "DROP": "Airdrop",
            "BORROW": "Borrow",
        }
        return action_map.get(action, action.title() if action else "Other")

    def _extract_reward_tokens(self, item: Dict) -> str:
        """Extract reward token symbols.

        Args:
            item: Opportunity data.

        Returns:
            Comma-separated reward token symbols.
        """
        daily_rewards = item.get("dailyRewards", 0)
        tokens = item.get("tokens", [])

        # Try to find reward token from tokens list
        reward_symbols = []
        for token in tokens:
            if isinstance(token, dict):
                symbol = token.get("symbol", "")
                # Exclude the stablecoin itself as reward
                if symbol and not any(s in symbol.upper() for s in ["USD", "DAI"]):
                    reward_symbols.append(symbol)

        if reward_symbols:
            return ", ".join(reward_symbols[:2])

        return "Various"
