"""Adaptive Momentum — dynamic lookback based on volatility regime"""
import pandas as pd
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class AdaptiveMomentumStrategy(BaseStrategy):
    name = "adaptive_momentum"
    display_name = "Adaptive Momentum"
    category = "trend"
    description = "Short lookback in high-vol, long lookback in low-vol. Self-calibrating momentum."
    default_params = {"min_lookback": 5, "max_lookback": 30, "vol_period": 20}

    def generate_signal(self, df, current_price):
        p = self.params
        if len(df) < p["max_lookback"] + 55:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="Insufficient data")
        ret_series = df["close"].pct_change()
        vol = ret_series.rolling(p["vol_period"]).std()
        vol_min = vol.rolling(50).min().iloc[-1]
        vol_max = vol.rolling(50).max().iloc[-1]
        vol_cur = vol.iloc[-1]
        vol_pct = (vol_cur - vol_min) / (vol_max - vol_min + 1e-8)
        lookback = int(p["min_lookback"] + (1 - vol_pct) * (p["max_lookback"] - p["min_lookback"]))
        lookback = max(p["min_lookback"], min(p["max_lookback"], lookback))
        ret = df["close"].iloc[-1] / df["close"].iloc[-lookback] - 1
        atr = ind.atr(df["high"], df["low"], df["close"], 14).iloc[-1]
        strength = min(abs(ret) * 10, 1.0)
        if ret > 0.002:
            return StrategySignal(name=self.name, action=SignalAction.BUY, strength=strength,
                entry=current_price, stop_loss=current_price - atr * 1.5, take_profit=current_price + atr * 3.0,
                reason=f"Adaptive BUY lb={lookback} ret={ret:.3%}")
        if ret < -0.002:
            return StrategySignal(name=self.name, action=SignalAction.SELL, strength=strength,
                entry=current_price, stop_loss=current_price + atr * 1.5, take_profit=current_price - atr * 3.0,
                reason=f"Adaptive SELL lb={lookback} ret={ret:.3%}")
        return StrategySignal(name=self.name, action=SignalAction.HOLD, reason=f"Signal weak ({ret:.3%})")
