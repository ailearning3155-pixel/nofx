"""
APEX — Central Risk Engine  (Implementation Guide Item 1 + 12)
Central gatekeeper between strategy signals and execution.
Every signal must pass through here before reaching the broker.
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Tuple
from loguru import logger


@dataclass
class TradeSignal:
    """Standardised signal object produced by strategies — never executes directly."""
    instrument:  str
    direction:   str           # BUY | SELL
    confidence:  float         # 0.0 – 1.0
    strategy:    str
    entry_price: Optional[float] = None
    stop_loss:   Optional[float] = None
    take_profit: Optional[float] = None
    atr:         Optional[float] = None
    units:       Optional[int]   = None


@dataclass
class RiskDecision:
    approved:    bool
    reason:      str
    units:       int   = 0
    risk_pct:    float = 0.0
    risk_amount: float = 0.0


class RiskEngine:
    """
    Central risk engine — single authority over trade approval.
    Implementation guide items: 1 (risk engine), 2 (decoupling), 12 (kill switch).
    """

    def __init__(self):
        self.peak_balance:       float = 0.0
        self.current_balance:    float = 0.0
        self.daily_pnl:          float = 0.0
        self.daily_trades:       int   = 0
        self.open_trade_count:   int   = 0
        self.kill_switch_active: bool  = False
        self.kill_switch_reason: str   = ""
        self.kill_switch_time:   Optional[datetime] = None
        self.max_drawdown_pct    = 15.0
        self.max_daily_loss_pct  = 3.0
        self.max_open_trades     = 3
        self.risk_per_trade_pct  = 1.0

    def validate(self, signal: TradeSignal) -> RiskDecision:
        """Full risk validation pipeline — single entry point."""
        if self.kill_switch_active:
            return RiskDecision(False, f"Kill switch active: {self.kill_switch_reason}")
        if self.open_trade_count >= self.max_open_trades:
            return RiskDecision(False, f"Max {self.max_open_trades} open trades reached")
        # Drawdown kill switch (item 12)
        if self.current_balance > 0 and self.peak_balance > 0:
            drawdown = (self.peak_balance - self.current_balance) / self.peak_balance * 100
            if drawdown >= self.max_drawdown_pct:
                self._activate_kill_switch(f"Drawdown {drawdown:.1f}% ≥ {self.max_drawdown_pct}%")
                return RiskDecision(False, f"Kill switch: drawdown {drawdown:.1f}%")
        # Daily loss
        if self.current_balance > 0 and self.daily_pnl < 0:
            daily_loss_pct = abs(self.daily_pnl) / self.current_balance * 100
            if daily_loss_pct >= self.max_daily_loss_pct:
                self._activate_kill_switch(f"Daily loss {daily_loss_pct:.1f}%")
                return RiskDecision(False, "Daily loss limit exceeded")
        # Exposure check (item 3)
        try:
            from core.risk.exposure_manager import get_exposure_manager
            ok, reason = get_exposure_manager().check(signal.instrument, signal.direction)
            if not ok:
                return RiskDecision(False, f"Exposure: {reason}")
        except Exception: pass
        # Correlation check (item 4)
        try:
            from core.risk.correlation_manager import get_correlation_manager
            ok, reason = get_correlation_manager().check(signal.instrument)
            if not ok:
                return RiskDecision(False, f"Correlation: {reason}")
        except Exception: pass
        # Size position
        units, risk_pct, risk_amount = self._size_position(signal)
        if units <= 0:
            return RiskDecision(False, "Position size zero — insufficient balance or SL too tight")
        signal.units = units
        logger.info(f"✅ Risk approved: {signal.instrument} {signal.direction} units={units:,} risk={risk_pct:.2f}%")
        return RiskDecision(True, "All risk checks passed", units, risk_pct, risk_amount)

    def _size_position(self, signal: TradeSignal) -> Tuple[int, float, float]:
        if not self.current_balance:
            return 0, 0, 0
        risk_amount = self.current_balance * (self.risk_per_trade_pct / 100)
        if signal.stop_loss and signal.entry_price:
            sl_dist = abs(signal.entry_price - signal.stop_loss)
        elif signal.atr:
            sl_dist = signal.atr * 1.5
        else:
            sl_dist = signal.entry_price * 0.005 if signal.entry_price else 0
        if sl_dist <= 0:
            return 0, 0, 0
        units = int(risk_amount / sl_dist)
        units = max(1000, (units // 1000) * 1000)
        return units, self.risk_per_trade_pct, risk_amount

    def update_balance(self, balance: float):
        self.current_balance = balance
        if balance > self.peak_balance:
            self.peak_balance = balance

    def record_trade_open(self):
        self.open_trade_count += 1
        self.daily_trades += 1

    def record_trade_close(self, pnl: float):
        self.open_trade_count = max(0, self.open_trade_count - 1)
        self.daily_pnl += pnl

    def _activate_kill_switch(self, reason: str):
        self.kill_switch_active = True
        self.kill_switch_reason = reason
        self.kill_switch_time   = datetime.utcnow()
        logger.critical(f"🚨 KILL SWITCH ACTIVATED: {reason}")

    def activate_kill_switch(self, reason: str = "Manual"):
        self._activate_kill_switch(reason)

    def deactivate_kill_switch(self):
        self.kill_switch_active = False
        self.kill_switch_reason = ""
        self.kill_switch_time   = None
        logger.warning("⚠️  Kill switch deactivated")

    def get_status(self) -> Dict:
        drawdown = 0.0
        if self.peak_balance > 0 and self.current_balance > 0:
            drawdown = (self.peak_balance - self.current_balance) / self.peak_balance * 100
        return {
            "kill_switch_active":   self.kill_switch_active,
            "kill_switch_reason":   self.kill_switch_reason,
            "kill_switch_time":     self.kill_switch_time.isoformat() if self.kill_switch_time else None,
            "current_balance":      self.current_balance,
            "peak_balance":         self.peak_balance,
            "current_drawdown_pct": round(drawdown, 2),
            "daily_pnl":            self.daily_pnl,
            "daily_trades":         self.daily_trades,
            "open_trade_count":     self.open_trade_count,
            "max_drawdown_pct":     self.max_drawdown_pct,
            "max_daily_loss_pct":   self.max_daily_loss_pct,
            "max_open_trades":      self.max_open_trades,
            "risk_per_trade_pct":   self.risk_per_trade_pct,
        }


_engine: Optional[RiskEngine] = None

def get_risk_engine() -> RiskEngine:
    global _engine
    if _engine is None:
        _engine = RiskEngine()
    return _engine
