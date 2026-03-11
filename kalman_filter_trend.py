"""Kalman Filter Trend — adaptive mean tracking"""
import pandas as pd
import numpy as np
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class KalmanFilterTrendStrategy(BaseStrategy):
    name = "kalman_filter_trend"
    display_name = "Kalman Filter Trend"
    category = "stat_arb"
    description = "Kalman filter as adaptive moving average. Trades when price diverges from Kalman estimate. Used by quant funds."
    default_params = {"Q": 1e-5, "R": 0.01, "atr_sl": 1.2, "atr_tp": 2.5, "deviation_mult": 1.5}

    def _kalman(self, prices: np.ndarray, Q: float, R: float):
        n = len(prices)
        x = np.zeros(n)  # state estimate
        P = np.zeros(n)  # error covariance
        x[0] = prices[0]; P[0] = 1.0
        for i in range(1, n):
            x_pred = x[i-1]; P_pred = P[i-1] + Q
            K = P_pred / (P_pred + R)
            x[i] = x_pred + K * (prices[i] - x_pred)
            P[i] = (1 - K) * P_pred
        return x

    def generate_signal(self, df: pd.DataFrame, current_price: float) -> StrategySignal:
        p = self.params
        if len(df) < 30:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="Not enough data")
        prices  = df["close"].values
        kalman  = self._kalman(prices, p["Q"], p["R"])
        atr     = ind.atr(df["high"], df["low"], df["close"], 14).iloc[-1]
        k_now   = kalman[-1]
        k_prev  = kalman[-2]
        c_now   = prices[-1]
        dev     = (c_now - k_now) / atr if atr > 0 else 0
        trend   = k_now - kalman[-5] if len(kalman) > 5 else 0
        if dev < -p["deviation_mult"] and trend > 0:
            return StrategySignal(name=self.name, action=SignalAction.BUY,
                strength=min(abs(dev)/4, 1.0), entry=current_price,
                stop_loss=current_price - atr * p["atr_sl"],
                take_profit=k_now + atr * p["atr_tp"],
                reason=f"Kalman pullback buy: price {dev:.1f}x ATR below trend filter")
        if dev > p["deviation_mult"] and trend < 0:
            return StrategySignal(name=self.name, action=SignalAction.SELL,
                strength=min(abs(dev)/4, 1.0), entry=current_price,
                stop_loss=current_price + atr * p["atr_sl"],
                take_profit=k_now - atr * p["atr_tp"],
                reason=f"Kalman mean revert sell: price {dev:.1f}x ATR above filter")
        return StrategySignal(name=self.name, action=SignalAction.HOLD,
            reason=f"Kalman deviation={dev:.2f} — no signal")
