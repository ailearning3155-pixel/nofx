"""EMA Trend + Pullback Entry"""
import pandas as pd
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class EMAPullbackStrategy(BaseStrategy):
    name = "ema_pullback"
    display_name = "EMA Trend + Pullback"
    category = "scalping"
    description = "Enter on pullback to EMA in direction of trend. Classic risk:reward entry."
    default_params = {"trend_ema":50,"entry_ema":20,"atr_sl":1.0,"atr_tp":2.5}
    def generate_signal(self, df, current_price):
        p=self.params
        if len(df)<p["trend_ema"]+5: return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="Insufficient data")
        trend=ind.ema(df["close"],p["trend_ema"]); entry=ind.ema(df["close"],p["entry_ema"])
        atr=ind.atr(df["high"],df["low"],df["close"],14).iloc[-1]
        close=df["close"].iloc[-1]; low=df["low"].iloc[-1]; high=df["high"].iloc[-1]
        bull_trend=close>trend.iloc[-1]
        # Pullback: in bull trend, price touched entry EMA from above
        if bull_trend and low<=entry.iloc[-1] and close>entry.iloc[-1]:
            return StrategySignal(name=self.name,action=SignalAction.BUY,strength=0.75,entry=current_price,
                stop_loss=current_price-atr*p["atr_sl"],take_profit=current_price+atr*p["atr_tp"],
                reason=f"Bull pullback to EMA{p['entry_ema']} in uptrend")
        if not bull_trend and high>=entry.iloc[-1] and close<entry.iloc[-1]:
            return StrategySignal(name=self.name,action=SignalAction.SELL,strength=0.75,entry=current_price,
                stop_loss=current_price+atr*p["atr_sl"],take_profit=current_price-atr*p["atr_tp"],
                reason=f"Bear pullback to EMA{p['entry_ema']} in downtrend")
        return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="No pullback entry")
