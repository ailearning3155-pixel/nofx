"""ATR Volatility Breakout"""
import pandas as pd
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class ATRBreakoutStrategy(BaseStrategy):
    name = "atr_breakout"
    display_name = "ATR Volatility Breakout"
    category = "volatility"
    description = "Price breaks ATR-based range around prior close. Momentum entry."
    default_params = {"atr_period":14,"breakout_mult":1.5,"atr_sl":1.0,"atr_tp":2.0}
    def generate_signal(self, df, current_price):
        p=self.params
        if len(df)<20: return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="Insufficient data")
        atr=ind.atr(df["high"],df["low"],df["close"],p["atr_period"])
        atr_val=atr.iloc[-1]; prev_close=df["close"].iloc[-2]
        upper=prev_close+atr_val*p["breakout_mult"]; lower=prev_close-atr_val*p["breakout_mult"]
        c=df["close"].iloc[-1]; pc=df["close"].iloc[-3] if len(df)>3 else prev_close
        if pc<=upper and c>upper:
            return StrategySignal(name=self.name,action=SignalAction.BUY,strength=0.70,entry=current_price,
                stop_loss=current_price-atr_val*p["atr_sl"],take_profit=current_price+atr_val*p["atr_tp"],
                reason=f"ATR upside breakout above {upper:.5f}")
        if pc>=lower and c<lower:
            return StrategySignal(name=self.name,action=SignalAction.SELL,strength=0.70,entry=current_price,
                stop_loss=current_price+atr_val*p["atr_sl"],take_profit=current_price-atr_val*p["atr_tp"],
                reason=f"ATR downside breakout below {lower:.5f}")
        return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="Inside ATR range")
