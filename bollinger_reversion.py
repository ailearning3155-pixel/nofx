"""Bollinger Band Reversion"""
import pandas as pd
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class BollingerReversionStrategy(BaseStrategy):
    name = "bollinger_reversion"
    display_name = "Bollinger Band Reversion"
    category = "mean_reversion"
    description = "Touch and close back inside BB bands. Mean reversion to midline."
    default_params = {"bb_period":20,"bb_std":2.0,"atr_sl":1.0,"atr_tp":1.8}
    def generate_signal(self, df, current_price):
        p=self.params
        if len(df)<p["bb_period"]+3: return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="Insufficient data")
        bb=ind.bbands(df["close"],p["bb_period"],p["bb_std"])
        atr=ind.atr(df["high"],df["low"],df["close"],14).iloc[-1]
        c=df["close"].iloc[-1]; pc=df["close"].iloc[-2]
        upper=bb["upper"].iloc[-1]; lower=bb["lower"].iloc[-1]; mid=bb["mid"].iloc[-1]
        pu=bb["upper"].iloc[-2]; pl=bb["lower"].iloc[-2]
        if pc>pu and c<=pu:
            return StrategySignal(name=self.name,action=SignalAction.SELL,strength=0.72,entry=current_price,
                stop_loss=current_price+atr*p["atr_sl"],take_profit=mid,reason=f"BB upper reversion to mid {mid:.5f}")
        if pc<pl and c>=pl:
            return StrategySignal(name=self.name,action=SignalAction.BUY,strength=0.72,entry=current_price,
                stop_loss=current_price-atr*p["atr_sl"],take_profit=mid,reason=f"BB lower reversion to mid {mid:.5f}")
        return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="No BB reversion signal")
