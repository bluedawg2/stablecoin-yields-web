"""Scrapers for various yield sources."""

from .base import BaseScraper
from .stablewatch import StableWatchScraper
from .morpho_lend import MorphoLendScraper
from .euler_lend import EulerLendScraper
from .morpho_loop import MorphoLoopScraper
from .euler_loop import EulerLoopScraper
from .merkl import MerklScraper
from .pendle_fixed import PendleFixedScraper
from .pendle_loop import PendleLoopScraper

# New scrapers
from .beefy import BeefyScraper
from .yearn import YearnScraper
from .compound import CompoundLendScraper, CompoundLoopScraper
from .aave import AaveLendScraper, AaveLoopScraper
from .midas import MidasScraper
from .spectra import SpectraScraper
from .gearbox import GearboxScraper
from .upshift import UpshiftScraper
from .ipor import IporFusionScraper
from .townsquare import TownSquareScraper
from .curvance import CurvanceScraper
from .accountable import AccountableScraper
from .lagoon import LagoonScraper
from .kamino import KaminoLendScraper, KaminoLoopScraper
from .jupiter import JupiterLendScraper, JupiterBorrowScraper

__all__ = [
    "BaseScraper",
    "StableWatchScraper",
    "MorphoLendScraper",
    "EulerLendScraper",
    "MorphoLoopScraper",
    "EulerLoopScraper",
    "MerklScraper",
    "PendleFixedScraper",
    "PendleLoopScraper",
    # New scrapers
    "BeefyScraper",
    "YearnScraper",
    "CompoundLendScraper",
    "CompoundLoopScraper",
    "AaveLendScraper",
    "AaveLoopScraper",
    "MidasScraper",
    "SpectraScraper",
    "GearboxScraper",
    "UpshiftScraper",
    "IporFusionScraper",
    "TownSquareScraper",
    "CurvanceScraper",
    "AccountableScraper",
    "LagoonScraper",
    "KaminoLendScraper",
    "KaminoLoopScraper",
    "JupiterLendScraper",
    "JupiterBorrowScraper",
]
