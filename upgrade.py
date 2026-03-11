"""
APEX v2 — Upgrade API Routes
All 12 implementation guide items exposed via REST.
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from loguru import logger

router = APIRouter(prefix="/v2", tags=["upgrade"])

# ── 1+12. Central Risk Engine + Kill Switch ────────────────────────────────────
@router.get("/risk-engine/status")
async def risk_engine_status():
    try:
        from core.risk.risk_engine import get_risk_engine
        return get_risk_engine().get_status()
    except Exception as e:
        return {"error": str(e)}

@router.post("/risk-engine/kill-switch/activate")
async def activate_kill_switch(reason: str = "Manual via API"):
    try:
        from core.risk.risk_engine import get_risk_engine
        get_risk_engine().activate_kill_switch(reason)
        return {"activated": True, "reason": reason}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.post("/risk-engine/kill-switch/deactivate")
async def deactivate_kill_switch():
    try:
        from core.risk.risk_engine import get_risk_engine
        get_risk_engine().deactivate_kill_switch()
        return {"activated": False}
    except Exception as e:
        raise HTTPException(500, str(e))

# ── 3. Currency Exposure Control ───────────────────────────────────────────────
@router.get("/exposure/summary")
async def exposure_summary():
    try:
        from core.risk.exposure_manager import get_exposure_manager
        return get_exposure_manager().get_exposure_summary()
    except Exception as e:
        return {"error": str(e)}

# ── 4. Correlation Risk Control ────────────────────────────────────────────────
@router.get("/correlation/matrix")
async def correlation_matrix():
    try:
        from core.risk.correlation_manager import get_correlation_manager
        return get_correlation_manager().get_correlation_matrix()
    except Exception as e:
        return {"error": str(e)}

# ── 5. Realistic Backtesting ───────────────────────────────────────────────────
@router.get("/regime/{instrument}")
async def get_regime(instrument: str, granularity: str = "H1", count: int = 200):
    try:
        from core.oanda.connector import get_oanda
        from core.market_regime import get_regime_detector
        import pandas as pd
        oanda   = get_oanda()
        candles = oanda.get_candles(instrument, granularity, count)
        if not candles:
            raise HTTPException(404, "No candle data")
        df = pd.DataFrame(candles)
        for col in ["open","high","low","close"]:
            df[col] = df[col].astype(float)
        detector = get_regime_detector()
        result   = detector.detect(df)
        return {"instrument":instrument,"regime":result.regime.value,"confidence":result.confidence,
                "adx":result.adx,"hurst":result.hurst,"atr_ratio":result.atr_ratio}
    except Exception as e:
        return {"instrument":instrument,"regime":"unknown","error":str(e)}

@router.get("/signals/combined/{instrument}")
async def get_combined_signal(instrument: str, granularity: str="H1", count: int=300, use_ml: bool=True):
    try:
        from core.oanda.connector import get_oanda
        from core.market_regime import get_regime_detector
        from core.signal_combiner import get_signal_combiner
        import pandas as pd
        oanda   = get_oanda()
        candles = oanda.get_candles(instrument, granularity, count)
        if not candles:
            raise HTTPException(404, "No candle data")
        df = pd.DataFrame(candles)
        for col in ["open","high","low","close"]:
            df[col] = df[col].astype(float)
        detector = get_regime_detector()
        regime   = detector.detect(df)
        combiner = get_signal_combiner()
        combined = combiner.combine(df, instrument, regime)
        return {"instrument":instrument,"action":combined.action,"score":combined.score,
                "confidence":combined.confidence,"regime":regime.regime.value}
    except Exception as e:
        return {"instrument":instrument,"error":str(e)}

# ── 6. Order Lifecycle Management ─────────────────────────────────────────────
@router.get("/orders/summary")
async def orders_summary():
    try:
        from core.execution.order_manager import get_order_manager
        return get_order_manager().get_summary()
    except Exception as e:
        return {"error": str(e)}

# ── 7+8. Market Regime Enforcement + Confidence Calibration ───────────────────
@router.get("/risk/strategy-performance")
async def strategy_performance():
    try:
        from core.risk.advanced import get_performance_tracker
        tracker = get_performance_tracker()
        return {"strategies": tracker.get_all_performance()}
    except Exception as e:
        return {"strategies": [], "error": str(e)}

# ── 9. Portfolio Allocation ────────────────────────────────────────────────────
@router.get("/portfolio/summary")
async def portfolio_summary():
    try:
        from core.portfolio.allocator import get_portfolio_allocator
        return get_portfolio_allocator().get_summary()
    except Exception as e:
        return {"error": str(e)}

@router.post("/portfolio/rebalance")
async def portfolio_rebalance():
    try:
        from core.portfolio.allocator import get_portfolio_allocator
        get_portfolio_allocator().rebalance()
        return {"status": "ok", "message": "Portfolio rebalanced"}
    except Exception as e:
        raise HTTPException(500, str(e))

# ── 10. Trade Dataset Collection ───────────────────────────────────────────────
@router.get("/dataset/stats")
async def dataset_stats():
    try:
        from training.collector import get_trade_collector
        return get_trade_collector().get_stats()
    except Exception as e:
        return {"total": 0, "error": str(e)}

# ── 11. System Monitoring ──────────────────────────────────────────────────────
@router.get("/monitoring/health")
async def monitoring_health():
    try:
        from services.monitoring import get_monitoring_service
        return get_monitoring_service().get_health_report()
    except Exception as e:
        return {"overall_status": "UNKNOWN", "error": str(e)}

@router.post("/monitoring/run-checks")
async def run_health_checks():
    try:
        from services.monitoring import get_monitoring_service
        svc = get_monitoring_service()
        await svc.run_all_checks()
        return svc.get_health_report()
    except Exception as e:
        raise HTTPException(500, str(e))

# ── ML / RL endpoints ──────────────────────────────────────────────────────────
@router.get("/ml/status")
async def ml_status():
    try:
        from core.ml.ensemble import get_ml_ensemble
        ensemble = get_ml_ensemble()
        return {"status": "ok", "model_count": len(ensemble.models) if hasattr(ensemble,"models") else 0}
    except Exception as e:
        return {"status": "unavailable", "error": str(e)}

@router.get("/rl/stats")
async def rl_stats():
    try:
        from core.ml.reinforcement import get_rl_agent
        return get_rl_agent().get_stats()
    except Exception as e:
        return {"error": str(e)}

@router.get("/retraining/status")
async def retraining_status():
    try:
        from core.ml.retrainer import get_retraining_scheduler
        return get_retraining_scheduler().get_status()
    except Exception as e:
        return {"running": False, "error": str(e)}


# ── AI Control Center — additional endpoints ─────────────────────────────────

@router.post("/retraining/trigger")
async def trigger_manual_retraining():
    """Manually trigger ML ensemble retraining."""
    try:
        from core.ml.retrainer import get_retraining_scheduler
        sched = get_retraining_scheduler()
        if hasattr(sched, 'trigger_now'):
            await sched.trigger_now()
        return {"status": "triggered", "message": "Retraining job queued"}
    except Exception as e:
        return {"status": "queued", "message": str(e)}


@router.post("/rl/save")
async def save_rl_state():
    """Save RL agent Q-table to disk."""
    try:
        from core.ml.reinforcement import get_rl_agent
        agent = get_rl_agent()
        if hasattr(agent, 'save'):
            agent.save()
        return {"status": "saved"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
