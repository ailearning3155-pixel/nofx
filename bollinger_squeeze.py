"""Bollinger Band Squeeze Breakout"""
import pandas as pd
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class BollingerSqueezeStrategy(BaseStrategy):
    name = "bollinger_squeeze"
    display_name = "Bollinger Band Squeeze Breakout"
    category = "volatility"
    description = "BB squeeze (low BW) followed by explosive breakout. Catches major moves."
    default_params = {"bb_period":20,"bb_std":2.0,"atr_sl":1.5,"atr_tp":3.0}
    def generate_signal(self, df, current_price):
        p=self.params
        if len(df)<p["bb_period"]+25: return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="Insufficient data")
        bb=ind.bbands(df["close"],p["bb_period"],p["bb_std"])
        bw=bb["bandwidth"]; bw_avg=bw.iloc[-20:].mean()
        is_squeeze=bw.iloc[-1]<bw_avg*0.7
        if not is_squeeze: return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="No squeeze")
        c=df["close"].iloc[-1]; pc=df["close"].iloc[-2]
        upper=bb["upper"].iloc[-1]; lower=bb["lower"].iloc[-1]
        atr=ind.atr(df["high"],df["low"],df["close"],14).iloc[-1]
        if c>upper and pc<=upper:
            return StrategySignal(name=self.name,action=SignalAction.BUY,strength=0.75,entry=current_price,
                stop_loss=current_price-atr*p["atr_sl"],take_profit=current_price+atr*p["atr_tp"],
                reason=f"BB squeeze → upside breakout")
        if c<lower and pc>=lower:
            return StrategySignal(name=self.name,action=SignalAction.SELL,strength=0.75,entry=current_price,
                stop_loss=current_price+atr*p["atr_sl"],take_profit=current_price-atr*p["atr_tp"],
                reason=f"BB squeeze → downside breakout")
        return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="In squeeze, awaiting breakout")
