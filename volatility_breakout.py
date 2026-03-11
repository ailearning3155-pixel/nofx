"""Volatility Breakout — trade explosive vol expansion"""
import pandas as pd
import numpy as np
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class VolatilityBreakoutStrategy(BaseStrategy):
    name = "volatility_breakout"
    display_name = "Volatility Breakout"
    category = "volatility"
    description = "Trades when current ATR is 2x above its moving average — volatility expansion signal."
    default_params = {"atr_period": 14, "atr_ma_period": 50, "atr_mult": 1.8, "sl_atr": 1.0, "tp_atr": 2.5}

    def generate_signal(self, df, current_price):
        p = self.params
        if len(df) < p["atr_ma_period"] + p["atr_period"]:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="Insufficient data")
        atr = ind.atr(df["high"], df["low"], df["close"], p["atr_period"])
        atr_ma = atr.rolling(p["atr_ma_period"]).mean()
        curr_atr = atr.iloc[-1]
        avg_atr  = atr_ma.iloc[-1]
        if pd.isna(avg_atr) or avg_atr == 0:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="ATR MA not ready")
        ratio = curr_atr / avg_atr
        if ratio < p["atr_mult"]:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason=f"Vol ratio {ratio:.2f} < {p['atr_mult']}")
        # Direction from last bar
        last = df.iloc[-1]
        is_bull = last["close"] > last["open"]
        strength = min(0.5 + (ratio - p["atr_mult"]) / 2, 1.0)
        if is_bull:
            return StrategySignal(name=self.name, action=SignalAction.BUY, strength=strength,
                entry=current_price, stop_loss=current_price - curr_atr * p["sl_atr"],
                take_profit=current_price + curr_atr * p["tp_atr"],
                reason=f"Vol breakout BULL: ATR={curr_atr:.5f} ({ratio:.1f}x avg)")
        return StrategySignal(name=self.name, action=SignalAction.SELL, strength=strength,
            entry=current_price, stop_loss=current_price + curr_atr * p["sl_atr"],
            take_profit=current_price - curr_atr * p["tp_atr"],
            reason=f"Vol breakout BEAR: ATR={curr_atr:.5f} ({ratio:.1f}x avg)")
