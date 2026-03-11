"""Market Structure Shift (MSS) — change of character in price structure"""
import pandas as pd
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class MarketStructureShiftStrategy(BaseStrategy):
    name = "market_structure_shift"
    display_name = "Market Structure Shift (MSS)"
    category = "scalping"
    description = "Detects Change of Character (CHoCH): first break of structure against prevailing trend."
    default_params = {"swing_lookback": 10, "confirm_bars": 2, "atr_sl": 1.0, "atr_tp": 2.5}

    def generate_signal(self, df, current_price):
        p = self.params
        if len(df) < p["swing_lookback"] * 3:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="Insufficient data")
        lb = p["swing_lookback"]
        # Determine prevailing trend by comparing swing highs/lows
        prev_swing_high = df["high"].iloc[-(lb*2):-lb].max()
        prev_swing_low  = df["low"].iloc[-(lb*2):-lb].min()
        curr_high = df["high"].iloc[-lb:].max()
        curr_low  = df["low"].iloc[-lb:].min()
        atr = ind.atr(df["high"], df["low"], df["close"], 14).iloc[-1]
        curr_close = df["close"].iloc[-1]
        prev_close = df["close"].iloc[-2]
        # Bullish MSS: was making lower lows, now breaks above prior swing high
        if curr_low < prev_swing_low and curr_close > prev_swing_high and prev_close < prev_swing_high:
            return StrategySignal(name=self.name, action=SignalAction.BUY, strength=0.77,
                entry=current_price, stop_loss=curr_low - atr * 0.3,
                take_profit=current_price + atr * p["atr_tp"],
                reason=f"Bullish MSS: broke above {prev_swing_high:.5f}")
        # Bearish MSS: was making higher highs, now breaks below prior swing low
        if curr_high > prev_swing_high and curr_close < prev_swing_low and prev_close > prev_swing_low:
            return StrategySignal(name=self.name, action=SignalAction.SELL, strength=0.77,
                entry=current_price, stop_loss=curr_high + atr * 0.3,
                take_profit=current_price - atr * p["atr_tp"],
                reason=f"Bearish MSS: broke below {prev_swing_low:.5f}")
        return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="No market structure shift")
