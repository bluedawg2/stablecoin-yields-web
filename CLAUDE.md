# Stablecoin Yield Aggregator

## Quick Reference
- **Run app**: `streamlit run streamlit_app.py`
- **Python**: 3.14 (no venv checked in — user manages their own)
- **No tests** — verify changes by running the app and checking scraper output

## Architecture
- `streamlit_app.py` (2700 lines) — monolith Streamlit UI with dark theme, also contains some inline scraper logic
- `scrapers/` — 30+ scrapers, each inherits `BaseScraper` from `scrapers/base.py`
- `models/opportunity.py` — `YieldOpportunity` dataclass used by all scrapers
- `config.py` — supported chains, scraper configs, leverage levels, stablecoin lists
- `utils/vpn.py` — VPN management for geo-restricted APIs
- `LESSONS.md` — documented bugs and root causes (READ BEFORE fixing scraper issues)

## Scraper Pattern
- All scrapers extend `BaseScraper` and implement `_fetch_data() -> List[YieldOpportunity]`
- BaseScraper provides: rate limiting, caching (.cache/ dir), VPN management, HTTP session
- New scrapers go in `scrapers/` as separate files, then register in `scrapers/__init__.py`

## Critical Rules
- **Morpho API**: Use `borrowApy` (current rate), NOT `avgNetBorrowApy` (historical average)
- **Pendle API**: `limit` param must be ≤100, larger values return empty results
- **Never hardcode yields/APYs** — always fetch from live APIs
- **Stablecoin filtering**: Check BOTH tokens in a pair are stablecoins (see Merkl bug in LESSONS.md)
- Cap unrealistic APYs (e.g., Euler collateral supply APY capped at 25% to prevent phantom results)

## Code Style
- No type annotations beyond what already exists in a file
- Commit messages: imperative, descriptive (e.g., "Fix phantom Euler loop results by capping collateral supply APY at 25%")
- No conventional commit prefixes (no feat:, fix:, etc.)

## Chains
- 25 supported chains listed in `config.py:SUPPORTED_CHAINS`
- Sonic and Berachain were intentionally removed — do not re-add
