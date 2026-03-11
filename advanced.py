"""
APEX — Advanced Risk & Portfolio Management
Covers all upgrade plan requirements:
- Position sizing (ATR-based, volatility-adjusted)
- Correlation control (prevent stacking correlated pairs)
- Currency exposure limits (max USD exposure 40%)
- Portfolio manager (capital allocation across categories)
- Strategy performance tracker (win rate, Sharpe, drawdown monitoring)
"""
from __future__ import annotations
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger

from config.settings import settings


# ── Known correlations between forex pairs ────────────────────────────────────
# Positive = move together, Negative = inverse. Magnitude 0–1.
PAIR_CORRELATIONS: Dict[Tuple[str, str], float] = {
    ("EUR_USD", "GBP_USD"): 0.82,
    ("EUR_USD", "AUD_USD"): 0.68,
    ("EUR_USD", "NZD_USD"): 0.62,
    ("EUR_USD", "USD_CHF"): -0.91,
    ("EUR_USD", "USD_JPY"): -0.54,
    ("GBP_USD", "AUD_USD"): 0.71,
    ("GBP_USD", "NZD_USD"): 0.65,
    ("GBP_USD", "USD_CHF"): -0.78,
    ("AUD_USD", "NZD_USD"): 0.93,
    ("USD_JPY", "USD_CHF"): 0.72,
    ("XAU_USD", "EUR_USD"): 0.55,
    ("XAU_USD", "USD_JPY"): -0.48,
}

# Currency base exposure per instrument
INSTRUMENT_CURRENCY_EXPOSURE: Dict[str, Dict[str, float]] = {
    "EUR_USD": {"EUR": 1.0, "USD": -1.0},
    "GBP_USD": {"GBP": 1.0, "USD": -1.0},
    "USD_JPY": {"USD": 1.0, "JPY": -1.0},
    "USD_CHF": {"USD": 1.0, "CHF": -1.0},
    "USD_CAD": {"USD": 1.0, "CAD": -1.0},
    "AUD_USD": {"AUD": 1.0, "USD": -1.0},
    "NZD_USD": {"NZD": 1.0, "USD": -1.0},
    "EUR_GBP": {"EUR": 1.0, "GBP": -1.0},
    "EUR_JPY": {"EUR": 1.0, "JPY": -1.0},
    "GBP_JPY": {"GBP": 1.0, "JPY": -1.0},
    "XAU_USD": {"XAU": 1.0, "USD": -1.0},
    "US500":   {"USD": 1.0},
}

MAX_CURRENCY_EXPOSURE_PCT = 0.40   # 40% max exposure per single currency


# ── Position Sizing ──────────────────────────────────────────────────────────

@dataclass
class PositionSizeResult:
    units:           float          # OANDA units to trade
    risk_amount:     float          # $ at risk
    risk_pct:        float          # % of balance at risk
    stop_pips:       float          # distance in pips to stop
    pip_value:       float          # value per pip
    atr_used:        float          # ATR value used for sizing
    volatility_adj:  float          # volatility adjustment factor
    approved:        bool = True
    reason:          str  = "OK"


class PositionSizer:
    """
    ATR-based position sizing with volatility adjustment.
    
    Formula:
        risk_amount = balance × risk_pct / 100
        units = risk_amount / (stop_distance_in_account_currency)
    
    Volatility adjustment: scale down in high-vol regimes.
    """

    def __init__(
        self,
        default_risk_pct: float = 1.0,
        atr_sl_multiplier: float = 1.5,
        max_position_pct: float = 5.0,    # max 5% of balance in any single trade
        vol_adj_enabled: bool = True,
    ):
        self.default_risk_pct    = default_risk_pct
        self.atr_sl_multiplier   = atr_sl_multiplier
        self.max_position_pct    = max_position_pct
        self.vol_adj_enabled     = vol_adj_enabled

    def calculate(
        self,
        balance: float,
        instrument: str,
        current_price: float,
        atr: float,
        risk_pct: Optional[float] = None,
        explicit_stop: Optional[float] = None,
        regime: str = "unknown",
    ) -> PositionSizeResult:
        """Calculate position size for a trade."""

        risk_pct = risk_pct or self.default_risk_pct

        # ── Volatility adjustment ─────────────────────────────────────────
        vol_adj = self._vol_adjustment(atr, current_price, regime)
        adjusted_risk = risk_pct * vol_adj

        # ── Stop distance ─────────────────────────────────────────────────
        if explicit_stop is not None:
            stop_dist = abs(current_price - explicit_stop)
        else:
            stop_dist = atr * self.atr_sl_multiplier

        if stop_dist <= 0:
            return PositionSizeResult(
                units=0, risk_amount=0, risk_pct=0,
                stop_pips=0, pip_value=0, atr_used=atr,
                volatility_adj=vol_adj, approved=False,
                reason="Invalid stop distance",
            )

        # ── Pip value calculation ─────────────────────────────────────────
        pip_size  = self._pip_size(instrument)
        stop_pips = stop_dist / pip_size

        # Approximate pip value in account currency (USD assumed)
        pip_value = self._pip_value_usd(instrument, current_price, pip_size)

        # ── Units ─────────────────────────────────────────────────────────
        risk_amount  = balance * adjusted_risk / 100.0
        max_amount   = balance * self.max_position_pct / 100.0
        risk_amount  = min(risk_amount, max_amount)

        if pip_value > 0 and stop_pips > 0:
            units = risk_amount / (pip_value * stop_pips)
        else:
            units = risk_amount / stop_dist

        # Round to sensible lot sizes
        units = self._round_units(units, instrument)

        return PositionSizeResult(
            units=units,
            risk_amount=round(risk_amount, 2),
            risk_pct=round(adjusted_risk, 3),
            stop_pips=round(stop_pips, 1),
            pip_value=round(pip_value, 5),
            atr_used=round(atr, 5),
            volatility_adj=round(vol_adj, 3),
            approved=units > 0,
            reason="OK" if units > 0 else "Units too small",
        )

    def _vol_adjustment(self, atr: float, price: float, regime: str) -> float:
        """Scale position size based on current volatility regime."""
        if not self.vol_adj_enabled:
            return 1.0
        atr_pct = atr / (price + 1e-10) * 100
        if atr_pct > 1.5 or regime == "volatile":
            return 0.6    # reduce size in high-vol
        elif atr_pct > 0.8:
            return 0.8
        elif atr_pct < 0.3 or regime == "ranging":
            return 1.1    # small boost in low-vol
        return 1.0

    def _pip_size(self, instrument: str) -> float:
        """Return pip size for the instrument."""
        if "JPY" in instrument:
            return 0.01
        if instrument in ("US500", "US30", "DE40", "UK100"):
            return 1.0
        if "XAU" in instrument or "XAG" in instrument:
            return 0.01
        return 0.0001

    def _pip_value_usd(self, instrument: str, price: float, pip_size: float) -> float:
        """Approximate pip value per unit in USD."""
        if instrument.endswith("_USD") or instrument.startswith("XAU"):
            return pip_size  # direct quote
        if instrument.startswith("USD_"):
            return pip_size / price  # indirect quote
        return pip_size  # cross pairs: rough approximation

    def _round_units(self, units: float, instrument: str) -> float:
        """Round to nearest micro-lot (1000 units)."""
        if units < 1000:
            return 0.0
        return round(units / 1000) * 1000


# ── Correlation Controller ────────────────────────────────────────────────────

class CorrelationController:
    """
    Prevents stacking highly correlated positions simultaneously.
    Uses a lookup table of known forex pair correlations.
    """

    def __init__(self, max_correlation: float = 0.70):
        self.max_correlation = max_correlation

    def check(
        self,
        new_instrument: str,
        new_direction: str,       # "BUY" | "SELL"
        open_trades: List[Dict],
    ) -> Tuple[bool, str]:
        """
        Returns (approved, reason).
        Blocks if a new trade would add excessive correlated exposure.
        """
        for trade in open_trades:
            existing_instrument = trade.get("instrument", "")
            existing_direction  = trade.get("direction", "")

            corr = self._get_correlation(new_instrument, existing_instrument)
            if abs(corr) < 0.01:
                continue

            # Same direction on positively correlated pairs → doubling up
            if corr > self.max_correlation and new_direction == existing_direction:
                return False, (
                    f"Correlation block: {new_instrument} ↔ {existing_instrument} "
                    f"corr={corr:.2f}, both {new_direction}"
                )

            # Opposite direction on negatively correlated pairs → also doubling up
            if corr < -self.max_correlation:
                opposing = {"BUY": "SELL", "SELL": "BUY"}.get(new_direction)
                if existing_direction == opposing:
                    return False, (
                        f"Correlation block: {new_instrument} ↔ {existing_instrument} "
                        f"inverse corr={corr:.2f}"
                    )

        return True, "Correlation check passed"

    def _get_correlation(self, a: str, b: str) -> float:
        if a == b:
            return 1.0
        return (
            PAIR_CORRELATIONS.get((a, b))
            or PAIR_CORRELATIONS.get((b, a))
            or 0.0
        )


# ── Currency Exposure Manager ─────────────────────────────────────────────────

class CurrencyExposureManager:
    """
    Tracks net currency exposure across all open positions.
    Blocks new trades that would push any single currency above 40%.
    """

    def __init__(self, max_exposure_pct: float = MAX_CURRENCY_EXPOSURE_PCT):
        self.max_exposure_pct = max_exposure_pct

    def check(
        self,
        new_instrument: str,
        new_direction: str,
        new_units: float,
        open_trades: List[Dict],
        balance: float,
    ) -> Tuple[bool, str]:
        """Return (approved, reason)."""
        exposure = self._compute_exposure(open_trades, balance)

        # Add the new trade
        inst_exp = INSTRUMENT_CURRENCY_EXPOSURE.get(new_instrument, {})
        sign     = 1.0 if new_direction == "BUY" else -1.0
        notional = new_units  # rough USD notional

        for currency, direction_factor in inst_exp.items():
            current = exposure.get(currency, 0.0)
            added   = abs(direction_factor * sign * notional / (balance + 1e-10))
            total   = current + added
            if total > self.max_exposure_pct:
                return False, (
                    f"Currency exposure: {currency} would reach {total:.1%} "
                    f"(limit {self.max_exposure_pct:.0%})"
                )

        return True, "Currency exposure OK"

    def get_exposure(self, open_trades: List[Dict], balance: float) -> Dict[str, float]:
        return self._compute_exposure(open_trades, balance)

    def _compute_exposure(self, open_trades: List[Dict], balance: float) -> Dict[str, float]:
        exposure: Dict[str, float] = defaultdict(float)
        for trade in open_trades:
            instrument = trade.get("instrument", "")
            direction  = trade.get("direction", "BUY")
            units      = abs(float(trade.get("units", 0)))
            sign       = 1.0 if direction == "BUY" else -1.0
            inst_exp   = INSTRUMENT_CURRENCY_EXPOSURE.get(instrument, {})
            for currency, factor in inst_exp.items():
                exposure[currency] += abs(factor * sign * units / (balance + 1e-10))
        return dict(exposure)


# ── Strategy Performance Tracker ─────────────────────────────────────────────

@dataclass
class StrategyStats:
    name:          str
    total_trades:  int   = 0
    wins:          int   = 0
    losses:        int   = 0
    total_pnl:     float = 0.0
    pnl_history:   List[float] = field(default_factory=list)
    enabled:       bool  = True
    disabled_at:   Optional[str] = None
    disable_reason: str  = ""

    @property
    def win_rate(self) -> float:
        return self.wins / self.total_trades if self.total_trades else 0.0

    @property
    def sharpe_ratio(self) -> float:
        if len(self.pnl_history) < 5:
            return 0.0
        mean = statistics.mean(self.pnl_history)
        std  = statistics.stdev(self.pnl_history) or 1e-10
        return mean / std * math.sqrt(252)

    @property
    def max_drawdown(self) -> float:
        if not self.pnl_history:
            return 0.0
        cumulative = list(pd.Series(self.pnl_history).cumsum())
        peak       = cumulative[0]
        max_dd     = 0.0
        for v in cumulative:
            peak   = max(peak, v)
            max_dd = max(max_dd, (peak - v) / (abs(peak) + 1e-10))
        return max_dd

    @property
    def profit_factor(self) -> float:
        gains  = sum(p for p in self.pnl_history if p > 0)
        losses = abs(sum(p for p in self.pnl_history if p < 0)) or 1e-10
        return gains / losses


class StrategyPerformanceTracker:
    """
    Monitors each strategy's live performance.
    Automatically disables strategies that fall below thresholds.
    Provides dynamic weighting for the signal combiner.
    """

    def __init__(
        self,
        min_win_rate:    float = 0.40,
        min_sharpe:      float = 0.5,
        max_drawdown:    float = 0.20,
        min_trades_eval: int   = 10,     # min trades before evaluation kicks in
    ):
        self.min_win_rate    = min_win_rate
        self.min_sharpe      = min_sharpe
        self.max_drawdown    = max_drawdown
        self.min_trades_eval = min_trades_eval
        self._stats: Dict[str, StrategyStats] = {}

    def record_trade(
        self, strategy: str, pnl: float, won: bool
    ):
        if strategy not in self._stats:
            self._stats[strategy] = StrategyStats(name=strategy)
        s = self._stats[strategy]
        s.total_trades += 1
        s.wins         += int(won)
        s.losses       += int(not won)
        s.total_pnl    += pnl
        s.pnl_history.append(pnl)
        # Keep last 200 trades only
        if len(s.pnl_history) > 200:
            s.pnl_history.pop(0)
        self._evaluate(s)

    def is_enabled(self, strategy: str) -> bool:
        return self._stats.get(strategy, StrategyStats(name=strategy)).enabled

    def get_weights(self) -> Dict[str, float]:
        """Dynamic weights for signal combiner: 1.0 = baseline."""
        weights = {}
        for name, s in self._stats.items():
            if not s.enabled:
                weights[name] = 0.0
                continue
            if s.total_trades < self.min_trades_eval:
                weights[name] = 1.0  # neutral until enough data
                continue
            # Blend win rate and Sharpe into a single weight
            wr_score     = s.win_rate / 0.55       # normalise around 55% target
            sharpe_score = max(0.1, s.sharpe_ratio) / 1.5
            weight       = 0.5 * wr_score + 0.5 * sharpe_score
            weights[name] = round(float(np.clip(weight, 0.2, 2.0)), 3)
        return weights

    def get_all_stats(self) -> List[Dict]:
        return [
            {
                "name":           s.name,
                "total_trades":   s.total_trades,
                "win_rate":       round(s.win_rate, 3),
                "sharpe_ratio":   round(s.sharpe_ratio, 3),
                "max_drawdown":   round(s.max_drawdown, 3),
                "profit_factor":  round(s.profit_factor, 3),
                "total_pnl":      round(s.total_pnl, 2),
                "enabled":        s.enabled,
                "disable_reason": s.disable_reason,
            }
            for s in self._stats.values()
        ]

    def _evaluate(self, s: StrategyStats):
        if s.total_trades < self.min_trades_eval:
            return
        issues = []
        if s.win_rate < self.min_win_rate:
            issues.append(f"win_rate={s.win_rate:.1%} < {self.min_win_rate:.1%}")
        if s.sharpe_ratio < self.min_sharpe and s.total_trades >= 20:
            issues.append(f"sharpe={s.sharpe_ratio:.2f} < {self.min_sharpe}")
        if s.max_drawdown > self.max_drawdown:
            issues.append(f"drawdown={s.max_drawdown:.1%} > {self.max_drawdown:.1%}")
        if issues and s.enabled:
            s.enabled       = False
            s.disabled_at   = datetime.utcnow().isoformat()
            s.disable_reason = "; ".join(issues)
            logger.warning(f"⚠️ Strategy '{s.name}' disabled: {s.disable_reason}")
        elif not issues and not s.enabled:
            # Re-enable if recovered
            s.enabled       = True
            s.disable_reason = ""
            logger.info(f"✅ Strategy '{s.name}' re-enabled after recovery")


# ── Portfolio Manager ─────────────────────────────────────────────────────────

class PortfolioManager:
    """
    Allocates capital across strategy categories.
    Prevents over-concentration in one strategy type.
    """

    CATEGORY_ALLOCATION: Dict[str, float] = {
        "trend":          0.30,
        "mean_reversion": 0.20,
        "volatility":     0.15,
        "scalping":       0.15,
        "stat_arb":       0.10,
        "ml":             0.10,
    }

    def __init__(self):
        self._category_exposure: Dict[str, float] = defaultdict(float)

    def get_allowed_risk(
        self,
        category: str,
        balance: float,
        base_risk_pct: float = 1.0,
    ) -> float:
        """Return the risk % allowed for a new trade in this category."""
        allocation  = self.CATEGORY_ALLOCATION.get(category, 0.10)
        current_exp = self._category_exposure.get(category, 0.0)
        remaining   = (allocation * balance) - current_exp

        if remaining <= 0:
            return 0.0

        # Scale risk proportionally to remaining allocation
        pct = min(base_risk_pct, remaining / balance * 100)
        return max(0.0, round(pct, 3))

    def record_open(self, category: str, notional: float):
        self._category_exposure[category] += notional

    def record_close(self, category: str, notional: float):
        self._category_exposure[category] = max(
            0.0, self._category_exposure.get(category, 0.0) - notional
        )

    def get_allocation_summary(self, balance: float) -> Dict:
        return {
            cat: {
                "target_pct":  round(pct, 2),
                "target_usd":  round(pct * balance, 2),
                "current_usd": round(self._category_exposure.get(cat, 0.0), 2),
                "utilisation": round(
                    self._category_exposure.get(cat, 0.0) / ((pct * balance) + 1e-10), 3
                ),
            }
            for cat, pct in self.CATEGORY_ALLOCATION.items()
        }


# ── Singletons ────────────────────────────────────────────────────────────────

_position_sizer:   Optional[PositionSizer]              = None
_corr_controller:  Optional[CorrelationController]      = None
_currency_manager: Optional[CurrencyExposureManager]    = None
_perf_tracker:     Optional[StrategyPerformanceTracker] = None
_portfolio_mgr:    Optional[PortfolioManager]           = None


def get_position_sizer()      -> PositionSizer:
    global _position_sizer
    if _position_sizer is None:
        _position_sizer = PositionSizer(
            default_risk_pct=settings.trading.risk_per_trade_pct
        )
    return _position_sizer

def get_correlation_controller() -> CorrelationController:
    global _corr_controller
    if _corr_controller is None:
        _corr_controller = CorrelationController()
    return _corr_controller

def get_currency_manager() -> CurrencyExposureManager:
    global _currency_manager
    if _currency_manager is None:
        _currency_manager = CurrencyExposureManager()
    return _currency_manager

def get_performance_tracker() -> StrategyPerformanceTracker:
    global _perf_tracker
    if _perf_tracker is None:
        _perf_tracker = StrategyPerformanceTracker()
    return _perf_tracker

def get_portfolio_manager() -> PortfolioManager:
    global _portfolio_mgr
    if _portfolio_mgr is None:
        _portfolio_mgr = PortfolioManager()
    return _portfolio_mgr
