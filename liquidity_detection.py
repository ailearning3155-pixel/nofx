"""Liquidity Detection — find and trade liquidity pool sweeps"""
import pandas as pd
import numpy as np
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class LiquidityDetectionStrategy(BaseStrategy):
    name = "liquidity_detection"
    display_name = "Liquidity Detection"
    category = "microstructure"
    description = "Identifies equal highs/lows (liquidity pools) and trades the sweep-and-reverse. Citadel-style."
    default_params = {"lookback": 30, "equal_threshold_atr": 0.3, "atr_sl": 0.8, "atr_tp": 2.5}

    def generate_signal(self, df: pd.DataFrame, current_price: float) -> StrategySignal:
        p = self.params
        if len(df) < p["lookback"]:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="Not enough data")
        atr = ind.atr(df["high"], df["low"], df["close"], 14).iloc[-1]
        tol = atr * p["equal_threshold_atr"]
        window = df.iloc[-p["lookback"]:-1]
        curr   = df.iloc[-1]
        # Equal highs (short-side liquidity above)
        near_highs = window[abs(window["high"] - window["high"].max()) < tol]
        # Equal lows (long-side liquidity below)
        near_lows  = window[abs(window["low"]  - window["low"].min())  < tol]
        sweep_high = len(near_highs) >= 2 and curr["high"] > window["high"].max() and curr["close"] < window["high"].max()
        sweep_low  = len(near_lows)  >= 2 and curr["low"]  < window["low"].min()  and curr["close"] > window["low"].min()
        if sweep_low:
            return StrategySignal(name=self.name, action=SignalAction.BUY, strength=0.78,
                entry=current_price, stop_loss=curr["low"] - atr * p["atr_sl"],
                take_profit=current_price + atr * p["atr_tp"],
                reason=f"Liquidity sweep below equal lows at {window['low'].min():.5f}")
        if sweep_high:
            return StrategySignal(name=self.name, action=SignalAction.SELL, strength=0.78,
                entry=current_price, stop_loss=curr["high"] + atr * p["atr_sl"],
                take_profit=current_price - atr * p["atr_tp"],
                reason=f"Liquidity sweep above equal highs at {window['high'].max():.5f}")
        return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="No liquidity sweep")
