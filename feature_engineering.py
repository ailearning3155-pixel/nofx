"""
APEX — Feature Engineering Layer
Calculates a comprehensive set of technical features from OHLCV data.
Used by ML models and the signal combiner for enriched decision-making.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from typing import List, Optional
from loguru import logger

from core.indicators import ind


class FeatureEngineer:
    """
    Builds a feature matrix from raw OHLCV bars.
    All features are normalised / stationary where possible.

    Feature categories:
    - Momentum (returns at multiple lookbacks)
    - Trend (EMA distances, ADX)
    - Volatility (ATR, BB width, realised vol)
    - Oscillators (RSI, Stochastic, CCI)
    - Volume / microstructure (if volume available)
    - Candle patterns (body ratio, upper/lower shadow)
    - Regime (Hurst, vol ratio)
    """

    def __init__(self, include_volume: bool = False):
        self.include_volume = include_volume

    def build(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Build feature DataFrame from OHLCV.
        Returns aligned DataFrame — rows with NaN are dropped.
        """
        if len(df) < 50:
            logger.warning("FeatureEngineer: need ≥ 50 bars")
            return pd.DataFrame()

        f = pd.DataFrame(index=df.index)
        c = df["close"]
        h = df["high"]
        l = df["low"]
        o = df["open"]

        # ── Momentum / Returns ────────────────────────────────────────────
        for n in [1, 2, 3, 5, 8, 13, 21]:
            f[f"ret_{n}"]    = c.pct_change(n)
            f[f"log_ret_{n}"] = np.log(c / c.shift(n))

        # ── EMA distances (trend bias) ────────────────────────────────────
        for period in [9, 21, 50, 100, 200]:
            ema = ind.ema(c, period)
            f[f"ema{period}_dist"] = (c - ema) / (ema + 1e-10)

        # EMA slopes
        for period in [9, 21, 50]:
            ema = ind.ema(c, period)
            f[f"ema{period}_slope"] = ema.pct_change(3)

        # EMA crossovers (binary + distance)
        ema9  = ind.ema(c, 9)
        ema21 = ind.ema(c, 21)
        ema50 = ind.ema(c, 50)
        f["ema_9_21_cross"]  = (ema9  - ema21) / (ema21 + 1e-10)
        f["ema_21_50_cross"] = (ema21 - ema50) / (ema50 + 1e-10)

        # ── Volatility ────────────────────────────────────────────────────
        atr14 = ind.atr(h, l, c, 14)
        atr7  = ind.atr(h, l, c, 7)
        f["atr14_norm"]  = atr14 / (c + 1e-10)
        f["atr7_norm"]   = atr7  / (c + 1e-10)
        f["atr_ratio"]   = atr7  / (atr14 + 1e-10)   # short vs long vol

        # Realised volatility (rolling std of returns)
        for n in [5, 10, 20]:
            f[f"realvol_{n}"] = c.pct_change().rolling(n).std()

        # Volatility regime change
        f["vol_change"] = f["realvol_5"] / (f["realvol_20"] + 1e-10)

        # ── Bollinger Bands ───────────────────────────────────────────────
        bb = ind.bbands(c, 20, 2.0)
        f["bb_pct"]       = bb["percent"]
        f["bb_width"]     = bb["bandwidth"]
        f["bb_squeeze"]   = (bb["bandwidth"] < bb["bandwidth"].rolling(50).mean()).astype(float)

        # ── RSI family ───────────────────────────────────────────────────
        f["rsi14"]   = ind.rsi(c, 14) / 100.0
        f["rsi7"]    = ind.rsi(c, 7)  / 100.0
        f["rsi28"]   = ind.rsi(c, 28) / 100.0
        f["rsi_diverge"] = f["rsi14"] - f["rsi7"]

        # RSI extremes
        f["rsi_overbought"]  = (f["rsi14"] > 0.70).astype(float)
        f["rsi_oversold"]    = (f["rsi14"] < 0.30).astype(float)

        # ── Stochastic ────────────────────────────────────────────────────
        try:
            stoch = ind.stoch(h, l, c, 14, 3)
            f["stoch_k"] = stoch["k"] / 100.0
            f["stoch_d"] = stoch["d"] / 100.0
        except Exception:
            f["stoch_k"] = 0.5
            f["stoch_d"] = 0.5

        # ── MACD ─────────────────────────────────────────────────────────
        try:
            macd_df = ind.macd(c, 12, 26, 9)
            f["macd"]      = macd_df["macd"]
            f["macd_sig"]  = macd_df["signal"]
            f["macd_hist"] = macd_df["histogram"]
            f["macd_cross"] = (macd_df["macd"] - macd_df["signal"]) / (c + 1e-10)
        except Exception:
            f["macd"] = 0.0
            f["macd_sig"] = 0.0
            f["macd_hist"] = 0.0
            f["macd_cross"] = 0.0

        # ── Candle patterns ───────────────────────────────────────────────
        candle_range = (h - l).replace(0, 1e-10)
        f["body_ratio"]   = (c - o).abs() / candle_range
        f["upper_shadow"]  = (h - pd.concat([c, o], axis=1).max(axis=1)) / candle_range
        f["lower_shadow"]  = (pd.concat([c, o], axis=1).min(axis=1) - l) / candle_range
        f["bullish_candle"] = (c > o).astype(float)

        # Consecutive candles in same direction
        f["consec_bull"] = (c > o).astype(int).groupby(
            ((c > o) != (c > o).shift()).cumsum()
        ).cumcount()
        f["consec_bear"] = (c <= o).astype(int).groupby(
            ((c <= o) != (c <= o).shift()).cumsum()
        ).cumcount()

        # ── Support / Resistance proximity ────────────────────────────────
        for n in [10, 20, 50]:
            recent_high = h.rolling(n).max()
            recent_low  = l.rolling(n).min()
            f[f"dist_high_{n}"] = (c - recent_high) / (recent_high + 1e-10)
            f[f"dist_low_{n}"]  = (c - recent_low)  / (recent_low  + 1e-10)

        # ── Volume (if available) ─────────────────────────────────────────
        if self.include_volume and "volume" in df.columns:
            vol = df["volume"].replace(0, 1).astype(float)
            f["vol_ratio_5"]  = vol / vol.rolling(5).mean()
            f["vol_ratio_20"] = vol / vol.rolling(20).mean()
            f["vol_spike"]    = (f["vol_ratio_5"] > 2.0).astype(float)

        # ── Hurst proxy (rolling autocorrelation) ────────────────────────
        for lag in [1, 5]:
            f[f"autocorr_{lag}"] = c.pct_change().rolling(20).apply(
                lambda x: x.autocorr(lag=lag) if len(x) >= lag + 1 else 0.0,
                raw=False,
            )

        # ── Hour of day / session (if datetime index) ─────────────────────
        if hasattr(df.index, "hour"):
            f["hour_sin"] = np.sin(2 * np.pi * df.index.hour / 24)
            f["hour_cos"] = np.cos(2 * np.pi * df.index.hour / 24)
            # London = 7-16 UTC, NY = 13-21 UTC
            f["london_session"] = ((df.index.hour >= 7) & (df.index.hour < 16)).astype(float)
            f["ny_session"]     = ((df.index.hour >= 13) & (df.index.hour < 21)).astype(float)
            f["overlap_session"] = ((df.index.hour >= 13) & (df.index.hour < 16)).astype(float)

        # ── Clip extreme values ───────────────────────────────────────────
        for col in f.columns:
            if f[col].dtype in [np.float64, np.float32]:
                f[col] = f[col].clip(-5.0, 5.0)

        return f.dropna()

    def get_feature_names(self) -> List[str]:
        """Return feature names (build on dummy data)."""
        dummy = pd.DataFrame({
            "open":  [1.0] * 100,
            "high":  [1.01] * 100,
            "low":   [0.99] * 100,
            "close": np.linspace(1.0, 1.05, 100),
            "volume": [1000] * 100,
        })
        return list(self.build(dummy).columns)


# Module singleton
_engineer: Optional[FeatureEngineer] = None

def get_feature_engineer(include_volume: bool = False) -> FeatureEngineer:
    global _engineer
    if _engineer is None:
        _engineer = FeatureEngineer(include_volume=include_volume)
    return _engineer
