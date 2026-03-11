"""Z-Score Pairs (single instrument version using synthetic spread)"""
import pandas as pd
import numpy as np
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class ZScorePairsStrategy(BaseStrategy):
    name = "zscore_pairs"
    display_name = "Z-Score Pairs / Stat Arb"
    category = "stat_arb"
    description = "Statistical arbitrage using rolling z-score of price vs its EMA fair value. Two Sigma style."
    default_params = {"window": 40, "z_entry": 2.0, "z_exit": 0.5, "atr_sl": 1.5, "atr_tp": 2.5}

    def generate_signal(self, df: pd.DataFrame, current_price: float) -> StrategySignal:
        p = self.params
        if len(df) < p["window"] + 5:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="Not enough data")
        close = df["close"]
        fair_value = ind.ema(close, p["window"])
        spread = close - fair_value
        rolling_mean = spread.rolling(p["window"]).mean()
        rolling_std  = spread.rolling(p["window"]).std()
        zscore = (spread - rolling_mean) / (rolling_std + 1e-8)
        z_now  = zscore.iloc[-1]
        z_prev = zscore.iloc[-2]
        atr    = ind.atr(df["high"], df["low"], close, 14).iloc[-1]
        if z_prev <= -p["z_entry"] and z_now > z_prev:
            return StrategySignal(name=self.name, action=SignalAction.BUY,
                strength=min(abs(z_now) / 3, 1.0), entry=current_price,
                stop_loss=current_price - atr * p["atr_sl"],
                take_profit=float(fair_value.iloc[-1]),
                reason=f"Stat arb: z={z_now:.2f} reverting from oversold vs EMA")
        if z_prev >= p["z_entry"] and z_now < z_prev:
            return StrategySignal(name=self.name, action=SignalAction.SELL,
                strength=min(abs(z_now) / 3, 1.0), entry=current_price,
                stop_loss=current_price + atr * p["atr_sl"],
                take_profit=float(fair_value.iloc[-1]),
                reason=f"Stat arb: z={z_now:.2f} reverting from overbought vs EMA")
        return StrategySignal(name=self.name, action=SignalAction.HOLD, reason=f"Z={z_now:.2f} within range")
