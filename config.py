"""Configuration for scrapers and supported chains."""

# All supported chains (23 total)
SUPPORTED_CHAINS = [
    "Ethereum",
    "Base",
    "Optimism",
    "Plasma",
    "Monad",
    "BSC",
    "World Chain",
    "HyperEVM",
    "Arbitrum",
    "Avalanche",
    "Etherlink",
    "Plume",
    "Katana",
    "Solana",
    "TAC",
    "Unichain",
    "Hemi",
    "Ink",
    "Polygon",
    "Sonic",
    "Berachain",
    "Sei",
]

# Pendle looping chains
PENDLE_LOOP_CHAINS = ["TAC", "Arbitrum", "Ethereum", "Unichain", "Base"]

# Pendle looping protocols (only Morpho has live PT collateral markets)
PENDLE_LOOP_PROTOCOLS = ["Morpho"]

# Target stablecoins for Pendle fixed yields
PENDLE_TARGET_STABLECOINS = [
    # Core stablecoins
    "USDC", "USDT", "DAI", "FRAX", "LUSD", "GHO", "PYUSD",
    # Ethena
    "USDe", "sUSDe", "SUSDE",
    # Sky/Spark
    "USDS", "sUSDS", "sDAI", "SDAI",
    # Coinshift
    "cUSD", "stcUSD",
    # Curve
    "crvUSD", "scrvUSD",
    # Frax
    "frxUSD", "sfrxUSD", "sFRAX",
    # Others
    "USDai", "reUSD", "NUSD", "savUSD", "USD3", "RLP", "rUSD",
    "USD", "iUSD", "eUSD", "USDM", "USDY", "USR", "REUSD",
    "AUSD", "BOLD", "USDA", "DOLA", "MIM", "ALUSD",
    # Midas / Morpho PT underlyings
    "mAPOLLO", "mHYPER", "sNUSD", "srUSDe", "wsrUS",
]

# Leverage levels for loop strategies
# Capped at 5x for safety - higher leverage has extreme liquidation risk
LEVERAGE_LEVELS = [1.0, 2.0, 3.0, 5.0]

# VPN countries in order of preference
VPN_COUNTRIES = ["Switzerland", "Singapore", "Argentina"]

# Scraper configurations
SCRAPER_CONFIGS = {
    "stablewatch": {
        "name": "StableWatch",
        "url": "https://www.stablewatch.io/analytics/metrics",
        "requires_vpn": False,
        "category": "Yield-Bearing Stablecoins",
    },
    "morpho_lend": {
        "name": "Morpho Lend",
        "api_url": "https://blue-api.morpho.org/graphql",
        "requires_vpn": False,
        "category": "Morpho Lend",
    },
    "euler_lend": {
        "name": "Euler Lend",
        "api_url": "https://app.euler.finance/api",
        "requires_vpn": False,
        "category": "Euler Lend",
    },
    "morpho_loop": {
        "name": "Morpho Loop",
        "requires_vpn": False,
        "category": "Morpho Borrow/Lend Loop",
    },
    "euler_loop": {
        "name": "Euler Loop",
        "requires_vpn": False,
        "category": "Euler Borrow/Lend Loop",
    },
    "merkl": {
        "name": "Merkl Rewards",
        "api_url": "https://api.merkl.xyz",
        "requires_vpn": False,
        "category": "Merkl Rewards",
    },
    "pendle_fixed": {
        "name": "Pendle Fixed Yields",
        "api_url": "https://api-v2.pendle.finance/core",
        "requires_vpn": False,
        "category": "Pendle Fixed Yields",
    },
    "pendle_loop": {
        "name": "Pendle Looping",
        "requires_vpn": False,
        "category": "Pendle Looping",
    },
}

# Cache duration in seconds (5 minutes)
CACHE_DURATION = 300

# Request timeout in seconds
REQUEST_TIMEOUT = 30

# Rate limit delay between requests (seconds)
RATE_LIMIT_DELAY = 1.0
