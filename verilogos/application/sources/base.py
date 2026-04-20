# verilogos/application/sources/base.py
"""Abstract base class for market data sources."""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import time
import logging

from verilogos.application.models import MarketTick

logger = logging.getLogger(__name__)


class BaseSource(ABC):
    """
    Abstract market data source.

    Each source must:
      1. Map its native symbol format to our internal format (e.g. "btc-irt" → "BTCIRT")
      2. Implement async fetch_ticks() that returns a list of MarketTick
    """

    def __init__(
        self,
        symbols: List[str],
        symbol_map: Optional[Dict[str, str]] = None,
        poll_interval: float = 5.0,
    ):
        """
        Args:
            symbols: Internal symbol names (e.g. ["BTCIRT", "ETHIRT"])
            symbol_map: Mapping from internal symbol → exchange-native symbol.
                        If None, uses lowercase of internal symbol.
            poll_interval: Seconds between polls (for REST sources).
        """
        self.symbols = symbols
        self.poll_interval = poll_interval

        # internal → exchange-native
        if symbol_map:
            self._to_native = dict(symbol_map)
        else:
            self._to_native = {s: s.lower() for s in symbols}

        # exchange-native → internal (reverse)
        self._to_internal = {v: k for k, v in self._to_native.items()}

        self._running = False
        self._last_prices: Dict[str, float] = {}

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable source name, e.g. 'nobitex'."""
        ...

    @abstractmethod
    async def fetch_ticks(self) -> List[MarketTick]:
        """
        Fetch latest ticks for all symbols.

        Returns:
            List of MarketTick (one per symbol that had data).
        """
        ...

    async def start(self):
        """Called once before polling begins. Override for session setup."""
        self._running = True
        logger.info(f"[{self.name}] source started — symbols: {self.symbols}")

    async def stop(self):
        """Called once after polling ends. Override for cleanup."""
        self._running = False
        logger.info(f"[{self.name}] source stopped")

    def _make_tick(
        self,
        symbol_native: str,
        price: float,
        volume: float = 0.0,
        timestamp: Optional[float] = None,
    ) -> Optional[MarketTick]:
        """Helper: build a MarketTick from exchange-native data."""
        internal = self._to_internal.get(symbol_native)
        if internal is None:
            logger.warning(f"[{self.name}] unknown native symbol: {symbol_native}")
            return None
        return MarketTick(
            symbol=internal,
            price=float(price),
            volume=float(volume),
            timestamp=timestamp or time.time(),
        )
