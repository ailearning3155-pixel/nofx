"""Moving Average Trend Following — multi-MA confluence"""
import pandas as pd
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class MovingAverageTrendStrategy(BaseStrategy):
    name = "moving_average_trend"
    display_name = "Moving Average Trend Following"
    category = "trend"
    description = "Price above 20/50/200 EMA stack = strong bull. All must align for signal."
    default_params = {"ema1":20,"ema2":50,"ema3":200,"atr_sl":1.5,"atr_tp":3.0}
    def generate_signal(self, df, current_price):
        p=self.params
        if len(df)<p["ema3"]+5: return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="Insufficient data")
        e1=ind.ema(df["close"],p["ema1"]); e2=ind.ema(df["close"],p["ema2"]); e3=ind.ema(df["close"],p["ema3"])
        atr=ind.atr(df["high"],df["low"],df["close"],14).iloc[-1]
        c=df["close"].iloc[-1]
        if c>e1.iloc[-1]>e2.iloc[-1]>e3.iloc[-1]:
            return StrategySignal(name=self.name,action=SignalAction.BUY,strength=0.80,entry=current_price,
                stop_loss=current_price-atr*p["atr_sl"],take_profit=current_price+atr*p["atr_tp"],
                reason=f"Full EMA stack bullish: {e1.iloc[-1]:.5f}>{e2.iloc[-1]:.5f}>{e3.iloc[-1]:.5f}")
        if c<e1.iloc[-1]<e2.iloc[-1]<e3.iloc[-1]:
            return StrategySignal(name=self.name,action=SignalAction.SELL,strength=0.80,entry=current_price,
                stop_loss=current_price+atr*p["atr_sl"],take_profit=current_price-atr*p["atr_tp"],
                reason=f"Full EMA stack bearish")
        return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="EMA stack not aligned")
