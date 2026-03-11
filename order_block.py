"""Order Block Entry — institutional demand/supply zones"""
import pandas as pd
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class OrderBlockStrategy(BaseStrategy):
    name = "order_block"
    display_name = "Order Block Entry"
    category = "scalping"
    description = "Last opposing candle before strong impulse. ICT/SMC institutional entry."
    default_params = {"impulse_atr":1.5,"lookback":30,"atr_sl":0.8,"atr_tp":2.5}
    def generate_signal(self, df, current_price):
        p=self.params
        if len(df)<20: return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="Insufficient data")
        atr=ind.atr(df["high"],df["low"],df["close"],14).iloc[-1]; close=df["close"].iloc[-1]
        lookback=min(p["lookback"],len(df)-3)
        for i in range(3,lookback):
            c1=df.iloc[-i]; c2=df.iloc[-(i-1)]; impulse=abs(c2["close"]-c2["open"])
            if c1["close"]<c1["open"] and c2["close"]>c2["open"] and impulse>atr*p["impulse_atr"]:
                if c1["low"]<=close<=c1["high"]:
                    return StrategySignal(name=self.name,action=SignalAction.BUY,strength=0.76,entry=current_price,
                        stop_loss=c1["low"]-atr*p["atr_sl"],take_profit=current_price+atr*p["atr_tp"],
                        reason=f"Bullish OB at {c1['low']:.5f}-{c1['high']:.5f}")
            if c1["close"]>c1["open"] and c2["close"]<c2["open"] and impulse>atr*p["impulse_atr"]:
                if c1["low"]<=close<=c1["high"]:
                    return StrategySignal(name=self.name,action=SignalAction.SELL,strength=0.76,entry=current_price,
                        stop_loss=c1["high"]+atr*p["atr_sl"],take_profit=current_price-atr*p["atr_tp"],
                        reason=f"Bearish OB at {c1['low']:.5f}-{c1['high']:.5f}")
        return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="No active OB")
