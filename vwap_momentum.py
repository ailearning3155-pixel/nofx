"""VWAP + Momentum Confirmation — composite scalping"""
import pandas as pd
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class VWAPMomentumStrategy(BaseStrategy):
    name = "vwap_momentum"
    display_name = "VWAP + Momentum Confirmation"
    category = "scalping"
    description = "Price must be above/below VWAP AND RSI must confirm momentum direction."
    default_params = {"rsi_period":14,"atr_sl":1.0,"atr_tp":2.0}
    def generate_signal(self, df, current_price):
        p=self.params
        if len(df)<20: return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="Insufficient data")
        if "volume" not in df.columns or df["volume"].sum()==0:
            return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="No volume")
        vwap=ind.vwap(df["high"],df["low"],df["close"],df["volume"]).iloc[-1]
        rsi=ind.rsi(df["close"],p["rsi_period"]).iloc[-1]
        atr=ind.atr(df["high"],df["low"],df["close"],14).iloc[-1]
        close=df["close"].iloc[-1]
        if close>vwap and rsi>55 and rsi<75:
            return StrategySignal(name=self.name,action=SignalAction.BUY,strength=0.73,entry=current_price,
                stop_loss=current_price-atr*p["atr_sl"],take_profit=current_price+atr*p["atr_tp"],
                reason=f"Above VWAP + RSI momentum {rsi:.0f}")
        if close<vwap and rsi<45 and rsi>25:
            return StrategySignal(name=self.name,action=SignalAction.SELL,strength=0.73,entry=current_price,
                stop_loss=current_price+atr*p["atr_sl"],take_profit=current_price-atr*p["atr_tp"],
                reason=f"Below VWAP + RSI momentum {rsi:.0f}")
        return StrategySignal(name=self.name,action=SignalAction.HOLD,reason=f"No VWAP+RSI confluence")
