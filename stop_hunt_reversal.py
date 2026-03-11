"""Stop Hunt Reversal"""
import pandas as pd
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class StopHuntReversalStrategy(BaseStrategy):
    name = "stop_hunt_reversal"
    display_name = "Stop Hunt Reversal"
    category = "scalping"
    description = "Spike beyond key level with sharp rejection = stop hunt. Trade the reversal."
    default_params = {"swing_lb":20,"spike_atr":0.6,"atr_sl":0.5,"atr_tp":2.0}
    def generate_signal(self, df, current_price):
        p=self.params
        if len(df)<p["swing_lb"]+5: return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="Insufficient data")
        lb=p["swing_lb"]; atr=ind.atr(df["high"],df["low"],df["close"],14).iloc[-1]
        swing_high=df["high"].iloc[-(lb+1):-1].max(); swing_low=df["low"].iloc[-(lb+1):-1].min()
        last=df.iloc[-1]
        upper_wick=last["high"]-max(last["open"],last["close"])
        lower_wick=min(last["open"],last["close"])-last["low"]
        if last["high"]>swing_high and upper_wick>atr*p["spike_atr"] and last["close"]<swing_high:
            return StrategySignal(name=self.name,action=SignalAction.SELL,strength=0.78,entry=current_price,
                stop_loss=last["high"]+atr*0.2,take_profit=current_price-atr*p["atr_tp"],
                reason=f"Stop hunt ABOVE {swing_high:.5f}")
        if last["low"]<swing_low and lower_wick>atr*p["spike_atr"] and last["close"]>swing_low:
            return StrategySignal(name=self.name,action=SignalAction.BUY,strength=0.78,entry=current_price,
                stop_loss=last["low"]-atr*0.2,take_profit=current_price+atr*p["atr_tp"],
                reason=f"Stop hunt BELOW {swing_low:.5f}")
        return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="No stop hunt detected")
