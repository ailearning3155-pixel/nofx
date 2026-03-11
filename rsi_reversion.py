"""RSI Reversion"""
import pandas as pd
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class RSIReversionStrategy(BaseStrategy):
    name = "rsi_reversion"
    display_name = "RSI Reversion"
    category = "mean_reversion"
    description = "RSI extreme zones with cross-back confirmation. High win-rate mean reversion."
    default_params = {"rsi_period":14,"oversold":30,"overbought":70,"atr_sl":1.2,"atr_tp":2.0}
    def generate_signal(self, df, current_price):
        p=self.params
        if len(df)<p["rsi_period"]+5: return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="Insufficient data")
        rsi=ind.rsi(df["close"],p["rsi_period"]); atr=ind.atr(df["high"],df["low"],df["close"],14).iloc[-1]
        pr=rsi.iloc[-2]; cr=rsi.iloc[-1]
        if pr<p["oversold"] and cr>=p["oversold"]:
            return StrategySignal(name=self.name,action=SignalAction.BUY,strength=min(0.6+(p["oversold"]-pr)/30,1.0),
                entry=current_price,stop_loss=current_price-atr*p["atr_sl"],take_profit=current_price+atr*p["atr_tp"],
                reason=f"RSI cross above {p['oversold']} from {pr:.1f}")
        if pr>p["overbought"] and cr<=p["overbought"]:
            return StrategySignal(name=self.name,action=SignalAction.SELL,strength=min(0.6+(pr-p["overbought"])/30,1.0),
                entry=current_price,stop_loss=current_price+atr*p["atr_sl"],take_profit=current_price-atr*p["atr_tp"],
                reason=f"RSI cross below {p['overbought']} from {pr:.1f}")
        return StrategySignal(name=self.name,action=SignalAction.HOLD,reason=f"RSI={cr:.1f}")
