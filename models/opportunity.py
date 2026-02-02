"""Data models for yield opportunities."""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class YieldOpportunity:
    """Represents a yield opportunity from any source."""

    category: str
    protocol: str
    chain: str
    stablecoin: str
    apy: float
    tvl: Optional[float] = None
    risk_score: str = "Medium"
    leverage: float = 1.0
    source_url: str = ""
    maturity_date: Optional[datetime] = None
    borrow_apy: Optional[float] = None
    supply_apy: Optional[float] = None
    reward_token: Optional[str] = None
    opportunity_type: str = ""  # e.g., "Hold Pendle YT", "Lend", "Supply", "LP"
    additional_info: dict = field(default_factory=dict)

    @property
    def unique_id(self) -> str:
        """Return a unique identifier for this opportunity.

        Used for tracking hidden items across sessions.
        """
        import hashlib
        # Create a unique key from identifying fields
        key_parts = [
            self.category,
            self.protocol,
            self.chain,
            self.stablecoin,
            self.source_url,
        ]
        key_str = "|".join(str(p) for p in key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()[:12]

    @property
    def formatted_apy(self) -> str:
        """Return APY as formatted percentage string."""
        if self.apy >= 100:
            return f"{self.apy:,.1f}%"
        return f"{self.apy:.2f}%"

    @property
    def formatted_tvl(self) -> str:
        """Return TVL as formatted string with units."""
        if self.tvl is None:
            return "N/A"
        if self.tvl >= 1_000_000_000:
            return f"${self.tvl / 1_000_000_000:.2f}B"
        if self.tvl >= 1_000_000:
            return f"${self.tvl / 1_000_000:.2f}M"
        if self.tvl >= 1_000:
            return f"${self.tvl / 1_000:.2f}K"
        return f"${self.tvl:.2f}"

    @property
    def formatted_leverage(self) -> str:
        """Return leverage as formatted string."""
        if self.leverage == 1.0:
            return "1x"
        return f"{self.leverage:.1f}x"

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "category": self.category,
            "protocol": self.protocol,
            "chain": self.chain,
            "stablecoin": self.stablecoin,
            "apy": self.apy,
            "tvl": self.tvl,
            "risk_score": self.risk_score,
            "leverage": self.leverage,
            "source_url": self.source_url,
            "maturity_date": self.maturity_date.isoformat() if self.maturity_date else None,
            "borrow_apy": self.borrow_apy,
            "supply_apy": self.supply_apy,
            "reward_token": self.reward_token,
            "opportunity_type": self.opportunity_type,
            "additional_info": self.additional_info,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "YieldOpportunity":
        """Create instance from dictionary."""
        maturity = data.get("maturity_date")
        if maturity and isinstance(maturity, str):
            maturity = datetime.fromisoformat(maturity)

        return cls(
            category=data["category"],
            protocol=data["protocol"],
            chain=data["chain"],
            stablecoin=data["stablecoin"],
            apy=data["apy"],
            tvl=data.get("tvl"),
            risk_score=data.get("risk_score", "Medium"),
            leverage=data.get("leverage", 1.0),
            source_url=data.get("source_url", ""),
            maturity_date=maturity,
            borrow_apy=data.get("borrow_apy"),
            supply_apy=data.get("supply_apy"),
            reward_token=data.get("reward_token"),
            opportunity_type=data.get("opportunity_type", ""),
            additional_info=data.get("additional_info", {}),
        )
