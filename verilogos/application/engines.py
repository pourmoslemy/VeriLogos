"""Core application engines for VeriLogos Layer 4."""

import logging
from collections import deque
from itertools import combinations
from typing import Deque, Dict, List, Optional, Set, Tuple, Callable
logger = logging.getLogger(__name__)
import numpy as np
try:
    import torch
except ImportError:
    torch = None

from verilogos.core.topology.complexes.complex import SimplicialComplex
from verilogos.application.models import (
    AlertSeverity,
    MarketRegime,
    MarketTick,
    MonitorConfig,
    TopologicalSnapshot,
    StructuralAlert,
)
from verilogos.core.reasoning.persistence.persistence_engine import (
    PersistenceEngine,
    PersistenceInterval,
)

logger = logging.getLogger("TopologyMonitor")

# Persistent Homology imports (optional — graceful fallback)
try:
    from verilogos.core.topology.complexes.temporal_filtration import Filtration
    from verilogos.core.topology.persistence.persistent_homology import PersistentHomology
    from verilogos.core.topology.persistence.barcode import Barcode
    from verilogos.core.topology.complexes.subcomplex import Subcomplex
    HAS_PERSISTENCE = True
except ImportError:
    HAS_PERSISTENCE = False

class CorrelationEngine:
    """
    Maintains rolling price windows and computes real-time
    correlation matrices between assets.
    """

    def __init__(self, config: MonitorConfig) -> None:
        self.config = config
        self.symbol_index: Dict[str, int] = {
            s: i for i, s in enumerate(config.symbols)
        }
        self.n = len(config.symbols)
        # Rolling price windows per symbol
        self.price_windows: Dict[str, Deque[float]] = {
            s: deque(maxlen=config.window_size) for s in config.symbols
        }
        # Rolling return windows per symbol
        self.return_windows: Dict[str, Deque[float]] = {
            s: deque(maxlen=config.window_size - 1) for s in config.symbols
        }

    def update(self, tick: MarketTick) -> None:
        """Add a new tick to the rolling window."""
        if tick.symbol not in self.symbol_index:
            return

        window = self.price_windows[tick.symbol]
        if len(window) > 0:
            prev_price = window[-1]
            if prev_price > 0:
                ret = (tick.price - prev_price) / prev_price
                self.return_windows[tick.symbol].append(ret)

        window.append(tick.price)

    def is_ready(self) -> bool:
        """Check if we have enough data to compute correlations."""
        min_len = self.config.min_ticks
        return all(
            len(self.return_windows[s]) >= min_len
            for s in self.config.symbols
        )

    def compute_correlation_matrix(self) -> np.ndarray:
        """Compute the correlation matrix from rolling return windows."""
        n = self.n
        if n == 1:
            return np.ones((1, 1))

        min_len = min(len(self.return_windows[s]) for s in self.config.symbols)

        if min_len < 2:
            return np.eye(n)

        # Build return matrix: (min_len × n)
        returns = np.zeros((min_len, n))
        for symbol, idx in self.symbol_index.items():
            rets = list(self.return_windows[symbol])
            returns[:, idx] = rets[-min_len:]

        # Compute Pearson correlation with numerical safety
        # Suppress RuntimeWarning when std=0 (constant prices → division by zero in np.corrcoef)
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            corr = np.corrcoef(returns, rowvar=False)

        # Handle NaN (constant price → zero correlation)
        corr = np.nan_to_num(corr, nan=0.0, posinf=1.0, neginf=-1.0)
        np.fill_diagonal(corr, 1.0)

        return corr

    def get_adaptive_threshold(self, corr_matrix: np.ndarray) -> float:
        """Compute adaptive correlation threshold based on distribution."""
        if not self.config.adaptive_threshold:
            return self.config.correlation_threshold

        # Extract upper triangle (excluding diagonal)
        upper = corr_matrix[np.triu_indices(self.n, k=1)]
        abs_corr = np.abs(upper)

        if len(abs_corr) == 0:
            return self.config.correlation_threshold

        threshold = np.percentile(abs_corr, self.config.threshold_percentile)
        # Clamp to reasonable range
        return float(np.clip(threshold, 0.2, 0.95))

class VietorisRipsBuilder:
    """
    Builds a Vietoris-Rips simplicial complex from a correlation/distance
    matrix using SANN's SimplicialComplex class.

    The complex is built by:
      1. Each asset = vertex (0-simplex)
      2. Two assets with \|correlation\| >= threshold → edge (1-simplex)
      3. k+1 assets all pairwise connected → k-simplex (up to max_dim)
    """

    def __init__(self, max_dim: int = 3) -> None:
        self.max_dim = max_dim

    def build_from_correlation(
        self,
        corr_matrix: np.ndarray,
        threshold: float,
        labels: Optional[List[str]] = None,
    ) -> SimplicialComplex:
        """
        Build Vietoris-Rips complex from a correlation matrix.

        Args:
            corr_matrix: N×N correlation matrix (values in [-1, 1])
            threshold: minimum \|correlation\| to create an edge
            labels: optional asset labels

        Returns:
            SimplicialComplex with all simplices up to max_dim
        """
        n = corr_matrix.shape[0]
        sc = SimplicialComplex()

        # Step 1: Add all vertices
        for i in range(n):
            sc.add_simplex((i,))

        # Step 2: Find edges (pairs with |corr| >= threshold)
        adjacency: Dict[int, Set[int]] = {i: set() for i in range(n)}
        for i in range(n):
            for j in range(i + 1, n):
                if abs(corr_matrix[i, j]) >= threshold:
                    sc.add_simplex((i, j))
                    adjacency[i].add(j)
                    adjacency[j].add(i)

        # Step 3: Add higher-dimensional simplices (clique detection)
        # A k-simplex exists iff all (k+1 choose 2) pairs are edges
        if self.max_dim >= 2:
            self._add_clique_simplices(sc, adjacency, n)

        return sc

    def _add_clique_simplices(
        self,
        sc: SimplicialComplex,
        adjacency: Dict[int, Set[int]],
        n: int,
    ) -> None:
        """Add higher-dimensional simplices by enumerating all cliques up to max_dim+1."""
        from itertools import combinations

        prev_cliques: List[Tuple[int, ...]] = [(i,) for i in range(n) if adjacency.get(i)]

        for dim in range(2, self.max_dim + 1):
            next_cliques: List[Tuple[int, ...]] = []
            seen: set = set()
            for clique in prev_cliques:
                common_neighbors = set(adjacency[clique[0]])
                for v in clique[1:]:
                    common_neighbors &= adjacency[v]
                for w in common_neighbors:
                    if w > clique[-1]:
                        new_clique = clique + (w,)
                        if new_clique not in seen:
                            seen.add(new_clique)
                            sc.add_simplex(new_clique)
                            next_cliques.append(new_clique)
            if not next_cliques:
                break
            prev_cliques = next_cliques

    def _bron_kerbosch(
        self,
        R: Set[int],
        P: Set[int],
        X: Set[int],
        adjacency: Dict[int, Set[int]],
        cliques: List[Tuple[int, ...]],
        min_size: int = 3,
        max_size: int = 4,
    ) -> None:
        """Bron-Kerbosch algorithm with pivoting for maximal clique enumeration."""
        if not P and not X:
            if len(R) >= min_size:
                cliques.append(tuple(sorted(R)))
            return

        if len(R) >= max_size:
            cliques.append(tuple(sorted(R)))
            return

        # Choose pivot
        pivot_candidates = P | X
        if not pivot_candidates:
            return
        pivot = max(pivot_candidates, key=lambda v: len(adjacency[v] & P))

        for v in list(P - adjacency[pivot]):
            neighbors = adjacency[v]
            self._bron_kerbosch(
                R=R | {v},
                P=P & neighbors,
                X=X & neighbors,
                adjacency=adjacency,
                cliques=cliques,
                min_size=min_size,
                max_size=max_size,
            )
            P = P - {v}
            X = X | {v}

    def build_from_distance(
        self,
        distance_matrix: np.ndarray,
        epsilon: float,
    ) -> SimplicialComplex:
        """
        Build Vietoris-Rips from a distance matrix with radius epsilon.
        Edge exists if distance < epsilon.
        """
        # Convert distance to "similarity" for threshold logic
        max_dist = distance_matrix.max()
        if max_dist == 0:
            similarity = np.ones_like(distance_matrix)
        else:
            similarity = 1.0 - (distance_matrix / max_dist)

        threshold = 1.0 - (epsilon / max_dist) if max_dist > 0 else 0.5
        return self.build_from_correlation(similarity, threshold)

class TopologyAnalyzer:
    """
    Core engine that builds simplicial complexes from market data
    and extracts topological features using SANN's SimplicialComplex.
    """

    def __init__(self, config: MonitorConfig) -> None:
        self.config = config
        self.rips_builder = VietorisRipsBuilder(max_dim=config.max_simplex_dim)

    def analyze(
        self,
        corr_matrix: np.ndarray,
        threshold: float,
        timestamp: float,
    ) -> TopologicalSnapshot:
        """
        Build a simplicial complex and extract topological features.

        Uses SANN's SimplicialComplex API:
          - add_simplex(vertices)     → build complex
          - compute_betti_numbers()   → Dict[int, int]
          - euler_characteristic()    → int
          - max_dim()                 → int
          - vertices, edges, triangles → List[Simplex]
        """
        # Build Vietoris-Rips complex
        sc = self.rips_builder.build_from_correlation(
            corr_matrix, threshold, self.config.symbols
        )

        # Extract topological invariants
        betti = sc.compute_betti_numbers()
        euler = sc.euler_characteristic()
        max_d = sc.max_dim

        # Count simplices per dimension
        num_simplices = {}
        for dim in range(max_d + 1):
            num_simplices[dim] = len(sc.get_simplices(dim))

        # Persistent Homology (only if enabled and available)
        persistence_data = {}
        if self.config.enable_persistence and HAS_PERSISTENCE:
            filtration = self._build_filtration(corr_matrix)
            if filtration is not None:
                persistence_data = self._compute_persistence_stats(filtration, max_d)

        return TopologicalSnapshot(
            timestamp=timestamp,
            betti_numbers=betti,
            euler_characteristic=euler,
            num_simplices=num_simplices,
            max_dimension=max_d,
            correlation_threshold=threshold,
            complex=sc,
            **persistence_data,
        )

    def _build_filtration(self, corr_matrix: np.ndarray) -> "Optional[Filtration]":
        """Build temporal filtration from multiple thresholds."""
        if not HAS_PERSISTENCE:
            return None
        try:
            thresholds = sorted(self.config.persistence_thresholds, reverse=True)
            complexes = []
            for thresh in thresholds:
                sc = self.rips_builder.build_from_correlation(
                    corr_matrix, thresh, self.config.symbols
                )
                complexes.append(sc)

            ambient = complexes[-1]
            steps = []
            for sc in complexes:
                all_simplices = set()
                for dim in range(sc.max_dim + 1):
                    for simplex in sc.get_simplices(dim):
                        verts = tuple(sorted(simplex.vertices)) if hasattr(simplex, 'vertices') else tuple(sorted(simplex))
                        all_simplices.add(verts)
                sub = Subcomplex(simplices=all_simplices, ambient=ambient)
                steps.append(sub)

            filtration = Filtration(ambient_complex=ambient, steps=steps)
            return filtration
        except Exception as e:
            logger.warning(f"Filtration build failed: {e}")
            return None

    def _compute_persistence_stats(self, filtration: "Filtration", max_dim: int) -> dict:
        """Compute persistence diagrams and derived statistics."""
        import math
        try:
            ph = PersistentHomology(filtration)
            diagrams = {}
            total_pers = {}
            max_pers = {}
            num_features = {}
            entropy = {}

            for dim in range(max_dim + 1):
                pairs = ph.compute(dim=dim)
                diagrams[dim] = pairs
                bc = Barcode(pairs)
                finite = bc.finite()
                total_pers[dim] = bc.total_persistence()
                max_pers[dim] = bc.max_persistence()
                num_features[dim] = len(finite)

                if finite:
                    lifetimes = [d - b for b, d in finite if d - b > 0]
                    total_lt = sum(lifetimes)
                    if total_lt > 0:
                        probs = [lt / total_lt for lt in lifetimes]
                        entropy[dim] = -sum(p * math.log(p + 1e-12) for p in probs)
                    else:
                        entropy[dim] = 0.0
                else:
                    entropy[dim] = 0.0

            return {
                "persistence_diagrams": diagrams,
                "total_persistence": total_pers,
                "max_persistence": max_pers,
                "num_persistent_features": num_features,
                "persistence_entropy": entropy,
            }
        except Exception as e:
            logger.warning(f"Persistence computation failed: {e}")
            return {}


class StructuralChangeDetector:
    """
    Detects structural changes in market topology by monitoring
    Betti numbers and Euler characteristic over time.

    Uses CUSUM algorithm on topological feature vectors with
    dimension-aware regime classification.
    """

    # ── Betti dimension weights ──
    # β₀ (components): fragmentation signal
    # β₁ (cycles): instability signal
    # β₂ (voids): complexity signal
    # Euler: phase-change signal
    _DIM_WEIGHTS = np.array([1.0, 1.5, 1.2, 1.3], dtype=np.float64)

    def __init__(self, config: MonitorConfig) -> None:
        self.config = config
        self.history: Deque[TopologicalSnapshot] = deque(
            maxlen=config.history_length
        )
        self.alerts: List[StructuralAlert] = []

        # Baseline statistics
        self._baseline_betti: Optional[np.ndarray] = None
        self._baseline_euler: Optional[float] = None
        self._betti_std: Optional[np.ndarray] = None
        self._euler_std: Optional[float] = None

        # CUSUM state — 4D: [β₀, β₁, β₂, Euler]
        self._cusum_pos: np.ndarray = np.zeros(4)
        self._cusum_neg: np.ndarray = np.zeros(4)

        # Trend tracking — last N betti vectors for slope estimation
        self._trend_window = min(10, config.history_length // 3)
        self._recent_betti: Deque[np.ndarray] = deque(maxlen=self._trend_window)

        # Cooldown: avoid alert spam
        self._last_alert_time: float = 0.0
        self._alert_cooldown: float = max(config.analysis_interval * 3, 15.0)
        # Persistence tracking
        self._previous_diagram: List[PersistenceInterval] = []
        self._persistence_threshold: float = 0.05
        self._min_lifetime: float = 0.01

    # ──────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────

    def update(
        self,
        snapshot: TopologicalSnapshot,
        persistence_diagram: Optional[List[PersistenceInterval]] = None,
    ) -> Optional[StructuralAlert]:
        """
        Process a new topological snapshot and check for structural changes.
        Returns an alert if a structural change is detected.
        """
        self.history.append(snapshot)
        self._recent_betti.append(snapshot.betti_vector())

        # Need enough history to establish baseline
        warmup = max(10, self.config.min_ticks // 2)
        if len(self.history) < warmup:
            snapshot.regime = MarketRegime.UNKNOWN
            return None

        # Update baseline statistics
        self._update_baseline()

        # Classify current regime (multi-signal)
        snapshot.regime = self._classify_regime(snapshot)

        # Detect change via CUSUM
        alert = self._cusum_detect(snapshot, persistence_diagram)

        if alert:
            self.alerts.append(alert)

        return alert

    # ──────────────────────────────────────────────────────
    # Baseline
    # ──────────────────────────────────────────────────────

    def _update_baseline(self) -> None:
        """Recalculate baseline statistics from recent history only."""
        if len(self.history) < 5:
            return

        # Use only the most recent 80% of history for baseline
        # so that old data doesn't dilute sensitivity
        n = len(self.history)
        start = max(0, n - int(self.config.history_length * 0.8))
        recent = list(self.history)[start:]

        betti_vectors = np.array([s.betti_vector() for s in recent])
        euler_values = np.array([s.euler_characteristic for s in recent])

        self._baseline_betti = np.mean(betti_vectors, axis=0)
        self._betti_std = np.std(betti_vectors, axis=0) + 1e-6
        self._baseline_euler = np.mean(euler_values)
        self._euler_std = np.std(euler_values) + 1e-6

    def _find_last_known_regime(self) -> MarketRegime:
        """
        Walk backwards through history to find the most recent
        snapshot whose regime is NOT UNKNOWN.
        Falls back to UNKNOWN if none found.
        """
        # history[-1] is current snapshot, start from -2
        for i in range(len(self.history) - 2, -1, -1):
            if self.history[i].regime != MarketRegime.UNKNOWN:
                return self.history[i].regime
        return MarketRegime.UNKNOWN

    # ──────────────────────────────────────────────────────
    # Regime Classification (improved)
    # ──────────────────────────────────────────────────────

    def _classify_regime(self, snapshot: TopologicalSnapshot) -> MarketRegime:
        """
        Multi-signal regime classification using:
          1. Per-dimension z-scores (weighted)
          2. Euler characteristic deviation
          3. Betti trend (slope)
          4. Absolute Betti values

        Regime logic:
          CRISIS        — β₀ spike (fragmentation) OR extreme weighted deviation
          VOLATILE       — β₁ elevated OR high Euler swing OR fast trend
          TRANSITIONING — moderate deviations OR non-zero trend
          STABLE        — everything within normal bounds
        """
        if self._baseline_betti is None or self._betti_std is None:
            return MarketRegime.UNKNOWN

        betti_vec = snapshot.betti_vector()
        euler = float(snapshot.euler_characteristic)
        sens = self.config.change_sensitivity  # default 2.0

        # ── Signal 1: Per-dimension z-scores ──
        z_betti = (betti_vec - self._baseline_betti) / self._betti_std
        z_euler = abs(euler - self._baseline_euler) / self._euler_std

        # Weighted deviation (dimension-aware)
        weighted_z = z_betti * self._DIM_WEIGHTS[:len(z_betti)]
        weighted_norm = float(np.linalg.norm(weighted_z))

        # ── Signal 2: Absolute Betti values ──
        b0 = betti_vec[0] if len(betti_vec) > 0 else 0.0
        b1 = betti_vec[1] if len(betti_vec) > 1 else 0.0
        b2 = betti_vec[2] if len(betti_vec) > 2 else 0.0

        # ── Signal 3: Trend (slope of β₀ and β₁ over recent window) ──
        trend_score = self._compute_trend_score()

        # ── Signal 4: Composite score ──
        # Combine weighted z-norm, euler deviation, and trend
        composite = (
            0.50 * weighted_norm +
            0.25 * z_euler +
            0.25 * trend_score
        )

        # ── Classification with sensitivity-scaled thresholds ──
        # CRISIS: β₀ fragmentation or extreme composite
        if (z_betti[0] > sens * 1.5 and b0 > 1) or composite > sens * 2.0:
            return MarketRegime.CRISIS

        # VOLATILE: β₁ cycles elevated or high euler swing or fast trend
        if (
            z_betti[1] > sens * 0.8
            or z_euler > sens * 1.2
            or (trend_score > sens and weighted_norm > sens * 0.5)
        ):
            return MarketRegime.VOLATILE

        # TRANSITIONING: moderate signals
        if composite > sens * 0.5 or trend_score > sens * 0.4:
            return MarketRegime.TRANSITIONING

        return MarketRegime.STABLE

    def _compute_trend_score(self) -> float:
        """
        Estimate how fast Betti numbers are changing.
        Uses simple linear regression slope on recent β₀ and β₁.
        Returns a non-negative score (higher = faster change).
        """
        if len(self._recent_betti) < 4:
            return 0.0

        vectors = np.array(list(self._recent_betti))
        n = vectors.shape[0]
        x = np.arange(n, dtype=np.float64)
        x_centered = x - x.mean()
        denom = np.sum(x_centered ** 2) + 1e-9

        # Slope for each Betti dimension
        slopes = np.zeros(min(vectors.shape[1], 3))
        for d in range(len(slopes)):
            y = vectors[:, d]
            slopes[d] = np.sum(x_centered * (y - y.mean())) / denom

        # Weighted slope magnitude
        weights = np.array([1.0, 1.5, 1.0])[:len(slopes)]
        return float(np.linalg.norm(slopes * weights))

    # ──────────────────────────────────────────────────────
    # CUSUM Detection (improved)
    # ──────────────────────────────────────────────────────

    def _cusum_detect(
        self,
        snapshot: TopologicalSnapshot,
        persistence_diagram: Optional[List[PersistenceInterval]] = None,
    ) -> Optional[StructuralAlert]:
        """
        Multivariate CUSUM on 4D feature: [β₀, β₁, β₂, Euler].
        Improvements:
          - Consistent 4D feature construction
          - Cooldown to prevent alert spam
          - Severity based on weighted magnitude
        """
        if (
            self._baseline_betti is None
            or self._betti_std is None
            or self._baseline_euler is None
            or self._euler_std is None
        ):
            return None

        # ── Build consistent 4D feature ──
        betti_vec = snapshot.betti_vector()  # default max_dim=3 → 4 elements
        feature = np.zeros(4, dtype=np.float64)
        feature[:3] = betti_vec[:3]
        feature[3] = float(snapshot.euler_characteristic)

        baseline = np.zeros(4, dtype=np.float64)
        baseline[:3] = self._baseline_betti[:3]
        baseline[3] = float(self._baseline_euler)

        std = np.zeros(4, dtype=np.float64)
        std[:3] = self._betti_std[:3]
        std[3] = float(self._euler_std)

        # Standardized deviation
        z = (feature - baseline) / std

        # CUSUM parameters
        k = 0.5  # slack (drift allowance)
        h = self.config.change_sensitivity * 3.0  # threshold

        # Update CUSUM
        self._cusum_pos = np.maximum(0.0, self._cusum_pos + z - k)
        self._cusum_neg = np.maximum(0.0, self._cusum_neg - z - k)

        # Check threshold
        exceeded_pos = self._cusum_pos > h
        exceeded_neg = self._cusum_neg > h

        if not (np.any(exceeded_pos) or np.any(exceeded_neg)):
            return None

        # ── Cooldown check ──
        now = snapshot.timestamp
        if (now - self._last_alert_time) < self._alert_cooldown:
            # Reset CUSUM but don't fire alert
            self._cusum_pos[:] = 0.0
            self._cusum_neg[:] = 0.0
            return None

        self._last_alert_time = now

        # Reset after detection
        self._cusum_pos[:] = 0.0
        self._cusum_neg[:] = 0.0

        # ── Persistence metrics ──
        persistence_enabled = persistence_diagram is not None
        diagram = persistence_diagram or []
        strong_now = [
            interval
            for interval in diagram
            if float(getattr(interval, "lifetime", 0.0)) > self._min_lifetime
        ]
        prev_strong = [
            interval
            for interval in self._previous_diagram
            if float(getattr(interval, "lifetime", 0.0)) > self._min_lifetime
        ]

        def _interval_key(interval: PersistenceInterval) -> Tuple[int, float, float]:
            return (
                int(interval.dimension),
                round(float(interval.birth), 6),
                round(float(interval.death) if interval.death is not None else -1.0, 6),
            )

        now_keys = {_interval_key(interval) for interval in strong_now}
        prev_keys = {_interval_key(interval) for interval in prev_strong}
        new_keys = now_keys - prev_keys
        disappeared_keys = prev_keys - now_keys
        has_persistent_features = len(new_keys) > 0 or len(disappeared_keys) > 0

        persistence_score = 0.0
        if strong_now:
            persistence_score = float(
                sum(float(interval.lifetime) for interval in strong_now) / len(strong_now)
            )

        # ── Build alert ──
        betti_change: Dict[int, int] = {}
        for dim in range(min(3, len(betti_vec))):
            betti_change[dim] = int(betti_vec[dim] - self._baseline_betti[dim])

        euler_change = int(
            snapshot.euler_characteristic - self._baseline_euler
        )

        # Weighted magnitude for severity/change score
        weighted_z = z * self._DIM_WEIGHTS
        change_score = float(np.linalg.norm(weighted_z))

        if change_score > 5.0:
            severity = AlertSeverity.CRITICAL
        elif change_score > 2.5:
            severity = AlertSeverity.WARNING
        else:
            severity = AlertSeverity.INFO

        previous_snapshot = self.history[-2] if len(self.history) >= 2 else snapshot
        last_known_regime = self._find_last_known_regime()
        if (
            previous_snapshot.regime == MarketRegime.UNKNOWN
            and last_known_regime != MarketRegime.UNKNOWN
        ):
            for i in range(len(self.history) - 2, -1, -1):
                if self.history[i].regime != MarketRegime.UNKNOWN:
                    previous_snapshot = self.history[i]
                    break

        dims_triggered = []
        labels = ["β₀", "β₁", "β₂", "χ"]
        for i in range(4):
            if exceeded_pos[i] or exceeded_neg[i]:
                direction = "↑" if exceeded_pos[i] else "↓"
                dims_triggered.append(f"{labels[i]}{direction}")

        betti_changed = any(delta != 0 for delta in betti_change.values()) or euler_change != 0
        logger.debug(
            "[DETECT] betti_changed=%s, persistence_score=%.4f, threshold=%.4f",
            betti_changed,
            persistence_score,
            self._persistence_threshold,
        )
        should_alert = betti_changed or persistence_score > self._persistence_threshold
        logger.debug(
            "[DETECT] alert_decision=%s, regime=%s",
            should_alert,
            snapshot.regime.value,
        )
        if persistence_enabled:
            if not should_alert:
                self._previous_diagram = list(diagram)
                return None

        persistent_features = [
            {
                "dimension": int(interval.dimension),
                "birth": float(interval.birth),
                "death": float(interval.death) if interval.death is not None else None,
                "lifetime": float(interval.lifetime),
            }
            for interval in strong_now
        ]

        self._previous_diagram = list(diagram)

        return StructuralAlert(
            timestamp=snapshot.timestamp,
            severity=severity,
            message=(
                f"Structural change: {', '.join(dims_triggered)} "
                f"(|wz|={change_score:.2f}, "
                f"betti_Δ={betti_change}, euler_Δ={euler_change})"
            ),
            change_score=change_score,
            current_snapshot=snapshot,
            previous_snapshot=previous_snapshot,
            old_regime=previous_snapshot.regime,
            new_regime=snapshot.regime,
            betti_change=betti_change,
            euler_change=euler_change,
            persistent_features=persistent_features,
            persistence_score=persistence_score,
        )

# ─── engines.py — append at the end of file ───

class TopologyEngine:
    """
    Orchestrator: receives MarketTick from SourceManager,
    drives the full pipeline, and emits snapshots + alerts.

    Usage:
        engine = TopologyEngine(config)
        engine.on_snapshot = my_snapshot_callback   # optional
        engine.on_alert    = my_alert_callback      # optional
        engine.process_tick(tick)
    """

    def __init__(self, config: MonitorConfig) -> None:
        self.config = config
        self.correlation = CorrelationEngine(config)
        self.correlation_engine = self.correlation  # backward compat alias
        self.analyzer = TopologyAnalyzer(config)
        self.topology_analyzer = self.analyzer  # backward compat alias
        self.detector = StructuralChangeDetector(config)
        self.change_detector = self.detector  # backward compat alias
        self.persistence_engine = PersistenceEngine()

        # Public history
        self.snapshots: List[TopologicalSnapshot] = []
        self.alerts: List[StructuralAlert] = []

        # Optional callbacks
        self.on_snapshot: Optional[Callable[[TopologicalSnapshot], None]] = None
        self.on_alert: Optional[Callable[[StructuralAlert], None]] = None

        # Throttle: minimum seconds between analyses
        self._last_analysis: float = 0.0

        logger.info(
            "TopologyEngine initialized — symbols=%s, window=%d, min_ticks=%d",
            config.symbols, config.window_size, config.min_ticks,
        )

    # ── Main entry point ──────────────────────────────────
    def process_tick(self, tick: MarketTick) -> Optional[Tuple[TopologicalSnapshot, Optional[StructuralAlert]]]:
        """
        Feed one market tick into the pipeline.
        Returns a TopologicalSnapshot if analysis was performed, else None.
        """
        # 1. Update correlation windows
        self.correlation.update(tick)

        # 2. Check readiness + throttle
        if not self.correlation.is_ready():
            return None

        now = tick.timestamp
        if now - self._last_analysis < self.config.analysis_interval:
            return None

        self._last_analysis = now

        # 3. Compute correlation matrix
        corr = self.correlation.compute_correlation_matrix()
        threshold = self.correlation.get_adaptive_threshold(corr)

        # 4. Build complex & extract topology
        snapshot = self.analyzer.analyze(corr, threshold, now)
        self.snapshots.append(snapshot)
        self.classify_snapshot_regime(snapshot)

        if self.on_snapshot:
            self.on_snapshot(snapshot)

        # 5. Detect structural change
        persistence_diagram: List[PersistenceInterval] = []
        try:
            logger.debug("[PERSIST] computing diagram for tick %s", tick.timestamp)
            persistence_diagram = (
                self.persistence_engine.compute_diagram(snapshot.complex)
                if snapshot.complex is not None
                else []
            )
            persistence_score = 0.0
            if persistence_diagram:
                finite_intervals = [
                    iv for iv in persistence_diagram if iv.is_finite
                ]
                if finite_intervals:
                    persistence_score = float(
                        sum(float(iv.lifetime) for iv in finite_intervals)
                        / len(finite_intervals)
                    )
            snapshot.persistent_features = [
                {
                    "dimension": int(interval.dimension),
                    "birth": float(interval.birth),
                    "death": float(interval.death) if interval.death is not None else None,
                    "lifetime": float(interval.lifetime) if interval.is_finite else 0.0,
                }
                for interval in persistence_diagram
                if interval.is_finite and float(interval.lifetime) > 0.0
            ]
            snapshot.persistence_score = persistence_score
            logger.debug(
                "[PERSIST] features=%d, score=%.4f",
                len(persistence_diagram),
                persistence_score,
            )
        except Exception as e:
            logger.error("[PERSIST] FAILED: %s", e, exc_info=True)
            persistence_diagram = []
            snapshot.persistent_features = []
            snapshot.persistence_score = 0.0
        alert = self.detector.update(snapshot, persistence_diagram=persistence_diagram)
        if alert:
            self.alerts.append(alert)
            logger.warning(
                "StructuralAlert: %s → %s | %s",
                alert.previous_snapshot.regime.value,
                alert.current_snapshot.regime.value,
                alert.message,
            )
            if self.on_alert:
                self.on_alert(alert)

        return (snapshot, alert)

    def classify_snapshot_regime(self, snapshot: TopologicalSnapshot) -> None:
        """Update snapshot regime if UNKNOWN based on Betti numbers."""
        if snapshot.regime == MarketRegime.UNKNOWN:
            snapshot.regime = MarketRegime.STABLE  # default for now

    # ── Bulk feed (for backtest) ──────────────────────────
    def process_ticks(self, ticks: List[MarketTick]) -> List[TopologicalSnapshot]:
        """Feed multiple ticks, return all generated snapshots."""
        results = []
        for t in ticks:
            snap = self.process_tick(t)
            if snap:
                results.append(snap)
        return results

    # ── State query helpers ───────────────────────────────
    @property
    def current_regime(self) -> MarketRegime:
        if self.snapshots:
            return self.snapshots[-1].regime
        return MarketRegime.UNKNOWN

    @property
    def latest_snapshot(self) -> Optional[TopologicalSnapshot]:
        return self.snapshots[-1] if self.snapshots else None

    def summary(self) -> dict:
        return {
            "total_snapshots": len(self.snapshots),
            "total_alerts": len(self.alerts),
            "current_regime": self.current_regime.value,
            "correlation_ready": self.correlation.is_ready(),
        }
