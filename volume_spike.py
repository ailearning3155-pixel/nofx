"""Volume Spike Breakout"""
import pandas as pd
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class VolumeSpikeStrategy(BaseStrategy):
    name = "volume_spike"
    display_name = "Volume Spike Breakout"
    category = "scalping"
    description = "2x average volume spike in direction of breakout. Institutional footprint signal."
    default_params = {"vol_period":20,"vol_mult":2.0,"atr_sl":1.0,"atr_tp":2.0}
    def generate_signal(self, df, current_price):
        p=self.params
        if len(df)<p["vol_period"]+3: return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="Insufficient data")
        if df["volume"].iloc[-p["vol_period"]:].sum()==0:
            return StrategySignal(name=self.name,action=SignalAction.HOLD,reason="No volume data")
        avg_vol=df["volume"].iloc[-(p["vol_period"]+1):-1].mean(); curr_vol=df["volume"].iloc[-1]
        atr=ind.atr(df["high"],df["low"],df["close"],14).iloc[-1]
        if curr_vol<avg_vol*p["vol_mult"]:
            return StrategySignal(name=self.name,action=SignalAction.HOLD,reason=f"No spike ({curr_vol/avg_vol:.1f}x)")
        last=df.iloc[-1]; is_bull=last["close"]>last["open"]
        strength=min(0.6+(curr_vol/avg_vol-p["vol_mult"])/4,1.0)
        if is_bull:
            return StrategySignal(name=self.name,action=SignalAction.BUY,strength=strength,entry=current_price,
                stop_loss=current_price-atr*p["atr_sl"],take_profit=current_price+atr*p["atr_tp"],
                reason=f"Bull vol spike {curr_vol/avg_vol:.1f}x avg")
        return StrategySignal(name=self.name,action=SignalAction.SELL,strength=strength,entry=current_price,
            stop_loss=current_price+atr*p["atr_sl"],take_profit=current_price-atr*p["atr_tp"],
            reason=f"Bear vol spike {curr_vol/avg_vol:.1f}x avg")
