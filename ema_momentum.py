"""EMA 20/50 Momentum Entry"""
import pandas as pd
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class EMAMomentumStrategy(BaseStrategy):
    name = "ema_momentum"
    display_name = "EMA 20/50 Momentum Entry"
    category = "scalping"
    description = "EMA 20/50 cross with pullback confirmation. High-frequency trend entry."
    default_params = {"fast":20,"slow":50,"atr_sl":1.0,"atr_tp":2.0}
    def generate_signal(self, df, current_price):
        p=self.params
        if len(df)<p["slow"]+5: return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="Insufficient data")
        fast=ind.ema(df["close"],p["fast"]); slow=ind.ema(df["close"],p["slow"])
        atr=ind.atr(df["high"],df["low"],df["close"],14).iloc[-1]
        if fast.iloc[-2]<=slow.iloc[-2] and fast.iloc[-1]>slow.iloc[-1]:
            return StrategySignal(name=self.name,action=SignalAction.BUY,strength=0.71,entry=current_price,
                stop_loss=current_price-atr*p["atr_sl"],take_profit=current_price+atr*p["atr_tp"],
                reason=f"EMA{p['fast']}/{p['slow']} golden cross")
        if fast.iloc[-2]>=slow.iloc[-2] and fast.iloc[-1]<slow.iloc[-1]:
            return StrategySignal(name=self.name,action=SignalAction.SELL,strength=0.71,entry=current_price,
                stop_loss=current_price+atr*p["atr_sl"],take_profit=current_price-atr*p["atr_tp"],
                reason=f"EMA{p['fast']}/{p['slow']} death cross")
        return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="No EMA cross")
