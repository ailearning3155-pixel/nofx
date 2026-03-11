"""Hidden Markov Regime Model — detect market regime then signal"""
import pandas as pd
import numpy as np
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class HiddenMarkovRegimeStrategy(BaseStrategy):
    name = "hidden_markov_regime"
    display_name = "Hidden Markov Regime"
    category = "stat_arb"
    description = "Uses Gaussian HMM-inspired regime detection (trend/range/volatile). Trades only in trending regime."
    default_params = {"window": 50, "vol_low": 0.3, "vol_high": 0.7, "atr_sl": 1.3, "atr_tp": 2.5}

    def _detect_regime(self, returns: np.ndarray, p: dict) -> str:
        """Returns: 'trending_up', 'trending_down', 'ranging', 'volatile'"""
        vol = returns.std()
        vol_percentiles = np.percentile(np.abs(returns), [30, 70])
        trend = returns.mean()
        autocorr = pd.Series(returns).autocorr(1) or 0
        if vol > vol_percentiles[1] * 1.5:
            return "volatile"
        if autocorr > 0.1 and trend > 0:
            return "trending_up"
        if autocorr > 0.1 and trend < 0:
            return "trending_down"
        return "ranging"

    def generate_signal(self, df: pd.DataFrame, current_price: float) -> StrategySignal:
        p = self.params
        if len(df) < p["window"]:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="Not enough data")
        returns = df["close"].pct_change().dropna().values[-p["window"]:]
        regime  = self._detect_regime(returns, p)
        atr     = ind.atr(df["high"], df["low"], df["close"], 14).iloc[-1]
        ema_fast = ind.ema(df["close"], 9).iloc[-1]
        ema_slow = ind.ema(df["close"], 21).iloc[-1]
        if regime == "trending_up" and ema_fast > ema_slow:
            return StrategySignal(name=self.name, action=SignalAction.BUY, strength=0.74,
                entry=current_price, stop_loss=current_price - atr * p["atr_sl"],
                take_profit=current_price + atr * p["atr_tp"],
                reason=f"HMM regime: TRENDING UP — long with trend")
        if regime == "trending_down" and ema_fast < ema_slow:
            return StrategySignal(name=self.name, action=SignalAction.SELL, strength=0.74,
                entry=current_price, stop_loss=current_price + atr * p["atr_sl"],
                take_profit=current_price - atr * p["atr_tp"],
                reason=f"HMM regime: TRENDING DOWN — short with trend")
        return StrategySignal(name=self.name, action=SignalAction.HOLD,
            reason=f"HMM regime: {regime.upper()} — no trade")
