# verilogos/application/sources/manager.py
"""SourceManager — aggregates multiple exchange sources."""

from typing import List, Callable, Awaitable, Optional, Dict, Set
import asyncio
import logging
import time

from verilogos.application.models import MarketTick
from verilogos.application.sources.base import BaseSource

logger = logging.getLogger(__name__)


class SourceManager:
    """
    Manages multiple BaseSource instances, polls them in parallel,
    deduplicates ticks, and forwards to a callback.
    """

    def __init__(
        self,
        sources: List[BaseSource],
        callback: Optional[Callable[[MarketTick], Awaitable[None]]] = None,
        dedup_window: float = 1.0,
    ):
        self._sources = sources
        self._callback = callback
        self._dedup_window = dedup_window
        self._running = False
        self._poll_task: Optional[asyncio.Task] = None
        # dedup: symbol → (price, timestamp)
        self._seen: Dict[str, tuple] = {}

    @property
    def sources(self) -> List[BaseSource]:
        return list(self._sources)

    async def start(self):
        """Start all sources and begin polling."""
        for src in self._sources:
            await src.start()
        self._running = True
        if self._callback:
            self._poll_task = asyncio.create_task(self._poll_loop())
        logger.info(
            f"[SourceManager] started with {len(self._sources)} source(s)"
        )

    async def stop(self):
        """Stop polling and shut down all sources."""
        self._running = False
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        for src in self._sources:
            await src.stop()
        logger.info("[SourceManager] stopped")

    async def fetch_all(self) -> List[MarketTick]:
        """Fetch ticks from all sources (one-shot, no callback)."""
        all_ticks: List[MarketTick] = []
        results = await asyncio.gather(
            *(src.fetch_ticks() for src in self._sources),
            return_exceptions=True,
        )
        for src, result in zip(self._sources, results):
            if isinstance(result, Exception):
                logger.error(f"[SourceManager] {src.name} error: {result}")
                continue
            all_ticks.extend(result)
        return self._deduplicate(all_ticks)

    def _deduplicate(self, ticks: List[MarketTick]) -> List[MarketTick]:
        """Remove duplicate ticks within the dedup window."""
        now = time.time()
        unique: List[MarketTick] = []

        # Clean old entries
        expired = [
            k for k, (_, ts) in self._seen.items()
            if now - ts > self._dedup_window
        ]
        for k in expired:
            del self._seen[k]

        for tick in ticks:
            key = tick.symbol
            prev = self._seen.get(key)
            if prev and prev[0] == tick.price and (now - prev[1]) < self._dedup_window:
                continue  # duplicate
            self._seen[key] = (tick.price, now)
            unique.append(tick)

        return unique

    async def _poll_loop(self):
        """Background loop: poll all sources and fire callback."""
        while self._running:
            try:
                ticks = await self.fetch_all()
                if self._callback:
                    for tick in ticks:
                        await self._callback(tick)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[SourceManager] poll error: {e}", exc_info=True)

            # Use the shortest poll interval among sources
            interval = min(
                (s.poll_interval for s in self._sources),
                default=5.0,
            )
            await asyncio.sleep(interval)
