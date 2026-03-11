"""Order Block + Liquidity Sweep — highest confluence ICT entry"""
import pandas as pd
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class OBLiquiditySweepStrategy(BaseStrategy):
    name = "ob_liquidity_sweep"
    display_name = "Order Block + Liquidity Sweep"
    category = "composite"
    description = "Liquidity sweep into an order block zone. The highest confluence SMC entry available."
    default_params = {"swing_lb": 15, "ob_lookback": 30, "impulse_atr": 1.5, "atr_sl": 0.8, "atr_tp": 3.0}

    def generate_signal(self, df, current_price):
        p = self.params
        if len(df) < 40:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="Insufficient data")
        atr = ind.atr(df["high"], df["low"], df["close"], 14).iloc[-1]
        close = df["close"].iloc[-1]
        lb = p["swing_lb"]
        swing_low  = df["low"].iloc[-(lb+1):-1].min()
        swing_high = df["high"].iloc[-(lb+1):-1].max()
        last = df.iloc[-1]
        swept_low  = last["low"] < swing_low and last["close"] > swing_low
        swept_high = last["high"] > swing_high and last["close"] < swing_high
        if not swept_low and not swept_high:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="No liquidity sweep")
        lookback = min(p["ob_lookback"], len(df) - 3)
        for i in range(3, lookback):
            c1 = df.iloc[-i]
            c2 = df.iloc[-(i-1)]
            impulse = abs(c2["close"] - c2["open"])
            if swept_low and c1["close"] < c1["open"] and c2["close"] > c2["open"] and impulse > atr * p["impulse_atr"]:
                if c1["low"] <= close <= c1["high"]:
                    return StrategySignal(name=self.name, action=SignalAction.BUY, strength=0.88,
                        entry=current_price, stop_loss=last["low"] - atr * 0.3,
                        take_profit=current_price + atr * p["atr_tp"],
                        reason=f"Sweep+OB confluence BUY at {close:.5f}")
            if swept_high and c1["close"] > c1["open"] and c2["close"] < c2["open"] and impulse > atr * p["impulse_atr"]:
                if c1["low"] <= close <= c1["high"]:
                    return StrategySignal(name=self.name, action=SignalAction.SELL, strength=0.88,
                        entry=current_price, stop_loss=last["high"] + atr * 0.3,
                        take_profit=current_price - atr * p["atr_tp"],
                        reason=f"Sweep+OB confluence SELL at {close:.5f}")
        return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="Sweep found but no OB")
