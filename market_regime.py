"""
APEX — Market Regime Detection
Classifies current market conditions as: TRENDING | RANGING | VOLATILE | BREAKOUT
Strategies only activate in suitable regimes to avoid false signals.
"""
import numpy as np
import pandas as pd
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional
from loguru import logger

from core.indicators import ind


class Regime(str, Enum):
    TRENDING  = "trending"
    RANGING   = "ranging"
    VOLATILE  = "volatile"
    BREAKOUT  = "breakout"
    UNKNOWN   = "unknown"


@dataclass
class RegimeResult:
    regime:     Regime
    confidence: float          # 0.0 – 1.0
    adx:        float = 0.0    # ADX value
    atr_ratio:  float = 0.0    # ATR relative to SMA
    bb_width:   float = 0.0    # Bollinger Band width
    hurst:      float = 0.0    # Hurst exponent (>0.5 = trending, <0.5 = mean-reverting)
    details:    Dict  = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}

    @property
    def is_trending(self) -> bool:
        return self.regime == Regime.TRENDING

    @property
    def is_ranging(self) -> bool:
        return self.regime == Regime.RANGING

    @property
    def is_volatile(self) -> bool:
        return self.regime in (Regime.VOLATILE, Regime.BREAKOUT)

    def allows_strategy(self, category: str) -> bool:
        """Return True if this regime is suitable for the strategy category."""
        rules = {
            Regime.TRENDING:  {"trend", "momentum", "adaptive_momentum", "scalping"},
            Regime.RANGING:   {"mean_reversion", "stat_arb", "microstructure"},
            Regime.VOLATILE:  {"volatility", "scalping", "composite"},
            Regime.BREAKOUT:  {"trend", "volatility", "scalping", "breakout"},
            Regime.UNKNOWN:   {"trend", "mean_reversion", "volatility", "scalping",
                               "stat_arb", "microstructure", "composite", "macro", "ml"},
        }
        allowed = rules.get(self.regime, set())
        return any(cat in category.lower() for cat in allowed) or category == "ml"


class MarketRegimeDetector:
    """
    Detects market regime using multiple indicators:
    - ADX (trend strength)
    - ATR / SMA ratio (volatility normalised)
    - Bollinger Band width (volatility squeeze/expansion)
    - Hurst exponent (mean-reversion vs trend-persistence)
    """

    def __init__(
        self,
        adx_period: int   = 14,
        adx_trend_thresh: float = 25.0,
        adx_range_thresh: float = 20.0,
        atr_period: int   = 14,
        vol_high_thresh: float  = 0.012,   # normalised ATR
        vol_low_thresh:  float  = 0.005,
        hurst_period:    int    = 100,
    ):
        self.adx_period       = adx_period
        self.adx_trend_thresh = adx_trend_thresh
        self.adx_range_thresh = adx_range_thresh
        self.atr_period       = atr_period
        self.vol_high_thresh  = vol_high_thresh
        self.vol_low_thresh   = vol_low_thresh
        self.hurst_period     = hurst_period

    # ── Public API ───────────────────────────────────────────────────────────

    def detect(self, df: pd.DataFrame) -> RegimeResult:
        """
        Classify regime from OHLCV DataFrame.
        Requires at least 100 bars for reliable Hurst estimation.
        """
        if len(df) < max(self.adx_period * 2, 50):
            return RegimeResult(regime=Regime.UNKNOWN, confidence=0.0)

        try:
            adx       = self._calc_adx(df)
            atr_ratio = self._calc_atr_ratio(df)
            bb_width  = self._calc_bb_width(df)
            hurst     = self._calc_hurst(df["close"])

            return self._classify(adx, atr_ratio, bb_width, hurst)
        except Exception as e:
            logger.debug(f"Regime detection error: {e}")
            return RegimeResult(regime=Regime.UNKNOWN, confidence=0.3)

    # ── Private calculations ─────────────────────────────────────────────────

    def _calc_adx(self, df: pd.DataFrame) -> float:
        """Average Directional Index — measures trend strength (not direction)."""
        high, low, close = df["high"], df["low"], df["close"]
        period = self.adx_period

        tr   = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
        atr  = tr.ewm(span=period, adjust=False).mean()

        up   = high - high.shift()
        down = low.shift() - low

        plus_dm  = up.where((up > down) & (up > 0), 0.0)
        minus_dm = down.where((down > up) & (down > 0), 0.0)

        plus_di  = 100 * plus_dm.ewm(span=period, adjust=False).mean()  / (atr + 1e-10)
        minus_di = 100 * minus_dm.ewm(span=period, adjust=False).mean() / (atr + 1e-10)

        dx  = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10)
        adx = dx.ewm(span=period, adjust=False).mean()
        return float(adx.iloc[-1])

    def _calc_atr_ratio(self, df: pd.DataFrame) -> float:
        """ATR normalised by closing price — measures volatility magnitude."""
        atr   = ind.atr(df["high"], df["low"], df["close"], self.atr_period)
        price = df["close"].iloc[-1]
        return float(atr.iloc[-1] / (price + 1e-10))

    def _calc_bb_width(self, df: pd.DataFrame) -> float:
        """Bollinger Band width — squeeze = low volatility, expansion = breakout."""
        bb = ind.bbands(df["close"], 20, 2.0)
        return float(bb["bandwidth"].iloc[-1])

    def _calc_hurst(self, close: pd.Series) -> float:
        """
        Hurst exponent via Rescaled Range (R/S) analysis.
        H > 0.55 → trending (persistent)
        H < 0.45 → mean-reverting
        H ≈ 0.50 → random walk
        """
        series = close.iloc[-self.hurst_period:].values.astype(float)
        if len(series) < 30:
            return 0.5

        lags    = range(2, min(20, len(series) // 4))
        rs_vals = []
        lag_vals = []
        for lag in lags:
            chunks = [series[i: i + lag] for i in range(0, len(series) - lag, lag)]
            rs_chunk = []
            for chunk in chunks:
                if len(chunk) < 2:
                    continue
                mean    = np.mean(chunk)
                std     = np.std(chunk, ddof=1) + 1e-10
                deviate = np.cumsum(chunk - mean)
                rs_chunk.append((deviate.max() - deviate.min()) / std)
            if rs_chunk:
                rs_vals.append(np.log(np.mean(rs_chunk) + 1e-10))
                lag_vals.append(np.log(lag))

        if len(lag_vals) < 2:
            return 0.5

        try:
            hurst = np.polyfit(lag_vals, rs_vals, 1)[0]
            return float(np.clip(hurst, 0.1, 0.9))
        except Exception:
            return 0.5

    def _classify(
        self,
        adx: float,
        atr_ratio: float,
        bb_width: float,
        hurst: float,
    ) -> RegimeResult:
        """Combine signals into a regime label with confidence score."""

        scores = {r: 0.0 for r in Regime}

        # ADX scoring
        if adx >= self.adx_trend_thresh:
            scores[Regime.TRENDING]  += 0.4
        elif adx <= self.adx_range_thresh:
            scores[Regime.RANGING]   += 0.3
        else:
            scores[Regime.RANGING]   += 0.15
            scores[Regime.TRENDING]  += 0.15

        # Volatility scoring
        if atr_ratio >= self.vol_high_thresh:
            scores[Regime.VOLATILE]  += 0.3
            scores[Regime.BREAKOUT]  += 0.2
        elif atr_ratio <= self.vol_low_thresh:
            scores[Regime.RANGING]   += 0.2
            scores[Regime.BREAKOUT]  += 0.1   # squeeze before breakout
        else:
            scores[Regime.TRENDING]  += 0.1
            scores[Regime.RANGING]   += 0.1

        # Hurst scoring
        if hurst >= 0.58:
            scores[Regime.TRENDING]  += 0.3
        elif hurst <= 0.42:
            scores[Regime.RANGING]   += 0.3
        else:
            scores[Regime.TRENDING]  += 0.1
            scores[Regime.RANGING]   += 0.1

        # BB width — squeeze detection
        if bb_width < 0.005:
            scores[Regime.BREAKOUT]  += 0.25

        best_regime = max(scores, key=lambda r: scores[r])
        total       = sum(scores.values()) or 1.0
        confidence  = scores[best_regime] / total

        return RegimeResult(
            regime=best_regime,
            confidence=round(confidence, 3),
            adx=round(adx, 2),
            atr_ratio=round(atr_ratio, 5),
            bb_width=round(bb_width, 5),
            hurst=round(hurst, 3),
            details={r.value: round(v, 3) for r, v in scores.items()},
        )


# Module-level singleton
_detector: Optional[MarketRegimeDetector] = None

def get_regime_detector() -> MarketRegimeDetector:
    global _detector
    if _detector is None:
        _detector = MarketRegimeDetector()
    return _detector
