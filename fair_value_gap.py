"""Fair Value Gap (FVG) Fill"""
import pandas as pd
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class FairValueGapStrategy(BaseStrategy):
    name = "fair_value_gap"
    display_name = "Fair Value Gap Fill"
    category = "scalping"
    description = "3-candle imbalance fill. Price returns to fill inefficiency."
    default_params = {"min_gap_atr":0.3,"atr_sl":1.0,"atr_tp":2.5}
    def generate_signal(self, df, current_price):
        p=self.params
        if len(df)<10: return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="Insufficient data")
        atr=ind.atr(df["high"],df["low"],df["close"],14).iloc[-1]; close=df["close"].iloc[-1]
        for i in range(2,min(20,len(df)-2)):
            c1=df.iloc[-(i+1)]; c3=df.iloc[-(i-1)]
            if c1["high"]<c3["low"] and (c3["low"]-c1["high"])>atr*p["min_gap_atr"]:
                if c1["high"]<=close<=c3["low"]:
                    return StrategySignal(name=self.name,action=SignalAction.BUY,strength=0.73,entry=current_price,
                        stop_loss=current_price-atr*p["atr_sl"],take_profit=current_price+atr*p["atr_tp"],
                        reason=f"Bullish FVG fill at {close:.5f}")
            if c1["low"]>c3["high"] and (c1["low"]-c3["high"])>atr*p["min_gap_atr"]:
                if c3["high"]<=close<=c1["low"]:
                    return StrategySignal(name=self.name,action=SignalAction.SELL,strength=0.73,entry=current_price,
                        stop_loss=current_price+atr*p["atr_sl"],take_profit=current_price-atr*p["atr_tp"],
                        reason=f"Bearish FVG fill at {close:.5f}")
        return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="No FVG fill")
