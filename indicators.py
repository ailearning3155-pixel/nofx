"""
APEX — Indicator Compatibility Layer
Tries pandas_ta first (more features), falls back to 'ta' package.
Both are installed: pandas_ta via  pip install pandas-ta==0.3.14b0
                   ta via          pip install ta

Usage in strategies:
    from core.indicators import ind
    rsi = ind.rsi(df["close"], 14)
    ema = ind.ema(df["close"], 9)
    atr = ind.atr(df["high"], df["low"], df["close"], 14)
    macd_df = ind.macd(df["close"])   # returns DataFrame
"""
import pandas as pd
import numpy as np
from typing import Optional

try:
    import pandas_ta as _pta
    _USE_PTA = True
except ImportError:
    _USE_PTA = False

try:
    import ta as _ta
    _USE_TA = True
except ImportError:
    _USE_TA = False


class Indicators:
    """Unified indicator interface — works with either pandas_ta or ta package."""

    # ── RSI ──
    def rsi(self, close: pd.Series, period: int = 14) -> pd.Series:
        if _USE_PTA:
            return _pta.rsi(close, length=period)
        if _USE_TA:
            return _ta.momentum.RSIIndicator(close, window=period).rsi()
        return self._rsi_manual(close, period)

    # ── EMA ──
    def ema(self, close: pd.Series, period: int) -> pd.Series:
        if _USE_PTA:
            return _pta.ema(close, length=period)
        return close.ewm(span=period, adjust=False).mean()

    # ── SMA ──
    def sma(self, close: pd.Series, period: int) -> pd.Series:
        return close.rolling(window=period).mean()

    # ── ATR ──
    def atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        if _USE_PTA:
            return _pta.atr(high, low, close, length=period)
        if _USE_TA:
            return _ta.volatility.AverageTrueRange(high, low, close, window=period).average_true_range()
        return self._atr_manual(high, low, close, period)

    # ── MACD ──
    def macd(self, close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """Returns DataFrame with columns: macd, signal, histogram"""
        if _USE_PTA:
            result = _pta.macd(close, fast=fast, slow=slow, signal=signal)
            result.columns = ["macd", "histogram", "signal"]
            return result
        if _USE_TA:
            ind = _ta.trend.MACD(close, window_slow=slow, window_fast=fast, window_sign=signal)
            return pd.DataFrame({
                "macd":      ind.macd(),
                "signal":    ind.macd_signal(),
                "histogram": ind.macd_diff(),
            })
        return self._macd_manual(close, fast, slow, signal)

    # ── Bollinger Bands ──
    def bbands(self, close: pd.Series, period: int = 20, std: float = 2.0) -> pd.DataFrame:
        """Returns DataFrame with: upper, mid, lower, bandwidth, percent"""
        if _USE_PTA:
            result = _pta.bbands(close, length=period, std=std)
            return pd.DataFrame({
                "lower":     result.iloc[:, 0],
                "mid":       result.iloc[:, 1],
                "upper":     result.iloc[:, 2],
                "bandwidth": result.iloc[:, 3],
                "percent":   result.iloc[:, 4],
            })
        mid = close.rolling(period).mean()
        std_series = close.rolling(period).std()
        upper = mid + std * std_series
        lower = mid - std * std_series
        return pd.DataFrame({"upper": upper, "mid": mid, "lower": lower,
                              "bandwidth": (upper - lower) / mid,
                              "percent": (close - lower) / (upper - lower)})

    # ── Stochastic ──
    def stoch(self, high: pd.Series, low: pd.Series, close: pd.Series,
              k: int = 14, d: int = 3) -> pd.DataFrame:
        if _USE_PTA:
            result = _pta.stoch(high, low, close, k=k, d=d)
            return pd.DataFrame({"k": result.iloc[:, 0], "d": result.iloc[:, 1]})
        if _USE_TA:
            ind = _ta.momentum.StochasticOscillator(high, low, close, window=k, smooth_window=d)
            return pd.DataFrame({"k": ind.stoch(), "d": ind.stoch_signal()})
        lowest_low   = low.rolling(k).min()
        highest_high = high.rolling(k).max()
        k_line = 100 * (close - lowest_low) / (highest_high - lowest_low)
        d_line = k_line.rolling(d).mean()
        return pd.DataFrame({"k": k_line, "d": d_line})

    # ── ADX ──
    def adx(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        if _USE_PTA:
            result = _pta.adx(high, low, close, length=period)
            return result.iloc[:, 0]
        if _USE_TA:
            return _ta.trend.ADXIndicator(high, low, close, window=period).adx()
        return pd.Series(np.nan, index=close.index)

    # ── VWAP ──
    def vwap(self, high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
        if _USE_PTA:
            return _pta.vwap(high, low, close, volume)
        typical_price = (high + low + close) / 3
        return (typical_price * volume).cumsum() / volume.cumsum()

    # ── Supertrend ──
    def supertrend(self, high: pd.Series, low: pd.Series, close: pd.Series,
                   period: int = 10, multiplier: float = 3.0) -> pd.DataFrame:
        """Returns DataFrame with: supertrend, direction (1=up, -1=down)"""
        if _USE_PTA:
            result = _pta.supertrend(high, low, close, length=period, multiplier=multiplier)
            return pd.DataFrame({
                "supertrend": result.iloc[:, 0],
                "direction":  result.iloc[:, 1],
            })
        # Manual implementation
        atr = self.atr(high, low, close, period)
        hl2 = (high + low) / 2
        upper_band = hl2 + multiplier * atr
        lower_band = hl2 - multiplier * atr
        supertrend = pd.Series(index=close.index, dtype=float)
        direction  = pd.Series(index=close.index, dtype=float)
        for i in range(1, len(close)):
            if close.iloc[i] > upper_band.iloc[i - 1]:
                direction.iloc[i] = 1
                supertrend.iloc[i] = lower_band.iloc[i]
            elif close.iloc[i] < lower_band.iloc[i - 1]:
                direction.iloc[i] = -1
                supertrend.iloc[i] = upper_band.iloc[i]
            else:
                direction.iloc[i] = direction.iloc[i - 1]
                supertrend.iloc[i] = supertrend.iloc[i - 1]
        return pd.DataFrame({"supertrend": supertrend, "direction": direction})

    # ── Manual fallbacks ──
    def _rsi_manual(self, close: pd.Series, period: int) -> pd.Series:
        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(period).mean()
        loss  = (-delta.clip(upper=0)).rolling(period).mean()
        rs    = gain / loss.replace(0, np.finfo(float).eps)
        return 100 - (100 / (1 + rs))

    def _atr_manual(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low  - prev_close).abs(),
        ], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    def _macd_manual(self, close: pd.Series, fast: int, slow: int, signal: int) -> pd.DataFrame:
        ema_fast  = close.ewm(span=fast,   adjust=False).mean()
        ema_slow  = close.ewm(span=slow,   adjust=False).mean()
        macd_line = ema_fast - ema_slow
        sig_line  = macd_line.ewm(span=signal, adjust=False).mean()
        return pd.DataFrame({
            "macd":      macd_line,
            "signal":    sig_line,
            "histogram": macd_line - sig_line,
        })


# Singleton — import this everywhere
ind = Indicators()
