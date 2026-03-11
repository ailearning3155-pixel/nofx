"""Breakout Trend Following — N-period high/low breakout"""
import pandas as pd
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class BreakoutTrendStrategy(BaseStrategy):
    name = "breakout_trend"
    display_name = "Breakout Trend Following"
    category = "trend"
    description = "Classic N-bar breakout. Buy new N-bar high, sell new N-bar low. Turtle Traders approach."
    default_params = {"period":20,"atr_sl":1.0,"atr_tp":3.0}
    def generate_signal(self, df, current_price):
        p=self.params
        if len(df)<p["period"]+2: return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="Insufficient data")
        high=df["high"].iloc[-(p["period"]+1):-1].max(); low=df["low"].iloc[-(p["period"]+1):-1].min()
        atr=ind.atr(df["high"],df["low"],df["close"],14).iloc[-1]
        c=df["close"].iloc[-1]; pc=df["close"].iloc[-2]
        if pc<=high and c>high:
            return StrategySignal(name=self.name,action=SignalAction.BUY,strength=0.74,entry=current_price,
                stop_loss=current_price-atr*p["atr_sl"],take_profit=current_price+atr*p["atr_tp"],
                reason=f"{p['period']}-bar breakout above {high:.5f}")
        if pc>=low and c<low:
            return StrategySignal(name=self.name,action=SignalAction.SELL,strength=0.74,entry=current_price,
                stop_loss=current_price+atr*p["atr_sl"],take_profit=current_price-atr*p["atr_tp"],
                reason=f"{p['period']}-bar breakdown below {low:.5f}")
        return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="No breakout")
