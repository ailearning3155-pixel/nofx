"""FVG + Market Structure — composite ICT strategy"""
import pandas as pd
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class FVGMarketStructureStrategy(BaseStrategy):
    name = "fvg_market_structure"
    display_name = "FVG + Market Structure"
    category = "composite"
    description = "Fair Value Gap fill confirmed by bullish/bearish market structure. High-confluence SMC entry."
    default_params = {"swing_lb": 10, "fvg_min_atr": 0.3, "atr_sl": 1.0, "atr_tp": 2.5}

    def generate_signal(self, df, current_price):
        p = self.params
        if len(df) < 30:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="Insufficient data")
        atr = ind.atr(df["high"], df["low"], df["close"], 14).iloc[-1]
        close = df["close"].iloc[-1]
        lb = p["swing_lb"]
        # Structure: higher highs = bullish
        is_bullish_structure = df["close"].iloc[-lb:].mean() > df["close"].iloc[-lb*2:-lb].mean()
        for i in range(3, min(20, len(df)-2)):
            c1 = df.iloc[-(i+1)]
            c3 = df.iloc[-(i-1)]
            if is_bullish_structure and c1["high"] < c3["low"]:
                gap_size = c3["low"] - c1["high"]
                if gap_size > atr * p["fvg_min_atr"] and c1["high"] <= close <= c3["low"]:
                    return StrategySignal(name=self.name, action=SignalAction.BUY, strength=0.82,
                        entry=current_price, stop_loss=current_price - atr * p["atr_sl"],
                        take_profit=current_price + atr * p["atr_tp"],
                        reason=f"Bullish FVG fill in bullish structure at {close:.5f}")
            if not is_bullish_structure and c1["low"] > c3["high"]:
                gap_size = c1["low"] - c3["high"]
                if gap_size > atr * p["fvg_min_atr"] and c3["high"] <= close <= c1["low"]:
                    return StrategySignal(name=self.name, action=SignalAction.SELL, strength=0.82,
                        entry=current_price, stop_loss=current_price + atr * p["atr_sl"],
                        take_profit=current_price - atr * p["atr_tp"],
                        reason=f"Bearish FVG fill in bearish structure at {close:.5f}")
        return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="No confluence FVG")
