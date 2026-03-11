"""Order Flow Imbalance — volume delta divergence from price"""
import pandas as pd
import numpy as np
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class OrderFlowImbalanceStrategy(BaseStrategy):
    name = "order_flow_imbalance"
    display_name = "Order Flow Imbalance"
    category = "microstructure"
    description = "Detects buying/selling pressure imbalance using volume-weighted price delta. Renaissance-style signal."
    default_params = {"lookback": 20, "imbalance_threshold": 0.6, "atr_sl": 1.0, "atr_tp": 2.0}

    def generate_signal(self, df: pd.DataFrame, current_price: float) -> StrategySignal:
        p = self.params
        if len(df) < p["lookback"] + 5:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="Not enough data")
        if df["volume"].sum() == 0:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="No volume data")
        window = df.iloc[-p["lookback"]:]
        # Classify each bar as buying (close>open) or selling
        buy_vol  = window.loc[window["close"] >= window["open"], "volume"].sum()
        sell_vol = window.loc[window["close"] <  window["open"], "volume"].sum()
        total_vol = buy_vol + sell_vol
        if total_vol == 0:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="Zero volume")
        buy_ratio = buy_vol / total_vol
        atr = ind.atr(df["high"], df["low"], df["close"], 14).iloc[-1]
        if buy_ratio >= p["imbalance_threshold"]:
            return StrategySignal(name=self.name, action=SignalAction.BUY,
                strength=round(buy_ratio, 2), entry=current_price,
                stop_loss=current_price - atr, take_profit=current_price + atr * p["atr_tp"],
                reason=f"Bullish OFI: {buy_ratio:.1%} buy pressure over {p['lookback']} bars")
        if (1 - buy_ratio) >= p["imbalance_threshold"]:
            return StrategySignal(name=self.name, action=SignalAction.SELL,
                strength=round(1-buy_ratio, 2), entry=current_price,
                stop_loss=current_price + atr, take_profit=current_price - atr * p["atr_tp"],
                reason=f"Bearish OFI: {1-buy_ratio:.1%} sell pressure over {p['lookback']} bars")
        return StrategySignal(name=self.name, action=SignalAction.HOLD,
            reason=f"Balanced flow: buy={buy_ratio:.1%}")
