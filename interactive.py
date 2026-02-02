"""Interactive TUI for browsing stablecoin yield opportunities."""

import json
import os
from pathlib import Path
from typing import List, Optional, Set
from textual.app import App, ComposeResult
from textual.widgets import DataTable, Header, Footer, Input, Static, Label
from textual.containers import Horizontal, Vertical, Container
from textual.binding import Binding
from rich.text import Text

from models.opportunity import YieldOpportunity


# Default location for hidden items file
HIDDEN_ITEMS_FILE = Path(__file__).parent / ".hidden_items.json"


class HiddenItemsManager:
    """Manages persistence of hidden opportunity items."""

    def __init__(self, filepath: Path = HIDDEN_ITEMS_FILE):
        self.filepath = filepath
        self._hidden_ids: Set[str] = set()
        self._load()

    def _load(self) -> None:
        """Load hidden items from file."""
        if self.filepath.exists():
            try:
                with open(self.filepath, "r") as f:
                    data = json.load(f)
                    self._hidden_ids = set(data.get("hidden_ids", []))
            except (json.JSONDecodeError, IOError):
                self._hidden_ids = set()

    def save(self) -> None:
        """Save hidden items to file."""
        try:
            with open(self.filepath, "w") as f:
                json.dump({"hidden_ids": list(self._hidden_ids)}, f, indent=2)
        except IOError:
            pass

    def is_hidden(self, opportunity: YieldOpportunity) -> bool:
        """Check if an opportunity is hidden."""
        return opportunity.unique_id in self._hidden_ids

    def toggle_hidden(self, opportunity: YieldOpportunity) -> bool:
        """Toggle hidden status for an opportunity. Returns new hidden status."""
        opp_id = opportunity.unique_id
        if opp_id in self._hidden_ids:
            self._hidden_ids.discard(opp_id)
            self.save()
            return False
        else:
            self._hidden_ids.add(opp_id)
            self.save()
            return True

    def unhide_all(self) -> None:
        """Remove all hidden items."""
        self._hidden_ids.clear()
        self.save()

    @property
    def hidden_count(self) -> int:
        """Return count of hidden items."""
        return len(self._hidden_ids)


class HelpBar(Static):
    """Help bar showing keyboard shortcuts and filter instructions."""

    def compose(self) -> ComposeResult:
        yield Static(
            "[b yellow]>>> Press F to filter <<<[/b yellow] | "
            "[b cyan]S[/b cyan]=Sort APY  [b cyan]T[/b cyan]=Sort TVL  [b cyan]K[/b cyan]=Sort Risk | "
            "[b cyan]H[/b cyan]=Hide  [b cyan]X[/b cyan]=Show Hidden | "
            "[b cyan]C[/b cyan]/[b cyan]Esc[/b cyan]=Clear  [b cyan]L[/b cyan]=Link  [b cyan]Q[/b cyan]=Quit",
            id="help-text"
        )


class FilterBar(Container):
    """Filter input bar."""

    def compose(self) -> ComposeResult:
        yield Label(" FILTER> ", id="filter-label")
        yield Input(placeholder="Category (e.g., Merkl)", id="filter-category", classes="filter-input")
        yield Input(placeholder="Protocol (e.g., Aave)", id="filter-protocol", classes="filter-input")
        yield Input(placeholder="Chain (e.g., Ethereum)", id="filter-chain", classes="filter-input")
        yield Input(placeholder="Asset (e.g., USDC, YT)", id="filter-stablecoin", classes="filter-input")
        yield Input(placeholder="Min APY", id="filter-min-apy", classes="filter-input-small")
        yield Input(placeholder="Max Risk", id="filter-max-risk", classes="filter-input-small")


class SummaryBar(Static):
    """Summary statistics bar."""

    def __init__(self, opportunities: List[YieldOpportunity], **kwargs):
        super().__init__(**kwargs)
        self.opportunities = opportunities

    def compose(self) -> ComposeResult:
        total = len(self.opportunities)
        categories = len(set(o.category for o in self.opportunities))

        if self.opportunities:
            best = max(self.opportunities, key=lambda x: x.apy)
            best_text = f"{best.formatted_apy} ({best.protocol})"
        else:
            best_text = "N/A"

        yield Static(
            f"  Total: {total} | Categories: {categories} | Best APY: {best_text}  ",
            id="summary-text"
        )


class YieldTableApp(App):
    """Interactive yield opportunities browser."""

    CSS = """
    Screen {
        background: $surface;
    }

    #help-bar {
        height: 1;
        background: $primary-darken-2;
        color: $text;
        text-align: center;
        dock: top;
    }

    #help-text {
        text-align: center;
    }

    #filter-bar {
        height: 7;
        padding: 1 1;
        background: #222288;
        dock: top;
        border: solid yellow;
        layout: horizontal;
        align: left middle;
    }

    #filter-label {
        width: 10;
        height: 3;
        padding: 1 0;
        color: yellow;
        text-style: bold;
    }

    .filter-input {
        width: 20;
        height: 3;
        margin: 0 1;
        border: solid white;
        background: #000033;
    }

    .filter-input-small {
        width: 12;
        height: 3;
        margin: 0 1;
        border: solid white;
        background: #000033;
    }

    .filter-input:focus, .filter-input-small:focus {
        border: solid cyan;
        background: #000066;
    }

    #summary-text {
        height: 1;
        background: $primary;
        color: $text;
        text-align: center;
        dock: bottom;
    }

    #link-display {
        height: 3;
        background: $surface-darken-1;
        color: $text;
        padding: 0 1;
        dock: bottom;
    }

    DataTable {
        height: 1fr;
    }

    DataTable > .datatable--header {
        background: $primary;
        color: $text;
    }

    DataTable > .datatable--cursor {
        background: $secondary;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("c", "clear_filters", "Clear Filters"),
        Binding("escape", "clear_filters", "Clear"),
        Binding("s", "sort_apy", "Sort APY"),
        Binding("t", "sort_tvl", "Sort TVL"),
        Binding("k", "sort_risk", "Sort Risk"),
        Binding("l", "show_link", "Show Link"),
        Binding("enter", "show_link", "Show Link"),
        Binding("f", "focus_filter", "Filter"),
        Binding("h", "toggle_hide", "Hide/Unhide"),
        Binding("x", "toggle_show_hidden", "Show Hidden"),
        Binding("u", "unhide_all", "Unhide All"),
    ]

    def __init__(self, opportunities: List[YieldOpportunity]):
        super().__init__()
        self.all_opportunities = opportunities
        self.hidden_manager = HiddenItemsManager()
        self.show_hidden = False  # By default, hide checked items
        self.filtered_opportunities = self._filter_hidden(opportunities)
        self.sort_column = "apy"
        self.sort_reverse = True
        self.selected_opp: Optional[YieldOpportunity] = None

    def _filter_hidden(self, opportunities: List[YieldOpportunity]) -> List[YieldOpportunity]:
        """Filter out hidden opportunities if show_hidden is False."""
        if self.show_hidden:
            return opportunities.copy()
        return [o for o in opportunities if not self.hidden_manager.is_hidden(o)]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield HelpBar(id="help-bar")
        yield FilterBar(id="filter-bar")
        yield DataTable(id="yield-table")
        yield Static("", id="link-display")
        yield SummaryBar(self.all_opportunities, id="summary-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Set up the table when app mounts."""
        table = self.query_one("#yield-table", DataTable)

        # Add columns - Hide column first
        table.add_column("Hide", key="hide", width=6)
        table.add_column("Category", key="category", width=28)
        table.add_column("Protocol", key="protocol", width=18)
        table.add_column("Chain", key="chain", width=14)
        table.add_column("Asset(s)", key="stablecoin", width=32)
        table.add_column("APY", key="apy", width=10)
        table.add_column("Leverage", key="leverage", width=10)
        table.add_column("TVL", key="tvl", width=12)
        table.add_column("Risk", key="risk", width=10)

        table.cursor_type = "row"
        table.zebra_stripes = True

        self._populate_table()

    def _format_stablecoin_display(self, opp: YieldOpportunity) -> str:
        """Format the stablecoin/asset column based on opportunity type.

        - Merkl YT rewards: Show "YT-TOKEN" format
        - Borrow/Lend loops: Show "COLLATERAL -> BORROW" format with maturity date for PTs
        - Multi-token pools: Show "TOKEN1/TOKEN2" format
        """
        additional = opp.additional_info or {}

        # Borrow/Lend loop: show collateral -> borrow (works for Morpho, Euler, Pendle loops)
        if "borrow_asset" in additional and "collateral" in additional:
            collateral = additional["collateral"]
            borrow = additional["borrow_asset"]

            # Add maturity date to PT tokens (e.g., PT-USDe -> PT-USDe-05Feb2026)
            if collateral.startswith("PT-") and opp.maturity_date:
                date_str = opp.maturity_date.strftime("%d%b%Y").lstrip("0")  # "5Feb2026"
                collateral = f"{collateral}-{date_str}"

            return f"{collateral}->{borrow}"

        # Merkl YT rewards: show YT prefix if it's a YT opportunity
        if opp.category == "Merkl Rewards":
            opp_type = opp.opportunity_type or ""
            name = additional.get("name", "") or ""

            # Check if it's a YT (Yield Token) opportunity
            if "YT" in opp_type.upper() or "HOLD YT" in name.upper() or "HOLD PENDLE YT" in name.upper():
                # Add YT prefix if not already there
                if not opp.stablecoin.upper().startswith("YT"):
                    return f"YT-{opp.stablecoin}"

            # Check for multi-token pools (LP with two tokens)
            tokens = additional.get("tokens", [])
            if len(tokens) >= 2:
                return "/".join(tokens[:2])

            # Check name for pool patterns like "TOKEN1-TOKEN2" or "TOKEN1/TOKEN2"
            if "/" in name or "-" in name:
                # Try to extract token pair from name
                import re
                pool_match = re.search(r'([A-Z0-9]+)[/-]([A-Z0-9]+)', name.upper())
                if pool_match:
                    t1, t2 = pool_match.groups()
                    # Only show if both are different from just the stablecoin
                    if t1 != t2:
                        return f"{t1}/{t2}"

        return opp.stablecoin

    def _populate_table(self, preserve_cursor: bool = False) -> None:
        """Populate table with filtered and sorted data.

        Args:
            preserve_cursor: If True, try to restore cursor to same row after repopulating.
        """
        table = self.query_one("#yield-table", DataTable)

        # Save cursor position if requested
        saved_cursor_row = table.cursor_row if preserve_cursor else 0

        table.clear()

        # Sort opportunities
        opportunities = self._sort_opportunities(self.filtered_opportunities)

        for opp in opportunities:
            # Checkbox display for hidden status
            is_hidden = self.hidden_manager.is_hidden(opp)
            checkbox = Text("[X]" if is_hidden else "[ ]", style="bold cyan" if is_hidden else "dim")

            # Color-code risk
            risk_style = {
                "Low": "green",
                "Medium": "yellow",
                "High": "red",
                "Very High": "bold red",
            }.get(opp.risk_score, "white")

            # Color-code APY
            apy_style = "green" if opp.apy > 10 else "white"
            if opp.apy > 50:
                apy_style = "yellow"
            if opp.apy > 100:
                apy_style = "red"

            # Format stablecoin display
            stablecoin_display = self._format_stablecoin_display(opp)

            table.add_row(
                checkbox,
                opp.category,
                opp.protocol,
                opp.chain,
                stablecoin_display,
                Text(opp.formatted_apy, style=apy_style),
                opp.formatted_leverage,
                opp.formatted_tvl,
                Text(opp.risk_score, style=risk_style),
            )

        # Restore cursor position if requested and valid
        if preserve_cursor and len(opportunities) > 0:
            # Clamp to valid range
            new_cursor = min(saved_cursor_row, len(opportunities) - 1)
            table.move_cursor(row=new_cursor)

        # Update summary
        self._update_summary()

    def _sort_opportunities(self, opportunities: List[YieldOpportunity]) -> List[YieldOpportunity]:
        """Sort opportunities by current sort column."""
        risk_order = {"Low": 0, "Medium": 1, "High": 2, "Very High": 3}

        sort_keys = {
            "apy": lambda o: o.apy,
            "tvl": lambda o: o.tvl if o.tvl else 0,
            "risk": lambda o: risk_order.get(o.risk_score, 2),
            "chain": lambda o: o.chain.lower(),
            "protocol": lambda o: o.protocol.lower(),
        }

        key_func = sort_keys.get(self.sort_column, sort_keys["apy"])
        return sorted(opportunities, key=key_func, reverse=self.sort_reverse)

    def _update_summary(self) -> None:
        """Update summary bar with filtered data."""
        total = len(self.filtered_opportunities)
        categories = len(set(o.category for o in self.filtered_opportunities))
        hidden_count = sum(1 for o in self.all_opportunities if self.hidden_manager.is_hidden(o))

        if self.filtered_opportunities:
            best = max(self.filtered_opportunities, key=lambda x: x.apy)
            best_text = f"{best.formatted_apy} ({best.protocol} on {best.chain})"
        else:
            best_text = "N/A"

        hidden_status = "[cyan]Showing hidden[/cyan]" if self.show_hidden else f"[dim]{hidden_count} hidden[/dim]"

        summary = self.query_one("#summary-text", Static)
        summary.update(
            f"  Showing: {total}/{len(self.all_opportunities)} | "
            f"Categories: {categories} | {hidden_status} | Best APY: {best_text}  "
        )

    def _apply_filters(self, preserve_cursor: bool = False) -> None:
        """Apply all filters to opportunities.

        Args:
            preserve_cursor: If True, try to restore cursor to same row after filtering.
        """
        # Start with hidden items filter
        filtered = self._filter_hidden(self.all_opportunities)

        # Get filter values
        category = self.query_one("#filter-category", Input).value.strip().lower()
        protocol = self.query_one("#filter-protocol", Input).value.strip().lower()
        chain = self.query_one("#filter-chain", Input).value.strip().lower()
        stablecoin = self.query_one("#filter-stablecoin", Input).value.strip().upper()
        min_apy_str = self.query_one("#filter-min-apy", Input).value.strip()
        max_risk = self.query_one("#filter-max-risk", Input).value.strip().lower()

        # Apply filters
        if category:
            filtered = [o for o in filtered if category in o.category.lower()]

        if protocol:
            filtered = [o for o in filtered if protocol in o.protocol.lower()]

        if chain:
            filtered = [o for o in filtered if chain in o.chain.lower()]

        if stablecoin:
            # Search both original stablecoin and formatted display (for YT, pools, etc.)
            filtered = [
                o for o in filtered
                if stablecoin in o.stablecoin.upper()
                or stablecoin in self._format_stablecoin_display(o).upper()
            ]

        if min_apy_str:
            try:
                min_apy = float(min_apy_str)
                filtered = [o for o in filtered if o.apy >= min_apy]
            except ValueError:
                pass

        if max_risk:
            risk_levels = ["low", "medium", "high", "very high"]
            if max_risk in risk_levels:
                max_idx = risk_levels.index(max_risk)
                filtered = [
                    o for o in filtered
                    if risk_levels.index(o.risk_score.lower()) <= max_idx
                ]

        self.filtered_opportunities = filtered
        self._populate_table(preserve_cursor=preserve_cursor)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle filter input changes."""
        self._apply_filters()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection to show link."""
        if event.row_key is not None:
            row_idx = event.cursor_row
            sorted_opps = self._sort_opportunities(self.filtered_opportunities)
            if 0 <= row_idx < len(sorted_opps):
                self.selected_opp = sorted_opps[row_idx]
                self._show_selected_link()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handle row highlight to track selection."""
        if event.row_key is not None:
            row_idx = event.cursor_row
            sorted_opps = self._sort_opportunities(self.filtered_opportunities)
            if 0 <= row_idx < len(sorted_opps):
                self.selected_opp = sorted_opps[row_idx]

    def _show_selected_link(self) -> None:
        """Show the link and strategy details for the selected opportunity."""
        if self.selected_opp:
            link_display = self.query_one("#link-display", Static)
            opp = self.selected_opp
            additional = opp.additional_info or {}

            # Build detail string for loop strategies
            details = []

            # Check if this is a looping strategy
            if "borrow_asset" in additional and "collateral" in additional:
                collateral = additional.get("collateral", opp.stablecoin)
                collateral_yield = additional.get("collateral_yield") or additional.get("pt_fixed_yield")
                borrow_asset = additional.get("borrow_asset")
                borrow_rate = additional.get("borrow_rate")
                lltv = additional.get("lltv")
                liquidity = additional.get("liquidity")
                is_estimated = additional.get("estimated_rate", False)

                # Add maturity date to PT tokens in detail display
                if collateral.startswith("PT-") and opp.maturity_date:
                    date_str = opp.maturity_date.strftime("%d%b%Y").lstrip("0")
                    collateral = f"{collateral}-{date_str}"

                details.append(f"[b cyan]Loop:[/b cyan] {collateral}")
                if collateral_yield:
                    details.append(f"({collateral_yield:.2f}% yield)")
                details.append(f"[dim]->[/dim] borrow {borrow_asset}")
                if borrow_rate:
                    rate_label = "[dim](est)[/dim]" if is_estimated else "[green](live)[/green]"
                    details.append(f"({borrow_rate:.2f}% {rate_label})")
                if lltv:
                    details.append(f"| LLTV: {lltv:.1f}%")
                if liquidity and liquidity >= 1000:
                    liq_str = f"${liquidity/1_000_000:.2f}M" if liquidity >= 1_000_000 else f"${liquidity/1_000:.1f}K"
                    details.append(f"| Liq: {liq_str}")

                # Show the math
                if collateral_yield and borrow_rate:
                    lev = opp.leverage
                    calc_apy = collateral_yield * lev - borrow_rate * (lev - 1)
                    details.append(f"| Math: {collateral_yield:.2f}%×{lev:.1f}x - {borrow_rate:.2f}%×{lev-1:.1f}x = {calc_apy:.2f}%")

            detail_str = " ".join(details) if details else ""
            link_display.update(
                f"{detail_str}\n[b]Link:[/b] {opp.source_url}"
            )

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

    def action_clear_filters(self) -> None:
        """Clear all filters."""
        self.query_one("#filter-category", Input).value = ""
        self.query_one("#filter-protocol", Input).value = ""
        self.query_one("#filter-chain", Input).value = ""
        self.query_one("#filter-stablecoin", Input).value = ""
        self.query_one("#filter-min-apy", Input).value = ""
        self.query_one("#filter-max-risk", Input).value = ""
        self._apply_filters()
        self.notify("Filters cleared")

    def action_sort_apy(self) -> None:
        """Sort by APY."""
        if self.sort_column == "apy":
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = "apy"
            self.sort_reverse = True
        self._populate_table(preserve_cursor=True)
        self.notify(f"Sorted by APY {'(high to low)' if self.sort_reverse else '(low to high)'}")

    def action_sort_tvl(self) -> None:
        """Sort by TVL."""
        if self.sort_column == "tvl":
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = "tvl"
            self.sort_reverse = True
        self._populate_table(preserve_cursor=True)
        self.notify(f"Sorted by TVL {'(high to low)' if self.sort_reverse else '(low to high)'}")

    def action_sort_risk(self) -> None:
        """Sort by Risk."""
        if self.sort_column == "risk":
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = "risk"
            self.sort_reverse = False  # Low risk first by default
        self._populate_table(preserve_cursor=True)
        self.notify(f"Sorted by Risk {'(high to low)' if self.sort_reverse else '(low to high)'}")

    def action_show_link(self) -> None:
        """Show link for selected row."""
        self._show_selected_link()
        if self.selected_opp:
            self.notify(f"Link: {self.selected_opp.source_url}")

    def action_focus_filter(self) -> None:
        """Focus the first filter input box."""
        self.query_one("#filter-category", Input).focus()
        self.notify("Type to filter, TAB to next box, ESC to clear")

    def action_toggle_hide(self) -> None:
        """Toggle hide status for selected row."""
        if self.selected_opp:
            is_now_hidden = self.hidden_manager.toggle_hidden(self.selected_opp)
            status = "hidden" if is_now_hidden else "visible"
            self.notify(f"{self.selected_opp.protocol} on {self.selected_opp.chain}: {status}")

            # If we just hid an item and show_hidden is False, re-apply filters
            if is_now_hidden and not self.show_hidden:
                self._apply_filters(preserve_cursor=True)
            else:
                self._populate_table(preserve_cursor=True)
        else:
            self.notify("No row selected")

    def action_toggle_show_hidden(self) -> None:
        """Toggle showing/hiding hidden items."""
        self.show_hidden = not self.show_hidden
        if self.show_hidden:
            self.notify("Now showing hidden items (marked with [X])")
        else:
            hidden_count = sum(1 for o in self.all_opportunities if self.hidden_manager.is_hidden(o))
            self.notify(f"Hidden items filtered out ({hidden_count} hidden)")
        self._apply_filters(preserve_cursor=True)

    def action_unhide_all(self) -> None:
        """Unhide all hidden items."""
        self.hidden_manager.unhide_all()
        self.notify("All items unhidden")
        self._apply_filters(preserve_cursor=True)


def run_interactive(opportunities: List[YieldOpportunity]) -> None:
    """Run the interactive TUI app.

    Args:
        opportunities: List of yield opportunities to display.
    """
    app = YieldTableApp(opportunities)
    app.run()
