"""Volatility Compression-Expansion — squeeze then fire"""
import pandas as pd
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class VolatilityCompressionStrategy(BaseStrategy):
    name = "volatility_compression"
    display_name = "Volatility Compression-Expansion"
    category = "volatility"
    description = "Identifies extended low-vol compression, then trades the expansion breakout."
    default_params = {"squeeze_bars": 10, "bb_period": 20, "bb_std": 2.0, "atr_sl": 1.2, "atr_tp": 3.0}

    def generate_signal(self, df, current_price):
        p = self.params
        if len(df) < p["bb_period"] + p["squeeze_bars"] + 5:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="Insufficient data")
        bb = ind.bbands(df["close"], p["bb_period"], p["bb_std"])
        bw = bb["bandwidth"]
        bw_avg = bw.iloc[-p["squeeze_bars"]-20:-p["squeeze_bars"]].mean()
        bw_squeeze = bw.iloc[-p["squeeze_bars"]:]
        in_squeeze = (bw_squeeze < bw_avg * 0.6).all()
        if not in_squeeze:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="Not in vol compression")
        curr_close = df["close"].iloc[-1]
        prev_close = df["close"].iloc[-2]
        upper = bb["upper"].iloc[-1]
        lower = bb["lower"].iloc[-1]
        atr = ind.atr(df["high"], df["low"], df["close"], 14).iloc[-1]
        if curr_close > upper and prev_close <= upper:
            return StrategySignal(name=self.name, action=SignalAction.BUY, strength=0.80,
                entry=current_price, stop_loss=current_price - atr * p["atr_sl"],
                take_profit=current_price + atr * p["atr_tp"],
                reason=f"Vol compression→expansion UPSIDE after {p['squeeze_bars']}-bar squeeze")
        if curr_close < lower and prev_close >= lower:
            return StrategySignal(name=self.name, action=SignalAction.SELL, strength=0.80,
                entry=current_price, stop_loss=current_price + atr * p["atr_sl"],
                take_profit=current_price - atr * p["atr_tp"],
                reason=f"Vol compression→expansion DOWNSIDE after {p['squeeze_bars']}-bar squeeze")
        return StrategySignal(name=self.name, action=SignalAction.HOLD, reason=f"In squeeze, no breakout yet")
