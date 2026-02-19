# Stablecoin Yield Aggregator

A Streamlit web app that aggregates live stablecoin yield opportunities across 35+ DeFi protocols and 25 blockchains, sorted by APY.

## What It Does

- Fetches live APY data from protocol APIs (no hardcoded values)
- Covers simple lending, leveraged borrow/lend loops, Pendle fixed yields, and LP rewards
- Filters and sorts results by APY, TVL, chain, leverage, risk, and stablecoin
- Caches results for 5 minutes to avoid hammering APIs on every page load

## Yield Categories

### Simple Lending
Deposit a stablecoin and earn the supply APY.

| Category | Protocols |
|---|---|
| Yield-Bearing Stablecoins | sUSDe, sDAI, etc. via StableWatch |
| Morpho Lend | Morpho Blue markets |
| Euler Lend | Euler v2 vaults |
| Aave Lend | Aave v3 |
| Compound Lend | Compound v3 |
| Kamino Lend | Solana |
| Jupiter Lend | Solana |
| Mystic Lend | Mystic protocol |
| Beefy Finance | Auto-compounding vaults |
| Yearn Finance | Yearn v3 vaults |
| Midas Finance | Institutional yield |
| Spectra Finance | Fixed/variable split |
| Gearbox Protocol | Passive lending pools |
| IPOR Fusion | Interest rate optimization |
| TownSquare | Credit markets |
| Curvance | Cross-chain lending |
| Upshift | Curated yield vaults |
| Accountable | Real-world asset yields |
| Lagoon Finance | Structured yield |
| Stake DAO Vaults | Curve/Convex strategies |
| Convex Finance | Curve LP rewards |
| Hyperion LP | Liquidity provision |
| Yo Yield | Yield optimization |
| Yield.fi | Aggregated yields |
| Ploutos Money | Fixed income |
| Nest Credit Vaults | Credit vaults |

### Leveraged Borrow/Lend Loops
Supply asset A as collateral, borrow asset B, re-supply asset B — repeat to amplify yield.

**Formula:** `Net APY = supply_apy × leverage − borrow_apy × (leverage − 1)`

Each vault pair appears at **multiple leverage levels** (2x, 3x, 5x) as separate rows, so you can pick your risk tolerance. Use the **Max Leverage** filter to hide higher-leverage rows.

| Category | Protocols |
|---|---|
| Morpho Borrow/Lend Loop | Morpho Blue |
| Euler Borrow/Lend Loop | Euler v2 |
| Compound Borrow/Lend Loop | Compound v3 |
| Kamino Borrow/Lend Loop | Solana |
| Jupiter Borrow | Solana |
| Mystic Borrow/Lend Loop | Mystic |

### Fixed Yields (Pendle)
Lock in a fixed APY until a maturity date by holding Pendle PT tokens.

- **Pendle Fixed Yields** — PT token fixed rates across all Pendle markets
- **Pendle Looping** — PT collateral loops via Morpho (leveraged fixed yield)

### External Rewards
- **Merkl Rewards** — Token incentive campaigns on liquidity positions

## UI Features

**Sidebar Filters:**
- Category, Chain, Stablecoin, Protocol (text search)
- Min APY, Max Leverage, Min TVL
- Exclude Yield Tokens (YT) — hides speculative Pendle YT rows
- Exclude expiring PT (≤14 days) — hides Pendle PTs near maturity

**Table:**
- Click any row to see details: supply/borrow breakdown, TVL, link to protocol
- Hide rows you're not interested in (persists across sessions via `.hidden_items.json`)
- Sort by APY, TVL, Chain, or Protocol

**Summary Metrics:** Results count, Avg APY, Max APY, Total TVL, Protocols, Chains

## Architecture

```
streamlit_app.py       Main UI (also contains StableWatch and Pendle inline scrapers)
scrapers/              35+ scraper classes, one per protocol
  base.py              BaseScraper: caching, rate limiting, HTTP session
  euler_loop.py        Example: cross-collateral loop discovery
  pendle_fixed.py      Pendle fixed yield fetcher
  ...
models/opportunity.py  YieldOpportunity dataclass
config.py              Chains, leverage levels, stablecoin lists
utils/
  risk.py              Risk score calculator
  vpn.py               VPN management for geo-restricted APIs
.cache/                API response cache (5-minute TTL)
```

## Supported Chains

25 chains including Ethereum, Base, Arbitrum, Optimism, Polygon, Avalanche, Solana, Mantle, Linea, Unichain, and more. See `config.py` for the full list.

## Risk Scores

Each opportunity is scored Low / Medium / High / Very High based on protocol maturity, leverage level, chain, and APY. Use the **Max Risk** filter (if enabled) to limit results.

Leverage adds significant liquidation risk. At 5x leverage, a ~20% collateral price drop can trigger liquidation.
