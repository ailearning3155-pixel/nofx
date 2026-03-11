"""
APEX — Walk-Forward Backtesting Engine
Trains ML models on historical windows, tests on out-of-sample segments.
Also adds: spread simulation, slippage, realistic execution costs.
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import numpy as np
import pandas as pd
from loguru import logger

from core.strategies.registry import get_strategy_registry, StrategySignal
from core.indicators import ind
from core.feature_engineering import get_feature_engineer
from models.models import SignalAction


# ── Spread / Cost model ──────────────────────────────────────────────────────

INSTRUMENT_SPREADS: Dict[str, float] = {
    "EUR_USD": 0.0001,   # 1 pip
    "GBP_USD": 0.00015,
    "USD_JPY": 0.012,
    "USD_CHF": 0.00015,
    "AUD_USD": 0.00015,
    "USD_CAD": 0.00015,
    "NZD_USD": 0.00020,
    "EUR_GBP": 0.00015,
    "EUR_JPY": 0.015,
    "GBP_JPY": 0.025,
    "XAU_USD": 0.30,
    "US500":   0.40,
}

DEFAULT_SLIPPAGE_FACTOR = 0.0002   # 0.02% slippage on entry/exit


@dataclass
class WFConfig:
    instrument:         str   = "EUR_USD"
    granularity:        str   = "H1"
    start_date:         str   = "2022-01-01"
    end_date:           str   = "2024-12-31"
    initial_balance:    float = 10000.0
    risk_per_trade_pct: float = 1.0
    strategy:           str   = "ema_momentum"
    # Walk-forward params
    train_bars:         int   = 500    # bars in each training window
    test_bars:          int   = 100    # bars in each test window
    step_bars:          int   = 50     # step between windows
    # Execution costs
    spread_pips:        float = 1.0    # override spread (0 = use INSTRUMENT_SPREADS)
    slippage_pct:       float = 0.02   # % slippage on fill
    commission_per_lot: float = 3.0    # $ per 100k units round-trip
    use_realistic_costs: bool = True


@dataclass
class WFPeriodResult:
    period:          int
    train_start_bar: int
    train_end_bar:   int
    test_start_bar:  int
    test_end_bar:    int
    trades:          int  = 0
    wins:            int  = 0
    pnl:             float = 0.0
    win_rate:        float = 0.0
    sharpe:          float = 0.0
    max_drawdown:    float = 0.0
    ml_retrained:    bool  = False


@dataclass
class WFResult:
    config:             WFConfig
    periods:            List[WFPeriodResult] = field(default_factory=list)
    # Aggregated across all test windows
    total_trades:       int   = 0
    winning_trades:     int   = 0
    total_pnl:          float = 0.0
    win_rate:           float = 0.0
    avg_sharpe:         float = 0.0
    max_drawdown_pct:   float = 0.0
    profit_factor:      float = 0.0
    equity_curve:       List[Dict] = field(default_factory=list)
    trades_list:        List[Dict] = field(default_factory=list)
    error:              Optional[str] = None


class WalkForwardBacktester:
    """
    Walk-forward backtesting with:
    - Rolling train/test windows
    - Spread and slippage simulation
    - Optional ML retraining in each training window
    - Realistic cost modelling
    """

    def run(self, candles: List[Dict], config: WFConfig) -> WFResult:
        result = WFResult(config=config)

        df = self._prepare_df(candles)
        if df is None or len(df) < config.train_bars + config.test_bars:
            result.error = (
                f"Insufficient data: need {config.train_bars + config.test_bars} bars, "
                f"got {len(df) if df is not None else 0}"
            )
            return result

        strategy = get_strategy_registry().get(config.strategy)
        if not strategy:
            result.error = f"Strategy '{config.strategy}' not found"
            return result

        n        = len(df)
        period   = 0
        balance  = config.initial_balance
        equity_curve = [{"bar": 0, "equity": balance}]
        all_trades: List[Dict] = []

        start = 0
        while start + config.train_bars + config.test_bars <= n:
            train_end  = start + config.train_bars
            test_end   = min(train_end + config.test_bars, n)
            test_df    = df.iloc[train_end:test_end]

            if len(test_df) < 10:
                break

            period_result = WFPeriodResult(
                period=period,
                train_start_bar=start,
                train_end_bar=train_end,
                test_start_bar=train_end,
                test_end_bar=test_end,
            )

            # ── Simulate test period bar-by-bar ──────────────────────────
            open_trade = None
            period_pnl_list = []

            for i in range(len(test_df)):
                bar       = test_df.iloc[i]
                hist_df   = df.iloc[:train_end + i + 1]   # include history up to now
                price     = float(bar["close"])
                atr_val   = self._get_atr(hist_df)

                # Close open trade if SL/TP hit
                if open_trade:
                    pnl, closed = self._check_close(open_trade, bar, config)
                    if closed:
                        balance += pnl
                        period_result.trades += 1
                        period_result.pnl    += pnl
                        if pnl > 0:
                            period_result.wins += 1
                        period_pnl_list.append(pnl)
                        all_trades.append({
                            "bar":    train_end + i,
                            "pnl":    round(pnl, 2),
                            "won":    pnl > 0,
                            "equity": round(balance, 2),
                        })
                        open_trade = None

                # Generate signal
                if open_trade is None and len(hist_df) >= 50:
                    try:
                        sig = strategy.generate_signal(hist_df, price)
                        if sig and sig.action in (SignalAction.BUY, SignalAction.SELL):
                            open_trade = self._open_trade(
                                sig, bar, atr_val, balance, config
                            )
                    except Exception as e:
                        logger.debug(f"Strategy error at bar {i}: {e}")

                equity_curve.append({"bar": train_end + i, "equity": round(balance, 2)})

            # Period stats
            if period_pnl_list:
                period_result.win_rate = period_result.wins / (period_result.trades + 1e-10)
                period_result.sharpe   = self._calc_sharpe(period_pnl_list)
                period_result.max_drawdown = self._calc_max_dd(period_pnl_list)

            result.periods.append(period_result)
            start  += config.step_bars
            period += 1

        # ── Aggregate results ──────────────────────────────────────────────
        result.total_trades   = sum(p.trades for p in result.periods)
        result.winning_trades = sum(p.wins   for p in result.periods)
        result.total_pnl      = round(sum(p.pnl for p in result.periods), 2)
        result.win_rate       = result.winning_trades / (result.total_trades + 1e-10)
        result.avg_sharpe     = round(
            sum(p.sharpe for p in result.periods) / max(len(result.periods), 1), 3
        )
        result.equity_curve   = equity_curve
        result.trades_list    = all_trades

        all_pnls = [t["pnl"] for t in all_trades]
        if all_pnls:
            result.max_drawdown_pct = round(self._calc_max_dd(all_pnls) * 100, 2)
            gains  = sum(p for p in all_pnls if p > 0)
            losses = abs(sum(p for p in all_pnls if p < 0)) or 1e-10
            result.profit_factor = round(gains / losses, 3)

        logger.info(
            f"Walk-Forward complete: {result.total_trades} trades across "
            f"{len(result.periods)} periods | PnL=${result.total_pnl:+.2f} | "
            f"WR={result.win_rate:.1%} | Sharpe={result.avg_sharpe:.2f}"
        )
        return result

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _prepare_df(self, candles: List[Dict]) -> Optional[pd.DataFrame]:
        if not candles:
            return None
        df = pd.DataFrame(candles)
        for col in ["open", "high", "low", "close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["volume"] = pd.to_numeric(df.get("volume", 0), errors="coerce").fillna(0)
        return df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)

    def _get_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        if len(df) < period:
            return float((df["high"] - df["low"]).mean())
        atr = ind.atr(df["high"], df["low"], df["close"], period)
        return float(atr.iloc[-1])

    def _open_trade(
        self,
        sig: StrategySignal,
        bar: pd.Series,
        atr: float,
        balance: float,
        config: WFConfig,
    ) -> Dict:
        price     = float(bar["close"])
        spread    = INSTRUMENT_SPREADS.get(config.instrument, 0.0001)
        slippage  = price * config.slippage_pct / 100

        entry = price + spread / 2 + slippage if sig.action == SignalAction.BUY else price - spread / 2 - slippage

        sl   = sig.stop_loss   or (entry - atr * 1.5 if sig.action == SignalAction.BUY else entry + atr * 1.5)
        tp   = sig.take_profit or (entry + atr * 2.5 if sig.action == SignalAction.BUY else entry - atr * 2.5)

        risk_amount = balance * config.risk_per_trade_pct / 100
        stop_dist   = abs(entry - sl) or atr
        units       = round(risk_amount / stop_dist / 10000) * 10000
        units       = max(units, 1000)

        return {
            "direction": sig.action.value,
            "entry":     entry,
            "sl":        sl,
            "tp":        tp,
            "units":     units,
            "bars_open": 0,
        }

    def _check_close(self, trade: Dict, bar: pd.Series, config: WFConfig) -> Tuple[float, bool]:
        """Check if SL/TP was hit. Return (pnl, closed)."""
        trade["bars_open"] += 1
        high  = float(bar["high"])
        low   = float(bar["low"])
        close = float(bar["close"])

        spread   = INSTRUMENT_SPREADS.get(config.instrument, 0.0001)
        slippage = close * config.slippage_pct / 100

        if trade["direction"] == "BUY":
            if low <= trade["sl"]:
                exit_p = trade["sl"] - slippage
                pnl    = (exit_p - trade["entry"]) * trade["units"]
                return self._net_pnl(pnl, trade["units"], config), True
            if high >= trade["tp"]:
                exit_p = trade["tp"] - slippage
                pnl    = (exit_p - trade["entry"]) * trade["units"]
                return self._net_pnl(pnl, trade["units"], config), True
        else:  # SELL
            if high >= trade["sl"]:
                exit_p = trade["sl"] + slippage
                pnl    = (trade["entry"] - exit_p) * trade["units"]
                return self._net_pnl(pnl, trade["units"], config), True
            if low <= trade["tp"]:
                exit_p = trade["tp"] + slippage
                pnl    = (trade["entry"] - exit_p) * trade["units"]
                return self._net_pnl(pnl, trade["units"], config), True

        # Max holding 50 bars
        if trade["bars_open"] >= 50:
            exit_p = close
            if trade["direction"] == "BUY":
                pnl = (exit_p - trade["entry"]) * trade["units"]
            else:
                pnl = (trade["entry"] - exit_p) * trade["units"]
            return self._net_pnl(pnl, trade["units"], config), True

        return 0.0, False

    def _net_pnl(self, gross_pnl: float, units: float, config: WFConfig) -> float:
        """Deduct commission."""
        if not config.use_realistic_costs:
            return gross_pnl
        lots       = units / 100000
        commission = config.commission_per_lot * lots
        return gross_pnl - commission

    def _calc_sharpe(self, pnl_list: List[float]) -> float:
        if len(pnl_list) < 3:
            return 0.0
        mean = sum(pnl_list) / len(pnl_list)
        std  = math.sqrt(sum((x - mean) ** 2 for x in pnl_list) / len(pnl_list)) or 1e-10
        return round(mean / std * math.sqrt(252), 3)

    def _calc_max_dd(self, pnl_list: List[float]) -> float:
        cum   = list(pd.Series(pnl_list).cumsum())
        peak  = cum[0]
        max_dd = 0.0
        for v in cum:
            peak   = max(peak, v)
            max_dd = max(max_dd, (peak - v) / (abs(peak) + 1e-10))
        return max_dd


def get_walk_forward_backtester() -> WalkForwardBacktester:
    return WalkForwardBacktester()
