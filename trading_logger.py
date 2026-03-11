"""
APEX — Structured Trading Logger
Records every decision with full context:
instrument, strategy, AI model, confidence, ML probability,
execution result, PnL.

Creates a machine-readable audit trail for analysis and retraining.
"""
from __future__ import annotations
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

TRADE_LOG_FILE   = LOG_DIR / "trades.jsonl"
SIGNAL_LOG_FILE  = LOG_DIR / "signals.jsonl"
SYSTEM_LOG_FILE  = LOG_DIR / "system.jsonl"


class StructuredLogger:
    """
    Writes structured JSON log lines for every trading event.
    Each line is a valid JSON object — easy to parse with pandas or stream to a DB.
    """

    # ── Signal events ─────────────────────────────────────────────────────────

    def log_signal(
        self,
        instrument:    str,
        direction:     str,
        strategy:      str,
        confidence:    float,
        ml_probability: Optional[float],
        regime:        str,
        signal_score:  float,
        buy_votes:     int,
        sell_votes:    int,
        ai_model:      str = "",
        execution_decision: str = "HOLD",  # EXECUTE | HOLD | BLOCKED
        block_reason:  str = "",
    ):
        event = {
            "ts":         datetime.utcnow().isoformat(),
            "event":      "signal",
            "instrument": instrument,
            "direction":  direction,
            "strategy":   strategy,
            "confidence": round(confidence, 4),
            "ml_prob":    round(ml_probability, 4) if ml_probability is not None else None,
            "regime":     regime,
            "score":      round(signal_score, 4),
            "buy_votes":  buy_votes,
            "sell_votes": sell_votes,
            "ai_model":   ai_model,
            "decision":   execution_decision,
            "block_reason": block_reason,
        }
        self._write(SIGNAL_LOG_FILE, event)
        logger.info(
            f"📊 {instrument} {direction} | strat={strategy} conf={confidence:.2f} "
            f"ml={ml_probability:.2f if ml_probability else 'N/A'} "
            f"regime={regime} → {execution_decision}"
        )

    # ── Trade events ──────────────────────────────────────────────────────────

    def log_trade_open(
        self,
        trade_id:    str,
        instrument:  str,
        direction:   str,
        units:       float,
        entry_price: float,
        stop_loss:   float,
        take_profit: float,
        strategy:    str,
        ai_model:    str,
        confidence:  float,
        ml_prob:     Optional[float],
        regime:      str,
        balance:     float,
        risk_amount: float,
    ):
        event = {
            "ts":          datetime.utcnow().isoformat(),
            "event":       "trade_open",
            "trade_id":    trade_id,
            "instrument":  instrument,
            "direction":   direction,
            "units":       units,
            "entry_price": entry_price,
            "stop_loss":   stop_loss,
            "take_profit": take_profit,
            "strategy":    strategy,
            "ai_model":    ai_model,
            "confidence":  round(confidence, 4),
            "ml_prob":     round(ml_prob, 4) if ml_prob is not None else None,
            "regime":      regime,
            "balance":     round(balance, 2),
            "risk_amount": round(risk_amount, 2),
        }
        self._write(TRADE_LOG_FILE, event)
        logger.info(
            f"📈 OPEN {direction} {units} {instrument} @ {entry_price:.5f} "
            f"SL={stop_loss:.5f} TP={take_profit:.5f} | {strategy}"
        )

    def log_trade_close(
        self,
        trade_id:    str,
        instrument:  str,
        direction:   str,
        units:       float,
        entry_price: float,
        exit_price:  float,
        pnl:         float,
        pnl_pct:     float,
        strategy:    str,
        close_reason: str,
        duration_min: float,
        balance:     float,
    ):
        won = pnl > 0
        event = {
            "ts":           datetime.utcnow().isoformat(),
            "event":        "trade_close",
            "trade_id":     trade_id,
            "instrument":   instrument,
            "direction":    direction,
            "units":        units,
            "entry_price":  entry_price,
            "exit_price":   exit_price,
            "pnl":          round(pnl, 2),
            "pnl_pct":      round(pnl_pct, 4),
            "won":          won,
            "strategy":     strategy,
            "close_reason": close_reason,
            "duration_min": round(duration_min, 1),
            "balance":      round(balance, 2),
        }
        self._write(TRADE_LOG_FILE, event)
        icon = "✅" if won else "❌"
        logger.info(
            f"{icon} CLOSE {instrument} @ {exit_price:.5f} "
            f"PnL={pnl:+.2f} ({pnl_pct:+.2%}) | {close_reason}"
        )

    # ── System events ─────────────────────────────────────────────────────────

    def log_risk_event(self, event_type: str, details: Dict[str, Any]):
        event = {
            "ts":    datetime.utcnow().isoformat(),
            "event": f"risk_{event_type}",
            **details,
        }
        self._write(SYSTEM_LOG_FILE, event)
        logger.warning(f"🚨 RISK EVENT [{event_type}]: {details}")

    def log_ml_retrain(self, result: Dict[str, Any]):
        event = {
            "ts":    datetime.utcnow().isoformat(),
            "event": "ml_retrain",
            **result,
        }
        self._write(SYSTEM_LOG_FILE, event)
        logger.info(f"🤖 ML RETRAIN: {result}")

    def log_regime_change(
        self, instrument: str, old_regime: str, new_regime: str, confidence: float
    ):
        event = {
            "ts":         datetime.utcnow().isoformat(),
            "event":      "regime_change",
            "instrument": instrument,
            "from":       old_regime,
            "to":         new_regime,
            "confidence": round(confidence, 3),
        }
        self._write(SYSTEM_LOG_FILE, event)
        logger.info(f"🔄 REGIME: {instrument} {old_regime} → {new_regime} ({confidence:.2f})")

    # ── Query helpers ─────────────────────────────────────────────────────────

    def read_recent_trades(self, n: int = 100) -> list:
        """Read the last N trade events from the log."""
        return self._read_tail(TRADE_LOG_FILE, n, event_types={"trade_open", "trade_close"})

    def read_recent_signals(self, n: int = 200) -> list:
        return self._read_tail(SIGNAL_LOG_FILE, n)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _write(self, path: Path, event: Dict):
        try:
            with open(path, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.error(f"Log write failed: {e}")

    def _read_tail(self, path: Path, n: int, event_types: Optional[set] = None) -> list:
        if not path.exists():
            return []
        records = []
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        if event_types is None or obj.get("event") in event_types:
                            records.append(obj)
                    except Exception:
                        pass
        except Exception as e:
            logger.error(f"Log read failed: {e}")
        return records[-n:]


# ── Singleton ─────────────────────────────────────────────────────────────────

_trading_logger: Optional[StructuredLogger] = None

def get_trading_logger() -> StructuredLogger:
    global _trading_logger
    if _trading_logger is None:
        _trading_logger = StructuredLogger()
    return _trading_logger
