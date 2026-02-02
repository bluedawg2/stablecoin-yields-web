"""Scraper for Euler borrow/lend loop strategies.

NOTE: This scraper is currently disabled because Euler loop opportunities
require live borrow rate data which is not easily available via public APIs.
For leveraged stablecoin strategies, use Pendle Looping via Morpho instead.

TAC chain opportunities (e.g., USDT/USN at 260% APY) can be found directly
at app.euler.finance but are not yet available in aggregator APIs.
"""

from typing import List

from .base import BaseScraper
from models.opportunity import YieldOpportunity


class EulerLoopScraper(BaseScraper):
    """Euler loop scraper - currently disabled.

    Euler loop opportunities require live borrow rate data and specific
    market pair information that isn't available via public APIs.

    For leveraged stablecoin yields, use:
    - Pendle Looping (via Morpho) - has live rate data
    - Check app.euler.finance directly for TAC chain opportunities
    """

    requires_vpn = False
    category = "Euler Borrow/Lend Loop"
    cache_file = "euler_loop"

    def _fetch_data(self) -> List[YieldOpportunity]:
        """Return empty list - scraper disabled due to data availability issues."""
        # Euler loop opportunities require:
        # 1. Live borrow rates (not available in DefiLlama pools API)
        # 2. Specific collateral-loan pair mappings
        # 3. LTV/LLTV data for leverage calculations
        #
        # These are available via Euler's subgraph but require complex
        # interest rate calculations. For now, disabled to avoid showing
        # inaccurate hardcoded data.
        return []
