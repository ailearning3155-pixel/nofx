"""Session Breakout — London/NY/Asian killzones"""
import pandas as pd
from datetime import time
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class SessionBreakoutStrategy(BaseStrategy):
    name = "session_breakout"
    display_name = "Session Breakout (London/NY)"
    category = "scalping"
    description = "Trades breakouts at London open (08:00 UTC) and NY killzone (13:00 UTC). High-probability entries."
    default_params = {"range_bars": 20, "atr_sl": 0.8, "atr_tp": 2.0}

    def generate_signal(self, df, current_price):
        p = self.params
        if len(df) < p["range_bars"] + 5:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="Insufficient data")
        try:
            last_time = pd.to_datetime(df["time"].iloc[-1])
            hour = last_time.hour
            is_london = 7 <= hour <= 10
            is_ny     = 13 <= hour <= 16
            if not (is_london or is_ny):
                return StrategySignal(name=self.name, action=SignalAction.HOLD, reason=f"Not in killzone (hour={hour})")
        except Exception:
            pass  # If no time data, still run on structure
        range_high = df["high"].iloc[-(p["range_bars"]+1):-1].max()
        range_low  = df["low"].iloc[-(p["range_bars"]+1):-1].min()
        curr_close = df["close"].iloc[-1]
        prev_close = df["close"].iloc[-2]
        atr = ind.atr(df["high"], df["low"], df["close"], 14).iloc[-1]
        if prev_close <= range_high and curr_close > range_high:
            return StrategySignal(name=self.name, action=SignalAction.BUY, strength=0.78,
                entry=current_price, stop_loss=range_low, take_profit=current_price + atr * p["atr_tp"],
                reason=f"Session breakout UP above {range_high:.5f}")
        if prev_close >= range_low and curr_close < range_low:
            return StrategySignal(name=self.name, action=SignalAction.SELL, strength=0.78,
                entry=current_price, stop_loss=range_high, take_profit=current_price - atr * p["atr_tp"],
                reason=f"Session breakout DOWN below {range_low:.5f}")
        return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="Inside session range")
