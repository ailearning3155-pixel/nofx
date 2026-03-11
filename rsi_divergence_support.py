"""RSI Divergence + Support Confluence"""
import pandas as pd
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class RSIDivergenceSupportStrategy(BaseStrategy):
    name = "rsi_divergence_support"
    display_name = "RSI Divergence + Support Zone"
    category = "scalping"
    description = "RSI bullish/bearish divergence AT a swing support/resistance level. Highest confluence."
    default_params = {"rsi_period":14,"div_lookback":15,"swing_lb":20,"atr_sl":1.0,"atr_tp":2.5}
    def generate_signal(self, df, current_price):
        p=self.params
        if len(df)<p["swing_lb"]+p["div_lookback"]+5: return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="Insufficient data")
        rsi=ind.rsi(df["close"],p["rsi_period"]); atr=ind.atr(df["high"],df["low"],df["close"],14).iloc[-1]
        lb=p["swing_lb"]; dlb=p["div_lookback"]
        swing_support=df["low"].iloc[-(lb+1):-1].min()
        swing_resist =df["high"].iloc[-(lb+1):-1].max()
        close=df["close"].iloc[-1]
        rsi_now=rsi.iloc[-1]; rsi_prev=rsi.iloc[-dlb]
        price_now=df["close"].iloc[-1]; price_prev=df["close"].iloc[-dlb]
        near_support=abs(close-swing_support)<atr*0.5
        near_resist =abs(close-swing_resist)<atr*0.5
        if price_now<price_prev and rsi_now>rsi_prev and near_support:
            return StrategySignal(name=self.name,action=SignalAction.BUY,strength=0.82,entry=current_price,
                stop_loss=swing_support-atr*0.3,take_profit=current_price+atr*p["atr_tp"],
                reason=f"Bull RSI div at support {swing_support:.5f}")
        if price_now>price_prev and rsi_now<rsi_prev and near_resist:
            return StrategySignal(name=self.name,action=SignalAction.SELL,strength=0.82,entry=current_price,
                stop_loss=swing_resist+atr*0.3,take_profit=current_price-atr*p["atr_tp"],
                reason=f"Bear RSI div at resistance {swing_resist:.5f}")
        return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="No RSI div+support confluence")
