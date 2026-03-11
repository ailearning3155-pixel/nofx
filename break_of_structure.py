"""Break of Structure (BOS)"""
import pandas as pd
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class BreakOfStructureStrategy(BaseStrategy):
    name = "break_of_structure"
    display_name = "Break of Structure (BOS)"
    category = "scalping"
    description = "Higher-high or lower-low structural break continuation entry."
    default_params = {"swing_lb":10,"atr_sl":1.2,"atr_tp":2.5}
    def generate_signal(self, df, current_price):
        p=self.params
        if len(df)<p["swing_lb"]+5: return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="Insufficient data")
        lb=p["swing_lb"]; atr=ind.atr(df["high"],df["low"],df["close"],14).iloc[-1]
        ph=df["high"].iloc[-(lb+1):-1].max(); pl=df["low"].iloc[-(lb+1):-1].min()
        c=df["close"].iloc[-1]; pc=df["close"].iloc[-2]
        if pc<=ph and c>ph:
            return StrategySignal(name=self.name,action=SignalAction.BUY,strength=0.74,entry=current_price,
                stop_loss=current_price-atr*p["atr_sl"],take_profit=current_price+atr*p["atr_tp"],
                reason=f"BOS above {ph:.5f}")
        if pc>=pl and c<pl:
            return StrategySignal(name=self.name,action=SignalAction.SELL,strength=0.74,entry=current_price,
                stop_loss=current_price+atr*p["atr_sl"],take_profit=current_price-atr*p["atr_tp"],
                reason=f"BOS below {pl:.5f}")
        return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="No BOS")
