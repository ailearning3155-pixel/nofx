"""Donchian Channel Breakout"""
import pandas as pd
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class DonchianBreakoutStrategy(BaseStrategy):
    name = "donchian_breakout"
    display_name = "Donchian Channel Breakout"
    category = "trend"
    description = "Donchian 20-period channel breakout. Entry on close beyond channel."
    default_params = {"period":20,"atr_sl":1.0,"atr_tp":2.5}
    def generate_signal(self, df, current_price):
        p=self.params
        if len(df)<p["period"]+2: return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="Insufficient data")
        high=df["high"].iloc[-(p["period"]+1):-1].max(); low=df["low"].iloc[-(p["period"]+1):-1].min()
        atr=ind.atr(df["high"],df["low"],df["close"],14).iloc[-1]
        curr_h=df["high"].iloc[-1]; curr_l=df["low"].iloc[-1]
        prev_h=df["high"].iloc[-2]; prev_l=df["low"].iloc[-2]
        if prev_h<=high and curr_h>high:
            return StrategySignal(name=self.name,action=SignalAction.BUY,strength=0.73,entry=current_price,
                stop_loss=current_price-atr*p["atr_sl"],take_profit=current_price+atr*p["atr_tp"],
                reason=f"Donchian upside break {high:.5f}")
        if prev_l>=low and curr_l<low:
            return StrategySignal(name=self.name,action=SignalAction.SELL,strength=0.73,entry=current_price,
                stop_loss=current_price+atr*p["atr_sl"],take_profit=current_price-atr*p["atr_tp"],
                reason=f"Donchian downside break {low:.5f}")
        return StrategySignal(name=self.name,action=SignalAction.HOLD,reason=f"Inside channel {low:.5f}-{high:.5f}")
