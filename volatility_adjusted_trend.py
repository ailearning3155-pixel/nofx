"""Volatility-Adjusted Trend Following"""
import pandas as pd
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class VolatilityAdjustedTrendStrategy(BaseStrategy):
    name = "volatility_adjusted_trend"
    display_name = "Volatility Adjusted Trend"
    category = "trend"
    description = "EMA cross filtered by vol regime. Stronger signal weight in low-vol trending markets."
    default_params = {"fast_ema": 10, "slow_ema": 30, "vol_period": 20, "vol_threshold": 0.015}

    def generate_signal(self, df, current_price):
        p = self.params
        if len(df) < p["slow_ema"] + p["vol_period"]:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="Insufficient data")
        fast = ind.ema(df["close"], p["fast_ema"])
        slow = ind.ema(df["close"], p["slow_ema"])
        vol  = df["close"].pct_change().rolling(p["vol_period"]).std().iloc[-1]
        atr  = ind.atr(df["high"], df["low"], df["close"], 14).iloc[-1]
        strength = 0.82 if vol < p["vol_threshold"] else 0.58
        if fast.iloc[-2] <= slow.iloc[-2] and fast.iloc[-1] > slow.iloc[-1]:
            return StrategySignal(name=self.name, action=SignalAction.BUY, strength=strength,
                entry=current_price, stop_loss=current_price - atr * 1.5, take_profit=current_price + atr * 3.0,
                reason=f"Vol-adj golden cross | vol={vol:.4f}")
        if fast.iloc[-2] >= slow.iloc[-2] and fast.iloc[-1] < slow.iloc[-1]:
            return StrategySignal(name=self.name, action=SignalAction.SELL, strength=strength,
                entry=current_price, stop_loss=current_price + atr * 1.5, take_profit=current_price - atr * 3.0,
                reason=f"Vol-adj death cross | vol={vol:.4f}")
        return StrategySignal(name=self.name, action=SignalAction.HOLD, reason=f"No cross | vol={vol:.4f}")
