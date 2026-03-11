"""Gradient Boosting Signal — XGBoost-style ML prediction"""
import pandas as pd
import numpy as np
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class GradientBoostingSignalStrategy(BaseStrategy):
    name = "gradient_boosting_signal"
    display_name = "Gradient Boosting ML Signal"
    category = "ml"
    description = "GradientBoosting classifier on technical + momentum features. Optimized for forex direction."
    default_params = {"train_bars": 250, "min_confidence": 0.63, "atr_sl": 1.3, "atr_tp": 2.8}

    def __init__(self, params=None):
        super().__init__(params)
        self._model = None
        self._last_trained = 0

    def _build_features(self, df):
        f = pd.DataFrame(index=df.index)
        c = df["close"]
        for n in [1, 3, 5, 10, 20]:
            f[f"ret_{n}"] = c.pct_change(n)
        f["rsi14"]  = ind.rsi(c, 14)
        f["rsi7"]   = ind.rsi(c, 7)
        for e in [9, 21, 50]:
            f[f"ema{e}_dist"] = (c - ind.ema(c, e)) / c
        f["atr_norm"] = ind.atr(df["high"], df["low"], c, 14) / c
        bb = ind.bbands(c, 20, 2)
        f["bb_pct"] = bb["percent"]
        f["vol_ratio"] = c.pct_change().rolling(5).std() / (c.pct_change().rolling(20).std() + 1e-8)
        f["body_ratio"] = abs(c - df["open"]) / (df["high"] - df["low"] + 1e-8)
        return f.dropna()

    def _train(self, df):
        try:
            from sklearn.ensemble import GradientBoostingClassifier
            feats = self._build_features(df)
            y = (df["close"].pct_change(1).shift(-1) > 0).astype(int)
            aligned = feats.join(y.rename("t")).dropna()
            if len(aligned) < 60:
                return False
            self._model = GradientBoostingClassifier(n_estimators=80, max_depth=4, learning_rate=0.1, random_state=42)
            self._model.fit(aligned.drop("t", axis=1).values, aligned["t"].values)
            return True
        except:
            return False

    def generate_signal(self, df, current_price):
        p = self.params
        if len(df) < p["train_bars"]:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason=f"Need {p['train_bars']} bars")
        if self._model is None or (len(df) - self._last_trained) > 50:
            if not self._train(df.iloc[-p["train_bars"]:]):
                return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="sklearn unavailable")
            self._last_trained = len(df)
        try:
            feats = self._build_features(df)
            proba = self._model.predict_proba(feats.iloc[-1:].values)[0]
            bull_prob, bear_prob = proba[1], proba[0]
            atr = ind.atr(df["high"], df["low"], df["close"], 14).iloc[-1]
            if bull_prob >= p["min_confidence"]:
                return StrategySignal(name=self.name, action=SignalAction.BUY, strength=bull_prob,
                    entry=current_price, stop_loss=current_price - atr * p["atr_sl"],
                    take_profit=current_price + atr * p["atr_tp"],
                    reason=f"GBM: {bull_prob:.1%} bull probability")
            if bear_prob >= p["min_confidence"]:
                return StrategySignal(name=self.name, action=SignalAction.SELL, strength=bear_prob,
                    entry=current_price, stop_loss=current_price + atr * p["atr_sl"],
                    take_profit=current_price - atr * p["atr_tp"],
                    reason=f"GBM: {bear_prob:.1%} bear probability")
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason=f"GBM uncertain (b={bull_prob:.1%})")
        except Exception as e:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason=f"GBM error: {e}")
