"""VPN management utilities using NordVPN CLI."""

import subprocess
import time
from typing import List, Optional


class VPNManager:
    """Manages NordVPN connections for geo-restricted sites."""

    def __init__(self, countries: Optional[List[str]] = None):
        """Initialize VPN manager with preferred countries.

        Args:
            countries: List of countries to try, in order of preference.
                      Defaults to Switzerland, Singapore, Argentina.
        """
        self.countries = countries or ["Switzerland", "Singapore", "Argentina"]
        self._connected_country: Optional[str] = None

    def is_connected(self) -> bool:
        """Check if VPN is currently connected.

        Returns:
            True if connected to VPN, False otherwise.
        """
        try:
            result = subprocess.run(
                ["nordvpn", "status"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return "Connected" in result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return False

    def get_current_country(self) -> Optional[str]:
        """Get the currently connected VPN country.

        Returns:
            Country name if connected, None otherwise.
        """
        try:
            result = subprocess.run(
                ["nordvpn", "status"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            for line in result.stdout.split("\n"):
                if "Country:" in line:
                    return line.split(":")[-1].strip()
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return None

    def connect(self, country: str) -> bool:
        """Connect to VPN in specified country.

        Args:
            country: Country name to connect to.

        Returns:
            True if connection successful, False otherwise.
        """
        try:
            # Disconnect first if already connected to a different country
            if self.is_connected():
                current = self.get_current_country()
                if current and current.lower() == country.lower():
                    self._connected_country = country
                    return True
                self.disconnect()

            result = subprocess.run(
                ["nordvpn", "connect", country],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Wait for connection to establish
            time.sleep(2)

            if self.is_connected():
                self._connected_country = country
                return True

            return False

        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return False

    def disconnect(self) -> bool:
        """Disconnect from VPN.

        Returns:
            True if disconnect successful, False otherwise.
        """
        try:
            subprocess.run(
                ["nordvpn", "disconnect"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self._connected_country = None
            time.sleep(1)
            return not self.is_connected()
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return False

    def ensure_vpn(self, preferred_countries: Optional[List[str]] = None) -> bool:
        """Ensure VPN is connected, trying fallback countries if needed.

        Args:
            preferred_countries: Countries to try, in order.
                               Defaults to instance countries.

        Returns:
            True if connected to any country, False if all failed.
        """
        countries = preferred_countries or self.countries

        # Already connected?
        if self.is_connected():
            return True

        # Try each country in order
        for country in countries:
            if self.connect(country):
                return True

        return False

    @property
    def connected_country(self) -> Optional[str]:
        """Get the country we're connected to (cached)."""
        return self._connected_country


# Global VPN manager instance
_vpn_manager: Optional[VPNManager] = None


def get_vpn_manager() -> VPNManager:
    """Get or create the global VPN manager instance."""
    global _vpn_manager
    if _vpn_manager is None:
        _vpn_manager = VPNManager()
    return _vpn_manager
