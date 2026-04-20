"""Application data models for VeriLogos Layer 4."""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class MarketRegime(Enum):
    """Detected market regime based on topological features."""

    STABLE = "STABLE"
    TRANSITIONING = "TRANSITIONING"
    VOLATILE = "VOLATILE"
    CRISIS = "CRISIS"
    UNKNOWN = "UNKNOWN"


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class MarketTick:
    """Single market tick data."""

    symbol: str
    price: float
    volume: float
    timestamp: float

    @classmethod
    def from_binance_ws(cls, data: dict) -> "MarketTick":
        """Parse Binance WebSocket trade stream."""
        return cls(
            symbol=data.get("s", "UNKNOWN"),
            price=float(data.get("p", 0.0)),
            volume=float(data.get("q", 0.0)),
            timestamp=float(data.get("T", time.time() * 1000)) / 1000.0,
        )

    @classmethod
    def from_dict(cls, data: dict) -> "MarketTick":
        """Generic parser."""
        return cls(
            symbol=data.get("symbol", "UNKNOWN"),
            price=float(data.get("price", 0.0)),
            volume=float(data.get("volume", 0.0)),
            timestamp=float(data.get("timestamp", time.time())),
        )


@dataclass
class TopologicalSnapshot:
    """Snapshot of topological features at a point in time."""

    timestamp: float
    betti_numbers: Dict[int, int]
    euler_characteristic: int
    num_simplices: Dict[int, int]
    max_dimension: int
    correlation_threshold: float
    regime: MarketRegime = MarketRegime.UNKNOWN
    complex: Optional[Any] = None
    persistent_features: List[Dict[str, Any]] = field(default_factory=list)
    persistence_score: float = 0.0
    persistence_diagrams: Optional[Dict[int, List[Tuple[float, float]]]] = None
    total_persistence: Optional[Dict[int, float]] = None
    max_persistence: Optional[Dict[int, float]] = None
    num_persistent_features: Optional[Dict[int, int]] = None
    persistence_entropy: Optional[Dict[int, float]] = None

    def betti_vector(self, max_dim: int = 3) -> np.ndarray:
        """Return Betti numbers as a fixed-length vector."""
        return np.array(
            [self.betti_numbers.get(k, 0) for k in range(max_dim + 1)],
            dtype=np.float64,
        )


@dataclass
class MonitorConfig:
    """Configuration for the topology monitor."""

    symbols: List[str] = field(
        default_factory=lambda: [
            "BTCUSDT",
            "ETHUSDT",
            "BNBUSDT",
            "SOLUSDT",
            "ADAUSDT",
            "XRPUSDT",
            "DOTUSDT",
            "AVAXUSDT",
            "MATICUSDT",
            "LINKUSDT",
        ]
    )
    window_size: int = 60
    min_ticks: int = 20
    correlation_threshold: float = 0.6
    adaptive_threshold: bool = True
    threshold_percentile: float = 75.0
    analysis_interval: float = 5.0
    max_simplex_dim: int = 3
    change_sensitivity: float = 2.0
    history_length: int = 50
    ws_url: str = "wss://stream.binance.com:9443/ws"
    output_dir: str = "topology_monitor_output"
    simulation_mode: bool = False
    simulation_speed: float = 1.0
    # Persistence options (used by TopologyAnalyzer)
    enable_persistence: bool = False
    persistence_thresholds: List[float] = field(
        default_factory=lambda: [0.01, 0.05, 0.1]
    )


@dataclass
class StructuralAlert:
    """Alert generated when structural change is detected."""

    timestamp: float
    severity: AlertSeverity
    message: str
    # Legacy schema (kept for compatibility)
    old_regime: MarketRegime = MarketRegime.UNKNOWN
    new_regime: MarketRegime = MarketRegime.UNKNOWN
    betti_change: Dict[int, int] = field(default_factory=dict)
    euler_change: int = 0
    # Current engines.py schema
    change_score: Optional[float] = None
    current_snapshot: Optional["TopologicalSnapshot"] = None
    previous_snapshot: Optional["TopologicalSnapshot"] = None
    # Persistence schema
    persistent_features: List[Dict[str, Any]] = field(default_factory=list)
    persistence_score: float = 0.0
