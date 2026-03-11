"""
APEX — ML Ensemble Module
XGBoost + RandomForest ensemble that estimates trade success probability.
Acts as a gating filter: trades only execute when P(success) >= threshold.

Training data is stored in the database and models are retrained weekly.
"""
from __future__ import annotations
import json
import os
import pickle
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger

from core.feature_engineering import get_feature_engineer


# ── Model persistence ────────────────────────────────────────────────────────
MODEL_DIR = Path("models/saved")
MODEL_DIR.mkdir(parents=True, exist_ok=True)

XGBOOST_PATH   = MODEL_DIR / "xgboost_ensemble.pkl"
RF_PATH        = MODEL_DIR / "random_forest.pkl"
META_PATH      = MODEL_DIR / "meta_model.pkl"
TRAINING_PATH  = MODEL_DIR / "training_data.csv"


@dataclass
class EnsemblePrediction:
    """Output from the ML ensemble."""
    probability:    float          # P(trade success), 0.0 – 1.0
    xgb_prob:       float = 0.0
    rf_prob:        float = 0.0
    meta_prob:      float = 0.0
    confidence:     float = 0.0
    model_agreement: float = 0.0   # std of individual predictions (low = high agreement)
    features_used:  int = 0
    trained_on:     int = 0        # number of training samples
    gate_pass:      bool = False   # True if above ML threshold
    threshold:      float = 0.65

    def __post_init__(self):
        self.gate_pass = self.probability >= self.threshold


@dataclass
class TradeRecord:
    """A single completed trade for building training data."""
    timestamp:     str
    instrument:    str
    direction:     str             # BUY | SELL
    strategy:      str
    regime:        str
    confidence:    float
    entry_price:   float
    exit_price:    float
    pnl_pct:       float
    won:           bool            # True if profitable
    features:      Dict = field(default_factory=dict)


class MLEnsemble:
    """
    Two-stage ML ensemble:
    Stage 1: XGBoost + RandomForest independently predict win probability
    Stage 2: Meta-model blends Stage 1 predictions with extra context features

    Fallback: if models not trained, returns neutral probability (0.5).
    """

    def __init__(self, ml_threshold: float = 0.65):
        self.ml_threshold = ml_threshold
        self.xgb_model    = None
        self.rf_model     = None
        self.meta_model   = None
        self.feature_eng  = get_feature_engineer()
        self.trained_on   = 0
        self._load_models()

    # ── Public API ───────────────────────────────────────────────────────────

    def predict(
        self,
        df: pd.DataFrame,
        regime: str = "unknown",
        strategy_confidence: float = 0.0,
        direction: str = "BUY",
    ) -> EnsemblePrediction:
        """
        Predict trade success probability from current market features.
        Returns neutral 0.5 if models not trained yet.
        """
        features = self.feature_eng.build(df)
        if features.empty or len(features) < 2:
            return self._neutral_prediction()

        last_row = features.iloc[-1:].values

        xgb_p  = self._predict_single(self.xgb_model,  last_row)
        rf_p   = self._predict_single(self.rf_model,    last_row)

        # Meta model gets XGB + RF + context
        if self.meta_model is not None:
            meta_input = np.array([[
                xgb_p, rf_p,
                strategy_confidence,
                self._regime_encode(regime),
                1.0 if direction == "BUY" else 0.0,
            ]])
            meta_p = self._predict_single(self.meta_model, meta_input)
        else:
            meta_p = (xgb_p + rf_p) / 2

        # Ensemble: weighted blend
        if self.xgb_model and self.rf_model:
            probability = 0.4 * xgb_p + 0.35 * rf_p + 0.25 * meta_p
            agreement   = 1.0 - np.std([xgb_p, rf_p, meta_p])
        elif self.xgb_model or self.rf_model:
            probability = xgb_p or rf_p
            agreement   = 0.6
        else:
            return self._neutral_prediction()

        probability = float(np.clip(probability, 0.0, 1.0))
        confidence  = float(np.clip(agreement, 0.0, 1.0))

        return EnsemblePrediction(
            probability=round(probability, 4),
            xgb_prob=round(xgb_p, 4),
            rf_prob=round(rf_p, 4),
            meta_prob=round(meta_p, 4),
            confidence=round(confidence, 4),
            model_agreement=round(float(np.std([xgb_p, rf_p])), 4),
            features_used=features.shape[1],
            trained_on=self.trained_on,
            gate_pass=probability >= self.ml_threshold,
            threshold=self.ml_threshold,
        )

    def train(self, trade_records: List[TradeRecord]) -> Dict:
        """
        Train/retrain all models on completed trade records.
        Should be called weekly via the scheduler.
        """
        if len(trade_records) < 50:
            return {"success": False, "reason": f"Need ≥ 50 trades, have {len(trade_records)}"}

        logger.info(f"🤖 Training ML ensemble on {len(trade_records)} trades...")

        # Build training dataset from stored features
        rows, labels = [], []
        for rec in trade_records:
            if rec.features:
                rows.append(list(rec.features.values()))
                labels.append(int(rec.won))

        if len(rows) < 50:
            return {"success": False, "reason": "Insufficient feature data in records"}

        X = np.array(rows)
        y = np.array(labels)

        result = {"success": True, "samples": len(rows), "pos_rate": float(y.mean())}

        # ── XGBoost ──────────────────────────────────────────────────────
        try:
            from xgboost import XGBClassifier
            xgb = XGBClassifier(
                n_estimators=200,
                max_depth=5,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                eval_metric="logloss",
                use_label_encoder=False,
                random_state=42,
                n_jobs=-1,
            )
            xgb.fit(X, y)
            self.xgb_model = xgb
            pickle.dump(xgb, open(XGBOOST_PATH, "wb"))
            result["xgb_trained"] = True
            logger.info("✅ XGBoost trained")
        except ImportError:
            logger.warning("xgboost not installed — skipping XGBoost training")
            result["xgb_trained"] = False
        except Exception as e:
            logger.warning(f"XGBoost training failed: {e}")
            result["xgb_trained"] = False

        # ── RandomForest ─────────────────────────────────────────────────
        try:
            from sklearn.ensemble import RandomForestClassifier
            rf = RandomForestClassifier(
                n_estimators=150,
                max_depth=8,
                min_samples_split=5,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
            )
            rf.fit(X, y)
            self.rf_model = rf
            pickle.dump(rf, open(RF_PATH, "wb"))
            result["rf_trained"] = True
            logger.info("✅ RandomForest trained")
        except ImportError:
            logger.warning("sklearn not installed — skipping RF training")
            result["rf_trained"] = False
        except Exception as e:
            logger.warning(f"RF training failed: {e}")
            result["rf_trained"] = False

        # ── Meta-model (blends XGB + RF + context) ───────────────────────
        if self.xgb_model and self.rf_model:
            try:
                from sklearn.linear_model import LogisticRegression
                xgb_preds = self.xgb_model.predict_proba(X)[:, 1]
                rf_preds  = self.rf_model.predict_proba(X)[:, 1]
                meta_X    = np.column_stack([xgb_preds, rf_preds])
                meta      = LogisticRegression(random_state=42)
                meta.fit(meta_X, y)
                self.meta_model = meta
                pickle.dump(meta, open(META_PATH, "wb"))
                result["meta_trained"] = True
                logger.info("✅ Meta-model trained")
            except Exception as e:
                logger.warning(f"Meta-model training failed: {e}")
                result["meta_trained"] = False

        self.trained_on = len(rows)
        result["trained_on"] = self.trained_on
        logger.info(f"🎯 ML Ensemble training complete: {result}")
        return result

    def store_trade_record(self, record: TradeRecord):
        """Append a completed trade record to the training CSV."""
        row = {
            "timestamp":   record.timestamp,
            "instrument":  record.instrument,
            "direction":   record.direction,
            "strategy":    record.strategy,
            "regime":      record.regime,
            "confidence":  record.confidence,
            "entry_price": record.entry_price,
            "exit_price":  record.exit_price,
            "pnl_pct":     record.pnl_pct,
            "won":         int(record.won),
            **{f"feat_{k}": v for k, v in (record.features or {}).items()},
        }
        df = pd.DataFrame([row])
        if TRAINING_PATH.exists():
            df.to_csv(TRAINING_PATH, mode="a", header=False, index=False)
        else:
            df.to_csv(TRAINING_PATH, index=False)

    def load_training_records(self) -> List[TradeRecord]:
        """Load all stored trade records for retraining."""
        if not TRAINING_PATH.exists():
            return []
        df = pd.read_csv(TRAINING_PATH)
        records = []
        feat_cols = [c for c in df.columns if c.startswith("feat_")]
        for _, row in df.iterrows():
            feats = {c.replace("feat_", ""): row[c] for c in feat_cols}
            records.append(TradeRecord(
                timestamp=str(row.get("timestamp", "")),
                instrument=str(row.get("instrument", "")),
                direction=str(row.get("direction", "BUY")),
                strategy=str(row.get("strategy", "")),
                regime=str(row.get("regime", "unknown")),
                confidence=float(row.get("confidence", 0.5)),
                entry_price=float(row.get("entry_price", 0)),
                exit_price=float(row.get("exit_price", 0)),
                pnl_pct=float(row.get("pnl_pct", 0)),
                won=bool(row.get("won", 0)),
                features=feats,
            ))
        return records

    # ── Private helpers ──────────────────────────────────────────────────────

    def _predict_single(self, model, X: np.ndarray) -> float:
        if model is None:
            return 0.5
        try:
            return float(model.predict_proba(X)[0, 1])
        except Exception:
            return 0.5

    def _neutral_prediction(self) -> EnsemblePrediction:
        return EnsemblePrediction(
            probability=0.5,
            xgb_prob=0.5,
            rf_prob=0.5,
            meta_prob=0.5,
            confidence=0.0,
            model_agreement=0.0,
            features_used=0,
            trained_on=0,
            gate_pass=False,
            threshold=self.ml_threshold,
        )

    def _regime_encode(self, regime: str) -> float:
        return {
            "trending": 1.0, "ranging": 0.5,
            "volatile": 0.75, "breakout": 0.9,
        }.get(regime, 0.5)

    def _load_models(self):
        for path, attr, label in [
            (XGBOOST_PATH, "xgb_model",  "XGBoost"),
            (RF_PATH,      "rf_model",   "RandomForest"),
            (META_PATH,    "meta_model", "Meta-model"),
        ]:
            if path.exists():
                try:
                    setattr(self, attr, pickle.load(open(path, "rb")))
                    logger.info(f"✅ Loaded {label} from {path}")
                except Exception as e:
                    logger.warning(f"Could not load {label}: {e}")

        if TRAINING_PATH.exists():
            try:
                df = pd.read_csv(TRAINING_PATH)
                self.trained_on = len(df)
            except Exception:
                pass


# ── Self-Learning Scheduler ──────────────────────────────────────────────────

class SelfLearningScheduler:
    """
    Runs automated weekly model retraining.
    Reward = profit - drawdown_penalty (RL-style).
    """

    def __init__(self, ensemble: MLEnsemble, retrain_interval_days: int = 7):
        self.ensemble  = ensemble
        self.interval  = timedelta(days=retrain_interval_days)
        self.last_train: Optional[datetime] = None

    def should_retrain(self) -> bool:
        if self.last_train is None:
            return True
        return datetime.utcnow() - self.last_train >= self.interval

    def retrain_if_due(self) -> Optional[Dict]:
        if not self.should_retrain():
            return None

        logger.info("🔄 Self-Learning: scheduled retraining triggered")
        records = self.ensemble.load_training_records()

        # Apply RL-style reward weighting
        records = self._apply_rl_rewards(records)

        result = self.ensemble.train(records)
        if result.get("success"):
            self.last_train = datetime.utcnow()
        return result

    def _apply_rl_rewards(self, records: List[TradeRecord]) -> List[TradeRecord]:
        """
        Weight recent trades more heavily (recency bias).
        Penalise trades that contributed to drawdowns.
        """
        n = len(records)
        for i, rec in enumerate(records):
            recency_weight = (i + 1) / n          # older = lower weight
            drawdown_penalty = max(0.0, -rec.pnl_pct * 0.5)
            rec.confidence = float(np.clip(
                rec.confidence * recency_weight - drawdown_penalty, 0.01, 1.0
            ))
        return records


# ── Singletons ───────────────────────────────────────────────────────────────

_ensemble:  Optional[MLEnsemble]           = None
_scheduler: Optional[SelfLearningScheduler] = None

def get_ml_ensemble() -> MLEnsemble:
    global _ensemble
    if _ensemble is None:
        _ensemble = MLEnsemble()
    return _ensemble

def get_self_learning_scheduler() -> SelfLearningScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = SelfLearningScheduler(get_ml_ensemble())
    return _scheduler
