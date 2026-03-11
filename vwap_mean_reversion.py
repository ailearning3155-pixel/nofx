"""VWAP Mean Reversion"""
import pandas as pd
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class VWAPMeanReversionStrategy(BaseStrategy):
    name = "vwap_mean_reversion"
    display_name = "VWAP Mean Reversion"
    category = "mean_reversion"
    description = "Reversion to VWAP when price deviates >2x ATR. Targets VWAP as TP."
    default_params = {"deviation_atr":2.0,"atr_sl":1.0,"atr_tp":1.5}
    def generate_signal(self, df, current_price):
        p=self.params
        if len(df)<20: return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="Insufficient data")
        if "volume" not in df.columns or df["volume"].sum()==0:
            return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="No volume data")
        vwap=ind.vwap(df["high"],df["low"],df["close"],df["volume"]).iloc[-1]
        atr=ind.atr(df["high"],df["low"],df["close"],14).iloc[-1]
        close=df["close"].iloc[-1]; dev=(close-vwap)/atr
        if dev<-p["deviation_atr"]:
            return StrategySignal(name=self.name,action=SignalAction.BUY,strength=min(0.5+abs(dev)/4,1.0),
                entry=current_price,stop_loss=current_price-atr*p["atr_sl"],take_profit=vwap,
                reason=f"VWAP dev={dev:.2f}x ATR — long to VWAP {vwap:.5f}")
        if dev>p["deviation_atr"]:
            return StrategySignal(name=self.name,action=SignalAction.SELL,strength=min(0.5+dev/4,1.0),
                entry=current_price,stop_loss=current_price+atr*p["atr_sl"],take_profit=vwap,
                reason=f"VWAP dev={dev:.2f}x ATR — short to VWAP {vwap:.5f}")
        return StrategySignal(name=self.name,action=SignalAction.HOLD,reason=f"VWAP dev={dev:.2f}")
