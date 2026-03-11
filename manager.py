"""APEX — Risk Manager"""
from loguru import logger
from config.settings import settings


class RiskManager:
    def __init__(self):
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.peak_balance = 0.0
        self.current_balance = 0.0
        self.kill_switch_active = False
        self.kill_switch_reason = ""
        self.max_daily_loss_pct = settings.trading.max_daily_loss_pct
        self.max_drawdown_pct   = settings.trading.max_drawdown_pct
        self.max_open_trades    = settings.trading.max_open_trades
        self.risk_per_trade     = settings.trading.risk_per_trade_pct

    def check_trade(self, instrument: str, direction: str, open_trade_count: int = 0) -> dict:
        if self.kill_switch_active:
            return {"approved": False, "reason": f"Kill switch active: {self.kill_switch_reason}"}
        if open_trade_count >= self.max_open_trades:
            return {"approved": False, "reason": f"Max {self.max_open_trades} open trades reached"}
        if self.current_balance > 0 and self.peak_balance > 0:
            drawdown = (self.peak_balance - self.current_balance) / self.peak_balance * 100
            if drawdown >= self.max_drawdown_pct:
                self.activate_kill_switch(f"Max drawdown {drawdown:.1f}% hit")
                return {"approved": False, "reason": f"Max drawdown exceeded: {drawdown:.1f}%"}
        if self.current_balance > 0:
            daily_loss_pct = abs(self.daily_pnl) / self.current_balance * 100
            if self.daily_pnl < 0 and daily_loss_pct >= self.max_daily_loss_pct:
                self.activate_kill_switch(f"Daily loss limit {daily_loss_pct:.1f}% hit")
                return {"approved": False, "reason": f"Daily loss limit exceeded: {daily_loss_pct:.1f}%"}
        return {"approved": True, "reason": "Risk checks passed"}

    def activate_kill_switch(self, reason: str = "Manual"):
        self.kill_switch_active = True
        self.kill_switch_reason = reason
        logger.critical(f"🚨 KILL SWITCH ACTIVATED: {reason}")

    def deactivate_kill_switch(self):
        self.kill_switch_active = False
        self.kill_switch_reason = ""
        logger.warning("Kill switch deactivated")

    def get_status(self) -> dict:
        return {
            "kill_switch_active":  self.kill_switch_active,
            "kill_switch_reason":  self.kill_switch_reason,
            "daily_pnl":           self.daily_pnl,
            "daily_trades":        self.daily_trades,
            "current_balance":     self.current_balance,
            "peak_balance":        self.peak_balance,
            "max_daily_loss_pct":  self.max_daily_loss_pct,
            "max_drawdown_pct":    self.max_drawdown_pct,
            "max_open_trades":     self.max_open_trades,
            "risk_per_trade":      self.risk_per_trade,
        }
