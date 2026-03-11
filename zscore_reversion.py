"""Z-Score Reversion"""
import pandas as pd
import numpy as np
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class ZScoreReversionStrategy(BaseStrategy):
    name = "zscore_reversion"
    display_name = "Z-Score Reversion"
    category = "mean_reversion"
    description = "Trades when price is statistically extreme (|z|>2.0). High probability mean reversion."
    default_params = {"lookback":30,"z_entry":2.0,"atr_sl":1.5,"atr_tp":2.5}
    def generate_signal(self, df, current_price):
        p=self.params
        if len(df)<p["lookback"]+5: return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="Insufficient data")
        close=df["close"].iloc[-p["lookback"]:]; mean=close.mean(); std=close.std()
        if std==0: return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="Zero std")
        z=(df["close"].iloc[-1]-mean)/std; pz=(df["close"].iloc[-2]-mean)/std
        atr=ind.atr(df["high"],df["low"],df["close"],14).iloc[-1]
        strength=min(abs(z)/3.5,1.0)
        if pz<=-p["z_entry"] and z>pz:
            return StrategySignal(name=self.name,action=SignalAction.BUY,strength=strength,entry=current_price,
                stop_loss=current_price-atr*p["atr_sl"],take_profit=mean,reason=f"Z={z:.2f} — oversold reversion")
        if pz>=p["z_entry"] and z<pz:
            return StrategySignal(name=self.name,action=SignalAction.SELL,strength=strength,entry=current_price,
                stop_loss=current_price+atr*p["atr_sl"],take_profit=mean,reason=f"Z={z:.2f} — overbought reversion")
        return StrategySignal(name=self.name,action=SignalAction.HOLD,reason=f"Z={z:.2f} — within normal range")
