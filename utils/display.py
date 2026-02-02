"""Display formatting utilities using rich library."""

from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from models.opportunity import YieldOpportunity


class DisplayFormatter:
    """Formats yield opportunities for terminal display."""

    RISK_COLORS = {
        "Low": "green",
        "Medium": "yellow",
        "High": "red",
        "Very High": "bold red",
    }

    CATEGORY_COLORS = {
        "Yield-Bearing Stablecoins": "cyan",
        "Morpho Lend": "blue",
        "Euler Lend": "blue",
        "Morpho Borrow/Lend Loop": "magenta",
        "Euler Borrow/Lend Loop": "magenta",
        "Merkl Rewards": "green",
        "Pendle Fixed Yields": "yellow",
        "Pendle Looping": "red",
    }

    def __init__(self):
        """Initialize the display formatter."""
        self.console = Console()

    def create_table(
        self,
        opportunities: List[YieldOpportunity],
        title: str = "Stablecoin Yield Opportunities",
        show_leverage: bool = True,
    ) -> Table:
        """Create a rich table from opportunities.

        Args:
            opportunities: List of yield opportunities to display.
            title: Table title.
            show_leverage: Whether to show leverage column.

        Returns:
            Rich Table object.
        """
        table = Table(
            title=title,
            show_header=True,
            header_style="bold",
            border_style="dim",
        )

        # Add columns
        table.add_column("Category", style="dim", width=25)
        table.add_column("Protocol", style="cyan")
        table.add_column("Chain", style="blue")
        table.add_column("Stablecoin", style="green")
        table.add_column("APY", justify="right", style="bold")
        if show_leverage:
            table.add_column("Leverage", justify="center")
        table.add_column("TVL", justify="right")
        table.add_column("Risk", justify="center")

        # Add rows
        for opp in opportunities:
            risk_style = self.RISK_COLORS.get(opp.risk_score, "white")
            risk_text = Text(opp.risk_score, style=risk_style)

            # Color APY based on value
            apy_style = "green" if opp.apy > 10 else "white"
            if opp.apy > 50:
                apy_style = "bold yellow"
            if opp.apy > 100:
                apy_style = "bold red"

            apy_text = Text(opp.formatted_apy, style=apy_style)

            row = [
                opp.category,
                opp.protocol,
                opp.chain,
                opp.stablecoin,
                apy_text,
            ]

            if show_leverage:
                leverage_style = "white"
                if opp.leverage >= 5:
                    leverage_style = "yellow"
                if opp.leverage >= 7:
                    leverage_style = "red"
                row.append(Text(opp.formatted_leverage, style=leverage_style))

            row.extend([
                opp.formatted_tvl,
                risk_text,
            ])

            table.add_row(*row)

        return table

    def display_opportunities(
        self,
        opportunities: List[YieldOpportunity],
        title: str = "Stablecoin Yield Opportunities",
        group_by_category: bool = False,
        sort_by_apy: bool = True,
    ) -> None:
        """Display opportunities in formatted table(s).

        Args:
            opportunities: List of opportunities to display.
            title: Table title.
            group_by_category: If True, create separate tables per category.
            sort_by_apy: If True, sort by APY descending.
        """
        if not opportunities:
            self.console.print("[yellow]No opportunities found.[/yellow]")
            return

        if sort_by_apy:
            opportunities = sorted(opportunities, key=lambda x: x.apy, reverse=True)

        if group_by_category:
            # Group by category
            categories = {}
            for opp in opportunities:
                if opp.category not in categories:
                    categories[opp.category] = []
                categories[opp.category].append(opp)

            for category, opps in categories.items():
                table = self.create_table(opps, title=category)
                self.console.print(table)
                self.console.print()
        else:
            table = self.create_table(opportunities, title=title)
            self.console.print(table)

    def display_summary(self, opportunities: List[YieldOpportunity]) -> None:
        """Display summary statistics.

        Args:
            opportunities: List of opportunities.
        """
        if not opportunities:
            return

        # Count by category
        categories = {}
        for opp in opportunities:
            categories[opp.category] = categories.get(opp.category, 0) + 1

        # Find best opportunities
        best_apy = max(opportunities, key=lambda x: x.apy)
        lowest_risk_high_apy = max(
            [o for o in opportunities if o.risk_score in ("Low", "Medium")],
            key=lambda x: x.apy,
            default=None,
        )

        summary = Text()
        summary.append("\nSummary\n", style="bold")
        summary.append(f"  Total opportunities: {len(opportunities)}\n")
        summary.append(f"  Categories: {len(categories)}\n")

        summary.append(f"\n  Best APY: {best_apy.formatted_apy} ", style="green")
        summary.append(f"({best_apy.protocol} on {best_apy.chain})\n")

        if lowest_risk_high_apy:
            summary.append(
                f"  Best Low/Medium Risk: {lowest_risk_high_apy.formatted_apy} ",
                style="cyan",
            )
            summary.append(
                f"({lowest_risk_high_apy.protocol} on {lowest_risk_high_apy.chain})\n"
            )

        summary.append("\n  By Category:\n")
        for cat, count in sorted(categories.items()):
            summary.append(f"    - {cat}: {count}\n")

        panel = Panel(summary, title="Summary", border_style="dim")
        self.console.print(panel)

    def display_error(self, message: str) -> None:
        """Display an error message.

        Args:
            message: Error message to display.
        """
        self.console.print(f"[bold red]Error:[/bold red] {message}")

    def display_warning(self, message: str) -> None:
        """Display a warning message.

        Args:
            message: Warning message to display.
        """
        self.console.print(f"[yellow]Warning:[/yellow] {message}")

    def display_info(self, message: str) -> None:
        """Display an info message.

        Args:
            message: Info message to display.
        """
        self.console.print(f"[blue]Info:[/blue] {message}")
