"""Dual Momentum — Gary Antonacci: absolute + relative momentum"""
import pandas as pd
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class DualMomentumStrategy(BaseStrategy):
    name = "dual_momentum"
    display_name = "Dual Momentum"
    category = "trend"
    description = "Absolute momentum (vs own history) AND relative momentum must both align. Reduces whipsaw."
    default_params = {"abs_lookback": 12, "rel_lookback": 6, "atr_sl": 2.0, "atr_tp": 4.0}

    def generate_signal(self, df, current_price):
        p = self.params
        if len(df) < p["abs_lookback"] + 5:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="Insufficient data")
        abs_ret = df["close"].iloc[-1] / df["close"].iloc[-p["abs_lookback"]] - 1
        rel_ret = df["close"].iloc[-1] / df["close"].iloc[-p["rel_lookback"]] - 1
        atr = ind.atr(df["high"], df["low"], df["close"], 14).iloc[-1]
        strength = min((abs(abs_ret) + abs(rel_ret)) * 5, 1.0)
        if abs_ret > 0 and rel_ret > 0:
            return StrategySignal(name=self.name, action=SignalAction.BUY, strength=strength,
                entry=current_price, stop_loss=current_price - atr * p["atr_sl"],
                take_profit=current_price + atr * p["atr_tp"],
                reason=f"Dual momentum BULL: abs={abs_ret:.2%} rel={rel_ret:.2%}")
        if abs_ret < 0 and rel_ret < 0:
            return StrategySignal(name=self.name, action=SignalAction.SELL, strength=strength,
                entry=current_price, stop_loss=current_price + atr * p["atr_sl"],
                take_profit=current_price - atr * p["atr_tp"],
                reason=f"Dual momentum BEAR: abs={abs_ret:.2%} rel={rel_ret:.2%}")
        return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="Momentum signals conflict")
