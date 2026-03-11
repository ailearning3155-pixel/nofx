"""MACD Momentum Cross"""
import pandas as pd
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class MACDMomentumStrategy(BaseStrategy):
    name = "macd_momentum"
    display_name = "MACD Momentum Cross"
    category = "scalping"
    description = "MACD signal line cross + histogram direction confirmation."
    default_params = {"fast":12,"slow":26,"signal":9,"atr_sl":1.2,"atr_tp":2.5}
    def generate_signal(self, df, current_price):
        p=self.params
        if len(df)<p["slow"]+p["signal"]+5: return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="Insufficient data")
        macd=ind.macd(df["close"],p["fast"],p["slow"],p["signal"])
        atr=ind.atr(df["high"],df["low"],df["close"],14).iloc[-1]
        ph=macd["histogram"].iloc[-2]; ch=macd["histogram"].iloc[-1]
        pl=macd["macd_line"].iloc[-2]-macd["signal_line"].iloc[-2]
        cl=macd["macd_line"].iloc[-1]-macd["signal_line"].iloc[-1]
        if pl<=0 and cl>0 and ch>0:
            return StrategySignal(name=self.name,action=SignalAction.BUY,strength=0.72,entry=current_price,
                stop_loss=current_price-atr*p["atr_sl"],take_profit=current_price+atr*p["atr_tp"],
                reason=f"MACD bullish cross + positive histogram")
        if pl>=0 and cl<0 and ch<0:
            return StrategySignal(name=self.name,action=SignalAction.SELL,strength=0.72,entry=current_price,
                stop_loss=current_price+atr*p["atr_sl"],take_profit=current_price-atr*p["atr_tp"],
                reason=f"MACD bearish cross + negative histogram")
        return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="No MACD cross")
