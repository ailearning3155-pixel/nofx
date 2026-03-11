"""Interest Rate Differential — carry trade based on rate spreads"""
import pandas as pd
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

RATE_DIFFERENTIALS = {
    "EUR_USD": -0.50, "GBP_USD": 0.75, "USD_JPY": 5.50,
    "AUD_USD": -0.75, "USD_CAD": 0.25, "NZD_USD": -0.50,
    "USD_CHF": 5.25, "XAU_USD": 0.0,
}

class InterestRateDifferentialStrategy(BaseStrategy):
    name = "interest_rate_differential"
    display_name = "Interest Rate Differential"
    category = "macro"
    description = "Carry trade: long high-yield vs low-yield. Uses approximate rate differentials per pair."
    default_params = {"min_differential": 2.0, "trend_ema": 50, "atr_sl": 2.0, "atr_tp": 5.0}

    def generate_signal(self, df, current_price):
        p = self.params
        if len(df) < p["trend_ema"] + 5:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="Insufficient data")
        # Get rate differential from lookup or default
        rate_diff = 0.0
        for pair, diff in RATE_DIFFERENTIALS.items():
            if pair.replace("_", "") in str(getattr(self, "_instrument", "")):
                rate_diff = diff
                break
        if abs(rate_diff) < p["min_differential"]:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason=f"Rate diff too low ({rate_diff:.2f}%)")
        ema = ind.ema(df["close"], p["trend_ema"])
        atr = ind.atr(df["high"], df["low"], df["close"], 14).iloc[-1]
        trend_bullish = df["close"].iloc[-1] > ema.iloc[-1]
        if rate_diff > 0 and trend_bullish:
            return StrategySignal(name=self.name, action=SignalAction.BUY, strength=0.65,
                entry=current_price, stop_loss=current_price - atr * p["atr_sl"],
                take_profit=current_price + atr * p["atr_tp"],
                reason=f"Carry BUY: rate diff={rate_diff:.2f}% + bullish trend")
        if rate_diff < 0 and not trend_bullish:
            return StrategySignal(name=self.name, action=SignalAction.SELL, strength=0.65,
                entry=current_price, stop_loss=current_price + atr * p["atr_sl"],
                take_profit=current_price - atr * p["atr_tp"],
                reason=f"Carry SELL: rate diff={rate_diff:.2f}% + bearish trend")
        return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="Rate diff conflicts with trend")
