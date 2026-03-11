"""Premium/Discount Entry — ICT equilibrium zones"""
import pandas as pd
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class PremiumDiscountStrategy(BaseStrategy):
    name = "premium_discount"
    display_name = "Premium/Discount Entry"
    category = "scalping"
    description = "Buy in discount (<50% of range), sell in premium (>50% of range). ICT concept."
    default_params = {"range_bars":50,"discount_pct":0.35,"premium_pct":0.65,"atr_sl":1.0,"atr_tp":2.0}
    def generate_signal(self, df, current_price):
        p=self.params
        if len(df)<p["range_bars"]+5: return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="Insufficient data")
        high=df["high"].iloc[-p["range_bars"]:].max(); low=df["low"].iloc[-p["range_bars"]:].min()
        if high==low: return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="No range")
        position=(current_price-low)/(high-low); atr=ind.atr(df["high"],df["low"],df["close"],14).iloc[-1]
        rsi=ind.rsi(df["close"],14).iloc[-1]
        if position<=p["discount_pct"] and rsi<45:
            return StrategySignal(name=self.name,action=SignalAction.BUY,strength=0.70,entry=current_price,
                stop_loss=current_price-atr*p["atr_sl"],take_profit=current_price+atr*p["atr_tp"],
                reason=f"Discount zone {position:.1%} of range — BUY")
        if position>=p["premium_pct"] and rsi>55:
            return StrategySignal(name=self.name,action=SignalAction.SELL,strength=0.70,entry=current_price,
                stop_loss=current_price+atr*p["atr_sl"],take_profit=current_price-atr*p["atr_tp"],
                reason=f"Premium zone {position:.1%} of range — SELL")
        return StrategySignal(name=self.name,action=SignalAction.HOLD,reason=f"Equilibrium ({position:.1%})")
