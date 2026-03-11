"""RSI Divergence — price makes new high/low but RSI doesn't"""
import pandas as pd
import numpy as np
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class RSIDivergenceStrategy(BaseStrategy):
    name = "rsi_divergence"
    display_name = "RSI Divergence"
    category = "scalping"
    description = "Hidden and regular divergence between price and RSI. High-probability reversal signal."
    default_params = {"rsi_period": 14, "lookback": 20, "atr_sl": 1.2, "atr_tp": 2.5}

    def generate_signal(self, df, current_price):
        p = self.params
        if len(df) < p["lookback"] + p["rsi_period"]:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="Insufficient data")
        rsi = ind.rsi(df["close"], p["rsi_period"])
        atr = ind.atr(df["high"], df["low"], df["close"], 14).iloc[-1]
        lb = p["lookback"]
        price_now  = df["close"].iloc[-1]
        price_prev = df["close"].iloc[-lb]
        rsi_now    = rsi.iloc[-1]
        rsi_prev   = rsi.iloc[-lb]
        if pd.isna(rsi_now) or pd.isna(rsi_prev):
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="RSI not ready")
        # Bearish divergence: price higher, RSI lower
        if price_now > price_prev and rsi_now < rsi_prev and rsi_now > 60:
            return StrategySignal(name=self.name, action=SignalAction.SELL, strength=0.75,
                entry=current_price, stop_loss=current_price + atr * p["atr_sl"],
                take_profit=current_price - atr * p["atr_tp"],
                reason=f"Bearish RSI divergence: price↑ RSI↓ ({rsi_prev:.0f}→{rsi_now:.0f})")
        # Bullish divergence: price lower, RSI higher
        if price_now < price_prev and rsi_now > rsi_prev and rsi_now < 40:
            return StrategySignal(name=self.name, action=SignalAction.BUY, strength=0.75,
                entry=current_price, stop_loss=current_price - atr * p["atr_sl"],
                take_profit=current_price + atr * p["atr_tp"],
                reason=f"Bullish RSI divergence: price↓ RSI↑ ({rsi_prev:.0f}→{rsi_now:.0f})")
        return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="No RSI divergence")
