"""Time-Series Momentum — Renaissance Technologies core approach"""
import pandas as pd
import numpy as np
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class TimeSeriesMomentumStrategy(BaseStrategy):
    name = "time_series_momentum"
    display_name = "Time-Series Momentum"
    category = "trend"
    description = "Vol-adjusted N-period return signal. If positive return → long. Core quant hedge fund technique."
    default_params = {"lookback": 20, "vol_lookback": 10, "atr_sl": 1.5, "atr_tp": 3.0}

    def generate_signal(self, df, current_price):
        p = self.params
        if len(df) < p["lookback"] + 5:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="Insufficient data")
        returns = df["close"].pct_change().dropna()
        lookback_return = df["close"].iloc[-1] / df["close"].iloc[-p["lookback"]] - 1
        vol = returns.iloc[-p["vol_lookback"]:].std() * (252 ** 0.5)
        vol_adj = lookback_return / (vol + 1e-8)
        atr = ind.atr(df["high"], df["low"], df["close"], 14).iloc[-1]
        strength = min(abs(vol_adj) / 2, 1.0)
        if vol_adj > 0.1:
            return StrategySignal(name=self.name, action=SignalAction.BUY, strength=strength,
                entry=current_price, stop_loss=current_price - atr * p["atr_sl"],
                take_profit=current_price + atr * p["atr_tp"],
                reason=f"TSM BUY: {p['lookback']}d={lookback_return:.2%} vol-adj={vol_adj:.2f}")
        if vol_adj < -0.1:
            return StrategySignal(name=self.name, action=SignalAction.SELL, strength=strength,
                entry=current_price, stop_loss=current_price + atr * p["atr_sl"],
                take_profit=current_price - atr * p["atr_tp"],
                reason=f"TSM SELL: {p['lookback']}d={lookback_return:.2%} vol-adj={vol_adj:.2f}")
        return StrategySignal(name=self.name, action=SignalAction.HOLD, reason=f"TSM weak ({vol_adj:.3f})")
