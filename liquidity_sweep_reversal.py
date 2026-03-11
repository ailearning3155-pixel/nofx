"""Liquidity Sweep Reversal — ICT/SMC stop hunt detection"""
import pandas as pd
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class LiquiditySweepReversalStrategy(BaseStrategy):
    name = "liquidity_sweep_reversal"
    display_name = "Liquidity Sweep Reversal"
    category = "scalping"
    description = "Detects stop hunt wicks beyond swing highs/lows, then trades the reversal. ICT Smart Money Concept."
    default_params = {"swing_lookback": 15, "wick_atr": 0.5, "atr_sl": 0.8, "atr_tp": 2.0}

    def generate_signal(self, df, current_price):
        p = self.params
        if len(df) < p["swing_lookback"] + 5:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="Insufficient data")
        lb = p["swing_lookback"]
        swing_high = df["high"].iloc[-(lb+1):-1].max()
        swing_low  = df["low"].iloc[-(lb+1):-1].min()
        last = df.iloc[-1]
        atr = ind.atr(df["high"], df["low"], df["close"], 14).iloc[-1]
        wick_up   = last["high"] - max(last["open"], last["close"])
        wick_down = min(last["open"], last["close"]) - last["low"]
        # Bearish sweep: wick above swing high, closes back below
        if last["high"] > swing_high and wick_up > atr * p["wick_atr"] and last["close"] < swing_high:
            return StrategySignal(name=self.name, action=SignalAction.SELL, strength=0.80,
                entry=current_price, stop_loss=last["high"] + atr * 0.3,
                take_profit=current_price - atr * p["atr_tp"],
                reason=f"Liquidity sweep ABOVE {swing_high:.5f} — reversal SELL")
        # Bullish sweep: wick below swing low, closes back above
        if last["low"] < swing_low and wick_down > atr * p["wick_atr"] and last["close"] > swing_low:
            return StrategySignal(name=self.name, action=SignalAction.BUY, strength=0.80,
                entry=current_price, stop_loss=last["low"] - atr * 0.3,
                take_profit=current_price + atr * p["atr_tp"],
                reason=f"Liquidity sweep BELOW {swing_low:.5f} — reversal BUY")
        return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="No liquidity sweep detected")
