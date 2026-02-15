#!/usr/bin/env python3
"""Stablecoin Investment Summarizer CLI Tool.

A CLI tool that scrapes stablecoin yield opportunities from multiple sources
and presents results in a formatted terminal table.
"""

import sys
from typing import List, Optional

import click
from rich.console import Console

from models.opportunity import YieldOpportunity
from scrapers import (
    StableWatchScraper,
    MorphoLendScraper,
    EulerLendScraper,
    MorphoLoopScraper,
    EulerLoopScraper,
    MerklScraper,
    PendleFixedScraper,
    PendleLoopScraper,
    # New scrapers
    BeefyScraper,
    YearnScraper,
    CompoundLendScraper,
    CompoundLoopScraper,
    AaveLendScraper,
    AaveLoopScraper,
    MidasScraper,
    SpectraScraper,
    GearboxScraper,
    UpshiftScraper,
    IporFusionScraper,
    TownSquareScraper,
    CurvanceScraper,
    AccountableScraper,
    LagoonScraper,
    KaminoLendScraper,
    KaminoLoopScraper,
    JupiterLendScraper,
    JupiterBorrowScraper,
    NestCreditScraper,
    StakeDaoScraper,
    ConvexScraper,
    HyperionScraper,
    YoScraper,
    YieldFiScraper,
    PloutosScraper,
    MysticLendScraper,
    MysticLoopScraper,
)
from utils.display import DisplayFormatter
from config import SUPPORTED_CHAINS

console = Console()

# Category name mappings
CATEGORY_ALIASES = {
    "stablewatch": "Yield-Bearing Stablecoins",
    "yield-bearing": "Yield-Bearing Stablecoins",
    "morpho-lend": "Morpho Lend",
    "morpho": "Morpho Lend",
    "euler-lend": "Euler Lend",
    "euler": "Euler Lend",
    "morpho-loop": "Morpho Borrow/Lend Loop",
    "euler-loop": "Euler Borrow/Lend Loop",
    "merkl": "Merkl Rewards",
    "pendle-fixed": "Pendle Fixed Yields",
    "pendle": "Pendle Fixed Yields",
    "pendle-loop": "Pendle Looping",
    # New sources
    "beefy": "Beefy Vaults",
    "yearn": "Yearn Vaults",
    "compound-lend": "Compound Lend",
    "compound": "Compound Lend",
    "compound-loop": "Compound Borrow/Lend Loop",
    "aave-lend": "Aave Lend",
    "aave": "Aave Lend",
    "aave-loop": "Aave Borrow/Lend Loop",
    "midas": "Midas Yield-Bearing",
    "spectra": "Spectra Fixed Yields",
    "gearbox": "Gearbox Lend",
    "upshift": "Upshift Vaults",
    "ipor": "IPOR Fusion",
    "ipor-fusion": "IPOR Fusion",
    "townsquare": "TownSquare Lend",
    "townsq": "TownSquare Lend",
    "curvance": "Curvance Lend",
    "accountable": "Accountable Yield",
    "lagoon": "Lagoon Vaults",
    "kamino-lend": "Kamino Lend",
    "kamino": "Kamino Lend",
    "kamino-loop": "Kamino Borrow/Lend Loop",
    "jupiter-lend": "Jupiter Lend",
    "jupiter": "Jupiter Lend",
    "jupiter-borrow": "Jupiter Borrow",
    "nest": "Nest Credit Vaults",
    "nest-credit": "Nest Credit Vaults",
    "plume-vaults": "Nest Credit Vaults",
    "stakedao": "Stake DAO Vaults",
    "stake-dao": "Stake DAO Vaults",
    "convex": "Convex Finance",
    "hyperion": "Hyperion LP",
    "aptos": "Hyperion LP",
    "yo": "Yo Yield",
    "yo-xyz": "Yo Yield",
    "yieldfi": "Yield.fi",
    "yield-fi": "Yield.fi",
    "ploutos": "Ploutos Money",
    "mystic": "Mystic Lend",
    "mystic-lend": "Mystic Lend",
    "mystic-loop": "Mystic Borrow/Lend Loop",
}

# Scraper instances for each category
SCRAPERS = {
    "Yield-Bearing Stablecoins": StableWatchScraper,
    "Morpho Lend": MorphoLendScraper,
    "Euler Lend": EulerLendScraper,
    "Morpho Borrow/Lend Loop": MorphoLoopScraper,
    "Euler Borrow/Lend Loop": EulerLoopScraper,
    "Merkl Rewards": MerklScraper,
    "Pendle Fixed Yields": PendleFixedScraper,
    "Pendle Looping": PendleLoopScraper,
    # New sources
    "Beefy Vaults": BeefyScraper,
    "Yearn Vaults": YearnScraper,
    "Compound Lend": CompoundLendScraper,
    "Compound Borrow/Lend Loop": CompoundLoopScraper,
    "Aave Lend": AaveLendScraper,
    "Aave Borrow/Lend Loop": AaveLoopScraper,
    "Midas Yield-Bearing": MidasScraper,
    "Spectra Fixed Yields": SpectraScraper,
    "Gearbox Lend": GearboxScraper,
    "Upshift Vaults": UpshiftScraper,
    "IPOR Fusion": IporFusionScraper,
    "TownSquare Lend": TownSquareScraper,
    "Curvance Lend": CurvanceScraper,
    "Accountable Yield": AccountableScraper,
    "Lagoon Vaults": LagoonScraper,
    "Kamino Lend": KaminoLendScraper,
    "Kamino Borrow/Lend Loop": KaminoLoopScraper,
    "Jupiter Lend": JupiterLendScraper,
    "Jupiter Borrow": JupiterBorrowScraper,
    "Nest Credit Vaults": NestCreditScraper,
    "Stake DAO Vaults": StakeDaoScraper,
    "Convex Finance": ConvexScraper,
    "Hyperion LP": HyperionScraper,
    "Yo Yield": YoScraper,
    "Yield.fi": YieldFiScraper,
    "Ploutos Money": PloutosScraper,
    "Mystic Lend": MysticLendScraper,
    "Mystic Borrow/Lend Loop": MysticLoopScraper,
}


def normalize_category(category: str) -> Optional[str]:
    """Normalize category name to canonical form.

    Args:
        category: User-provided category name.

    Returns:
        Canonical category name or None if not found.
    """
    category_lower = category.lower().strip()

    # Check aliases
    if category_lower in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[category_lower]

    # Check exact match (case-insensitive)
    for canonical in SCRAPERS.keys():
        if canonical.lower() == category_lower:
            return canonical

    return None


def fetch_opportunities(
    categories: Optional[List[str]] = None,
    use_cache: bool = True,
) -> List[YieldOpportunity]:
    """Fetch yield opportunities from specified categories.

    Args:
        categories: List of categories to fetch. If None, fetch all.
        use_cache: Whether to use cached data.

    Returns:
        List of yield opportunities.
    """
    opportunities = []
    formatter = DisplayFormatter()

    # Determine which scrapers to use
    if categories:
        scraper_classes = {}
        for cat in categories:
            normalized = normalize_category(cat)
            if normalized and normalized in SCRAPERS:
                scraper_classes[normalized] = SCRAPERS[normalized]
            else:
                formatter.display_warning(f"Unknown category: {cat}")
    else:
        scraper_classes = SCRAPERS

    if not scraper_classes:
        formatter.display_error("No valid categories specified")
        return []

    # Fetch from each scraper
    for category_name, scraper_class in scraper_classes.items():
        try:
            console.print(f"[dim]Fetching {category_name}...[/dim]")
            scraper = scraper_class()
            category_opportunities = scraper.fetch(use_cache=use_cache)
            opportunities.extend(category_opportunities)
            console.print(f"[green]  Found {len(category_opportunities)} opportunities[/green]")
        except Exception as e:
            formatter.display_warning(f"Failed to fetch {category_name}: {e}")

    return opportunities


def filter_opportunities(
    opportunities: List[YieldOpportunity],
    min_apy: Optional[float] = None,
    max_risk: Optional[str] = None,
    chain: Optional[str] = None,
    stablecoin: Optional[str] = None,
    protocol: Optional[str] = None,
    max_leverage: Optional[float] = None,
    min_tvl: Optional[float] = None,
) -> List[YieldOpportunity]:
    """Filter opportunities based on criteria.

    Args:
        opportunities: List of opportunities to filter.
        min_apy: Minimum APY threshold.
        max_risk: Maximum risk level (Low, Medium, High, Very High).
        chain: Filter by blockchain.
        stablecoin: Filter by stablecoin symbol.
        protocol: Filter by protocol name.
        max_leverage: Maximum leverage level.
        min_tvl: Minimum TVL threshold.

    Returns:
        Filtered list of opportunities.
    """
    filtered = opportunities

    if min_apy is not None:
        filtered = [o for o in filtered if o.apy >= min_apy]

    if max_risk:
        risk_levels = ["Low", "Medium", "High", "Very High"]
        max_risk_normalized = max_risk.title()
        if max_risk_normalized in risk_levels:
            max_idx = risk_levels.index(max_risk_normalized)
            filtered = [
                o for o in filtered
                if risk_levels.index(o.risk_score) <= max_idx
            ]

    if chain:
        chain_lower = chain.lower()
        filtered = [o for o in filtered if o.chain.lower() == chain_lower]

    if stablecoin:
        stablecoin_upper = stablecoin.upper()
        filtered = [
            o for o in filtered
            if stablecoin_upper in o.stablecoin.upper()
        ]

    if protocol:
        protocol_lower = protocol.lower()
        filtered = [
            o for o in filtered
            if protocol_lower in o.protocol.lower()
        ]

    if max_leverage is not None:
        filtered = [o for o in filtered if o.leverage <= max_leverage]

    if min_tvl is not None:
        filtered = [o for o in filtered if o.tvl and o.tvl >= min_tvl]

    return filtered


def sort_opportunities(
    opportunities: List[YieldOpportunity],
    sort_by: str = "apy",
    ascending: bool = False,
) -> List[YieldOpportunity]:
    """Sort opportunities by specified field.

    Args:
        opportunities: List of opportunities to sort.
        sort_by: Field to sort by (apy, tvl, risk, chain, protocol).
        ascending: If True, sort ascending; otherwise descending.

    Returns:
        Sorted list of opportunities.
    """
    risk_order = {"Low": 0, "Medium": 1, "High": 2, "Very High": 3}

    sort_keys = {
        "apy": lambda o: o.apy,
        "tvl": lambda o: o.tvl if o.tvl else 0,
        "risk": lambda o: risk_order.get(o.risk_score, 2),
        "chain": lambda o: o.chain.lower(),
        "protocol": lambda o: o.protocol.lower(),
        "stablecoin": lambda o: o.stablecoin.lower(),
        "leverage": lambda o: o.leverage,
    }

    key_func = sort_keys.get(sort_by.lower(), sort_keys["apy"])
    return sorted(opportunities, key=key_func, reverse=not ascending)


@click.command()
@click.option(
    "--category", "-c",
    multiple=True,
    help="Filter by category (can specify multiple). Options: stablewatch, morpho-lend, euler-lend, morpho-loop, euler-loop, merkl, pendle-fixed, pendle-loop, beefy, yearn, compound, compound-loop, aave, aave-loop, midas, spectra, gearbox, upshift, ipor, townsquare, curvance, accountable, lagoon, kamino, kamino-loop, jupiter, jupiter-borrow, nest-credit",
)
@click.option(
    "--min-apy",
    type=float,
    help="Filter by minimum APY percentage",
)
@click.option(
    "--max-risk",
    type=click.Choice(["Low", "Medium", "High", "Very High"], case_sensitive=False),
    help="Filter by maximum risk level",
)
@click.option(
    "--chain",
    help="Filter by blockchain (e.g., Ethereum, Arbitrum, Base)",
)
@click.option(
    "--stablecoin", "-s",
    help="Filter by stablecoin symbol (e.g., USDC, USDT, DAI)",
)
@click.option(
    "--protocol", "-p",
    help="Filter by protocol name (e.g., Morpho, Euler, Pendle)",
)
@click.option(
    "--max-leverage",
    type=float,
    help="Filter by maximum leverage level",
)
@click.option(
    "--min-tvl",
    type=float,
    help="Filter by minimum TVL in USD (e.g., 1000000 for $1M)",
)
@click.option(
    "--sort-by",
    type=click.Choice(["apy", "tvl", "risk", "chain", "protocol", "leverage"], case_sensitive=False),
    default="apy",
    help="Sort results by field (default: apy)",
)
@click.option(
    "--ascending", "--asc",
    is_flag=True,
    help="Sort in ascending order (default is descending)",
)
@click.option(
    "--refresh", "-r",
    is_flag=True,
    help="Force refresh cached data",
)
@click.option(
    "--group-by-category", "-g",
    is_flag=True,
    help="Group results by category instead of sorting",
)
@click.option(
    "--top", "-t",
    type=int,
    help="Show only top N opportunities",
)
@click.option(
    "--no-summary",
    is_flag=True,
    help="Hide the summary section",
)
@click.option(
    "--list-categories",
    is_flag=True,
    help="List available categories and exit",
)
@click.option(
    "--list-chains",
    is_flag=True,
    help="List supported chains and exit",
)
@click.option(
    "--interactive/--no-interactive", "-i",
    default=True,
    help="Launch interactive grid view (default: enabled)",
)
def main(
    category: tuple,
    min_apy: Optional[float],
    max_risk: Optional[str],
    chain: Optional[str],
    stablecoin: Optional[str],
    protocol: Optional[str],
    max_leverage: Optional[float],
    min_tvl: Optional[float],
    sort_by: str,
    ascending: bool,
    refresh: bool,
    group_by_category: bool,
    top: Optional[int],
    no_summary: bool,
    list_categories: bool,
    list_chains: bool,
    interactive: bool,
):
    """Stablecoin Investment Summarizer - Find the best stablecoin yields across DeFi.

    Scrapes yield opportunities from multiple sources including Morpho, Euler,
    Pendle, Merkl, and more. Displays results in an interactive grid with
    filtering and sorting.

    Examples:

        # Launch interactive grid (default)
        python main.py

        # Static table output (no interactive mode)
        python main.py --no-interactive

        # Sort by TVL descending
        python main.py --no-interactive --sort-by tvl

        # Filter by category and protocol
        python main.py --category morpho-lend --protocol Morpho

        # Show only low/medium risk, no leverage
        python main.py --no-interactive --max-risk medium --max-leverage 1

        # Force refresh data
        python main.py --refresh
    """
    formatter = DisplayFormatter()

    # Handle info commands
    if list_categories:
        console.print("\n[bold]Available Categories:[/bold]\n")
        for cat in SCRAPERS.keys():
            aliases = [k for k, v in CATEGORY_ALIASES.items() if v == cat]
            console.print(f"  • {cat}")
            if aliases:
                console.print(f"    [dim]Aliases: {', '.join(aliases)}[/dim]")
        console.print()
        return

    if list_chains:
        console.print("\n[bold]Supported Chains:[/bold]\n")
        for chain_name in SUPPORTED_CHAINS:
            console.print(f"  • {chain_name}")
        console.print()
        return

    # Fetch opportunities
    console.print("\n[bold]Stablecoin Investment Summarizer[/bold]\n")

    categories_list = list(category) if category else None
    use_cache = not refresh

    opportunities = fetch_opportunities(
        categories=categories_list,
        use_cache=use_cache,
    )

    if not opportunities:
        formatter.display_error("No opportunities found")
        sys.exit(1)

    # Apply filters
    opportunities = filter_opportunities(
        opportunities,
        min_apy=min_apy,
        max_risk=max_risk,
        chain=chain,
        stablecoin=stablecoin,
        protocol=protocol,
        max_leverage=max_leverage,
        min_tvl=min_tvl,
    )

    if not opportunities:
        formatter.display_warning("No opportunities match the specified filters")
        sys.exit(0)

    # Launch interactive mode or static display
    if interactive:
        console.print(f"\n[green]Loaded {len(opportunities)} opportunities. Launching interactive view...[/green]\n")
        try:
            from interactive import run_interactive
            run_interactive(opportunities)
        except ImportError as e:
            console.print(f"[yellow]Interactive mode requires textual. Install with: pip install textual[/yellow]")
            console.print(f"[dim]Falling back to static display...[/dim]\n")
            interactive = False

    if not interactive:
        # Sort results
        if not group_by_category:
            opportunities = sort_opportunities(opportunities, sort_by=sort_by, ascending=ascending)

        # Limit results if requested
        if top:
            opportunities = opportunities[:top]

        # Display results
        console.print()
        formatter.display_opportunities(
            opportunities,
            group_by_category=group_by_category,
            sort_by_apy=False,  # Already sorted above
        )

        # Display summary
        if not no_summary:
            formatter.display_summary(opportunities)

        console.print()


if __name__ == "__main__":
    main()
