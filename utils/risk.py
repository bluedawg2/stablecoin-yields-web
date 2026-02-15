"""Risk assessment utilities for yield opportunities."""

from datetime import datetime
from typing import Optional


class RiskAssessor:
    """Calculates risk scores for yield opportunities."""

    # Protocol maturity scores (lower = more mature = less risky)
    PROTOCOL_MATURITY = {
        "aave": 1,
        "morpho": 2,
        "euler": 2,
        "pendle": 2,
        "compound": 1,
        "silo": 3,
        "merkl": 2,
        # New protocols
        "beefy": 2,
        "yearn": 1,
        "midas": 3,
        "spectra": 3,
        "gearbox": 2,
        "upshift": 3,
        "ipor": 3,
        "townsquare": 3,
        "curvance": 3,
        "accountable": 3,
        "stakedao": 2,
        "convex": 2,
        "hyperion": 3,
        "yo": 3,
        "yieldfi": 3,
        "ploutos": 3,
        "kamino": 2,
        "jupiter": 2,
        "lagoon": 3,
        "nest credit": 3,
    }

    # Chain risk scores (lower = more established = less risky)
    CHAIN_RISK = {
        "ethereum": 1,
        "arbitrum": 1,
        "base": 1,
        "optimism": 1,
        "polygon": 1,
        "avalanche": 2,
        "bsc": 2,
        "solana": 2,
        "sei": 3,
        "monad": 4,
        "plasma": 4,
        "hyperevm": 4,
        "etherlink": 4,
        "plume": 4,
        "katana": 4,
        "tac": 4,
        "unichain": 3,
        "hemi": 4,
        "ink": 4,
        "world chain": 3,
        "linea": 3,
        "mantle": 3,
        "sonieum": 4,
        "rootstock": 3,
        "aptos": 4,
    }

    # Strategy type base risk
    STRATEGY_RISK = {
        "simple_lend": 1,
        "lend": 1,
        "loop": 3,
        "pendle_fixed": 2,
        "pendle_loop": 4,
        "reward": 2,
        "yield_bearing": 2,
        "vault": 2,
        "fixed": 2,
    }

    @classmethod
    def calculate_risk_score(
        cls,
        strategy_type: str,
        leverage: float = 1.0,
        protocol: str = "",
        chain: str = "",
        maturity_date: Optional[datetime] = None,
        apy: float = 0.0,
    ) -> str:
        """Calculate risk score for an opportunity.

        Args:
            strategy_type: Type of strategy (simple_lend, loop, pendle_fixed, etc.)
            leverage: Leverage level (1.0 = no leverage)
            protocol: Protocol name
            chain: Blockchain name
            maturity_date: For Pendle positions, the maturity date
            apy: Annual percentage yield

        Returns:
            Risk score as "Low", "Medium", "High", or "Very High"
        """
        score = 0

        # Base strategy risk
        score += cls.STRATEGY_RISK.get(strategy_type.lower(), 2) * 10

        # Leverage risk (exponential)
        if leverage > 1:
            score += (leverage - 1) * 15
            if leverage >= 5:
                score += 20
            if leverage >= 7:
                score += 20
            if leverage >= 10:
                score += 30

        # Protocol maturity
        protocol_lower = protocol.lower()
        for proto, maturity in cls.PROTOCOL_MATURITY.items():
            if proto in protocol_lower:
                score += maturity * 5
                break
        else:
            score += 15  # Unknown protocol

        # Chain risk
        chain_lower = chain.lower()
        chain_risk = cls.CHAIN_RISK.get(chain_lower, 4)
        score += chain_risk * 5

        # Maturity date risk (for Pendle)
        if maturity_date:
            # Handle timezone-aware vs naive datetimes
            now = datetime.now()
            if maturity_date.tzinfo is not None:
                # Make now timezone-aware (UTC)
                from datetime import timezone
                now = datetime.now(timezone.utc)
            days_to_maturity = (maturity_date - now).days
            if days_to_maturity < 7:
                score += 30  # Very close to maturity
            elif days_to_maturity < 30:
                score += 15
            elif days_to_maturity < 90:
                score += 5

        # Suspiciously high APY
        if apy > 100:
            score += 20
        elif apy > 50:
            score += 10
        elif apy > 30:
            score += 5

        # Convert score to category
        if score < 25:
            return "Low"
        elif score < 50:
            return "Medium"
        elif score < 75:
            return "High"
        else:
            return "Very High"

    @classmethod
    def get_leverage_risk_warning(cls, leverage: float) -> Optional[str]:
        """Get warning message for high leverage.

        Args:
            leverage: Leverage level

        Returns:
            Warning message or None if no warning needed.
        """
        if leverage >= 10:
            return "EXTREME liquidation risk - small price moves can wipe position"
        elif leverage >= 7:
            return "Very high liquidation risk - requires active monitoring"
        elif leverage >= 5:
            return "High liquidation risk - monitor closely"
        elif leverage >= 3:
            return "Moderate liquidation risk"
        elif leverage > 1:
            return "Some liquidation risk"
        return None
