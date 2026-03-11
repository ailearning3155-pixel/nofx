"""Random Forest Signal — ML-based price direction prediction"""
import pandas as pd
import numpy as np
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class RandomForestSignalStrategy(BaseStrategy):
    name = "random_forest_signal"
    display_name = "Random Forest ML Signal"
    category = "ml"
    description = "Trains Random Forest on 20 technical features to predict next-bar direction. Retrains every 200 bars."
    default_params = {"train_bars": 200, "feature_bars": 20, "min_confidence": 0.62, "atr_sl": 1.2, "atr_tp": 2.5}

    def __init__(self, params=None):
        super().__init__(params)
        self._model = None
        self._last_trained = 0

    def _build_features(self, df):
        features = pd.DataFrame(index=df.index)
        close = df["close"]
        features["ret_1"]  = close.pct_change(1)
        features["ret_3"]  = close.pct_change(3)
        features["ret_5"]  = close.pct_change(5)
        features["ret_10"] = close.pct_change(10)
        features["rsi"]    = ind.rsi(close, 14)
        features["rsi_fast"] = ind.rsi(close, 7)
        ema9  = ind.ema(close, 9)
        ema21 = ind.ema(close, 21)
        features["ema_spread"]  = (ema9 - ema21) / close
        features["atr_norm"]    = ind.atr(df["high"], df["low"], close, 14) / close
        bb = ind.bbands(close, 20, 2)
        features["bb_pct"]   = bb["percent"]
        features["bb_bw"]    = bb["bandwidth"]
        macd_df = ind.macd(close)
        features["macd_hist"] = macd_df["histogram"]
        features["vol_5"]  = close.pct_change().rolling(5).std()
        features["vol_20"] = close.pct_change().rolling(20).std()
        features["vol_ratio"] = features["vol_5"] / (features["vol_20"] + 1e-8)
        features["high_low_ratio"] = (df["high"] - df["low"]) / close
        features["close_position"] = (close - df["low"]) / (df["high"] - df["low"] + 1e-8)
        return features.dropna()

    def _train(self, df):
        try:
            from sklearn.ensemble import RandomForestClassifier
            feats = self._build_features(df)
            future_ret = df["close"].pct_change(1).shift(-1)
            y = (future_ret > 0).astype(int)
            aligned = feats.join(y.rename("target")).dropna()
            if len(aligned) < 50:
                return False
            X = aligned.drop("target", axis=1).values
            y_vals = aligned["target"].values
            self._model = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42, n_jobs=1)
            self._model.fit(X, y_vals)
            return True
        except ImportError:
            return False
        except Exception:
            return False

    def generate_signal(self, df, current_price):
        p = self.params
        if len(df) < p["train_bars"]:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason=f"Need {p['train_bars']} bars to train")
        # Retrain every 50 bars
        if self._model is None or (len(df) - self._last_trained) > 50:
            success = self._train(df.iloc[-p["train_bars"]:])
            self._last_trained = len(df)
            if not success:
                return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="sklearn not available or train failed")
        try:
            feats = self._build_features(df)
            if len(feats) == 0:
                return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="Feature error")
            X_pred = feats.iloc[-1:].values
            proba = self._model.predict_proba(X_pred)[0]
            atr = ind.atr(df["high"], df["low"], df["close"], 14).iloc[-1]
            bull_prob, bear_prob = proba[1], proba[0]
            if bull_prob >= p["min_confidence"]:
                return StrategySignal(name=self.name, action=SignalAction.BUY, strength=bull_prob,
                    entry=current_price, stop_loss=current_price - atr * p["atr_sl"],
                    take_profit=current_price + atr * p["atr_tp"],
                    reason=f"RF predicts UP with {bull_prob:.1%} confidence")
            if bear_prob >= p["min_confidence"]:
                return StrategySignal(name=self.name, action=SignalAction.SELL, strength=bear_prob,
                    entry=current_price, stop_loss=current_price + atr * p["atr_sl"],
                    take_profit=current_price - atr * p["atr_tp"],
                    reason=f"RF predicts DOWN with {bear_prob:.1%} confidence")
            return StrategySignal(name=self.name, action=SignalAction.HOLD,
                reason=f"RF confidence low (bull={bull_prob:.1%} bear={bear_prob:.1%})")
        except Exception as e:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason=f"RF predict error: {e}")
