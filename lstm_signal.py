"""LSTM-style Temporal Signal — numpy-based sequence model (no tensorflow required)"""
import pandas as pd
import numpy as np
from core.strategies.registry import BaseStrategy, StrategySignal
from core.indicators import ind
from models.models import SignalAction

class LSTMSignalStrategy(BaseStrategy):
    name = "lstm_signal"
    display_name = "LSTM Temporal Model"
    category = "ml"
    description = "Simulates LSTM-style sequential feature extraction using rolling statistics. "  \
                  "Captures non-linear temporal patterns without requiring TensorFlow."
    default_params = {"seq_len": 20, "train_bars": 300, "min_confidence": 0.63, "atr_sl": 1.2, "atr_tp": 2.5}

    def __init__(self, params=None):
        super().__init__(params)
        self._weights = None
        self._scaler  = None
        self._last_trained = 0

    def _extract_sequence_features(self, df: pd.DataFrame) -> np.ndarray:
        """Extract temporal sequence features (LSTM-style rolling windows)"""
        close  = df["close"]
        high   = df["high"]
        low    = df["low"]
        seq    = self.params["seq_len"]
        features = []
        for lag in range(1, seq + 1):
            ret = close.pct_change(lag)
            features.append(ret)
        rsi = ind.rsi(close, 14)
        features.append(rsi / 100)
        bb   = ind.bbands(close, 20, 2)
        features.append(bb["percent"])
        ema9  = ind.ema(close, 9)
        ema21 = ind.ema(close, 21)
        features.append((ema9 - ema21) / (close + 1e-8))
        atr_series = ind.atr(high, low, close, 14)
        features.append(atr_series / (close + 1e-8))
        vol5  = close.pct_change().rolling(5).std()
        vol20 = close.pct_change().rolling(20).std()
        features.append(vol5)
        features.append(vol20)
        feat_df = pd.concat(features, axis=1).dropna()
        return feat_df.values

    def _sigmoid(self, x):
        return 1 / (1 + np.exp(-np.clip(x, -20, 20)))

    def _train(self, df: pd.DataFrame) -> bool:
        try:
            X = self._extract_sequence_features(df)
            if len(X) < 50:
                return False
            y_raw = df["close"].pct_change(1).shift(-1)
            y = (y_raw > 0).astype(float)
            y_aligned = y.iloc[-len(X):].values[:-1]
            X_train = X[:-1]
            mean = X_train.mean(axis=0)
            std  = X_train.std(axis=0) + 1e-8
            self._scaler = (mean, std)
            X_norm = (X_train - mean) / std
            n_feat = X_norm.shape[1]
            np.random.seed(42)
            w1 = np.random.randn(n_feat, 16) * 0.1
            b1 = np.zeros(16)
            w2 = np.random.randn(16, 1) * 0.1
            b2 = np.zeros(1)
            lr = 0.01
            for _ in range(200):
                h = np.tanh(X_norm @ w1 + b1)
                out = self._sigmoid(h @ w2 + b2).flatten()
                err = out - y_aligned
                dw2 = h.T @ err.reshape(-1,1) / len(X_norm)
                db2 = err.mean()
                dh  = (err.reshape(-1,1) @ w2.T) * (1 - h**2)
                dw1 = X_norm.T @ dh / len(X_norm)
                db1 = dh.mean(axis=0)
                w1 -= lr * dw1; b1 -= lr * db1
                w2 -= lr * dw2; b2 -= lr * db2
            self._weights = (w1, b1, w2, b2)
            return True
        except Exception:
            return False

    def _predict(self, X_last: np.ndarray) -> float:
        w1, b1, w2, b2 = self._weights
        mean, std = self._scaler
        x = (X_last - mean) / std
        h = np.tanh(x @ w1 + b1)
        return float(self._sigmoid(h @ w2 + b2))

    def generate_signal(self, df: pd.DataFrame, current_price: float) -> StrategySignal:
        p = self.params
        if len(df) < p["train_bars"]:
            return StrategySignal(name=self.name, action=SignalAction.HOLD,
                reason=f"Need {p['train_bars']} bars to train LSTM model")
        if self._weights is None or (len(df) - self._last_trained) > 100:
            if not self._train(df.iloc[-p["train_bars"]:]):
                return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="LSTM training failed")
            self._last_trained = len(df)
        X = self._extract_sequence_features(df)
        if len(X) == 0:
            return StrategySignal(name=self.name, action=SignalAction.HOLD, reason="Feature error")
        prob_up = self._predict(X[-1])
        atr = ind.atr(df["high"], df["low"], df["close"], 14).iloc[-1]
        if prob_up >= p["min_confidence"]:
            return StrategySignal(name=self.name, action=SignalAction.BUY,
                strength=round(prob_up, 3), entry=current_price,
                stop_loss=current_price - atr * p["atr_sl"],
                take_profit=current_price + atr * p["atr_tp"],
                reason=f"LSTM temporal model: {prob_up:.1%} probability UP")
        if (1 - prob_up) >= p["min_confidence"]:
            return StrategySignal(name=self.name, action=SignalAction.SELL,
                strength=round(1-prob_up, 3), entry=current_price,
                stop_loss=current_price + atr * p["atr_sl"],
                take_profit=current_price - atr * p["atr_tp"],
                reason=f"LSTM temporal model: {1-prob_up:.1%} probability DOWN")
        return StrategySignal(name=self.name, action=SignalAction.HOLD,
            reason=f"LSTM uncertain: P(up)={prob_up:.1%}")
