"""Short-Term Mean Reversion — 2-5 day reversion after extreme move"""
import pandas as pd
import numpy as np
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class ShortTermMeanReversionStrategy(BaseStrategy):
    name = "short_term_mean_reversion"
    display_name = "Short-Term Mean Reversion"
    category = "mean_reversion"
    description = "Buys after 3+ consecutive down bars, sells after 3+ consecutive up bars. High win rate, small edges."
    default_params = {"consecutive_bars": 3, "min_move_atr": 1.0, "atr_sl": 0.8, "atr_tp": 1.2}

    def generate_signal(self, df, current_price):
        p = self.params
        if len(df) < 20:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="Insufficient data")
        atr = ind.atr(df["high"], df["low"], df["close"], 14).iloc[-1]
        closes = df["close"].values
        n = p["consecutive_bars"]
        total_move = abs(closes[-1] - closes[-n-1])
        if total_move < atr * p["min_move_atr"]:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="Move too small")
        all_down = all(closes[-(i+1)] < closes[-(i+2)] for i in range(n))
        all_up   = all(closes[-(i+1)] > closes[-(i+2)] for i in range(n))
        strength = min(0.55 + (n - 3) * 0.1, 0.85)
        if all_down:
            return StrategySignal(name=self.name, action=SignalAction.BUY, strength=strength,
                entry=current_price, stop_loss=current_price - atr * p["atr_sl"],
                take_profit=current_price + atr * p["atr_tp"],
                reason=f"{n} consecutive down bars — mean reversion BUY")
        if all_up:
            return StrategySignal(name=self.name, action=SignalAction.SELL, strength=strength,
                entry=current_price, stop_loss=current_price + atr * p["atr_sl"],
                take_profit=current_price - atr * p["atr_tp"],
                reason=f"{n} consecutive up bars — mean reversion SELL")
        return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="No consecutive extreme run")
