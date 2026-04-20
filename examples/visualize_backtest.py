"""
VeriLogos Backtest Visualization Suite
======================================
Generates publication-quality plots from backtest results.
Based on "Truth as Geometry" - Simplicial Complex Logic framework.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
from datetime import datetime
import ast
from typing import Dict, List, Tuple

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['axes.labelsize'] = 11

class VeriLogosVisualizer:
    """Visualization suite for VeriLogos backtest results."""
    
    def __init__(self, results_dir: str = "backtest_results"):
        self.results_dir = Path(results_dir)
        self.snapshots = None
        self.alerts = None
        self.regime_history = None

    @staticmethod
    def _parse_simplex_dict(value):
        """Safely parse num_simplices string values (Python dict format)."""
        if not isinstance(value, str) or not value.strip():
            return {}
        try:
            parsed = ast.literal_eval(value)
            if not isinstance(parsed, dict):
                return {}
            normalized = {}
            for key, item in parsed.items():
                try:
                    d_key = int(key)
                    d_val = int(float(item)) if pd.notna(item) else 0
                    normalized[d_key] = d_val
                except (TypeError, ValueError):
                    continue
            return normalized
        except (ValueError, SyntaxError):
            return {}

    @staticmethod
    def _save_empty_plot(save_path, title: str, message: str):
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.axis('off')
        ax.set_title(title, fontweight='bold')
        ax.text(0.5, 0.5, message, ha='center', va='center', fontsize=11)
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✅ Saved: {save_path}")
        plt.close(fig)
        
    def load_data(self):
        """Load all CSV files."""
        print("📊 Loading backtest results...")

        snapshots_file = self.results_dir / "snapshots.csv"
        alerts_file = self.results_dir / "alerts.csv"
        regime_file = self.results_dir / "regime_history.csv"

        if not snapshots_file.exists():
            raise FileNotFoundError(f"Missing required file: {snapshots_file}")

        # Load snapshots
        self.snapshots = pd.read_csv(snapshots_file)
        self.snapshots['datetime'] = pd.to_datetime(
            self.snapshots.get('datetime'), errors='coerce'
        )
        self.snapshots = self.snapshots.dropna(subset=['datetime']).copy()

        for col in ['betti_0', 'betti_1', 'betti_2', 'euler', 'max_dimension', 'threshold']:
            if col in self.snapshots.columns:
                self.snapshots[col] = pd.to_numeric(
                    self.snapshots[col], errors='coerce'
                ).fillna(0.0)

        if 'num_simplices' in self.snapshots.columns:
            self.snapshots['num_simplices_dict'] = self.snapshots['num_simplices'].apply(
                self._parse_simplex_dict
            )
        else:
            self.snapshots['num_simplices_dict'] = [{} for _ in range(len(self.snapshots))]

        # Load alerts
        if alerts_file.exists():
            self.alerts = pd.read_csv(alerts_file)
            if 'datetime' in self.alerts.columns:
                self.alerts['datetime'] = pd.to_datetime(
                    self.alerts['datetime'], errors='coerce'
                )
                self.alerts = self.alerts.dropna(subset=['datetime']).copy()
            else:
                self.alerts['datetime'] = pd.NaT
            self.alerts['message'] = self.alerts.get('message', '').fillna('').astype(str)
            self.alerts['severity'] = self.alerts.get('severity', 'INFO').fillna('INFO').astype(str)
        else:
            self.alerts = pd.DataFrame(columns=['datetime', 'message', 'severity'])

        # Load regime history
        if regime_file.exists():
            self.regime_history = pd.read_csv(regime_file)
            if 'datetime' in self.regime_history.columns:
                self.regime_history['datetime'] = pd.to_datetime(
                    self.regime_history['datetime'], errors='coerce'
                )
                self.regime_history = self.regime_history.dropna(subset=['datetime']).copy()
            else:
                self.regime_history['datetime'] = self.snapshots['datetime']
            self.regime_history['regime'] = self.regime_history.get('regime', 'UNKNOWN').fillna('UNKNOWN')
        else:
            self.regime_history = pd.DataFrame({
                'datetime': self.snapshots['datetime'],
                'regime': self.snapshots.get('regime', pd.Series(['UNKNOWN'] * len(self.snapshots))).fillna('UNKNOWN')
            })

        print(f"✅ Loaded {len(self.snapshots)} snapshots, {len(self.alerts)} alerts")
        
    def plot_betti_evolution(self, save_path: str = "betti_evolution.png"):
        """
        Plot Betti numbers evolution over time.
        
        Betti numbers (β₀, β₁, β₂) represent topological features:
        - β₀: connected components (market clusters)
        - β₁: 1-dimensional holes (cycles, feedback loops)
        - β₂: 2-dimensional voids (higher-order structures)
        """
        if self.snapshots is None or self.snapshots.empty:
            self._save_empty_plot(save_path, "Betti Number Evolution", "No snapshot data available")
            return

        fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
        
        time = self.snapshots['datetime']
        
        # β₀ - Connected Components
        axes[0].plot(time, self.snapshots['betti_0'], 
                    color='#2E86AB', linewidth=1.5, alpha=0.8)
        axes[0].fill_between(time, self.snapshots['betti_0'], 
                            alpha=0.3, color='#2E86AB')
        axes[0].set_ylabel('β₀ (Components)', fontweight='bold')
        axes[0].set_title('Betti Number Evolution - Topological Market Structure', 
                         fontsize=14, fontweight='bold')
        axes[0].grid(True, alpha=0.3)
        
        # β₁ - 1D Holes (Cycles)
        axes[1].plot(time, self.snapshots['betti_1'], 
                    color='#A23B72', linewidth=1.5, alpha=0.8)
        axes[1].fill_between(time, self.snapshots['betti_1'], 
                            alpha=0.3, color='#A23B72')
        axes[1].set_ylabel('β₁ (Cycles)', fontweight='bold')
        axes[1].grid(True, alpha=0.3)
        
        # β₂ - 2D Voids
        axes[2].plot(time, self.snapshots['betti_2'], 
                    color='#F18F01', linewidth=1.5, alpha=0.8)
        axes[2].fill_between(time, self.snapshots['betti_2'], 
                            alpha=0.3, color='#F18F01')
        axes[2].set_ylabel('β₂ (Voids)', fontweight='bold')
        axes[2].set_xlabel('Time', fontweight='bold')
        axes[2].grid(True, alpha=0.3)
        
        # Add regime background shading
        self._add_regime_shading(axes)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✅ Saved: {save_path}")
        plt.close()
        
    def plot_regime_timeline(self, save_path: str = "regime_timeline.png"):
        """
        Plot regime transitions over time with statistics.
        """
        if self.regime_history is None or self.regime_history.empty:
            self._save_empty_plot(save_path, "Regime Timeline", "No regime history available")
            return

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), 
                                       gridspec_kw={'height_ratios': [3, 1]})
        
        # Map regimes to numeric values for plotting
        regime_map = {
            'UNKNOWN': 0,
            'STABLE': 1,
            'TRANSITIONING': 2,
            'VOLATILE': 3,
            'CRISIS': 4
        }
        
        self.regime_history['regime_num'] = self.regime_history['regime'].map(regime_map)
        
        # Main timeline
        colors = {
            'UNKNOWN': '#95A3A4',
            'STABLE': '#27AE60',
            'TRANSITIONING': '#F39C12',
            'VOLATILE': '#E67E22',
            'CRISIS': '#C0392B'
        }
        
        for regime, color in colors.items():
            mask = self.regime_history['regime'] == regime
            if mask.any():
                ax1.scatter(self.regime_history.loc[mask, 'datetime'],
                          self.regime_history.loc[mask, 'regime_num'],
                          c=color, label=regime, s=10, alpha=0.6)
        
        ax1.set_ylabel('Market Regime', fontweight='bold')
        ax1.set_yticks(list(regime_map.values()))
        ax1.set_yticklabels(list(regime_map.keys()))
        ax1.set_title('Market Regime Timeline - SC-Logic Classification', 
                     fontsize=14, fontweight='bold')
        ax1.legend(loc='upper right', framealpha=0.9)
        ax1.grid(True, alpha=0.3, axis='x')
        
        # Regime distribution
        regime_counts = self.regime_history['regime'].value_counts()
        regime_pcts = (regime_counts / len(self.regime_history) * 100).round(1)
        
        bars = ax2.bar(regime_counts.index, regime_counts.values,
                      color=[colors.get(r, '#95A3A4') for r in regime_counts.index],
                      alpha=0.7, edgecolor='black', linewidth=1.5)
        
        # Add percentage labels
        for bar, pct in zip(bars, regime_pcts):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{pct}%', ha='center', va='bottom', fontweight='bold')
        
        ax2.set_ylabel('Count', fontweight='bold')
        ax2.set_xlabel('Regime', fontweight='bold')
        ax2.set_title('Regime Distribution', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✅ Saved: {save_path}")
        plt.close()
        
    def plot_alert_analysis(self, save_path: str = "alert_analysis.png"):
        """
        Analyze and visualize structural change alerts.
        """
        if self.alerts is None or self.alerts.empty:
            self._save_empty_plot(save_path, "Alert Analysis", "No alerts available")
            return

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # Extract alert types from messages
        def parse_alert_type(msg):
            if 'β0↑' in msg:
                return 'β₀ Increase'
            elif 'β0↓' in msg:
                return 'β₀ Decrease'
            elif 'β1↑' in msg:
                return 'β₁ Increase'
            elif 'β1↓' in msg:
                return 'β₁ Decrease'
            elif '→' in msg:
                return 'Regime Transition'
            else:
                return 'Other'
        
        self.alerts['alert_type'] = self.alerts['message'].apply(parse_alert_type)
        
        # 1. Alert timeline
        alert_colors = {
            'β₀ Increase': '#3498DB',
            'β₀ Decrease': '#2980B9',
            'β₁ Increase': '#E74C3C',
            'β₁ Decrease': '#C0392B',
            'Regime Transition': '#F39C12',
            'Other': '#95A3A4'
        }
        
        for alert_type, color in alert_colors.items():
            mask = self.alerts['alert_type'] == alert_type
            if mask.any():
                axes[0, 0].scatter(self.alerts.loc[mask, 'datetime'],
                                 [alert_type] * mask.sum(),
                                 c=color, s=30, alpha=0.6, label=alert_type)
        
        axes[0, 0].set_ylabel('Alert Type', fontweight='bold')
        axes[0, 0].set_title('Alert Timeline', fontsize=12, fontweight='bold')
        axes[0, 0].legend(loc='upper right', fontsize=8)
        axes[0, 0].grid(True, alpha=0.3, axis='x')
        
        # 2. Alert type distribution
        alert_counts = self.alerts['alert_type'].value_counts()
        axes[0, 1].pie(alert_counts.values, labels=alert_counts.index,
                      autopct='%1.1f%%', startangle=90,
                      colors=[alert_colors.get(t, '#95A3A4') for t in alert_counts.index])
        axes[0, 1].set_title('Alert Type Distribution', fontsize=12, fontweight='bold')
        
        # 3. Alerts per hour
        self.alerts['hour'] = self.alerts['datetime'].dt.hour
        hourly_alerts = self.alerts.groupby('hour').size()
        axes[1, 0].bar(hourly_alerts.index, hourly_alerts.values,
                      color='#9B59B6', alpha=0.7, edgecolor='black')
        axes[1, 0].set_xlabel('Hour of Day', fontweight='bold')
        axes[1, 0].set_ylabel('Alert Count', fontweight='bold')
        axes[1, 0].set_title('Alert Distribution by Hour', fontsize=12, fontweight='bold')
        axes[1, 0].grid(True, alpha=0.3, axis='y')
        
        # 4. Severity distribution
        severity_counts = self.alerts['severity'].value_counts()
        axes[1, 1].bar(severity_counts.index, severity_counts.values,
                      color=['#27AE60', '#F39C12', '#E74C3C'][:len(severity_counts)],
                      alpha=0.7, edgecolor='black')
        axes[1, 1].set_xlabel('Severity', fontweight='bold')
        axes[1, 1].set_ylabel('Count', fontweight='bold')
        axes[1, 1].set_title('Alert Severity Distribution', fontsize=12, fontweight='bold')
        axes[1, 1].grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✅ Saved: {save_path}")
        plt.close()
        
    def plot_euler_characteristic(self, save_path: str = "euler_characteristic.png"):
        """
        Plot Euler characteristic evolution.
        
        χ = β₀ - β₁ + β₂ (Euler-Poincaré formula)
        Represents overall topological complexity.
        """
        if self.snapshots is None or self.snapshots.empty:
            self._save_empty_plot(save_path, "Euler Characteristic", "No snapshot data available")
            return

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
        
        time = self.snapshots['datetime']
        euler = self.snapshots['euler']
        
        # Main plot
        ax1.plot(time, euler, color='#8E44AD', linewidth=1.5, alpha=0.8)
        ax1.fill_between(time, euler, alpha=0.3, color='#8E44AD')
        ax1.axhline(y=0, color='red', linestyle='--', linewidth=1, alpha=0.5)
        ax1.set_ylabel('χ (Euler Characteristic)', fontweight='bold')
        ax1.set_title('Euler Characteristic Evolution - Topological Complexity Measure',
                     fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        
        # Add regime shading
        self._add_regime_shading([ax1])
        
        # Rolling statistics
        window = min(100, len(euler) // 10)
        if window > 1:
            rolling_mean = pd.Series(euler).rolling(window=window, center=True).mean()
            rolling_std = pd.Series(euler).rolling(window=window, center=True).std()
            
            ax2.plot(time, rolling_mean, color='#16A085', linewidth=2, label=f'Mean (window={window})')
            ax2.fill_between(time, 
                            rolling_mean - rolling_std,
                            rolling_mean + rolling_std,
                            alpha=0.3, color='#16A085', label='±1 Std Dev')
            ax2.set_ylabel('Rolling Statistics', fontweight='bold')
            ax2.set_xlabel('Time', fontweight='bold')
            ax2.legend(loc='upper right')
            ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✅ Saved: {save_path}")
        plt.close()
        
    def plot_simplex_distribution(self, save_path: str = "simplex_distribution.png"):
        """
        Plot distribution of simplices by dimension over time.
        """
        if self.snapshots is None or self.snapshots.empty:
            self._save_empty_plot(save_path, "Simplex Distribution", "No snapshot data available")
            return

        if 'num_simplices_dict' not in self.snapshots.columns:
            print("⚠️  Simplex data not available")
            return
        
        # Extract simplex counts by dimension
        dims = [0, 1, 2, 3]
        simplex_data = {dim: [] for dim in dims}
        
        for _, row in self.snapshots.iterrows():
            s_dict = row['num_simplices_dict']
            for dim in dims:
                simplex_data[dim].append(s_dict.get(dim, 0))
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
        
        time = self.snapshots['datetime']
        colors = ['#3498DB', '#E74C3C', '#F39C12', '#9B59B6']
        labels = ['0-simplices (vertices)', '1-simplices (edges)', 
                 '2-simplices (triangles)', '3-simplices (tetrahedra)']
        
        # Stacked area plot
        ax1.stackplot(time, *[simplex_data[d] for d in dims],
                     labels=labels, colors=colors, alpha=0.7)
        ax1.set_ylabel('Simplex Count', fontweight='bold')
        ax1.set_title('Simplicial Complex Structure Evolution', 
                     fontsize=14, fontweight='bold')
        ax1.legend(loc='upper left', framealpha=0.9)
        ax1.grid(True, alpha=0.3)
        
        # Individual dimension plots
        for dim, color, label in zip(dims, colors, labels):
            ax2.plot(time, simplex_data[dim], color=color, 
                    linewidth=1.5, alpha=0.8, label=label)
        
        ax2.set_ylabel('Count (log scale)', fontweight='bold')
        ax2.set_xlabel('Time', fontweight='bold')
        ax2.set_yscale('log')
        ax2.legend(loc='upper left', framealpha=0.9)
        ax2.grid(True, alpha=0.3, which='both')
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✅ Saved: {save_path}")
        plt.close()
        
    def plot_comprehensive_dashboard(self, save_path: str = "dashboard.png"):
        """
        Create a comprehensive dashboard with all key metrics.
        """
        if self.snapshots is None or self.snapshots.empty:
            self._save_empty_plot(save_path, "Comprehensive Dashboard", "No snapshot data available")
            return

        fig = plt.figure(figsize=(18, 12))
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        
        time = self.snapshots['datetime']
        
        # 1. Betti numbers (top row, spans 2 columns)
        ax1 = fig.add_subplot(gs[0, :2])
        ax1.plot(time, self.snapshots['betti_0'], label='β₀', linewidth=1.5, alpha=0.8)
        ax1.plot(time, self.snapshots['betti_1'], label='β₁', linewidth=1.5, alpha=0.8)
        ax1.plot(time, self.snapshots['betti_2'], label='β₂', linewidth=1.5, alpha=0.8)
        ax1.set_ylabel('Betti Numbers', fontweight='bold')
        ax1.set_title('Topological Features', fontsize=12, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. Regime distribution (top right)
        ax2 = fig.add_subplot(gs[0, 2])
        regime_counts = self.regime_history['regime'].value_counts()
        ax2.pie(regime_counts.values, labels=regime_counts.index, autopct='%1.1f%%')
        ax2.set_title('Regime Distribution', fontsize=12, fontweight='bold')
        
        # 3. Euler characteristic (middle left)
        ax3 = fig.add_subplot(gs[1, 0])
        ax3.plot(time, self.snapshots['euler'], color='#8E44AD', linewidth=1.5)
        ax3.axhline(y=0, color='red', linestyle='--', alpha=0.5)
        ax3.set_ylabel('χ', fontweight='bold')
        ax3.set_title('Euler Characteristic', fontsize=12, fontweight='bold')
        ax3.grid(True, alpha=0.3)
        
        # 4. Alert timeline (middle center)
        ax4 = fig.add_subplot(gs[1, 1])
        if self.alerts is not None and not self.alerts.empty:
            alert_counts_time = self.alerts.set_index('datetime').resample('1h').size()
            ax4.bar(alert_counts_time.index, alert_counts_time.values,
                    width=0.04, color='#E74C3C', alpha=0.7)
        else:
            ax4.text(0.5, 0.5, "No alerts", ha='center', va='center', transform=ax4.transAxes)
        ax4.set_ylabel('Alerts/Hour', fontweight='bold')
        ax4.set_title('Alert Frequency', fontsize=12, fontweight='bold')
        ax4.grid(True, alpha=0.3, axis='y')
        
        # 5. Max dimension (middle right)
        ax5 = fig.add_subplot(gs[1, 2])
        ax5.plot(time, self.snapshots['max_dimension'], 
                color='#16A085', linewidth=1.5, drawstyle='steps-post')
        ax5.set_ylabel('Max Dimension', fontweight='bold')
        ax5.set_title('Complex Dimension', fontsize=12, fontweight='bold')
        ax5.grid(True, alpha=0.3)
        
        # 6. Regime timeline (bottom, spans all columns)
        ax6 = fig.add_subplot(gs[2, :])
        regime_map = {'UNKNOWN': 0, 'STABLE': 1, 'TRANSITIONING': 2, 
                     'VOLATILE': 3, 'CRISIS': 4}
        colors_map = {'UNKNOWN': '#95A3A4', 'STABLE': '#27AE60', 
                     'TRANSITIONING': '#F39C12', 'VOLATILE': '#E67E22', 
                     'CRISIS': '#C0392B'}
        
        for regime, color in colors_map.items():
            mask = self.regime_history['regime'] == regime
            if mask.any():
                ax6.scatter(self.regime_history.loc[mask, 'datetime'],
                          [regime_map[regime]] * mask.sum(),
                          c=color, s=5, alpha=0.6, label=regime)
        
        ax6.set_yticks(list(regime_map.values()))
        ax6.set_yticklabels(list(regime_map.keys()))
        ax6.set_xlabel('Time', fontweight='bold')
        ax6.set_title('Market Regime Timeline', fontsize=12, fontweight='bold')
        ax6.legend(loc='upper right', ncol=5, fontsize=8)
        ax6.grid(True, alpha=0.3, axis='x')
        
        fig.suptitle('VeriLogos Backtest Dashboard - SC-Logic Analysis', 
                    fontsize=16, fontweight='bold', y=0.995)
        
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✅ Saved: {save_path}")
        plt.close()
        
    def _add_regime_shading(self, axes):
        """Add regime background shading to axes."""
        if self.regime_history is None or self.regime_history.empty:
            return

        regime_colors = {
            'STABLE': ('#27AE60', 0.1),
            'TRANSITIONING': ('#F39C12', 0.1),
            'VOLATILE': ('#E67E22', 0.15),
            'CRISIS': ('#C0392B', 0.2)
        }
        
        for ax in axes:
            current_regime = None
            start_time = None
            
            for idx, row in self.regime_history.iterrows():
                if row['regime'] != current_regime:
                    if current_regime and start_time:
                        color, alpha = regime_colors.get(current_regime, ('#95A3A4', 0.05))
                        ax.axvspan(start_time, row['datetime'], 
                                  color=color, alpha=alpha, zorder=0)
                    current_regime = row['regime']
                    start_time = row['datetime']
            
            # Last regime
            if current_regime and start_time:
                color, alpha = regime_colors.get(current_regime, ('#95A3A4', 0.05))
                ax.axvspan(start_time, self.regime_history.iloc[-1]['datetime'],
                          color=color, alpha=alpha, zorder=0)
    
    def generate_all_plots(self, output_dir: str = "visualizations"):
        """Generate all visualization plots."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        print("\n🎨 Generating VeriLogos visualizations...")
        print("=" * 60)
        
        self.load_data()

        plot_jobs = [
            ("betti_evolution", self.plot_betti_evolution, output_path / "betti_evolution.png"),
            ("regime_timeline", self.plot_regime_timeline, output_path / "regime_timeline.png"),
            ("alert_analysis", self.plot_alert_analysis, output_path / "alert_analysis.png"),
            ("euler_characteristic", self.plot_euler_characteristic, output_path / "euler_characteristic.png"),
            ("simplex_distribution", self.plot_simplex_distribution, output_path / "simplex_distribution.png"),
            ("dashboard", self.plot_comprehensive_dashboard, output_path / "dashboard.png"),
        ]

        for name, fn, path in plot_jobs:
            try:
                fn(path)
            except Exception as exc:
                print(f"⚠️  Failed to generate {name}: {exc}")
        
        print("=" * 60)
        print(f"✅ All visualizations saved to: {output_path}/")
        print("\n📊 Summary Statistics:")
        print(f"   • Total ticks: {len(self.snapshots):,}")
        print(f"   • Total alerts: {len(self.alerts):,}")
        regime_count = self.regime_history['regime'].nunique() if self.regime_history is not None and not self.regime_history.empty else 0
        print(f"   • Unique regimes: {regime_count}")
        print(f"   • Time range: {self.snapshots['datetime'].min()} → {self.snapshots['datetime'].max()}")
        print(f"   • Mean β₀: {self.snapshots['betti_0'].mean():.2f}")
        print(f"   • Mean β₁: {self.snapshots['betti_1'].mean():.2f}")
        print(f"   • Mean β₂: {self.snapshots['betti_2'].mean():.2f}")
        print(f"   • Mean χ: {self.snapshots['euler'].mean():.2f}")


if __name__ == "__main__":
    visualizer = VeriLogosVisualizer("backtest_results")
    visualizer.generate_all_plots("visualizations")
