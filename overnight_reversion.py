"""Overnight Gap Reversion — gaps tend to fill within the session"""
import pandas as pd
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class OvernightReversionStrategy(BaseStrategy):
    name = "overnight_reversion"
    display_name = "Overnight Reversion"
    category = "mean_reversion"
    description = "Trades gap fills: if open gaps up from prev close, short expecting fill. Vice versa for gap down."
    default_params = {"min_gap_pct": 0.001, "atr_sl": 1.0, "atr_tp": 1.5}

    def generate_signal(self, df, current_price):
        p = self.params
        if len(df) < 3:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="Insufficient data")
        prev_close = df["close"].iloc[-2]
        curr_open  = df["open"].iloc[-1]
        gap_pct = (curr_open - prev_close) / prev_close
        atr = ind.atr(df["high"], df["low"], df["close"], 14).iloc[-1]
        strength = min(abs(gap_pct) / 0.005, 1.0)
        if gap_pct > p["min_gap_pct"]:
            return StrategySignal(name=self.name, action=SignalAction.SELL, strength=strength,
                entry=current_price, stop_loss=current_price + atr * p["atr_sl"],
                take_profit=prev_close,
                reason=f"Gap UP {gap_pct:.3%} — short for gap fill to {prev_close:.5f}")
        if gap_pct < -p["min_gap_pct"]:
            return StrategySignal(name=self.name, action=SignalAction.BUY, strength=strength,
                entry=current_price, stop_loss=current_price - atr * p["atr_sl"],
                take_profit=prev_close,
                reason=f"Gap DOWN {gap_pct:.3%} — long for gap fill to {prev_close:.5f}")
        return StrategySignal(name=self.name, action=SignalAction.HOLD, reason=f"Gap too small ({gap_pct:.4%})")
